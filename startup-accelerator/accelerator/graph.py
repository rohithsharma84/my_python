r"""The orchestration graph.

    START
      |
      v
  [ research ] <---------------------------+
      |                                    |
      v                                    |
  [ funding ] <--------------------+       |
      |                            |       |
      v                            |       |
  [ pitch_coach ]                  |       |
      |                            |       |
      v                            |       |
  [ critique ]                     |       |
      |                            |       |
      v                            |       |
  [ router ] --- gaps -> funding --+       |
      |     \                              |
      |      \-- gaps -> research ---------+
      |
      | pass, or revision cap reached
      v
  [ finalize ] --> END

Why LangGraph rather than CrewAI or AutoGen: the backward edges above are the whole
point of the assignment, and here they are ordinary edges that either fire or do not.
A CrewAI hierarchical crew would leave re-delegation to the manager agent's discretion,
so a demo run might never exercise the loop; an AutoGen group chat would produce
feedback but not a guaranteed terminating path to a finished outline. The cost is that
this file exists at all — CrewAI would have inferred the wiring from role descriptions.

`router` is a *node*, not just a conditional edge function, because the decision has
side effects: it increments `revision_round`, loads `pending_gaps` for the target agent,
and logs the branch it took. Conditional edge functions in LangGraph return a
destination and cannot write state, so the state change happens in the node and the
edge function simply reads `state["route"]`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from langgraph.graph import END, START, StateGraph

from .agents import critique_node, funding_node, pitch_coach_node, research_node
from .config import DEFAULT_MAX_REVISIONS
from .memory import remember_run
from .state import AcceleratorState
from .tracing import logger, render_trace


def router_node(state: AcceleratorState) -> dict[str, Any]:
    """Decide whether to ship the outline or send it back, and to whom.

    Routing precedence when both agents have gaps: **research first**. The Funding
    Advisor consumes the research brief, so fixing market facts first means funding
    is re-derived against corrected inputs rather than patched twice.
    """
    log = logger()
    critique = state["critique"]
    rnd = state.get("revision_round", 0)
    max_revisions = state.get("max_revisions", DEFAULT_MAX_REVISIONS)

    actionable = [g for g in critique.gaps if g.target_agent in ("research", "funding")]

    if critique.verdict == "pass" or not actionable:
        reason = (
            f"Critique passed the outline at {critique.score}/10 with no gaps to route."
            if critique.verdict == "pass"
            else f"Scored {critique.score}/10, but all remaining gaps are wording-level "
            "(target 'none') — not worth a revision round."
        )
        log.log("loop_decision", node="router", revision_round=rnd, route="finalize", reason=reason)
        return {"route": "finalize", "pending_gaps": [], "route_reason": reason}

    if rnd >= max_revisions:
        reason = (
            f"Scored {critique.score}/10 with {len(actionable)} open gap(s), but the "
            f"revision cap of {max_revisions} is reached — shipping the current outline "
            "with its weaknesses documented."
        )
        log.log("loop_decision", node="router", revision_round=rnd, route="finalize", reason=reason)
        return {"route": "finalize", "pending_gaps": [], "route_reason": reason}

    target = "research" if any(g.target_agent == "research" for g in actionable) else "funding"
    gaps = [g for g in actionable if g.target_agent == target]
    next_round = rnd + 1
    reason = (
        f"Scored {critique.score}/10 with {len(gaps)} gap(s) owned by '{target}'. "
        "Research is fixed before funding because the Funding Advisor consumes the "
        "research brief."
    )

    log.log("loop_decision", node="router", revision_round=rnd, route=target, reason=reason)
    log.log(
        "revision",
        node="router",
        revision_round=next_round,
        to=target,
        gap_count=len(gaps),
        fields=", ".join(g.field for g in gaps),
    )

    return {
        "route": target,
        "pending_gaps": gaps,
        "revision_round": next_round,
        "route_reason": reason,
    }


def route_after_critique(state: AcceleratorState) -> str:
    """Conditional edge — reads the decision `router_node` already made and logged."""
    return state.get("route", "finalize")


def finalize_node(state: AcceleratorState) -> dict[str, Any]:
    """Render the deliverable, write findings back to vector memory, close the trace."""
    log = logger()
    outline = state["pitch_outline"]
    critique = state["critique"]
    rnd = state.get("revision_round", 0)

    log.log("node_start", node="finalize", revision_round=rnd, mode="deliver",
            note="Rendering the outline and writing findings back to memory.")

    markdown = outline.to_markdown(state["domain"], state["stage"])
    log.write_artifact("pitch_outline.md", markdown)

    # Write-back: the next run on an adjacent domain retrieves these findings.
    memory_file = remember_run(
        state["domain"], state["stage"], state["research_brief"], state["funding_brief"]
    )
    log.log("node_end", node="finalize", revision_round=rnd,
            summary=f"wrote pitch_outline.md and remembered findings as {memory_file.name}")

    log.log(
        "run_end",
        node="finalize",
        revision_round=rnd,
        final_score=critique.score,
        final_verdict=critique.verdict,
        slide_count=len(outline.slides),
        memory_file=memory_file.name,
    )

    # trace.md is rendered last so it includes the run_end event.
    log.write_artifact("trace.md", render_trace(log.run_dir))

    return {"outline_markdown": markdown, "run_dir": str(log.run_dir)}


def build_graph():
    """Wire and compile the agent team."""
    builder = StateGraph(AcceleratorState)

    builder.add_node("research", research_node)
    builder.add_node("funding", funding_node)
    builder.add_node("pitch_coach", pitch_coach_node)
    builder.add_node("critique", critique_node)
    builder.add_node("router", router_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "research")
    builder.add_edge("research", "funding")
    builder.add_edge("funding", "pitch_coach")
    builder.add_edge("pitch_coach", "critique")
    builder.add_edge("critique", "router")
    builder.add_conditional_edges(
        "router",
        route_after_critique,
        {"research": "research", "funding": "funding", "finalize": "finalize"},
    )
    builder.add_edge("finalize", END)

    return builder.compile()


def initial_state(
    domain: str,
    stage: str = "pre-seed",
    max_revisions: int = DEFAULT_MAX_REVISIONS,
    use_web: bool = True,
) -> AcceleratorState:
    return {
        "domain": domain,
        "stage": stage,
        "max_revisions": max_revisions,
        "use_web": use_web,
        "revision_round": 0,
        "pending_gaps": [],
        "handoffs": [],
        "memory_hits": [],
    }


def write_diagram(run_dir: Path) -> Path:
    """Persist the graph's own mermaid rendering next to the run's other artifacts."""
    diagram = build_graph().get_graph().draw_mermaid()
    path = run_dir / "graph.mmd"
    path.write_text(diagram, encoding="utf-8")
    return path


def graph_dot() -> str:
    """Graphviz DOT for the compiled graph, for `st.graphviz_chart`.

    Streamlit has no native mermaid renderer, and LangGraph's `draw_mermaid_png()`
    calls out to mermaid.ink — which would make the UI fail offline. DOT renders
    client-side with no extra dependency and no network, so it is what the UI uses;
    the mermaid source is still written to `graph.mmd` for anyone who wants it.
    """
    graph = build_graph().get_graph()
    # The three edges out of `router` are the feedback loop; colour them so the
    # cycle is the first thing a reader notices.
    lines = [
        "digraph G {",
        '  rankdir=TB; bgcolor="transparent";',
        '  node [shape=box style="rounded,filled" fillcolor="#f2f0ff" '
        'fontname="Helvetica" color="#8b7fd4"];',
        '  edge [fontname="Helvetica" fontsize=10 color="#6b6b6b"];',
        '  __start__ [shape=ellipse fillcolor="#ffffff"];',
        '  __end__ [shape=ellipse fillcolor="#bfb6fc"];',
    ]
    for edge in graph.edges:
        if edge.source == "router" and edge.target != "finalize":
            lines.append(
                f'  {edge.source} -> {edge.target} '
                f'[style=dashed color="#d9534f" label="feedback"];'
            )
        elif edge.source == "router":
            lines.append(f'  {edge.source} -> {edge.target} [style=dashed label="pass / cap"];')
        else:
            lines.append(f"  {edge.source} -> {edge.target};")
    lines.append("}")
    return "\n".join(lines)
