"""
Local keyword-based document retrieval (Stage B – MVP stub).

For the MVP this implements a simple TF-IDF-like keyword retrieval over
markdown/text files on disk.  The interface is designed so it can be
replaced by Azure AI Search without changing the callers:

    retriever.search(query, top_k) -> list[RetrievedChunk]

Each chunk carries the doc metadata and a relevance score so the explainer
can attach citations to recovery steps.
"""

from __future__ import annotations

import json
import logging
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class DocumentChunk:
    """A single chunk from an ingested document."""

    chunk_id: str
    doc_id: str
    title: str
    doc_type: str
    service: str
    source_path: str
    text: str
    tokens: list[str] = field(default_factory=list)


@dataclass
class RetrievedChunk:
    """A chunk returned by a search query with its relevance score."""

    chunk_id: str
    doc_id: str
    title: str
    doc_type: str
    service: str
    excerpt: str
    relevance_score: float


# ---------------------------------------------------------------------------
# Chunking helper
# ---------------------------------------------------------------------------

_CHUNK_SIZE = 400  # words
_CHUNK_OVERLAP = 50


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9_\-.]+", text.lower())


def _chunk_text(text: str, chunk_size: int = _CHUNK_SIZE, overlap: int = _CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping word-based chunks."""
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += chunk_size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Retrieval engine
# ---------------------------------------------------------------------------


class LocalRetriever:
    """
    Keyword-based retrieval over local document chunks.

    Usage:
        retriever = LocalRetriever(docs_dir="data/sample_docs", store_path="data/ingested_docs.jsonl")
        retriever.load_docs()          # on startup
        results = retriever.search("config service restart", top_k=3)
    """

    def __init__(self, docs_dir: str | Path, store_path: str | Path) -> None:
        self._docs_dir = Path(docs_dir)
        self._store_path = Path(store_path)
        self._chunks: list[DocumentChunk] = []
        self._idf: dict[str, float] = {}

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def load_docs(self) -> int:
        """Load chunks from JSONL store; auto-index sample_docs on first run."""
        self._chunks = []
        if self._store_path.exists():
            with self._store_path.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        data = json.loads(line)
                        chunk = DocumentChunk(**data)
                        self._chunks.append(chunk)

        if not self._chunks:
            self._auto_index_sample_docs()

        self._build_idf()
        logger.info("LocalRetriever: %d chunks loaded", len(self._chunks))
        return len(self._chunks)

    def ingest(self, content: str, doc_id: str, title: str, doc_type: str = "TSG", service: str = "", source_path: str = "") -> int:
        """Chunk content and persist to JSONL store; returns number of chunks stored."""
        raw_chunks = _chunk_text(content)
        new_chunks: list[DocumentChunk] = []
        for i, text in enumerate(raw_chunks):
            chunk = DocumentChunk(
                chunk_id=f"{doc_id}::chunk{i}",
                doc_id=doc_id,
                title=title,
                doc_type=doc_type,
                service=service,
                source_path=source_path,
                text=text,
                tokens=_tokenize(text),
            )
            new_chunks.append(chunk)

        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        with self._store_path.open("a", encoding="utf-8") as fh:
            for chunk in new_chunks:
                fh.write(json.dumps(chunk.__dict__) + "\n")

        self._chunks.extend(new_chunks)
        self._build_idf()
        return len(new_chunks)

    def _auto_index_sample_docs(self) -> None:
        """Automatically ingest all .md / .txt files in docs_dir."""
        if not self._docs_dir.exists():
            return
        for path in sorted(self._docs_dir.glob("**/*.md")) + sorted(self._docs_dir.glob("**/*.txt")):
            text = path.read_text(encoding="utf-8")
            service = _infer_service_from_path(path)
            self.ingest(
                content=text,
                doc_id=path.stem,
                title=path.stem.replace("_", " ").title(),
                doc_type="TSG",
                service=service,
                source_path=str(path),
            )

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 5, service_filter: str = "") -> list[RetrievedChunk]:
        """Return the top-k most relevant chunks for `query` (BM25-lite scoring)."""
        if not self._chunks:
            return []

        query_tokens = set(_tokenize(query))
        scored: list[tuple[float, DocumentChunk]] = []

        for chunk in self._chunks:
            if service_filter and chunk.service and service_filter.lower() not in chunk.service.lower():
                continue
            score = self._bm25_score(query_tokens, chunk)
            if score > 0:
                scored.append((score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)
        results: list[RetrievedChunk] = []
        for score, chunk in scored[:top_k]:
            max_score = scored[0][0] if scored else 1.0
            norm_score = round(min(score / max_score, 1.0), 4)
            results.append(
                RetrievedChunk(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    title=chunk.title,
                    doc_type=chunk.doc_type,
                    service=chunk.service,
                    excerpt=_extract_excerpt(chunk.text, query_tokens),
                    relevance_score=norm_score,
                )
            )
        return results

    # ------------------------------------------------------------------
    # Scoring helpers
    # ------------------------------------------------------------------

    def _build_idf(self) -> None:
        """Build inverse-document-frequency table for all terms."""
        df: dict[str, int] = {}
        for chunk in self._chunks:
            for token in set(chunk.tokens):
                df[token] = df.get(token, 0) + 1
        N = len(self._chunks) or 1
        self._idf = {t: math.log((N - n + 0.5) / (n + 0.5) + 1) for t, n in df.items()}

    def _bm25_score(self, query_tokens: set[str], chunk: DocumentChunk, k1: float = 1.5, b: float = 0.75) -> float:
        if not chunk.tokens:
            return 0.0
        avg_len = sum(len(c.tokens) for c in self._chunks) / len(self._chunks)
        doc_len = len(chunk.tokens)
        score = 0.0
        tf_map: dict[str, int] = {}
        for tok in chunk.tokens:
            tf_map[tok] = tf_map.get(tok, 0) + 1

        for token in query_tokens:
            if token not in tf_map:
                continue
            tf = tf_map[token]
            idf = self._idf.get(token, 0.0)
            numerator = tf * (k1 + 1)
            denominator = tf + k1 * (1 - b + b * doc_len / avg_len)
            score += idf * numerator / denominator
        return score


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _infer_service_from_path(path: Path) -> str:
    name = path.stem.lower()
    mapping = {
        "identity": "PilotFish.Identity",
        "config": "PilotFish.Config",
        "datastore": "PilotFish.DataStore",
        "messaging": "PilotFish.Messaging",
        "control_plane_api": "PilotFish.ControlPlane.API",
        "control_plane_worker": "PilotFish.ControlPlane.Worker",
        "gateway": "PilotFish.Gateway",
    }
    for key, svc in mapping.items():
        if key in name:
            return svc
    return ""


def _extract_excerpt(text: str, query_tokens: set[str], window: int = 60) -> str:
    """Return a short excerpt containing the first query token hit."""
    words = text.split()
    for i, word in enumerate(words):
        if _tokenize(word) and _tokenize(word)[0] in query_tokens:
            start = max(0, i - 10)
            end = min(len(words), i + window)
            snippet = " ".join(words[start:end])
            return f"...{snippet}..."
    return " ".join(words[:window]) + "..."
