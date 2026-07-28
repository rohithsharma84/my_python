# Startup Accelerator — Multi-Agent Workflow Planner

A LangGraph agent team that takes a startup domain (`fintech`, `healthtech`, `climate insurtech`)
and produces a founder-ready pitch deck outline. A **Research Agent**, a **Funding Advisor** and a
**Pitch Coach** collaborate over shared state and a FAISS vector memory, and a **Critique Agent**
routes weaknesses back to whichever agent owns them — a real cycle in the graph, not a prompt
convention.

## How to Run

```
cd startup-accelerator
cp .env.example .env      # fill in OPENAI_API_KEY; TAVILY_API_KEY and LANGSMITH_* are optional
uv sync
```

**CLI**

```
uv run main.py --domain fintech --stage pre-seed
uv run main.py --domain healthtech --stage seed --max-revisions 2
uv run main.py --domain "climate insurtech" --no-web        # memory-only, no network research
```

The chat model comes from `OPENAI_MODEL_NAME` in `.env` (`gpt-5-mini`); embeddings are
`text-embedding-3-small`.

**Streamlit interface**

```
uv run streamlit run app.py
```

Only `OPENAI_API_KEY` is required. Without `TAVILY_API_KEY` the team runs on vector memory plus
model knowledge; without `LANGSMITH_API_KEY` it still writes complete local traces.

## What It Does

### Research Agent
**Owns** market trends, the beachhead customer segment, bottom-up market sizing, the competitive
set, customer pain points and timing signals.
**Does not own** funding sources or slide structure.
Retrieves method guidance from `research_playbook.md`, runs three Tavily searches, and emits a
typed `ResearchBrief`. Every trend carries an `evidence` field — a URL, a corpus filename, or the
literal `model-knowledge` — so downstream agents can tell grounded claims from priors. Anything it
could not establish goes into `open_questions` rather than being quietly invented.

### Funding Advisor
**Owns** grant programmes, accelerators, investor theses, the suggested ask, use of funds and
funding-readiness gaps.
**Does not own** market facts — it cites the Research Agent's findings rather than re-deriving them.
Retrieves from `grants_and_programs.md` (SBIR/STTR, EIC Accelerator, Horizon Europe, YC, Techstars,
sector programmes, stage-to-capital mapping) and emits a typed `FundingBrief`. Each programme's
`fit_rationale` must reference something concrete from the research brief; a rationale that would
read the same for any domain is treated as a failure.

### Pitch Coach
**Owns** the 10–12 slide outline: slide order, titles, per-slide purpose, talking points, the
narrative arc and the closing ask.
**Does not own** fact discovery — every substantive claim must trace to one of the two briefs.
Retrieves from `pitch_playbook.md` and tags each slide with a `source_agent`, so the finished
outline shows which agent supplied each slide's substance.

### Critique Agent
Not a founder-facing role — this is the feedback mechanism. It scores the outline out of 10
against a seven-point investor-readiness rubric and emits at most five structured
`Gap(target_agent, field, severity, request)` items. It diagnoses and delegates; it never writes
content itself.

## Coordination Flow

```
  START
    |
    v
[ Research Agent ] <-----------------------+
    |  market facts                        |
    v                                      |
[ Funding Advisor ] <----------------+     |
    |  capital strategy               |    |
    v                                 |    |
[ Pitch Coach ]                       |    |
    |  deck outline                   |    |
    v                                 |    |
[ Critique Agent ]                    |    |
    |  score + routed gaps            |    |
    v                                 |    |
[ Router ] -- gaps owned by funding --+    |
    |      \                                \
    |       \-- gaps owned by research ------+
    |
    | verdict=pass, or revision cap reached
    v
[ Finalize ] --> END
```

The three forward edges are the sequential pipeline. The two backward edges out of `router` are the
feedback loop, and `finalize` writes the run's findings back into vector memory so later runs
inherit them.

### Feedback loop integration

Three mechanisms make the loop do real work rather than just re-running:

1. **Typed routing.** `Gap.target_agent` is an enum (`research | funding | none`), so the branch is
   a dictionary lookup, not a parse of an LLM sentence. `Gap.field` is constrained to the actual
   field names on each brief, so a revised agent knows exactly what to rewrite.
2. **Three execution modes.** An agent entered via the loop runs in **refine** mode — it receives
   its own previous brief plus the gaps addressed to it, and must improve rather than restart. An
   agent whose *input* changed runs in **revisit** mode and reconciles its existing output with the
   new upstream findings. First pass is **initial**.
3. **The review reaches everyone.** Every re-run agent, including the Pitch Coach, sees the
   reviewer's full verdict and gap list — not only the gaps routed to it. This was added after an
   early run where revisions improved the briefs but the outline's headline came out byte-identical
   three rounds running: the Pitch Coach was rebuilding from better material while blind to what
   the reviewer had actually objected to.

Research is fixed before funding when both have gaps, because the Funding Advisor consumes the
research brief — patching funding first would mean patching it twice. `MAX_REVISIONS` (default 2,
`--max-revisions`) guarantees termination.

## Vector memory

FAISS + `OpenAIEmbeddings`, built directly on the `faiss` package. Two roles:

- **Seed corpus** — `memory/corpus/*.md`, three hand-written playbooks the agents retrieve method
  guidance and programme reference from.
- **Write-back** — every completed run appends its findings to `memory/corpus/past_briefs/` and
  indexes them immediately, so a later run on an adjacent domain builds on earlier work. A run on
  `parametric crop insurance` retrieved 14 chunks from an earlier `climate insurtech` brief.

Retrieval uses **two reserved budgets** (4 playbook slots, 3 past-brief slots) rather than one
top-k. A single top-k does not survive contact with the write-back: past briefs are written in the
same vocabulary as the query, so once a handful accumulate they win every slot. On a measured run
`research_playbook.md` had dropped to zero retrievals — the agents had stopped receiving the method
guidance entirely. Reserved budgets fix that, and make the trace show both kinds of memory on every
query.

## Trace logging

Every run writes `runs/<timestamp>/`:

| File | Contents |
|---|---|
| `log.jsonl` | Every event: `run_start`, `node_start`, `memory_query`, `memory_hit`, `tool_call`, `handoff`, `critique`, `loop_decision`, `revision`, `node_end`, `run_end` |
| `trace.md` | Narrated walkthrough — every step, every retrieval with its similarity score, a per-agent contribution table, a convergence table across revision rounds, and memory provenance |
| `pitch_outline.md` | The deliverable |
| `graph.mmd` | The graph's own mermaid rendering |

LangSmith tracing runs alongside via `@traceable` on each node, driven by the `LANGSMITH_*` quartet.
It is strictly optional — `tracing.traced()` degrades to a no-op decorator when the key is absent,
so the demo produces a full reasoning trace with no network, no key and no quota.

The Streamlit app surfaces all of this in four tabs: **Pitch Outline**, **Reasoning Trace** (plus
the raw event log), **Memory** (every retrieval with source, section and similarity), and **Graph**
(the compiled graph rendered with the feedback edges highlighted).

## Architecture & Design Decisions

- **LangGraph over CrewAI and AutoGen.** The feedback loop is the assignment's hard requirement, and
  in LangGraph it is an ordinary edge that either fires or does not — deterministic, capped, and
  visible in the rendered diagram. A CrewAI `Process.hierarchical` crew leaves re-delegation to the
  manager agent's discretion, so a given demo run might never exercise the loop; an AutoGen
  `GroupChat` produces feedback naturally but cannot guarantee a terminating path to a finished
  outline. The cost is roughly 150 lines of wiring CrewAI would have inferred from role
  descriptions. Secondary reason: this repo already has CrewAI and AutoGen demos, and
  `ai-langgraph-demos/` only uses the prebuilt `create_agent`, so a hand-written `StateGraph` was
  the gap.
- **`router` is a node, not just a conditional edge.** The decision has side effects — increment
  `revision_round`, load `pending_gaps`, log the branch. LangGraph's conditional edge functions
  return a destination and cannot write state, so the work happens in a node and the edge function
  just reads `state["route"]`.
- **Structured output everywhere.** Every agent returns a Pydantic model via
  `with_structured_output(...)`. Field descriptions *are* the instructions the model reads, which is
  why `market_size` demands visible arithmetic in its description rather than only in a system
  prompt. It also makes routing a lookup instead of a parse.
- **Retrieval is deterministic, not agent-driven.** These agents have fixed, role-scoped information
  needs, so search happens before the LLM call rather than through a ReAct loop. The trace shows
  exactly what every agent looked at and token cost is predictable; the cost is that an agent cannot
  chase a surprising result mid-turn.
- **FAISS built directly, not via `langchain-community`.** LangChain 1.x moved the `FAISS`
  vectorstore into `langchain-community`; the store here is ~90 lines and avoids that dependency
  tree while keeping the retrieval mechanics visible.
- **Markdown-heading chunking.** The corpus is split on `##` boundaries so each grant programme or
  playbook rule stays intact. A retrieved fragment should be a complete idea an agent can act on,
  which matters more here than uniform chunk size.

## Challenges & Trade-offs

- **The Critique Agent is an LLM judging the same model family's work.** It is not an investor. It
  reliably finds genuine rubric violations — unsourced TAM figures, vague customer segments,
  milestone-free asks — but its score is noisy.
- **Scores do not climb monotonically, and the trace says so.** A typical two-revision run scores
  something like 6 → 7 → 6. A more specific draft gives the reviewer more concrete material to
  object to, so the score partly tracks detail rather than quality. `trace.md`'s convergence section
  reports score and gap count per round and states plainly which direction each moved — including
  when neither improved. It does not dress up a flat run as progress.
- **Capping the gap list needed care.** An early version let the critique emit eleven gaps at once
  and the revision closed none of them properly. Capping at five fixed that but introduced a
  saturated metric: the model read "at most 5" as a target and returned exactly five every round,
  so gap count could never fall. Rewording it as an explicit ceiling ("often two or three; five is
  a ceiling, not a target") produced honest counts — a recent run went 3 → 3 → 4.
- **The gaps that survive are mostly not the agents' to close.** After two revisions the residual
  items converge on things no agent can do: *secure signed pilot agreements*, *run a dated
  Crunchbase export*, *commission a legal memo*. That is arguably the system working — it has
  narrowed the deck's weaknesses down to real founder homework — but it means additional revision
  rounds have sharply diminishing returns, which is the honest justification for a low cap.
- **Model choice dominates output quality, more than any prompt change.** During development, on
  `gpt-4o-mini` the market slide came out as "the market is $10B and we need 5%" — the exact
  top-down anti-pattern the playbook rejects — no matter how the prompt was worded. On `gpt-5-mini`
  the same run produced a bottom-up estimate built from a USDA Census farm count times a stated ACV.
  The prompts here assume a model of roughly that capability; dropping to a weaker one degrades the
  output far more than it degrades the orchestration.
- **The index fingerprint has to include the embedding model.** `text-embedding-3-small` and
  `ada-002` are both 1536-dimensional, so swapping models does not raise — FAISS compares the new
  query vectors against an index built in a different space and returns quietly wrong neighbours.
  `_manifest()` in `memory.py` therefore fingerprints the model alongside corpus mtimes, and a
  change to either rebuilds the index automatically.
- **Web results are unverified.** Tavily snippets are passed to agents as-is. The `evidence` field
  records where a claim came from, but nothing checks that the source says what the agent claims.
- **The grant corpus is hand-seeded and will go stale.** Award sizes and programme terms change
  yearly. It is a starting point for diligence, not a quote, and the corpus says so.
- **Write-back is unfiltered.** Every run's findings enter memory whether or not they were any good,
  so a weak run can pollute later ones. A quality gate on write-back — only remember runs scoring
  above some threshold — is the obvious next step.
- **Revisiting costs tokens.** Routing back to research re-runs funding and the Pitch Coach too.
  That is correct (their inputs changed) but a two-revision run is roughly three times the cost of a
  clean pass.

## Project layout

```
startup-accelerator/
  main.py                  CLI demo runner
  app.py                   Streamlit interface
  accelerator/
    config.py              env loading, capability flags, LLM/embedding factories
    state.py               Pydantic output contracts + the LangGraph state
    memory.py              FAISS store: chunking, persistence, search, write-back
    tools.py               memory search (reserved budgets) + Tavily web search
    agents.py              the four node functions and their system prompts
    graph.py               StateGraph wiring, router, finalize, diagram rendering
    tracing.py             JSONL RunLogger, @traceable shim, trace narration
  memory/corpus/           seed playbooks + past_briefs/ write-back
  runs/<timestamp>/        per-run artifacts
```

## Concepts Demonstrated

- Hand-written LangGraph `StateGraph` with cycles, a conditional edge, and a state-mutating router node
- Reducer-based state accumulation (`Annotated[list, operator.add]`) for handoffs and memory hits
- Role-scoped agents with explicit non-responsibilities and typed output contracts
- Critique-driven feedback loops with typed routing, execution modes and a termination cap
- FAISS vector memory with heading-aware chunking, persistence, cross-run write-back and reserved retrieval budgets
- Structured event logging (JSONL) with narrated trace rendering
- Optional LangSmith tracing that degrades to a no-op
- Graceful capability degradation — missing Tavily or LangSmith keys narrow the run instead of breaking it
- Streaming a LangGraph run into a Streamlit UI with live per-agent output
