"""Vector memory backing the agent team.

A small FAISS store built directly on `faiss` + `OpenAIEmbeddings`. LangChain 1.x
dropped the `FAISS` vectorstore wrapper into `langchain-community`, and pulling in
that whole dependency tree for one class is not worth it — the store here is about
eighty lines and makes the retrieval mechanics visible, which suits a teaching repo.

Two roles:

* **Seed corpus** (`memory/corpus/*.md`) — accelerator knowledge the agents retrieve
  from: grant programmes, the pitch playbook, the research playbook.
* **Write-back** (`memory/corpus/past_briefs/*.md`) — each completed run appends its
  own findings, so a later run on an adjacent domain retrieves what the team already
  learned. This is what makes the memory span runs rather than just one graph pass.

Vectors are L2-normalised and searched with inner product, which makes the returned
score a cosine similarity in [-1, 1].
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from .config import (
    CORPUS_DIR,
    EMBEDDING_MODEL,
    INDEX_DIR,
    PAST_BRIEFS_DIR,
    get_embeddings,
)

# Chunks longer than this get split again; markdown sections are the primary unit.
MAX_CHUNK_CHARS = 1400
MIN_CHUNK_CHARS = 80


@dataclass(frozen=True)
class Chunk:
    text: str
    source: str
    heading: str

    def to_hit(self, score: float) -> dict[str, Any]:
        return {
            "source": self.source,
            "heading": self.heading,
            "score": round(float(score), 4),
            "snippet": self.text,
        }


def chunk_markdown(text: str, source: str) -> list[Chunk]:
    """Split a markdown file on its `##` headings, then hard-wrap oversized sections.

    Heading-aware chunking keeps each grant programme or playbook rule intact, which
    matters more here than uniform chunk size — a retrieved fragment should be a
    complete idea an agent can act on.
    """
    sections = re.split(r"\n(?=##\s)", text)
    chunks: list[Chunk] = []

    for section in sections:
        section = section.strip()
        if len(section) < MIN_CHUNK_CHARS:
            continue

        first_line = section.splitlines()[0].strip()
        heading = first_line.lstrip("#").strip() if first_line.startswith("#") else "(intro)"

        if len(section) <= MAX_CHUNK_CHARS:
            chunks.append(Chunk(section, source, heading))
            continue

        # Oversized section: split on blank lines, packing paragraphs up to the limit.
        buffer = ""
        for paragraph in section.split("\n\n"):
            if len(buffer) + len(paragraph) + 2 > MAX_CHUNK_CHARS and buffer:
                chunks.append(Chunk(buffer.strip(), source, heading))
                buffer = ""
            buffer += paragraph + "\n\n"
        if len(buffer.strip()) >= MIN_CHUNK_CHARS:
            chunks.append(Chunk(buffer.strip(), source, heading))

    return chunks


def _corpus_files() -> list[Path]:
    files = sorted(CORPUS_DIR.glob("*.md"))
    files += sorted(PAST_BRIEFS_DIR.glob("*.md"))
    return files


def _manifest() -> dict[str, Any]:
    """Index fingerprint — the embedding model plus every corpus file's mtime.

    The model has to be part of this. `text-embedding-3-small` and `ada-002` both produce
    1536-dimensional vectors, so swapping one for the other does not raise: FAISS happily
    compares new query vectors against an index built in a different embedding space and
    returns quietly wrong neighbours. A mismatch on either half forces a rebuild.
    """
    return {
        "embedding_model": EMBEDDING_MODEL,
        "files": {str(p.relative_to(CORPUS_DIR)): p.stat().st_mtime for p in _corpus_files()},
    }


def _normalize(vectors: np.ndarray) -> np.ndarray:
    vectors = np.asarray(vectors, dtype="float32")
    faiss.normalize_L2(vectors)
    return vectors


class VectorMemory:
    """FAISS index over the accelerator's markdown corpus."""

    def __init__(self) -> None:
        self.index: faiss.Index | None = None
        self.chunks: list[Chunk] = []
        self._embeddings = None

    # -- lifecycle -------------------------------------------------------- #

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = get_embeddings()
        return self._embeddings

    def load_or_build(self) -> "VectorMemory":
        """Load the persisted index, rebuilding when the corpus has changed."""
        index_path = INDEX_DIR / "corpus.faiss"
        docs_path = INDEX_DIR / "docs.json"

        if index_path.exists() and docs_path.exists():
            payload = json.loads(docs_path.read_text(encoding="utf-8"))
            if payload.get("manifest") == _manifest():
                self.index = faiss.read_index(str(index_path))
                self.chunks = [Chunk(**c) for c in payload["chunks"]]
                return self

        return self.build()

    def build(self) -> "VectorMemory":
        """Embed every corpus chunk from scratch and persist the result."""
        self.chunks = []
        for path in _corpus_files():
            self.chunks.extend(
                chunk_markdown(path.read_text(encoding="utf-8"), path.name)
            )

        if not self.chunks:
            raise SystemExit(
                f"No corpus files found under {CORPUS_DIR} — the vector memory would be empty."
            )

        vectors = _normalize(np.array(self.embeddings.embed_documents([c.text for c in self.chunks])))
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)
        self._persist()
        return self

    def _persist(self) -> None:
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(INDEX_DIR / "corpus.faiss"))
        (INDEX_DIR / "docs.json").write_text(
            json.dumps(
                {
                    "manifest": _manifest(),
                    "chunks": [c.__dict__ for c in self.chunks],
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    # -- query ------------------------------------------------------------ #

    def search(
        self,
        query: str,
        k: int = 4,
        min_score: float = 0.15,
        only: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return the k nearest chunks as trace-friendly dicts.

        `min_score` drops weak matches so an off-topic query returns nothing rather
        than three irrelevant snippets the agent would then try to use.

        `only` restricts results to a set of source filenames. Filtering happens after
        the search rather than inside it because a flat FAISS index has no metadata
        filter — so we over-fetch and then narrow, which is fine at this corpus size.
        """
        if self.index is None:
            self.load_or_build()

        vector = _normalize(np.array([self.embeddings.embed_query(query)]))
        depth = min(len(self.chunks), k if only is None else max(k * 8, 40))
        scores, indices = self.index.search(vector, depth)

        hits = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1 or score < min_score:
                continue
            chunk = self.chunks[idx]
            if only is not None and chunk.source not in only:
                continue
            hits.append(chunk.to_hit(score))
            if len(hits) == k:
                break
        return hits

    def playbook_sources(self) -> set[str]:
        """The hand-written corpus, i.e. everything that is not a past run's brief."""
        past = {p.name for p in PAST_BRIEFS_DIR.glob("*.md")}
        return {c.source for c in self.chunks} - past

    # -- write-back ------------------------------------------------------- #

    def add_markdown(self, text: str, source: str) -> int:
        """Embed and append a new document. Returns the number of chunks added."""
        new_chunks = chunk_markdown(text, source)
        if not new_chunks:
            return 0

        vectors = _normalize(np.array(self.embeddings.embed_documents([c.text for c in new_chunks])))
        if self.index is None:
            self.load_or_build()
        self.index.add(vectors)
        self.chunks.extend(new_chunks)
        self._persist()
        return len(new_chunks)


@lru_cache(maxsize=1)
def get_memory() -> VectorMemory:
    """Process-wide memory instance, built on first use."""
    return VectorMemory().load_or_build()


def format_hits(hits: list[dict[str, Any]]) -> str:
    """Render retrieved chunks for an agent prompt, keeping the source attached so
    the agent can cite it and the trace can show where a claim came from."""
    if not hits:
        return "(no relevant entries in accelerator memory)"
    return "\n\n".join(
        f"[memory: {h['source']} — {h['heading']} | similarity {h['score']}]\n{h['snippet']}"
        for h in hits
    )


def remember_run(domain: str, stage: str, research_brief, funding_brief) -> Path:
    """Write this run's findings back into the corpus and index them.

    Stored as a normal markdown file so it is human-readable and so a future run
    picks it up through the same chunking path as the hand-written corpus.
    """
    # Resolve the index *before* the new file lands on disk. Otherwise the manifest
    # check would see an unindexed corpus file, rebuild everything, and then
    # `add_markdown` would append a second copy of the same chunks.
    memory = get_memory()

    PAST_BRIEFS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc)
    slug = re.sub(r"[^a-z0-9]+", "-", domain.lower()).strip("-") or "domain"
    path = PAST_BRIEFS_DIR / f"{slug}-{timestamp:%Y%m%d_%H%M%S}.md"

    lines = [
        f"# Prior accelerator brief — {domain} ({stage})",
        "",
        f"Generated {timestamp:%Y-%m-%d}. Findings from an earlier run of the agent team.",
        "",
        "## Market summary",
        "",
        research_brief.market_summary,
        "",
        "## Trends observed",
        "",
    ]
    lines += [f"- **{t.title}** — {t.detail} (evidence: {t.evidence})" for t in research_brief.trends]
    lines += ["", "## Market size", "", research_brief.market_size, "", "## Competitive set", ""]
    lines += [f"- **{c.name}** — {c.positioning} Gap: {c.gap}" for c in research_brief.competitors]
    lines += ["", "## Customer pains", ""]
    lines += [f"- {p}" for p in research_brief.customer_pains]
    lines += ["", "## Funding strategy", "", funding_brief.capital_strategy, "", "## Programmes identified", ""]
    lines += [
        f"- **{p.name}** ({p.kind}, {p.typical_amount}, {p.stage_fit}) — {p.fit_rationale}"
        for p in funding_brief.programs
    ]
    lines += ["", "## Readiness gaps flagged", ""]
    lines += [f"- {g}" for g in funding_brief.readiness_gaps]
    lines.append("")

    text = "\n".join(lines)
    path.write_text(text, encoding="utf-8")

    # Index it immediately so a second run in the same process can retrieve it.
    memory.add_markdown(text, path.name)
    return path
