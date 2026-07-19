# MarketScout — Build & Connect a Custom MCP Server (VS Code + GitHub Copilot CLI)

**Objective:** Build a custom MCP (Model Context Protocol) server that gives an AI
agent live market-research abilities, then connect **GitHub Copilot CLI** to it
from inside VS Code and generate a cited market-research report.

### The pipeline

```
 You type a question            GitHub Copilot CLI              MarketScout server            Tavily API
 ┌────────────────────┐        ┌──────────────────┐  MCP over  ┌────────────────────┐        ┌──────────┐
 │ "Compare NVIDIA    │───────▶│  agent decides   │───HTTP────▶│  company_brief     │───────▶│ live web │
 │  and AMD..."       │        │  which tools to  │  :8000/mcp │  product_lineup    │        │  search  │
 └────────────────────┘        │  call, and when  │◀───────────│  price_trends      │◀───────│          │
                               └──────────────────┘   results  │  competitor_...    │        └──────────┘
                                        │                      │  industry_news     │
                                        ▼                      └────────────────────┘
                               cited report in your terminal
```

The key idea: **the server only provides tools** (search functions). The
**agent** (Copilot CLI) reads each tool's description, plans which ones to
call, calls them over MCP, and synthesizes the final report itself.

---

## Prerequisites

| Requirement | Check with | Get it from |
|---|---|---|
| VS Code (latest) | Help > About | https://code.visualstudio.com |
| Python 3.10+ | `python --version` | https://python.org |
| uv (Python package runner) | `uv --version` | `winget install astral-sh.uv` or https://docs.astral.sh/uv |
| Node.js 22+ | `node --version` | https://nodejs.org |
| GitHub account with Copilot access | — | https://github.com/features/copilot |
| Tavily API key (free tier) | — | https://app.tavily.com |

---

## Part 1 — Set up the project in VS Code

1. **Open the folder**: In VS Code, **File > Open Folder...** and select `mcp-demo1`.

2. **Create your `.env` file**: In the Explorer sidebar, right-click `.env.example`
   → **Copy**, then paste and rename the copy to `.env`. Open it and replace
   `tvly-your-key-here` with your real Tavily API key:

   ```
   TAVILY_API_KEY=tvly-abc123...
   ```

   > The `.env` file is git-ignored so your key never gets committed.

3. **Skim `server.py`** (2 minutes): Notice the three MCP building blocks —
   `@mcp.tool` (functions the agent can call), `@mcp.resource` (data it can
   read), and `@mcp.prompt` (templates it can reuse). The docstring on each
   tool is what the agent reads when deciding which tool to use.

---

## Part 2 — Start the MCP server

4. **Open a terminal**: **Terminal > New Terminal**.

5. **Run the server**:

   ```
   uv run server.py
   ```

   The first run creates a virtual environment and installs dependencies
   automatically. You should see:

   ```
   Starting MarketScout MCP server at http://127.0.0.1:8000/mcp ...
   ```

   **Leave this terminal running** — this is your MCP server.

---

## Part 3 — Install and connect GitHub Copilot CLI

6. **Open a second terminal**: click the **`+`** button in the terminal panel
   (or **Terminal > New Terminal** again).

7. **Install Copilot CLI** (one-time):

   ```
   npm install -g @github/copilot
   ```

8. **Start Copilot CLI**:

   ```
   copilot
   ```

   If this is your first run, authenticate when prompted: type `/login` and
   follow the device-code flow in your browser.

9. **Register the MCP server**. Inside the Copilot CLI session, type:

   ```
   /mcp add
   ```

   Fill in the fields when prompted:
   - **Server name:** `MarketScout`
   - **Server type:** `HTTP`
   - **URL:** `http://127.0.0.1:8000/mcp`
   - Leave headers/tools as defaults, then save (follow the on-screen key hint, e.g. `Ctrl+S`).

   > **Alternative (manual config):** instead of `/mcp add`, create the file
   > `C:\Users\<you>\.copilot\mcp-config.json` with:
   >
   > ```json
   > {
   >   "mcpServers": {
   >     "MarketScout": {
   >       "type": "http",
   >       "url": "http://127.0.0.1:8000/mcp"
   >     }
   >   }
   > }
   > ```
   >
   > then restart `copilot`.

10. **Verify the connection**: type `/mcp` — you should see **MarketScout**
    listed with its five tools (`company_brief`, `product_lineup`,
    `price_trends`, `competitor_landscape`, `industry_news`).

---

## Part 4 — Run a market-research query

11. **Paste this prompt** into the Copilot CLI session:

    ```
    Create a market research report comparing NVIDIA and AMD. Cover these points:
    1. Company overview and market position
    2. Product portfolio (gaming GPUs, AI/data center chips, etc.)
    3. Pricing and recent price trends
    4. Key competitors (Intel, Qualcomm, etc.) and positioning
    5. Strategic moves and future outlook
    Keep it concise (under 300 words) and use credible sources.
    Use the MarketScout tools for all research.
    ```

12. **Approve the tool calls**: Copilot CLI asks permission before running
    each MCP tool. Approve them (choose the "allow for this session" option
    to avoid re-approving every call).

13. **Watch the agent work**: it will call `company_brief`, `product_lineup`,
    `price_trends`, etc. for each company — check the server terminal to see
    requests arriving — then write a cited report in the CLI.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Missing TAVILY_API_KEY` on server start | You skipped step 2 — create `.env` with your key in the `mcp-demo1` folder. |
| `/mcp` shows MarketScout as failed/disconnected | Is the server terminal still running? Restart `uv run server.py`, then restart `copilot`. |
| Copilot answers from memory without calling tools | Add "Use the MarketScout tools for all research" to your prompt, or ask it explicitly to call `company_brief` first. |
| Port 8000 already in use | Change the port in the last line of `server.py` (e.g. `port=8001`) and update the URL in your MCP config to match. |
| `copilot` not recognized | Reopen the terminal so PATH refreshes after the npm install, or check `npm bin -g` is on your PATH. |

## What to explore next

- Add your own tool: write a new function in `server.py`, decorate it with
  `@mcp.tool`, restart the server — Copilot CLI picks it up automatically.
- Try the built-in prompt template: `/mcp` shows the `compare_companies`
  prompt the server exposes.
- Point a different MCP client at the same server (VS Code Copilot Chat
  agent mode via `.vscode/mcp.json`, Claude Code via `claude mcp add`) — the
  server doesn't change; that's the point of MCP.
