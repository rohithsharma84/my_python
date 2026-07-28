"""The two information sources agents draw on: live web search and vector memory.

Both are plain functions rather than LLM-bound tools. The agents in this system have
fixed, role-scoped information needs — the Research Agent always wants market
searches, the Funding Advisor always wants programme searches — so retrieval happens
deterministically before the LLM call rather than through a ReAct loop the model
drives. That keeps the trace readable (you can see exactly what every agent looked
at) and the token cost predictable, at the cost of the model not being able to
follow up on a surprising result mid-turn.

Every call emits a trace event, so `runs/<ts>/log.jsonl` records every query the
team ran and how many results came back.
"""

from __future__ import annotations

from typing import Any

from .config import get_settings
from .memory import format_hits, get_memory
from .tracing import logger


def search_memory(
    query: str,
    node: str,
    revision_round: int = 0,
    k: int = 4,
    recall_k: int = 3,
) -> tuple[list[dict[str, Any]], str]:
    """Query the accelerator's vector memory and log every hit with its source.

    Retrieval is split into two reserved budgets rather than one top-k:

    * `k` slots from the hand-written **playbooks** — how to size a market, which
      grants exist, what makes a deck work.
    * `recall_k` slots from **past run briefs** — what this team already learned about
      related domains.

    A single top-k over the whole corpus does not work here: past briefs are written in
    the same vocabulary as the query, so once a handful accumulate they win every slot
    and the method guidance stops reaching the agent. Measured on a real run, the
    research playbook dropped to zero retrievals. Reserving budgets fixes that and has
    the side benefit of making the trace show both kinds of memory every time.

    Returns the raw hits (for the UI and state) and a prompt-ready rendering.
    """
    log = logger()
    memory = get_memory()
    playbooks = memory.playbook_sources()

    log.log("memory_query", node=node, revision_round=revision_round, query=query,
            k=k, recall_k=recall_k)

    hits = memory.search(query, k=k, only=playbooks)
    if recall_k:
        past_sources = {c.source for c in memory.chunks} - playbooks
        if past_sources:
            hits += memory.search(query, k=recall_k, only=past_sources)

    for hit in hits:
        log.log(
            "memory_hit",
            node=node,
            revision_round=revision_round,
            source=hit["source"],
            heading=hit["heading"],
            score=hit["score"],
            # Not `kind` — that is the event-type parameter on RunLogger.log().
            memory_kind="playbook" if hit["source"] in playbooks else "past_brief",
        )

    return hits, format_hits(hits)


def web_search(
    queries: list[str],
    node: str,
    revision_round: int = 0,
    max_results: int = 4,
) -> str:
    """Run several Tavily searches and return a prompt-ready digest.

    Degrades to a clear placeholder when `TAVILY_API_KEY` is absent or the search
    fails, so a missing optional key never breaks the run — the agent is told it is
    working from model knowledge, and says so in its `evidence` fields.
    """
    log = logger()
    settings = get_settings()

    if not settings.has_web:
        return "(web search disabled — no TAVILY_API_KEY; rely on memory and model knowledge)"

    from langchain_tavily import TavilySearch

    tool = TavilySearch(max_results=max_results)
    sections: list[str] = []

    for query in queries:
        try:
            response = tool.invoke({"query": query})
            results = response.get("results", []) if isinstance(response, dict) else []
            log.log(
                "tool_call",
                node=node,
                revision_round=revision_round,
                tool="tavily_search",
                query=query,
                result_count=len(results),
                ok=True,
            )
            if not results:
                continue
            lines = [f"[web search: \"{query}\"]"]
            lines += [
                f"- {r.get('title', 'untitled')} ({r.get('url', 'no url')})\n  {(r.get('content') or '')[:600]}"
                for r in results
            ]
            sections.append("\n".join(lines))
        except Exception as exc:  # noqa: BLE001 — a search failure must not end the run
            log.log(
                "tool_call",
                node=node,
                revision_round=revision_round,
                tool="tavily_search",
                query=query,
                result_count=0,
                ok=False,
                error=str(exc)[:300],
            )

    if not sections:
        return "(web search returned nothing usable — rely on memory and model knowledge)"
    return "\n\n".join(sections)
