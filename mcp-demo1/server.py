"""MarketScout — a teaching demo of a custom MCP server.

An MCP (Model Context Protocol) server exposes three kinds of things to an
AI agent:

  * tools     — functions the agent can call (here: live web research)
  * resources — read-only data the agent can look up
  * prompts   — reusable prompt templates the agent can fill in

This server wraps the Tavily web-search API in a set of market-research
tools, then serves them over Streamable HTTP so any MCP client (GitHub
Copilot CLI in this demo) can connect at http://127.0.0.1:8000/mcp
"""

import os
from typing import Any

from dotenv import load_dotenv
from fastmcp import FastMCP
from tavily import TavilyClient

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
if not TAVILY_API_KEY:
    raise SystemExit(
        "Missing TAVILY_API_KEY — copy .env.example to .env and paste in your key "
        "(free tier available at https://app.tavily.com)."
    )

tavily = TavilyClient(api_key=TAVILY_API_KEY)

mcp = FastMCP(name="MarketScout")


def _search(query: str, **kwargs: Any) -> dict[str, Any]:
    """Run a Tavily search and trim the raw response down to what an agent needs:
    a synthesized summary plus a list of cited sources."""
    response = tavily.search(query=query, include_answer=True, **kwargs)
    return {
        "query": query,
        "summary": response.get("answer"),
        "sources": [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("content"),
            }
            for item in response.get("results", [])
        ],
    }


# --------------------------------------------------------------------------
# Tools — each @mcp.tool function becomes callable by the connected agent.
# The docstring is what the agent reads to decide when to use the tool,
# so write it like an instruction manual entry.
# --------------------------------------------------------------------------

@mcp.tool
def company_brief(company: str) -> dict[str, Any]:
    """Get an overview of a company: what it does, its market position,
    business model, and headquarters."""
    return _search(
        f"{company} company overview market position business model",
        max_results=6,
        search_depth="advanced",
    )


@mcp.tool
def product_lineup(company: str, segment: str = "") -> dict[str, Any]:
    """List a company's main products and product lines. Optionally focus on
    a segment such as 'gaming GPUs' or 'data center chips'."""
    focus = f" {segment}" if segment else ""
    return _search(
        f"{company}{focus} product lineup portfolio current products",
        max_results=8,
        search_depth="advanced",
    )


@mcp.tool
def price_trends(product_or_company: str) -> dict[str, Any]:
    """Find current pricing and recent price trends for a product or a
    company's product range."""
    return _search(
        f"{product_or_company} pricing current prices recent price trends",
        max_results=8,
        search_depth="advanced",
    )


@mcp.tool
def competitor_landscape(company: str, industry: str = "") -> dict[str, Any]:
    """Identify a company's main competitors and how they are positioned
    against each other. Optionally narrow to an industry."""
    scope = f" in {industry}" if industry else ""
    return _search(
        f"main competitors of {company}{scope} competitive positioning market share",
        max_results=8,
        search_depth="advanced",
    )


@mcp.tool
def industry_news(company: str, days: int = 30) -> dict[str, Any]:
    """Get recent news about a company: launches, partnerships, acquisitions,
    and strategic moves within the last N days (default 30)."""
    return _search(
        f"{company} recent news product launches partnerships strategy",
        topic="news",
        days=days,
        max_results=8,
    )


# --------------------------------------------------------------------------
# Resource — static data the agent can read (no side effects, no arguments).
# --------------------------------------------------------------------------

@mcp.resource("resource://marketscout/playbook")
def research_playbook() -> list[str]:
    """The suggested order of tool calls for a full market-research report."""
    return [
        "1. company_brief for each company",
        "2. product_lineup for each company",
        "3. price_trends for each company",
        "4. competitor_landscape for the market",
        "5. industry_news for each company",
        "6. Synthesize into a cited report",
    ]


# --------------------------------------------------------------------------
# Prompt — a reusable template the client can offer to its user.
# --------------------------------------------------------------------------

@mcp.prompt
def compare_companies(company_a: str, company_b: str) -> str:
    """Generate a market-research comparison prompt for two companies."""
    return (
        f"Create a market research report comparing {company_a} and {company_b}. "
        "Cover: company overview and market position, product portfolio, "
        "pricing and recent price trends, key competitors and positioning, "
        "and strategic moves / future outlook. Keep it under 300 words and "
        "cite credible sources with URLs."
    )


if __name__ == "__main__":
    print("Starting MarketScout MCP server at http://127.0.0.1:8000/mcp ...")
    mcp.run(transport="http", host="127.0.0.1", port=8000)
