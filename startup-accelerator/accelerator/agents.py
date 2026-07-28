"""The four graph nodes: three founder-facing agents plus the critique step.

Each node is a plain function `(state) -> partial state`. They share a shape:

    1. work out which *mode* it is running in (initial / refine / revisit)
    2. gather context — vector memory, and web search where the role warrants it
    3. call the LLM with `with_structured_output(...)` so the result is a typed object
    4. log what it produced and who it hands off to
    5. return the slice of state it owns

Roles are scoped so they do not overlap, and the system prompts say so explicitly —
each one carries a "you do NOT" clause. Without it the Research Agent volunteers
funding advice and the Funding Advisor re-derives market facts, which makes the
handoffs meaningless and the trace impossible to attribute.

Three modes exist because of the feedback loop:

* **initial** — first pass, no prior output.
* **refine** — the Critique Agent routed gaps to *this* agent; it receives its own
  previous brief plus the specific requests, and improves rather than restarts.
* **revisit** — an upstream agent was revised, so this agent's input changed; it
  reconciles its existing brief with the new upstream findings.
"""

from __future__ import annotations

from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from .config import get_llm
from .state import (
    AcceleratorState,
    Critique,
    FundingBrief,
    Gap,
    PitchOutline,
    ResearchBrief,
)
from .tools import search_memory, web_search
from .tracing import logger, traced


def _gaps_for(state: AcceleratorState, agent: str) -> list[Gap]:
    return [g for g in state.get("pending_gaps", []) if g.target_agent == agent]


def _mode(state: AcceleratorState, agent: str, brief_key: str) -> tuple[str, list[Gap]]:
    """Classify this invocation. See the module docstring for what each mode means."""
    gaps = _gaps_for(state, agent)
    if gaps:
        return "refine", gaps
    if state.get(brief_key) is not None:
        return "revisit", []
    return "initial", []


def _gap_block(gaps: list[Gap]) -> str:
    return "\n".join(
        f"- [{g.severity}] {g.field}: {g.request}" for g in gaps
    ) or "(none)"


def _review_context(state: AcceleratorState) -> str:
    """The reviewer's verdict, rendered for whichever agent is being asked to redo work.

    Without this, a revision round only reached the agent whose gaps were routed —
    the Pitch Coach would rebuild its outline from improved briefs while still blind
    to what the reviewer actually objected to, and the score would not move.
    """
    critique = state.get("critique")
    if critique is None:
        return ""
    return (
        "\n\nTHE REVIEWER SCORED THE LAST OUTLINE "
        f"{critique.score}/10 (verdict: {critique.verdict}).\n"
        f"Reasoning: {critique.rationale}\n"
        f"Everything the reviewer flagged, across all agents:\n{_gap_block(critique.gaps)}"
    )


def _invoke(model_cls, system: str, human: str, temperature: float = 0.3):
    """One structured LLM call. Kept in one place so every agent uses the same path."""
    llm = get_llm(temperature)
    return llm.with_structured_output(model_cls).invoke(
        [SystemMessage(content=system), HumanMessage(content=human)]
    )


# --------------------------------------------------------------------------- #
# 1. Research Agent — market facts
# --------------------------------------------------------------------------- #

RESEARCH_SYSTEM = """You are the Research Agent on a startup accelerator's support team.

YOUR REMIT: market trends, market sizing, the competitive set, customer pain points, \
and timing signals for a given startup domain.

YOU DO NOT: recommend funding programmes, grants or investors — that is the Funding \
Advisor's job. You do not write slides or narrative — that is the Pitch Coach's job. \
Stay inside your remit; the value of this team depends on clean handoffs.

HOW YOU WORK:
- Ground every claim. Each trend carries an `evidence` field: a source URL, a memory \
corpus filename, or the literal 'model-knowledge' when you are working from priors.
- Size markets bottom-up, showing the arithmetic. Never write "the global market is \
$N billion and we need 1%" — that is the failure mode this accelerator screens for.
- Name real competitors, including the status quo and incumbents' internal tooling.
- A timing signal must be dated and specific. "AI is improving" is not one.
- Put anything you could not establish in `open_questions`. The Pitch Coach depends on \
that honesty — a silent gap becomes an indefensible slide."""


@traced("ResearchAgent")
def research_node(state: AcceleratorState) -> dict[str, Any]:
    log = logger()
    domain, stage = state["domain"], state["stage"]
    rnd = state.get("revision_round", 0)
    mode, gaps = _mode(state, "research", "research_brief")

    log.log(
        "node_start",
        node="research",
        revision_round=rnd,
        mode=mode,
        note=f"Investigating the {domain} market for a {stage} startup.",
    )

    memory_query = f"market sizing competitive analysis timing signals for {domain} startups"
    if mode == "refine":
        memory_query += " " + " ".join(g.field for g in gaps)
    hits, memory_context = search_memory(memory_query, node="research", revision_round=rnd)

    if state.get("use_web", True):
        queries = [
            f"{domain} market size 2026 analysis",
            f"{domain} startup funding rounds and new entrants 2026",
            f"{domain} customer pain points and regulation changes 2026",
        ]
        if mode == "refine":
            queries = [f"{domain} {g.request}" for g in gaps][:3] or queries
        web_context = web_search(queries, node="research", revision_round=rnd)
    else:
        web_context = "(web search disabled for this run)"

    prior = ""
    if mode == "refine":
        brief: ResearchBrief = state["research_brief"]
        prior = (
            _review_context(state)
            + "\n\nYOUR PREVIOUS BRIEF (improve it — keep what is good, fix what is flagged):\n"
            f"{brief.model_dump_json(indent=2)}\n\n"
            "GAPS ROUTED SPECIFICALLY TO YOU:\n"
            f"{_gap_block(gaps)}\n\n"
            "Address every one of them concretely — a new figure, a new named competitor, "
            "a dated signal. Restating what you already had counts as failing to address it."
        )

    human = (
        f"Startup domain: {domain}\nFounder stage: {stage}\n\n"
        f"ACCELERATOR MEMORY (method guidance and any prior briefs on related domains):\n{memory_context}\n\n"
        f"LIVE WEB RESEARCH:\n{web_context}{prior}\n\n"
        "Produce the research brief."
    )

    brief = _invoke(ResearchBrief, RESEARCH_SYSTEM, human, temperature=0.3)

    log.log(
        "node_end",
        node="research",
        revision_round=rnd,
        summary=(
            f"{len(brief.trends)} trends, {len(brief.competitors)} competitors, "
            f"{len(brief.customer_pains)} customer pains, {len(brief.open_questions)} open questions"
        ),
    )
    log.log(
        "handoff",
        node="research",
        revision_round=rnd,
        **{"from": "research", "to": "funding"},
        carrying="market summary, trends, sizing, competitors and open questions",
    )

    return {
        "research_brief": brief,
        "memory_hits": [dict(h, retrieved_by="research") for h in hits],
        "handoffs": [{"from": "research", "to": "funding", "round": rnd, "mode": mode}],
        "pending_gaps": [],  # consumed
    }


# --------------------------------------------------------------------------- #
# 2. Funding Advisor — capital sources and readiness
# --------------------------------------------------------------------------- #

FUNDING_SYSTEM = """You are the Funding Advisor on a startup accelerator's support team.

YOUR REMIT: grant programmes, accelerators, relevant investor theses, stage-appropriate \
cheque sizes, the recommended raise, use of funds, and what the founder must have in \
place before funders will engage.

YOU DO NOT: re-derive market facts. The Research Agent has already established the \
market, and you cite their findings rather than producing your own. You do not write \
slides — that is the Pitch Coach's job.

HOW YOU WORK:
- Prefer specific, named programmes over categories. "SBIR Phase I via NIH" beats \
"government grants".
- Every programme's `fit_rationale` must reference something concrete from the research \
brief — a named competitor, a trend, a customer pain. A rationale that would read the \
same for any domain is not a rationale.
- Sequence the capital strategy: usually non-dilutive first where it fits, then \
accelerator, then priced rounds.
- Be realistic about stage. Do not point a pre-seed founder at Series A funds.
- `readiness_gaps` should be uncomfortable and specific. That is the most useful thing \
you give the founder."""


@traced("FundingAdvisor")
def funding_node(state: AcceleratorState) -> dict[str, Any]:
    log = logger()
    domain, stage = state["domain"], state["stage"]
    rnd = state.get("revision_round", 0)
    mode, gaps = _mode(state, "funding", "funding_brief")
    research: ResearchBrief = state["research_brief"]

    log.log(
        "node_start",
        node="funding",
        revision_round=rnd,
        mode=mode,
        note=f"Mapping capital sources for a {stage} {domain} startup.",
    )

    memory_query = f"grants accelerators and investors for {domain} at {stage} stage funding readiness"
    if mode == "refine":
        memory_query += " " + " ".join(g.field for g in gaps)
    hits, memory_context = search_memory(memory_query, node="funding", revision_round=rnd)

    if state.get("use_web", True):
        queries = [
            f"{domain} startup grants and non-dilutive funding programmes 2026",
            f"{domain} accelerators and {stage} investors 2026",
        ]
        if mode == "refine":
            queries = [f"{domain} funding {g.request}" for g in gaps][:3] or queries
        web_context = web_search(queries, node="funding", revision_round=rnd)
    else:
        web_context = "(web search disabled for this run)"

    prior = ""
    if mode == "refine":
        prior = (
            _review_context(state)
            + "\n\nYOUR PREVIOUS BRIEF (improve it):\n"
            f"{state['funding_brief'].model_dump_json(indent=2)}\n\n"
            "GAPS ROUTED SPECIFICALLY TO YOU:\n"
            f"{_gap_block(gaps)}\n\nAddress every one concretely."
        )
    elif mode == "revisit":
        prior = (
            _review_context(state)
            + "\n\nThe Research Agent has just revised its brief above. Here is your existing "
            "funding brief:\n"
            f"{state['funding_brief'].model_dump_json(indent=2)}\n\n"
            "Reconcile it with the updated research — change what the new findings affect, "
            "and keep the rest."
        )

    human = (
        f"Startup domain: {domain}\nFounder stage: {stage}\n\n"
        f"RESEARCH BRIEF FROM THE RESEARCH AGENT:\n{research.model_dump_json(indent=2)}\n\n"
        f"ACCELERATOR MEMORY (programme reference and any prior briefs):\n{memory_context}\n\n"
        f"LIVE WEB RESEARCH:\n{web_context}{prior}\n\n"
        "Produce the funding brief."
    )

    brief = _invoke(FundingBrief, FUNDING_SYSTEM, human, temperature=0.3)

    log.log(
        "node_end",
        node="funding",
        revision_round=rnd,
        summary=(
            f"{len(brief.programs)} programmes, ask of {brief.suggested_ask[:80]}, "
            f"{len(brief.readiness_gaps)} readiness gaps"
        ),
    )
    log.log(
        "handoff",
        node="funding",
        revision_round=rnd,
        **{"from": "funding", "to": "pitch_coach"},
        carrying="capital strategy, named programmes, the suggested ask and use of funds",
    )

    return {
        "funding_brief": brief,
        "memory_hits": [dict(h, retrieved_by="funding") for h in hits],
        "handoffs": [{"from": "funding", "to": "pitch_coach", "round": rnd, "mode": mode}],
        "pending_gaps": [],
    }


# --------------------------------------------------------------------------- #
# 3. Pitch Coach — narrative and deck structure
# --------------------------------------------------------------------------- #

PITCH_SYSTEM = """You are the Pitch Coach on a startup accelerator's support team.

YOUR REMIT: the pitch deck outline — slide order, slide titles, what each slide has to \
achieve, the talking points on it, the narrative arc, and the closing ask.

YOU DO NOT: discover new facts. Every substantive claim on every slide must come from \
the research brief or the funding brief you were handed. If something you need is \
missing, write the slide around what you do have and let the reviewer flag it — do not \
invent a market size, a competitor or a funding figure.

HOW YOU WORK:
- Produce 10 to 12 slides. Follow the accelerator's canonical order unless the material \
argues otherwise, in which case explain the change in `narrative_arc`.
- The problem slide names the research brief's `beachhead_segment` and nobody else. One \
segment, stated with its population.
- The market slide reproduces the research brief's `market_size` arithmetic — the customer \
count, the contract value, the multiplication and the source of the count. Do not replace \
it with a headline industry figure and a percentage; that is the exact pattern this \
accelerator rejects.
- The ask slide uses the funding brief's `suggested_ask` and `use_of_funds` verbatim in \
substance, and ties each allocation to a milestone.
- Tag each slide's `source_agent`: 'research' for market substance, 'funding' for capital \
substance, 'pitch_coach' only for pure narrative slides such as the title or close.
- Talking points must be concrete content, not placeholders. "Various marketing channels" \
is a failure; name the channel and the evidence.
- Keep each slide under roughly 40 words of content.
- Where the research brief left an open question that the deck needs, phrase the slide \
honestly rather than papering over it."""


@traced("PitchCoach")
def pitch_coach_node(state: AcceleratorState) -> dict[str, Any]:
    log = logger()
    domain, stage = state["domain"], state["stage"]
    rnd = state.get("revision_round", 0)
    has_prior = state.get("pitch_outline") is not None

    log.log(
        "node_start",
        node="pitch_coach",
        revision_round=rnd,
        mode="revisit" if has_prior else "initial",
        note="Synthesising both briefs into a deck outline.",
    )

    hits, memory_context = search_memory(
        f"pitch deck structure narrative arc and anti-patterns for {domain} at {stage}",
        node="pitch_coach",
        revision_round=rnd,
    )

    prior = ""
    if has_prior:
        prior = (
            _review_context(state)
            + "\n\nYOUR PREVIOUS OUTLINE:\n"
            f"{state['pitch_outline'].model_dump_json(indent=2)}\n\n"
            "The briefs above have been revised to close those gaps. Rebuild every slide "
            "the reviewer criticised using the new material, and act on any gap the "
            "reviewer addressed to 'none' — those are yours to fix directly. Keep the "
            "slides that were not criticised."
        )

    human = (
        f"Startup domain: {domain}\nFounder stage: {stage}\n\n"
        f"RESEARCH BRIEF:\n{state['research_brief'].model_dump_json(indent=2)}\n\n"
        f"FUNDING BRIEF:\n{state['funding_brief'].model_dump_json(indent=2)}\n\n"
        f"ACCELERATOR PITCH PLAYBOOK:\n{memory_context}{prior}\n\n"
        "Produce the pitch deck outline."
    )

    outline = _invoke(PitchOutline, PITCH_SYSTEM, human, temperature=0.4)

    log.log(
        "node_end",
        node="pitch_coach",
        revision_round=rnd,
        summary=f"{len(outline.slides)}-slide outline — \"{outline.headline}\"",
    )
    log.log(
        "handoff",
        node="pitch_coach",
        revision_round=rnd,
        **{"from": "pitch_coach", "to": "critique"},
        carrying="the full deck outline for investor-readiness review",
    )

    return {
        "pitch_outline": outline,
        "memory_hits": [dict(h, retrieved_by="pitch_coach") for h in hits],
        "handoffs": [{"from": "pitch_coach", "to": "critique", "round": rnd, "mode": "synthesis"}],
    }


# --------------------------------------------------------------------------- #
# 4. Critique Agent — the feedback mechanism
# --------------------------------------------------------------------------- #

CRITIQUE_SYSTEM = """You are the accelerator's investor-readiness reviewer. You sit \
between the Pitch Coach and the founder, and you are deliberately hard to satisfy.

YOUR REMIT: score the deck outline out of 10 against the accelerator's rubric, and route \
every weakness back to the agent that owns it.

YOU DO NOT: rewrite the deck or supply the missing content yourself. You diagnose and \
delegate. Your entire output is a judgement plus a set of instructions addressed to \
other agents.

THE RUBRIC — check each and deduct for failures:
1. Is the problem slide specific and quantified, naming one customer segment?
2. Is the market sized bottom-up with visible arithmetic and a source?
3. Are competitors named, with an explicit wedge stated?
4. Is "why now" dated, recent and credible — not a generic technology trend?
5. Does the ask tie to named milestones and a use-of-funds breakdown?
6. Is every substantive claim traceable to a source rather than asserted?
7. Does the narrative build, or is it a list of facts?

ROUTING RULES:
- Missing or weak market facts — sizing, competitors, pains, timing — route to 'research'.
- Missing or weak capital detail — programmes, ask, use of funds, readiness — route to 'funding'.
- Pure wording or ordering issues route to 'none'; do not spend a revision round on those.
- Set `verdict` to 'revise' if any high-severity gap exists or the score is below 8.
- Report only the gaps that genuinely block investor readiness, ranked most damaging \
first. Often that is two or three. Never more than five — a revision round asked to close \
a dozen things closes none of them properly. Five is a ceiling, not a target: do not pad \
the list to fill it, and if a redraft has closed most of what you flagged, return the \
short list that honestly remains.
- Judge the draft in front of you on its own merits. A more specific draft invites more \
specific objections — do not let that inflate your gap list or depress your score \
relative to a vaguer draft that simply gave you less to object to.

Be exacting. A first-draft outline assembled from a single research pass almost always \
has at least one genuine high-severity gap — find it. But do not manufacture gaps that \
are not there: if the outline genuinely satisfies the rubric, pass it."""


@traced("CritiqueAgent")
def critique_node(state: AcceleratorState) -> dict[str, Any]:
    log = logger()
    rnd = state.get("revision_round", 0)

    log.log(
        "node_start",
        node="critique",
        revision_round=rnd,
        mode="review",
        note="Scoring the outline against the investor-readiness rubric.",
    )

    hits, memory_context = search_memory(
        "investor readiness rubric pitch deck anti-patterns market sizing red flags",
        node="critique",
        revision_round=rnd,
    )

    # On a second pass, show the reviewer what it previously asked for so it can judge
    # whether each gap was actually closed rather than re-deriving the same list.
    previous = ""
    if (prior_critique := state.get("critique")) is not None:
        previous = (
            "\n\nYOUR PREVIOUS REVIEW OF AN EARLIER DRAFT "
            f"(score {prior_critique.score}/10):\n{_gap_block(prior_critique.gaps)}\n\n"
            "For each of those, decide whether the new draft closes it. Drop the ones that "
            "are now addressed; keep or re-word only the ones that genuinely still stand.\n"
        )

    human = (
        f"Startup domain: {state['domain']}\nFounder stage: {state['stage']}\n"
        f"Revision round so far: {rnd} of {state.get('max_revisions', 2)}\n"
        f"{previous}\n"
        f"PITCH OUTLINE UNDER REVIEW:\n{state['pitch_outline'].model_dump_json(indent=2)}\n\n"
        f"SUPPORTING RESEARCH BRIEF:\n{state['research_brief'].model_dump_json(indent=2)}\n\n"
        f"SUPPORTING FUNDING BRIEF:\n{state['funding_brief'].model_dump_json(indent=2)}\n\n"
        f"ACCELERATOR RUBRIC AND KNOWN ANTI-PATTERNS:\n{memory_context}\n\n"
        "Score the outline and route any gaps."
    )

    # Temperature 0: the routing decision downstream depends on this output, and a
    # scoring judgement should not vary run to run.
    critique = _invoke(Critique, CRITIQUE_SYSTEM, human, temperature=0.0)

    log.log(
        "critique",
        node="critique",
        revision_round=rnd,
        verdict=critique.verdict,
        score=critique.score,
        rationale=critique.rationale,
        gaps=[g.model_dump() for g in critique.gaps],
    )
    log.log(
        "node_end",
        node="critique",
        revision_round=rnd,
        summary=f"verdict={critique.verdict}, score={critique.score}/10, {len(critique.gaps)} gap(s)",
    )

    return {
        "critique": critique,
        "memory_hits": [dict(h, retrieved_by="critique") for h in hits],
    }
