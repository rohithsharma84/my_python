"""CLI demo: a startup domain in, a pitch deck outline out.

    uv run main.py --domain fintech --stage pre-seed
    uv run main.py --domain healthtech --no-web --max-revisions 1

The model comes from OPENAI_MODEL_NAME in .env.
"""

from __future__ import annotations

import argparse
import sys

from accelerator.config import DEFAULT_MAX_REVISIONS, get_settings, require_openai
from accelerator.graph import build_graph, initial_state, write_diagram
from accelerator.state import Critique
from accelerator.tracing import ROLE_NAMES, start_run

WIDTH = 72

# Briefs routinely contain '€', '—' and other non-cp1252 characters. Without this the
# Windows console raises or prints replacement characters on an otherwise good run.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def banner(text: str, char: str = "=") -> None:
    print("\n" + char * WIDTH)
    print(text)
    print(char * WIDTH)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the accelerator's multi-agent team over a startup domain."
    )
    parser.add_argument("--domain", required=True, help="Startup domain, e.g. 'fintech' or 'climate insurtech'.")
    parser.add_argument("--stage", default="pre-seed", help="Founder stage (default: pre-seed).")
    parser.add_argument(
        "--max-revisions",
        type=int,
        default=DEFAULT_MAX_REVISIONS,
        help=f"How many times the Critique Agent may send work back (default: {DEFAULT_MAX_REVISIONS}).",
    )
    parser.add_argument(
        "--no-web",
        action="store_true",
        help="Skip Tavily searches and run on vector memory plus model knowledge only.",
    )
    return parser.parse_args(argv)


def describe_update(node: str, update: dict) -> None:
    """One line per node completion, so a long run shows progress as it happens."""
    role = ROLE_NAMES.get(node, node)

    if node == "research":
        brief = update["research_brief"]
        print(f"  [{role}] {len(brief.trends)} trends | {len(brief.competitors)} competitors "
              f"| {len(brief.open_questions)} open questions")
    elif node == "funding":
        brief = update["funding_brief"]
        print(f"  [{role}] {len(brief.programs)} programmes | ask: {brief.suggested_ask[:60]}")
    elif node == "pitch_coach":
        outline = update["pitch_outline"]
        print(f"  [{role}] {len(outline.slides)} slides | \"{outline.headline[:60]}\"")
    elif node == "critique":
        critique: Critique = update["critique"]
        print(f"  [{role}] verdict={critique.verdict} score={critique.score}/10 "
              f"| {len(critique.gaps)} gap(s)")
        for gap in critique.gaps:
            print(f"      -> {gap.target_agent:<9} [{gap.severity:<6}] {gap.field}: {gap.request[:70]}")
    elif node == "router":
        route = update.get("route")
        if route == "finalize":
            print(f"  [Router] shipping the outline - {update.get('route_reason', '')}")
        else:
            print(f"  [Router] FEEDBACK LOOP -> sending work back to {ROLE_NAMES.get(route, route)} "
                  f"(round {update.get('revision_round')})")
    elif node == "finalize":
        print(f"  [{role}] artifacts written to {update['run_dir']}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    require_openai()  # exits with an actionable message rather than a 401 mid-run

    settings = get_settings()
    use_web = not args.no_web and settings.has_web

    banner("STARTUP ACCELERATOR - MULTI-AGENT WORKFLOW PLANNER")
    print(f"Domain          : {args.domain}")
    print(f"Stage           : {args.stage}")
    print(f"Max revisions   : {args.max_revisions}")
    print(f"Model           : {settings.model_name} (embeddings: {settings.embedding_model})")
    print(f"Web research    : {'on' if use_web else 'off (memory + model knowledge only)'}")
    print(
        "LangSmith       : "
        + (f"on -> project '{settings.langsmith_project}'" if settings.has_langsmith
           else "off (local traces only)")
    )
    if args.no_web and settings.has_web:
        print("Note            : --no-web given, Tavily key present but unused")
    elif not settings.has_web:
        print("Note            : no TAVILY_API_KEY set")

    run = start_run(
        args.domain,
        args.stage,
        use_web=use_web,
        langsmith=settings.has_langsmith,
        model=settings.model_name,
        max_revisions=args.max_revisions,
    )
    write_diagram(run.run_dir)

    graph = build_graph()
    state = initial_state(args.domain, args.stage, args.max_revisions, use_web)

    banner("AGENT WORKFLOW", "-")
    final: dict = {}
    for chunk in graph.stream(state, stream_mode="updates"):
        for node, update in chunk.items():
            describe_update(node, update)
            final.update(update)

    banner("PITCH DECK OUTLINE")
    print(final.get("outline_markdown", "(no outline produced)"))

    banner("RUN ARTIFACTS", "-")
    for name in ("log.jsonl", "trace.md", "pitch_outline.md", "graph.mmd"):
        path = run.run_dir / name
        marker = "ok " if path.exists() else "-- "
        print(f"  {marker}{path}")
    print("\nRead trace.md for the narrated reasoning path of this run.")
    if settings.has_langsmith:
        print(f"The same run is also traced in LangSmith under project '{settings.langsmith_project}'.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
