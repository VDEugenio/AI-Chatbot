"""
In-memory BM25 keyword index.

BM25 scores chunks by exact-term overlap with the query. It's the classic
"keyword search" signal and — per Karpathy's gist — often outperforms vector
search on questions whose wording overlaps the source docs (names, jargon,
specific nouns like "Kubernetes", "DraftKings"). We pair it here with an LLM
reranker so keyword recall is followed by semantic precision.

The index is built once at startup from the same Chroma collection used for
vector search, so both retrievers see identical chunks/metadata.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Tiny English stopword list — trimming these sharpens BM25 scores on short
# queries without requiring a full NLTK dependency.
_STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "if", "then", "of", "in", "on",
        "at", "to", "for", "with", "by", "from", "as", "is", "are", "was",
        "were", "be", "been", "being", "it", "this", "that", "these", "those",
        "i", "you", "he", "she", "we", "they", "them", "his", "her", "their",
        "do", "does", "did", "can", "could", "would", "should", "will",
        "about", "into", "over", "out",
    }
)


def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, drop stopwords."""
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


@dataclass
class BM25Index:
    """
    Simple wrapper around rank_bm25.BM25Okapi plus the Documents it indexes.

    Scores returned by `search` are normalized to [0, 1] by dividing by the
    max score for the query, so they're roughly comparable to Chroma's
    relevance scores. (True comparability across retrievers requires more
    care, but this is good enough for debug/logging.)
    """

    documents: list[Document]
    _bm25: BM25Okapi

    @classmethod
    def from_vectorstore(cls, vectorstore: Any) -> "BM25Index":
        """
        Build a BM25 index over every chunk in the Chroma collection.

        Uses the underlying Chroma collection's .get() because LangChain's
        Chroma wrapper doesn't expose a "dump all documents" method.
        """
        data = vectorstore._collection.get(include=["documents", "metadatas"])
        contents: list[str] = data.get("documents") or []
        metadatas: list[dict] = data.get("metadatas") or [{} for _ in contents]

        if not contents:
            raise RuntimeError(
                "Chroma collection is empty — cannot build BM25 index. "
                "Run Pipeline/ingest.py first."
            )

        docs = [
            Document(page_content=c, metadata=m or {})
            for c, m in zip(contents, metadatas)
        ]
        tokenized_corpus = [_tokenize(d.page_content) for d in docs]
        bm25 = BM25Okapi(tokenized_corpus)

        logger.info("Built BM25 index over %d chunks", len(docs))
        return cls(documents=docs, _bm25=bm25)

    def search(self, query: str, k: int) -> list[tuple[Document, float]]:
        """Return the top-k (Document, normalized_score) pairs for `query`."""
        tokens = _tokenize(query)
        if not tokens:
            return []

        scores = self._bm25.get_scores(tokens)
        if len(scores) == 0:
            return []

        max_score = float(scores.max())
        # argsort ascending → slice last k → reverse to descending
        top_indices = scores.argsort()[-k:][::-1]

        results: list[tuple[Document, float]] = []
        for idx in top_indices:
            raw = float(scores[idx])
            norm = raw / max_score if max_score > 0 else 0.0
            results.append((self.documents[idx], norm))
        return results

    def __len__(self) -> int:
        return len(self.documents)
