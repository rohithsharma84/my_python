"""Environment loading, capability detection, and the shared LLM/embedding factories.

Everything that reads `.env` lives here so the rest of the package never touches
`os.getenv` directly. Capability flags (`has_web`, `has_langsmith`) let the graph
degrade gracefully instead of crashing when an optional key is missing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"
MEMORY_DIR = PROJECT_ROOT / "memory"
CORPUS_DIR = MEMORY_DIR / "corpus"
PAST_BRIEFS_DIR = CORPUS_DIR / "past_briefs"
INDEX_DIR = MEMORY_DIR / "index"

DEFAULT_MODEL = "gpt-5-mini"

EMBEDDING_MODEL = "text-embedding-3-small"

# How many times the Critique agent may send work back before we ship what we have.
DEFAULT_MAX_REVISIONS = 2


@dataclass(frozen=True)
class Settings:
    """Resolved configuration for one process. Never holds a secret value in a
    field that gets logged — only the booleans below are ever printed."""

    model_name: str
    embedding_model: str
    has_openai: bool
    has_web: bool
    has_langsmith: bool
    langsmith_project: str

    def summary_line(self) -> str:
        """A secrets-safe one-liner for the CLI banner and the Streamlit sidebar."""
        return (
            f"model={self.model_name} | "
            f"web_search={'on' if self.has_web else 'off (memory-only)'} | "
            f"langsmith={'on -> ' + self.langsmith_project if self.has_langsmith else 'off (local traces only)'}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load `.env` once and report which capabilities are available."""
    load_dotenv(PROJECT_ROOT / ".env")

    has_langsmith = bool(os.getenv("LANGSMITH_API_KEY"))
    if has_langsmith:
        # The LangChain/LangGraph runtimes pick tracing up from the environment,
        # so setting these here is what actually turns tracing on.
        os.environ["LANGSMITH_TRACING"] = "true"
        os.environ.setdefault("LANGSMITH_PROJECT", "Startup-Accelerator")
    else:
        # Prevent a half-configured .env from making every LLM call retry against
        # an endpoint it cannot authenticate to.
        os.environ["LANGSMITH_TRACING"] = "false"

    return Settings(
        model_name=os.getenv("OPENAI_MODEL_NAME") or DEFAULT_MODEL,
        embedding_model=EMBEDDING_MODEL,
        has_openai=bool(os.getenv("OPENAI_API_KEY")),
        has_web=bool(os.getenv("TAVILY_API_KEY")),
        has_langsmith=has_langsmith,
        langsmith_project=os.getenv("LANGSMITH_PROJECT", "Startup-Accelerator"),
    )


def require_openai() -> None:
    """Fail fast with an actionable message rather than a 401 deep inside a node."""
    if not get_settings().has_openai:
        raise SystemExit(
            "Missing OPENAI_API_KEY — copy .env.example to .env and fill it in.\n"
            "Every agent in this system needs it; there is no offline fallback for the LLM."
        )


@lru_cache(maxsize=4)
def get_llm(temperature: float = 0.3):
    """Shared chat model.

    Cached per temperature so the Research/Funding agents (exploratory, warmer)
    and the Critique agent (deterministic, temperature 0) reuse two clients
    instead of constructing one per node call.
    """
    from langchain_openai import ChatOpenAI

    require_openai()
    settings = get_settings()

    kwargs: dict = {"model": settings.model_name, "api_key": os.environ["OPENAI_API_KEY"]}
    # The gpt-5 family only accepts the default temperature; sending one is a 400.
    if not settings.model_name.startswith("gpt-5"):
        kwargs["temperature"] = temperature

    return ChatOpenAI(**kwargs)


@lru_cache(maxsize=1)
def get_embeddings():
    """Embedding model backing the vector memory."""
    from langchain_openai import OpenAIEmbeddings

    require_openai()
    return OpenAIEmbeddings(model=EMBEDDING_MODEL, api_key=os.environ["OPENAI_API_KEY"])
