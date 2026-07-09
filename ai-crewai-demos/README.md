# Agentic RAG: Router-Retriever System with PDF and Web Search Tools

A CrewAI multi-agent system that routes a question to either a PDF vector search, a live web search, or direct LLM generation, then formulates a source-grounded answer.

## How to Run

```
cd ai-crewai-demos
cp .env.example .env   # fill in OPENAI_API_KEY, OPENAI_MODEL_NAME, TAVILY_API_KEY
jupyter notebook crewai-websearch-rag.ipynb
```

Restart the kernel and "Run All" for a clean end-to-end run.

## What It Does

### Router Agent
Role: **Query Router**. Acts as the crew's `manager_agent` in a `Process.hierarchical` Crew. Classifies each incoming question as `PDF` (answerable from the static reference document), `WEB` (needs fresh/current info), or `DIRECT` (general knowledge, no retrieval), then delegates the task to the Retriever agent with instructions on which single tool to use.

### Retriever Agent
Role: **Answer Retriever**. Holds both retrieval tools and formulates the final answer from whichever source the Router instructed it to use (or from its own knowledge for `DIRECT` questions).

### Tools
- **PDF Search** — `PDFSearchTool` runs `vectorstore.similarity_search` (FAISS, top 3 chunks, 1000-char chunks with 50-char overlap) over `input/transformer_research_paper-dataset.pdf` ("Attention Is All You Need") and returns raw page snippets, mirroring the Web Search tool's raw-results style so the Retriever formulates the answer itself instead of a hidden second LLM call doing it.
- **Web Search** — `TavilySearchTool` posts to the Tavily API and returns the top 3 result titles/URLs.

## Coordination Flow

```
user question
      |
      v
Router (manager_agent) -- classifies PDF / WEB / DIRECT
      |
      v
delegates to Answer Retriever (single coworker, tools=[PDF Search, Web Search])
      |
      v
Retriever calls the instructed tool (or none) and writes the final answer
```

Assigning the single `Task` to the Retriever agent restricts the Router's delegation to that one coworker (CrewAI only injects a delegation tool for `[task.agent]` when `task.agent` is set), so the Router → Retriever pairing is structural, not just a convention.

## Sample Output

See the notebook's own printed run for three sample questions (one PDF-routed, one web-routed, one direct) and `output/trace.log` for the full CrewAI trace of each run.

## Architecture & Design Decisions

- **`Process.hierarchical` over a manual dispatch script**: CrewAI's built-in manager/delegation mechanism produces a native, inspectable trace (the "Delegate work to coworker" tool call) that satisfies the assignment's explicit Router/Retriever role requirement without hand-rolling classification parsing.
- **PDF tool returns raw snippets, not a `RetrievalQA` answer**: keeps the Retriever's own reasoning in the trace instead of hiding synthesis behind a second internal LLM call.
- **Trace logging**: `verbose=True` on both agents, `output_log_file="output/trace.log"` and `tracing=True` (CrewAI's hosted trace viewer) on the Crew, a `Task.callback` that prints on completion, and per-LLM token usage summaries (`router_llm`, `retriever_llm`) plus the Crew's total — together these explain each agent's contribution and cost per run.

## Challenges & Trade-offs

- The Retriever holds both tools at all times; nothing structurally prevents it from picking the wrong one — it relies on following the Router's delegated instructions rather than an architectural restriction (a manual two-crew dispatch, building the Retriever with only the matching tool per branch, would enforce this but loses CrewAI's native delegation trace).
- Fixed `k=3` retrieval may miss relevant PDF content for questions that need broader context.
- The Router classifies "blind": CrewAI's `Delegate work to coworker` tool only exposes coworker `role` names to the manager agent, not their tools or the PDF's actual content, so the Router never sees the document or the vectorstore. Its only "knowledge" of the PDF's scope is the one-line hardcoded description in its own backstory/task prompt — classification is an LLM guess against that description, not a grounded check. Questions that fall inside the PDF's real content but don't match that description's phrasing (or that are simultaneously time-sensitive and PDF-covered) can be misclassified.

## Concepts Demonstrated

- Hierarchical multi-agent delegation (`Process.hierarchical`, `manager_agent`, coworker-restricted delegation via `Task.agent`)
- Tool-restricted-by-instruction retrieval across two heterogeneous sources
- FAISS-based RAG over a PDF (`PyPDFLoader`, `RecursiveCharacterTextSplitter`, `OpenAIEmbeddings`, `FAISS.similarity_search`)
- Live web search via the Tavily API
- CrewAI trace logging and per-agent token usage accounting
