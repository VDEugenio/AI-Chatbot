"""Thin wrapper around the Anthropic SDK for Claude chat completions."""

import json
import logging
import re
from collections.abc import AsyncIterator

import anthropic

from .config import Settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Raised when the LLM call fails for any reason."""


_RERANK_SYSTEM = (
    "You are a strict relevance judge. You read a question and a numbered "
    "list of text chunks, and you score each chunk for how well it helps "
    "answer the question. Be strict: most chunks should score low."
)

_RERANK_PREAMBLE = (
    "Score each chunk on a 0-10 scale (0 = irrelevant, 10 = directly answers).\n"
    "Return ONLY a JSON array of objects like "
    '[{"id": 1, "score": 9}, {"id": 2, "score": 2}, ...] — one entry per '
    "chunk, no prose, no markdown fencing.\n\n"
)

# Per-candidate character budget for the rerank prompt. ~30 × 600 ≈ 18k chars.
_RERANK_CHUNK_CHARS = 600

_JSON_ARRAY_RE = re.compile(r"\[\s*\{.*?\}\s*\]", re.DOTALL)


def _cached_system(text: str) -> list[dict]:
    """Wrap a system prompt string in Anthropic's prompt-cache format.

    Caches the system prompt for up to 5 minutes (ephemeral), saving prefill
    time and token cost on every request after the first in a cache window.
    """
    return [{"type": "text", "text": text, "cache_control": {"type": "ephemeral"}}]


class ClaudeClient:
    """Single-purpose async client that takes a system+user prompt and returns text."""

    def __init__(self, settings: Settings) -> None:
        self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self._model = settings.claude_model
        self._max_tokens = settings.max_tokens
        self._temperature = settings.temperature
        # Reranker can run on a cheaper/faster model if configured.
        self._rerank_model = settings.rerank_model or settings.claude_model

    async def answer(self, system: str, messages: list[dict]) -> str:
        """
        Call Claude with a full multi-turn message list and return the text.

        `messages` must follow Anthropic's format: a list of
        `{"role": "user"|"assistant", "content": str}` dicts, ending with a
        user turn (which should already include any RAG context).
        """
        try:
            response = await self._client.messages.create(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                system=_cached_system(system),
                messages=messages,
            )
        except anthropic.APIError as exc:
            logger.exception("Anthropic API error")
            raise LLMError(f"Anthropic API error: {exc}") from exc

        # `content` is a list of typed blocks; concatenate the text blocks.
        text_parts = [
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ]
        if not text_parts:
            raise LLMError("Claude returned no text content.")
        return "".join(text_parts).strip()

    async def answer_stream(
        self, system: str, messages: list[dict]
    ) -> AsyncIterator[str]:
        """
        Stream Claude's response, yielding raw text deltas as they arrive.

        The caller reassembles the full answer and signals completion to the
        HTTP client (e.g. by sending a final SSE event).
        """
        try:
            async with self._client.messages.stream(
                model=self._model,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
                system=_cached_system(system),
                messages=messages,
            ) as stream:
                async for text in stream.text_stream:
                    yield text
        except anthropic.APIError as exc:
            logger.exception("Anthropic streaming API error")
            raise LLMError(f"Anthropic API error: {exc}") from exc

    async def rerank(
        self,
        question: str,
        candidates: list[str],
        top_k: int,
    ) -> list[tuple[int, float]]:
        """
        Ask Claude to score each candidate on a 0–10 scale and return the
        top-k by score as (original_index, normalized_score) pairs.

        Normalized score = claude_score / 10.0, so it sits in [0, 1] and is
        loosely comparable to Chroma/BM25 scores.

        On any parsing failure we fall back to preserving input order with
        a neutral score of 0.0 — the caller still gets a valid ranking (the
        BM25 order it passed in) and the error is logged.
        """
        if not candidates:
            return []

        # Build the numbered chunk block, truncating each candidate to keep
        # the prompt bounded even for large first-stage candidate pools.
        numbered: list[str] = []
        for i, text in enumerate(candidates, start=1):
            snippet = text.strip().replace("\n", " ")
            if len(snippet) > _RERANK_CHUNK_CHARS:
                snippet = snippet[:_RERANK_CHUNK_CHARS] + "..."
            numbered.append(f"[{i}] {snippet}")

        user_prompt = (
            f"{_RERANK_PREAMBLE}"
            f"Question: {question}\n\n"
            f"Chunks:\n" + "\n".join(numbered)
        )

        try:
            response = await self._client.messages.create(
                model=self._rerank_model,
                max_tokens=2048,
                temperature=0.0,
                system=_RERANK_SYSTEM,
                messages=[{"role": "user", "content": user_prompt}],
            )
        except anthropic.APIError as exc:
            logger.warning("Rerank call failed, keeping input order: %s", exc)
            return [(i, 0.0) for i in range(min(top_k, len(candidates)))]

        text = "".join(
            b.text for b in response.content if getattr(b, "type", None) == "text"
        )

        # The model is instructed to return ONLY a JSON array, but we
        # tolerate small preambles/suffixes by regex-extracting the first
        # JSON array block.
        match = _JSON_ARRAY_RE.search(text)
        if not match:
            logger.warning(
                "Rerank response had no JSON array, keeping input order. "
                "Response head: %r",
                text[:200],
            )
            return [(i, 0.0) for i in range(min(top_k, len(candidates)))]

        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            logger.warning("Rerank JSON parse failed (%s), keeping input order", exc)
            return [(i, 0.0) for i in range(min(top_k, len(candidates)))]

        scored: list[tuple[int, float]] = []
        seen: set[int] = set()
        for entry in parsed:
            if not isinstance(entry, dict):
                continue
            try:
                one_based = int(entry["id"])
                score = float(entry["score"])
            except (KeyError, TypeError, ValueError):
                continue
            idx = one_based - 1
            if idx < 0 or idx >= len(candidates) or idx in seen:
                continue
            seen.add(idx)
            scored.append((idx, max(0.0, min(1.0, score / 10.0))))

        # Sort by score desc, then trim to top_k.
        scored.sort(key=lambda pair: pair[1], reverse=True)
        return scored[:top_k]
