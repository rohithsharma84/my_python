import os
from typing import Dict, List, Optional, Any
from fastmcp import FastMCP
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("TAVILY_API_KEY")
if not api_key:
    raise ValueError("Please set the TAVILY_API_KEY environment variable.")

mcp = FastMCP(name="MarketIntel")

@mcp.resource("resource://market/topics")
def market_topics() -> List[str]:
    return [
        "Competitor overview",
        "Pricing snapshot",
        "Product portfolio mapping",
        "Market landscape",
        "Feature comparison",
        "Regional GTM",
    ]


def _tsearch(query: str, **kw) -> Dict[str, Any]:
    resp = TavilyClient(api_key=api_key).search(query=query, **kw)
    return {
        "query_used": query,
        "answer": resp.get("answer"),
        "results": [
            {k: r.get(k) for k in ("title", "url", "content", "score", "published_date")}
            for r in resp.get("results", [])
        ],
    }

@mcp.tool(annotations={"title": "Company Overview"}, description="Get a company overview with headquarters, products, business model, and recent news.")
def company_overview(name: str, region: Optional[str] = None, max_results: int = 8) -> Dict[str, Any]:
    reg = f" in {region}" if region else ""
    query = f"Company overview of {name}{reg}: founding, headquarters, products, business model, recent news"
    return _tsearch(query, max_results=max_results, search_depth="advanced", include_answer="advanced")

@mcp.tool(annotations={"title": "List Competitors"}, description="List main direct and emerging competitors for a company, optionally filtered by category and region.")
def list_competitors(name: str, category: Optional[str] = None, region: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]:
    cat = f" in {category}" if category else ""
    reg = f" in {region}" if region else ""
    query = f"Top competitors of {name}{cat}{reg}: include upstart challengers"
    return _tsearch(query, max_results=max_results, search_depth="advanced", include_answer="advanced")

@mcp.tool(annotations={"title": "Product Portfolio Map"}, description="Map a company's product portfolio, including suites, tiers, and product segments.")
def product_portfolio(company: str, focus_keywords: Optional[str] = None, max_results: int = 12) -> Dict[str, Any]:
    kws = f" ({focus_keywords})" if focus_keywords else ""
    query = f"{company} product portfolio{kws}: product list, suites, tiers, segments"
    search_res = _tsearch(query, max_results=max_results, search_depth="advanced", include_answer="advanced")
    product_urls = [r["url"] for r in search_res.get("results", []) if r.get("url") and any(tok in r["url"].lower() for tok in ["product", "products", "pricing", "solutions"])]
    extracted: Dict[str, Any] = {}
    if product_urls:
        try:
            extracted = TavilyClient(api_key=api_key).extract(urls=product_urls[:10], extract_depth="advanced", format="markdown")
        except Exception as e:
            extracted = {"error": f"extract_failed: {e}"}
    return {"search": search_res, "extracted": extracted}

@mcp.tool(annotations={"title": "Pricing Snapshot"}, description="Collect pricing, tier, billing, and discount information for a company or product.")
def pricing_snapshot(product_or_company: str, region: Optional[str] = None, currency_hint: Optional[str] = None, max_results: int = 10) -> Dict[str, Any]:
    reg = f" in {region}" if region else ""
    cur = f" in {currency_hint}" if currency_hint else ""
    query = f"Pricing for {product_or_company}{reg}{cur}: list price, tiers, billing cycles, discounts, hidden fees"
    return _tsearch(query, max_results=max_results, search_depth="advanced", include_answer="advanced")

@mcp.tool(annotations={"title": "Recent News Pulse"}, description="Summarize recent news, funding, acquisitions, launches, and leadership updates.")
def recent_news_pulse(company: str, days: int = 30, max_results: int = 10) -> Dict[str, Any]:
    query = f"Recent news about {company}: funding, acquisitions, launches, leadership"
    return _tsearch(query, topic="news", days=days, max_results=max_results, search_depth="advanced", include_answer="advanced")


def main() -> None:
    print("🚀 Starting MarketIntel MCP server...")
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()
