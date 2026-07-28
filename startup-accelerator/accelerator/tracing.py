"""Interaction logging and reasoning traceability.

Two layers, deliberately independent:

* **Local JSONL** — every event the graph emits is appended to
  `runs/<timestamp>/log.jsonl`. This is the authoritative record and it works with
  no network, no API key and no quota. `render_trace()` turns it into a narrated
  `trace.md` explaining how the team reached its answer.
* **LangSmith** — the `@traceable` decorator on each node gives a hosted tree view of
  the same run. It is strictly optional: when `LANGSMITH_API_KEY` is absent, tracing
  is disabled in `config.get_settings()` and the run proceeds on local logs alone.

Event kinds emitted: run_start, node_start, node_end, memory_query, memory_hit,
tool_call, handoff, critique, loop_decision, revision, run_end.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import RUNS_DIR

# Agent identifier -> the founder-facing role name used in narration.
ROLE_NAMES = {
    "research": "Research Agent",
    "funding": "Funding Advisor",
    "pitch_coach": "Pitch Coach",
    "critique": "Critique Agent",
    "finalize": "Finalizer",
}


class RunLogger:
    """Append-only JSONL event log for a single run.

    A module-level instance is set by `start_run()` so node functions can log
    without threading a logger through the graph state — LangGraph state is
    serialised between nodes, and a file handle does not belong in it.
    """

    def __init__(self, run_dir: Path) -> None:
        self.run_dir = run_dir
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = run_dir / "log.jsonl"
        self.events: list[dict[str, Any]] = []
        self._console = True

    def log(self, kind: str, node: str = "-", revision_round: int = 0, **payload: Any) -> dict[str, Any]:
        event = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "kind": kind,
            "node": node,
            "revision_round": revision_round,
            **payload,
        }
        self.events.append(event)
        with self.log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        return event

    def write_artifact(self, name: str, text: str) -> Path:
        path = self.run_dir / name
        path.write_text(text, encoding="utf-8")
        return path


_active: RunLogger | None = None


def start_run(domain: str, stage: str, **meta: Any) -> RunLogger:
    """Open a fresh run directory and make it the active logger."""
    global _active
    run_dir = RUNS_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    _active = RunLogger(run_dir)
    _active.log("run_start", domain=domain, stage=stage, **meta)
    return _active


def logger() -> RunLogger:
    """The active logger, or a throwaway one if the graph is invoked directly
    (as in a unit test) without `start_run()`."""
    global _active
    if _active is None:
        _active = RunLogger(RUNS_DIR / datetime.now().strftime("%Y%m%d_%H%M%S"))
    return _active


def traced(name: str):
    """`@traceable` if LangSmith is configured, otherwise a no-op decorator.

    Keeps the node definitions in `agents.py` free of `if settings.has_langsmith`
    branching — they just wear the decorator.
    """

    def decorator(func):
        from .config import get_settings

        if not get_settings().has_langsmith:
            return func

        from langsmith import traceable

        return traceable(name=name, run_type="chain")(func)

    return decorator


# --------------------------------------------------------------------------- #
# Narration
# --------------------------------------------------------------------------- #


def _read_events(run_dir: Path) -> list[dict[str, Any]]:
    log_file = run_dir / "log.jsonl"
    if not log_file.exists():
        return []
    return [json.loads(line) for line in log_file.read_text(encoding="utf-8").splitlines() if line.strip()]


def render_trace(run_dir: Path) -> str:
    """Turn the JSONL log into a human-readable narrative of the run.

    This is the "narrate how agents arrived at the final output" deliverable: a
    chronological walkthrough, a per-agent contribution table, and an explicit
    account of every feedback loop that fired.
    """
    events = _read_events(run_dir)
    if not events:
        return "# Reasoning trace\n\n(no events recorded)\n"

    start = next((e for e in events if e["kind"] == "run_start"), {})
    end = next((e for e in events if e["kind"] == "run_end"), {})

    out: list[str] = [
        "# Reasoning Trace",
        "",
        f"**Domain:** {start.get('domain', '?')}  ",
        f"**Stage:** {start.get('stage', '?')}  ",
        f"**Run directory:** `{run_dir.name}`  ",
        f"**Started:** {start.get('ts', '?')}  ",
        f"**Web search:** {'enabled' if start.get('use_web') else 'disabled (memory-only)'}  ",
        f"**LangSmith:** {'enabled' if start.get('langsmith') else 'disabled (local trace only)'}",
        "",
        "---",
        "",
        "## How the team reached its answer",
        "",
    ]

    # -- chronological narration ------------------------------------------ #
    step = 0
    for event in events:
        kind = event["kind"]
        node = event.get("node", "-")
        role = ROLE_NAMES.get(node, node)
        rnd = event.get("revision_round", 0)
        suffix = f" _(revision round {rnd})_" if rnd else ""

        if kind == "node_start":
            step += 1
            mode = event.get("mode", "initial")
            out.append(f"### Step {step} — {role}{suffix}")
            out.append("")
            out.append(f"Entered in **{mode}** mode. {event.get('note', '')}".strip())
            out.append("")
        elif kind == "memory_query":
            out.append(f"- Queried vector memory: _\"{event.get('query', '')}\"_")
        elif kind == "memory_hit":
            out.append(
                f"  - Retrieved `{event.get('source')}` → *{event.get('heading')}* "
                f"(similarity {event.get('score')})"
            )
        elif kind == "tool_call":
            status = "ok" if event.get("ok", True) else f"failed — {event.get('error', 'unknown error')}"
            out.append(
                f"- Called `{event.get('tool')}` with _\"{event.get('query', '')}\"_ → "
                f"{event.get('result_count', 0)} results ({status})"
            )
        elif kind == "node_end":
            summary = event.get("summary", "")
            out.append("")
            out.append(f"**Produced:** {summary}")
            out.append("")
        elif kind == "handoff":
            out.append(
                f"> **Handoff:** {ROLE_NAMES.get(event.get('from'), event.get('from'))} → "
                f"{ROLE_NAMES.get(event.get('to'), event.get('to'))} — {event.get('carrying', '')}"
            )
            out.append("")
        elif kind == "critique":
            out.append(
                f"**Critique verdict:** `{event.get('verdict')}` "
                f"(score {event.get('score')}/10) — {event.get('rationale', '')}"
            )
            out.append("")
            for gap in event.get("gaps", []):
                out.append(
                    f"- gap → **{ROLE_NAMES.get(gap['target_agent'], gap['target_agent'])}** "
                    f"[{gap['severity']}] `{gap['field']}`: {gap['request']}"
                )
            out.append("")
        elif kind == "loop_decision":
            out.append(f"**Router decision:** → `{event.get('route')}` — {event.get('reason', '')}")
            out.append("")
        elif kind == "revision":
            out.append(
                f"🔁 **Feedback loop fired.** Work sent back to "
                f"{ROLE_NAMES.get(event.get('to'), event.get('to'))} with "
                f"{event.get('gap_count', 0)} gap(s) to close."
            )
            out.append("")

    # -- per-agent contribution table ------------------------------------- #
    by_node: dict[str, Counter] = defaultdict(Counter)
    for event in events:
        if event.get("node", "-") != "-":
            by_node[event["node"]][event["kind"]] += 1

    out += ["---", "", "## Agent contributions", "",
            "| Agent | Times invoked | Memory queries | Tool calls |", "|---|---|---|---|"]
    for node, counts in by_node.items():
        out.append(
            f"| {ROLE_NAMES.get(node, node)} | {counts['node_start']} | "
            f"{counts['memory_query']} | {counts['tool_call']} |"
        )
    out.append("")

    # -- convergence ------------------------------------------------------ #
    critiques = [e for e in events if e["kind"] == "critique"]
    out += ["## Convergence across revision rounds", ""]
    if critiques:
        out.append("| Round | Score | Open gaps | Verdict |")
        out.append("|---|---|---|---|")
        for c in critiques:
            out.append(
                f"| {c.get('revision_round', 0)} | {c.get('score')}/10 | "
                f"{len(c.get('gaps', []))} | `{c.get('verdict')}` |"
            )
        out.append("")
        if len(critiques) > 1:
            first, last = critiques[0], critiques[-1]
            first_gaps, last_gaps = len(first.get("gaps", [])), len(last.get("gaps", []))
            gap_delta = last_gaps - first_gaps
            score_delta = (last.get("score") or 0) - (first.get("score") or 0)

            out.append(
                f"Open gaps went {first_gaps} → {last_gaps} ({gap_delta:+d}); "
                f"score went {first.get('score')} → {last.get('score')} ({score_delta:+d})."
            )
            if gap_delta < 0 or score_delta > 0:
                verdict = (
                    "The revisions closed real ground. Gap count is the more reliable "
                    "signal of the two — the reviewer raises its bar as the deck gets more "
                    "specific, so a flat score alongside falling gaps is still progress."
                )
            elif gap_delta == 0 and score_delta == 0:
                verdict = (
                    "The revisions did not move either measure. Either the agents could not "
                    "source what the reviewer asked for, or the reviewer replaced closed gaps "
                    "with newly visible ones of equal weight — compare the two rounds' gap "
                    "lists above to tell which."
                )
            else:
                verdict = (
                    "Both measures moved the wrong way. This is a known failure mode of an "
                    "LLM reviewer: a more detailed draft exposes more surface to object to. "
                    "Treat the final outline as a draft and read the gap list as the to-do."
                )
            out.append("")
            out.append(verdict)
        out.append("")

    # -- feedback loop summary -------------------------------------------- #
    revisions = [e for e in events if e["kind"] == "revision"]
    out += ["## Feedback loops", ""]
    if revisions:
        out.append(f"{len(revisions)} loop(s) fired:")
        out.append("")
        for rev in revisions:
            out.append(
                f"- Round {rev.get('revision_round')}: back to "
                f"**{ROLE_NAMES.get(rev.get('to'), rev.get('to'))}** to close "
                f"{rev.get('gap_count', 0)} gap(s) — {rev.get('fields', '')}"
            )
    else:
        out.append("None — the Critique Agent passed the outline on the first attempt.")
    out.append("")

    # -- memory provenance ------------------------------------------------- #
    hits = [e for e in events if e["kind"] == "memory_hit"]
    out += ["## Memory provenance", ""]
    if hits:
        sources = Counter(h.get("source") for h in hits)
        out.append("| Corpus file | Times retrieved |")
        out.append("|---|---|")
        for source, count in sources.most_common():
            out.append(f"| `{source}` | {count} |")
        prior = [s for s in sources if s not in {"grants_and_programs.md", "pitch_playbook.md", "research_playbook.md"}]
        if prior:
            out.append("")
            out.append(
                "Entries from `past_briefs/` were retrieved, so this run built on "
                f"findings from earlier runs: {', '.join(f'`{p}`' for p in prior)}."
            )
    else:
        out.append("No memory retrievals recorded.")
    out.append("")

    if end:
        out += [
            "---",
            "",
            "## Outcome",
            "",
            f"- Final score: **{end.get('final_score', '?')}/10**",
            f"- Revision rounds used: **{end.get('revision_round', 0)}**",
            f"- Slides produced: **{end.get('slide_count', '?')}**",
            f"- Memory written back: `{end.get('memory_file', 'n/a')}`",
            "",
        ]

    return "\n".join(out)
