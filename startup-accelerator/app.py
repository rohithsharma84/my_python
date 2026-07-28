"""Streamlit interface for the accelerator's agent team.

    uv run streamlit run app.py

The graph is driven with `.stream(stream_mode="updates")` so each agent's result
appears as it completes rather than after a two-minute freeze. Everything the run
produces — outline, reasoning trace, memory provenance, graph diagram — is surfaced
in a tab, which is the "visualize how agents arrived at the output" requirement.
"""

from __future__ import annotations

import json

import streamlit as st

from accelerator.config import DEFAULT_MAX_REVISIONS, get_settings
from accelerator.graph import build_graph, graph_dot, initial_state, write_diagram
from accelerator.tracing import ROLE_NAMES, render_trace, start_run

st.set_page_config(page_title="Startup Accelerator — Agent Team", page_icon="🚀", layout="wide")

STAGES = ["idea / pre-product", "pre-seed", "seed", "Series A"]


# --------------------------------------------------------------------------- #
# Sidebar — inputs and capability status
# --------------------------------------------------------------------------- #

settings = get_settings()

with st.sidebar:
    st.title("🚀 Accelerator")
    st.caption("A Research Agent, a Funding Advisor and a Pitch Coach, orchestrated with LangGraph.")

    domain = st.text_input("Startup domain", value="fintech", help="e.g. fintech, healthtech, climate insurtech")
    stage = st.selectbox("Founder stage", STAGES, index=1)
    max_revisions = st.slider(
        "Max feedback rounds",
        0, 3, DEFAULT_MAX_REVISIONS,
        help="How many times the Critique Agent may send work back to the Research Agent or Funding Advisor.",
    )
    use_web = st.toggle(
        "Live web research", value=settings.has_web, disabled=not settings.has_web,
        help="Uses Tavily. Disabled when TAVILY_API_KEY is not set.",
    )
    run_clicked = st.button("Run the agent team", type="primary", width="stretch")

    st.divider()
    st.subheader("Environment")
    st.write(f"Model: `{settings.model_name}`")
    st.write(f"Embeddings: `{settings.embedding_model}`")
    st.write(("✅ " if settings.has_openai else "❌ ") + "OpenAI key")
    st.write(("✅ " if settings.has_web else "⚪ ") + "Tavily key (web search)")
    st.write(
        f"✅ LangSmith → `{settings.langsmith_project}`"
        if settings.has_langsmith
        else "⚪ LangSmith (local traces only)"
    )


st.title("Multi-Agent Workflow Planner")

if not settings.has_openai:
    st.error("Missing `OPENAI_API_KEY`. Copy `.env.example` to `.env` and fill it in, then reload.")
    st.stop()


# --------------------------------------------------------------------------- #
# Run
# --------------------------------------------------------------------------- #


def execute(domain: str, stage: str, max_revisions: int, use_web: bool) -> dict:
    """Stream the graph, rendering each agent's contribution as it lands."""
    run = start_run(
        domain, stage,
        use_web=use_web, langsmith=settings.has_langsmith,
        model=settings.model_name, max_revisions=max_revisions,
    )
    write_diagram(run.run_dir)

    graph = build_graph()
    state = initial_state(domain, stage, max_revisions, use_web)
    final: dict = {}

    live = st.container()
    progress = st.progress(0.0, text="Starting the Research Agent…")
    # Nominal step budget: 5 nodes on a clean pass, plus 4 per feedback round.
    budget = 5 + 4 * max_revisions
    done = 0

    for chunk in graph.stream(state, stream_mode="updates"):
        for node, update in chunk.items():
            final.update(update)
            done += 1
            progress.progress(min(done / budget, 0.99), text=f"{ROLE_NAMES.get(node, node)} finished")

            with live:
                if node == "research":
                    brief = update["research_brief"]
                    with st.expander(f"🔍 Research Agent — {len(brief.trends)} trends, "
                                     f"{len(brief.competitors)} competitors", expanded=False):
                        st.write(brief.market_summary)
                        st.markdown(f"**Market size** — {brief.market_size}")
                        st.markdown("**Trends**")
                        for t in brief.trends:
                            st.markdown(f"- **{t.title}** — {t.detail}  \n  _evidence: {t.evidence}_")
                        st.markdown("**Competitors**")
                        for c in brief.competitors:
                            st.markdown(f"- **{c.name}** — {c.positioning} _Gap:_ {c.gap}")
                        st.markdown("**Customer pains**")
                        st.markdown("\n".join(f"- {p}" for p in brief.customer_pains))
                        if brief.open_questions:
                            st.warning("Open questions: " + "; ".join(brief.open_questions))

                elif node == "funding":
                    brief = update["funding_brief"]
                    with st.expander(f"💰 Funding Advisor — {len(brief.programs)} programmes", expanded=False):
                        st.write(brief.capital_strategy)
                        st.markdown(f"**Suggested ask** — {brief.suggested_ask}")
                        st.table([
                            {"Programme": p.name, "Type": p.kind, "Amount": p.typical_amount,
                             "Stage fit": p.stage_fit}
                            for p in brief.programs
                        ])
                        st.markdown("**Use of funds**")
                        st.markdown("\n".join(f"- {u}" for u in brief.use_of_funds))
                        st.markdown("**Readiness gaps**")
                        st.markdown("\n".join(f"- {g}" for g in brief.readiness_gaps))

                elif node == "pitch_coach":
                    outline = update["pitch_outline"]
                    st.info(f"🎤 **Pitch Coach** drafted {len(outline.slides)} slides — _{outline.headline}_")

                elif node == "critique":
                    critique = update["critique"]
                    icon = "✅" if critique.verdict == "pass" else "⚠️"
                    with st.expander(f"{icon} Critique Agent — {critique.score}/10, "
                                     f"verdict `{critique.verdict}`", expanded=True):
                        st.write(critique.rationale)
                        if critique.strengths:
                            st.markdown("**Strengths**")
                            st.markdown("\n".join(f"- {s}" for s in critique.strengths))
                        if critique.gaps:
                            st.markdown("**Gaps routed back**")
                            st.table([
                                {"To": ROLE_NAMES.get(g.target_agent, g.target_agent),
                                 "Severity": g.severity, "Field": g.field, "Request": g.request}
                                for g in critique.gaps
                            ])

                elif node == "router":
                    route = update.get("route")
                    reason = update.get("route_reason", "")
                    if route == "finalize":
                        st.success(f"🏁 **Router** — shipping the outline. {reason}")
                    else:
                        st.warning(
                            f"🔁 **Feedback loop** — work sent back to "
                            f"**{ROLE_NAMES.get(route, route)}** (round {update.get('revision_round')})."
                        )

    progress.progress(1.0, text="Done")
    final["_run_dir"] = run.run_dir
    return final


if run_clicked:
    if not domain.strip():
        st.warning("Enter a startup domain first.")
        st.stop()
    with st.status("Running the agent team…", expanded=True):
        st.session_state["result"] = execute(domain.strip(), stage, max_revisions, use_web)

result = st.session_state.get("result")

if not result:
    st.info("Set a domain in the sidebar and press **Run the agent team**.")
    with st.expander("How this works"):
        st.markdown(
            """
The **Research Agent** establishes market facts, hands them to the **Funding Advisor**,
who maps capital sources, and both briefs go to the **Pitch Coach**, who writes the deck
outline. A **Critique Agent** then scores it and routes any weakness back to whichever
agent owns it — that backward edge is the feedback loop, and it is capped so the run
always terminates.

All three agents read from a FAISS vector memory of accelerator knowledge, and every
completed run writes its findings back, so later runs on adjacent domains build on
earlier ones.
"""
        )
    st.stop()


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #

run_dir = result["_run_dir"]
outline_tab, trace_tab, memory_tab, graph_tab = st.tabs(
    ["📄 Pitch Outline", "🧭 Reasoning Trace", "🧠 Memory", "🕸️ Graph"]
)

with outline_tab:
    markdown = result.get("outline_markdown", "(no outline produced)")
    st.download_button("Download pitch_outline.md", markdown, file_name="pitch_outline.md")
    st.markdown(markdown)

with trace_tab:
    st.caption(f"Full event log: `{run_dir / 'log.jsonl'}`")
    st.markdown(render_trace(run_dir))
    with st.expander("Raw event log (JSONL)"):
        events = [
            json.loads(line)
            for line in (run_dir / "log.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        st.dataframe(events, width="stretch")

with memory_tab:
    hits = result.get("memory_hits", [])
    st.caption(
        f"{len(hits)} retrievals from the FAISS corpus across the run. "
        "Entries from `past_briefs/` are findings this team produced on earlier runs."
    )
    st.dataframe(
        [
            {"Retrieved by": ROLE_NAMES.get(h.get("retrieved_by"), h.get("retrieved_by")),
             "Source": h["source"], "Section": h["heading"], "Similarity": h["score"]}
            for h in hits
        ],
        width="stretch",
    )
    for hit in hits:
        with st.expander(f"{hit['source']} — {hit['heading']} ({hit['score']})"):
            st.markdown(hit["snippet"])

with graph_tab:
    st.caption(
        "The compiled LangGraph. The dashed red edges out of `router` are the feedback "
        "loop — that is the whole reason this system uses LangGraph."
    )
    st.graphviz_chart(graph_dot(), width="stretch")
    with st.expander("Mermaid source (also saved as graph.mmd in the run directory)"):
        st.code((run_dir / "graph.mmd").read_text(encoding="utf-8"), language="text")
