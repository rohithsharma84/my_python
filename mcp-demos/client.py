# client.py
import asyncio
import os
import re
from typing import Any, Dict, List, Tuple

from fastmcp import Client
from fastmcp.client.transports import StreamableHttpTransport

ENDPOINT = os.getenv("MARKETINTEL_ENDPOINT", "http://127.0.0.1:8000/mcp")

# --- simple helpers ----------------------------------------------------------
def parse_vs(query: str) -> Tuple[str, str]:
    parts = re.split(r"\s+v(?:s\.?)?\s+", query.strip(), flags=re.I)
    if len(parts) != 2:
        raise ValueError("Please provide input like: 'CompanyA vs CompanyB'")
    return parts[0].strip(), parts[1].strip()

def top_urls(result_dict: Dict[str, Any], n: int = 3) -> List[str]:
    # Works with your tool outputs: {'answer': ..., 'results': [{url, ...}, ...]}
    urls = []
    for r in result_dict.get("results", []):
        url = r.get("url")
        if url:
            urls.append(url)
        if len(urls) >= n:
            break
    return urls

def pick_answer(result_dict: Dict[str, Any]) -> str:
    ans = result_dict.get("answer")
    return ans.strip() if isinstance(ans, str) else ""

# --- core client logic -------------------------------------------------------
async def research_vs(query: str, endpoint: str = ENDPOINT) -> None:
    a, b = parse_vs(query)
    transport = StreamableHttpTransport(url=endpoint)
    client = Client(transport)

    used_tools: List[str] = []
    data: Dict[str, Dict[str, Any]] = {a: {}, b: {}}

    async def call_tool(tool: str, args: Dict[str, Any]) -> Any:
        # call and collect tool usage
        res = await client.call_tool(tool, args, raise_on_error=False)
        if res.is_error:
            # surface the server's error text if available
            text = res.content[0].text if res.content else "Unknown tool error"
            return {"error": text}
        used_tools.append(tool)
        # Prefer structured data (FastMCP .data) but fall back to JSON/blocks
        return res.data if res.data is not None else {"content": [c.text for c in res.content if hasattr(c, "text")]}

    async with client:
        await client.ping()

        # --- Company A ---
        data[a]["overview"] = await call_tool("company_overview", {"name": a})
        data[a]["portfolio"] = await call_tool("product_portfolio", {"company": a})
        data[a]["pricing"] = await call_tool("pricing_snapshot", {"product_or_company": a})
        data[a]["news"] = await call_tool("recent_news_pulse", {"company": a})

        # --- Company B ---
        data[b]["overview"] = await call_tool("company_overview", {"name": b})
        data[b]["portfolio"] = await call_tool("product_portfolio", {"company": b})
        data[b]["pricing"] = await call_tool("pricing_snapshot", {"product_or_company": b})
        data[b]["news"] = await call_tool("recent_news_pulse", {"company": b})

    # --- format a quick report ------------------------------------------------
    def section(name: str) -> str:
        ov = data[name]["overview"]
        pf = data[name]["portfolio"]
        pr = data[name]["pricing"]
        nw = data[name]["news"]

        pf_search = pf.get("search", {}) if isinstance(pf, dict) else {}
        pf_ans = pick_answer(pf_search) if pf_search else ""
        pf_urls = top_urls(pf_search) if pf_search else []

        txt = [f"# {name}"]
        if isinstance(ov, dict):
            ans = pick_answer(ov)
            if ans:
                txt += [f"**Overview (auto-synthesized):** {ans}"]
            urls = top_urls(ov)
            if urls:
                txt += ["Sources (overview):"] + [f"- {u}" for u in urls]
        if pf_ans:
            txt += [f"\n**Portfolio (summary):** {pf_ans}"]
        if pf_urls:
            txt += ["Sources (portfolio):"] + [f"- {u}" for u in pf_urls]
        if isinstance(pr, dict):
            pr_ans = pick_answer(pr)
            pr_urls = top_urls(pr)
            if pr_ans:
                txt += [f"\n**Pricing (snapshot):** {pr_ans}"]
            if pr_urls:
                txt += ["Sources (pricing):"] + [f"- {u}" for u in pr_urls]
        if isinstance(nw, dict):
            nw_ans = pick_answer(nw)
            nw_urls = top_urls(nw)
            if nw_ans:
                txt += [f"\n**Recent news (last 30d):** {nw_ans}"]
            if nw_urls:
                txt += ["Sources (news):"] + [f"- {u}" for u in nw_urls]
        return "\n".join(txt)

    report_lines = [
        "============================================================",
        f"MarketIntel quick compare: {a} vs {b}",
        "============================================================",
        section(a),
        "",
        section(b),
        "",
        "============================================================",
        "**Tools used (in order):** " + ", ".join(used_tools),
    ]

    print("\n".join(report_lines))


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MarketIntel MCP client (Streamable HTTP).")
    parser.add_argument("query", nargs="?", default="simplilearn vs edureka",
                        help="e.g., 'simplilearn vs edureka'")
    parser.add_argument("--endpoint", default=ENDPOINT,
                        help="MCP server endpoint (default env MARKETINTEL_ENDPOINT or http://127.0.0.1:8000/mcp)")
    args = parser.parse_args()

    asyncio.run(research_vs(args.query, endpoint=args.endpoint))
