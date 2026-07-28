"""The shared vocabulary of the agent team.

Two kinds of thing live here:

1. **Pydantic output models** — the contract each agent must fill. They are handed
   to `llm.with_structured_output(...)`, so the field descriptions below are the
   actual instructions the model reads. Structured output is what makes the
   feedback loop deterministic: the router switches on `Gap.target_agent`, an
   enum, rather than on an LLM sentence we would have to parse.

2. **`AcceleratorState`** — the LangGraph state. Every node receives the whole
   state and returns a partial dict that LangGraph merges in. List fields carry
   `operator.add` reducers so appends accumulate instead of overwriting.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Literal, TypedDict

from pydantic import BaseModel, Field

TargetAgent = Literal["research", "funding", "none"]
Severity = Literal["high", "medium", "low"]


# --------------------------------------------------------------------------- #
# Research Agent output
# --------------------------------------------------------------------------- #


class Trend(BaseModel):
    title: str = Field(description="Short name for the trend, under 10 words.")
    detail: str = Field(description="Two or three sentences explaining the trend and why it matters now.")
    evidence: str = Field(
        description="Where this came from: a source URL, a memory corpus filename, "
        "or the literal string 'model-knowledge' if neither."
    )


class Competitor(BaseModel):
    name: str = Field(description="Company or product name.")
    positioning: str = Field(description="One sentence on who they serve and how they win.")
    gap: str = Field(description="What they leave underserved — the wedge a new entrant could take.")


class ResearchBrief(BaseModel):
    """Market facts only. No funding sources, no slide structure."""

    market_summary: str = Field(description="A tight paragraph framing the market for a founder.")
    beachhead_segment: str = Field(
        description="ONE named, countable customer segment to win first — a role or "
        "organisation type, its approximate population, and where that count comes from. "
        "E.g. 'the ~1,900 US community banks under $1B in assets (FDIC call reports)'. "
        "Not a demographic ('tech-savvy consumers') and not a list of segments."
    )
    trends: list[Trend] = Field(description="Between 3 and 6 current, specific trends.")
    market_size: str = Field(
        description="A BOTTOM-UP estimate that shows its arithmetic: number of target "
        "customers x realistic annual contract value = SAM, then TAM and SOM. State the "
        "source of the customer count. A top-down figure ('the market is $10B, we need "
        "5%') is a failure. If you cannot ground the count, say so explicitly instead of "
        "inventing one."
    )
    competitors: list[Competitor] = Field(description="Between 3 and 5 notable players.")
    customer_pains: list[str] = Field(description="Between 3 and 5 concrete, specific customer pain points.")
    timing_signals: list[str] = Field(description="2 to 4 reasons this is the right moment ('why now').")
    open_questions: list[str] = Field(
        default_factory=list,
        description="Things you could not establish. Be honest — the Pitch Coach relies on this.",
    )


# --------------------------------------------------------------------------- #
# Funding Advisor output
# --------------------------------------------------------------------------- #


class FundingProgram(BaseModel):
    name: str = Field(description="Programme, fund, or grant name.")
    kind: Literal["grant", "accelerator", "vc", "angel", "debt", "competition"] = Field(
        description="What type of capital this is."
    )
    typical_amount: str = Field(description="Typical cheque size or award range, with currency.")
    stage_fit: str = Field(description="The company stage this suits, e.g. 'pre-seed to seed'.")
    fit_rationale: str = Field(
        description="Why THIS startup domain fits THIS programme. Reference a specific "
        "finding from the research brief where possible."
    )
    source: str = Field(description="Source URL, memory corpus filename, or 'model-knowledge'.")


class FundingBrief(BaseModel):
    """Capital sources and funding readiness only. Does not restate market facts
    as its own findings, and does not write slides."""

    capital_strategy: str = Field(
        description="A paragraph on the sensible funding path for this domain and stage, "
        "e.g. non-dilutive grant first, then accelerator, then seed."
    )
    programs: list[FundingProgram] = Field(description="Between 4 and 7 relevant, specific programmes.")
    suggested_ask: str = Field(description="The raise amount to put on the ask slide, with justification.")
    use_of_funds: list[str] = Field(description="3 to 5 allocation lines, each with a rough percentage.")
    readiness_gaps: list[str] = Field(
        description="What this founder must have in place before these funders will engage."
    )


# --------------------------------------------------------------------------- #
# Pitch Coach output
# --------------------------------------------------------------------------- #


class Slide(BaseModel):
    number: int = Field(description="1-based slide position.")
    title: str = Field(description="The slide title as it would appear on the deck.")
    purpose: str = Field(description="One sentence: what this slide has to achieve for the investor.")
    talking_points: list[str] = Field(description="2 to 4 bullets of concrete content, not placeholders.")
    source_agent: Literal["research", "funding", "pitch_coach"] = Field(
        description="Which agent supplied the substance on this slide. Use 'pitch_coach' "
        "only for pure narrative slides such as the title or closing slide."
    )


class PitchOutline(BaseModel):
    """Narrative structure only. Every fact must trace to the research or funding
    brief — the Pitch Coach does not discover anything new."""

    headline: str = Field(description="The one-line positioning statement for the title slide.")
    narrative_arc: str = Field(description="A short paragraph on how the story builds across the deck.")
    slides: list[Slide] = Field(description="Between 10 and 12 slides, numbered in order.")
    the_ask: str = Field(description="The closing ask, drawn from the funding brief.")

    def to_markdown(self, domain: str, stage: str) -> str:
        lines = [
            f"# Pitch Deck Outline — {domain}",
            "",
            f"**Stage:** {stage}  ",
            f"**Positioning:** {self.headline}",
            "",
            "## Narrative arc",
            "",
            self.narrative_arc,
            "",
            "## Slides",
            "",
        ]
        for slide in self.slides:
            lines.append(f"### {slide.number}. {slide.title}")
            lines.append(f"*Purpose:* {slide.purpose}  ")
            lines.append(f"*Sourced from:* `{slide.source_agent}`")
            lines.append("")
            lines.extend(f"- {point}" for point in slide.talking_points)
            lines.append("")
        lines.extend(["## The ask", "", self.the_ask, ""])
        return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Critique agent output — this is what drives the feedback loop
# --------------------------------------------------------------------------- #


class Gap(BaseModel):
    target_agent: TargetAgent = Field(
        description="Which agent must fix this: 'research' for missing market facts, "
        "'funding' for missing capital detail, 'none' if it is purely a wording issue "
        "the Pitch Coach could fix without new input."
    )
    field: str = Field(
        description="The exact field that must change, so the owning agent knows what to "
        "rewrite. For 'research' one of: beachhead_segment, market_summary, market_size, "
        "trends, competitors, customer_pains, timing_signals. For 'funding' one of: "
        "capital_strategy, programs, suggested_ask, use_of_funds, readiness_gaps. "
        "For 'none' name the slide."
    )
    severity: Severity = Field(description="How badly this weakens the deck.")
    request: str = Field(
        description="A direct, actionable instruction addressed to the target agent. "
        "Write it as a task, e.g. 'Find a defensible TAM figure with a cited source.'"
    )


class Critique(BaseModel):
    """Scores the outline and routes any gaps back to the agent that owns them."""

    verdict: Literal["pass", "revise"] = Field(
        description="'revise' if any high-severity gap exists or the score is below 8."
    )
    score: int = Field(ge=1, le=10, description="Investor-readiness score out of 10.")
    strengths: list[str] = Field(description="2 to 4 things the outline does well.")
    gaps: list[Gap] = Field(
        default_factory=list,
        description="Only the gaps that genuinely block investor readiness, ranked most "
        "damaging first — often two or three, never more than five. Empty when the verdict "
        "is 'pass'. Five is a ceiling, not a target; do not pad the list to reach it.",
        max_length=5,
    )
    rationale: str = Field(description="A short paragraph explaining the score and verdict.")


# --------------------------------------------------------------------------- #
# Graph state
# --------------------------------------------------------------------------- #


class AcceleratorState(TypedDict, total=False):
    """Shared blackboard. Nodes return partial dicts; LangGraph merges them."""

    # Inputs
    domain: str
    stage: str
    max_revisions: int
    use_web: bool

    # Agent outputs — each replaced wholesale by its owning agent
    research_brief: ResearchBrief
    funding_brief: FundingBrief
    pitch_outline: PitchOutline
    critique: Critique

    # Feedback-loop control
    revision_round: int
    pending_gaps: list[Gap]  # gaps the next node must address; cleared once consumed
    route: str  # the router's last decision, kept for the trace
    route_reason: str  # why it decided that, surfaced in the CLI and UI

    # Accumulating record of what happened, appended to by every node
    handoffs: Annotated[list[dict[str, Any]], operator.add]
    memory_hits: Annotated[list[dict[str, Any]], operator.add]

    # Populated by the finalize node
    run_dir: str
    outline_markdown: str
