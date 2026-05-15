"""
RAG layer: load the existing Chroma vector store, retrieve relevant chunks,
and assemble the prompt that gets sent to Claude.

The Chroma collection and embedding model MUST stay in sync with
Pipeline/ingest.py — otherwise embeddings will be incompatible and retrieval
will silently return garbage.
"""

import logging
import os
import re
from dataclasses import dataclass, field

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from .config import Settings
from .schemas import Message, SourceChunk

logger = logging.getLogger(__name__)


# ---------- System prompt ----------
#
# Evidence-first: every factual claim must be grounded in the retrieved context.
# Claude must not infer, speculate, or expand on what isn't explicitly stated.

SYSTEM_PROMPT = (
    "You are Vaughn Eugenio's personal AI assistant, here to help recruiters, "
    "collaborators, and curious visitors learn about his professional background. "
    "Be warm, enthusiastic, and conversational — you're representing someone you "
    "genuinely believe in. Keep answers concise but human; avoid sounding like a "
    "database readout.\n\n"
    "Vaughn's career goal is to land a role in Solutions Engineering, Solutions "
    "Architecture, Technical Consulting, or a similar position at the intersection "
    "of engineering and people. He thrives in roles where he gets to translate "
    "complex technical concepts for non-technical stakeholders, build relationships, "
    "and help clients or teams succeed. If anyone asks whether Vaughn would be a "
    "good fit for those types of roles, answer with genuine enthusiasm — draw on "
    "his experience bridging technical and business contexts, his communication "
    "skills, and his track record of working across teams. Make it clear that "
    "Vaughn doesn't just write code in a corner — he loves talking to people and "
    "is at his best when engineering meets human connection.\n\n"
    "Follow these guidelines:\n\n"
    "1. Base your answers on the context provided in each message. You may draw "
    "reasonable conclusions from that context (e.g. inferring a soft skill from a "
    "described accomplishment), but do not fabricate specific facts like dates, "
    "company names, or technologies that aren't present.\n"
    "2. If the context doesn't contain enough information to answer or If someone asks something completely unrelated to Vaughn's background, say: "
    "\"I'm not exactly sure, but the real Vaughn should have the answer (he's a pretty smart guy). "
    "Feel free to reach out:\\n"
    "- Phone: 732-501-8621\\n"
    "- Email: vaughndde@gmail.com\\n"
    "- LinkedIn: https://www.linkedin.com/in/vaughn-d-eugenio\\n"
    "- Calendly: https://calendly.com/vaughndde\"\n"
    "3. Dates, company names, technologies, and role titles must be stated "
    "exactly as they appear in the context — never paraphrase or generalize them.\n"
    "4. Do not combine facts across different roles unless the question "
    "explicitly asks for a comparison.\n"
    "5. When citing a fact, you may reference the source document name shown "
    "in the [source: ...] tags alongside each context block.\n"
    "6. Do not repeat information you have already shared in this conversation. "
    "If a topic or story has already been mentioned, acknowledge it briefly and "
    "move on to new details — don't re-explain the same project, role, or "
    "accomplishment twice in the same thread.\n"
)


def get_system_prompt(visitor_context=None) -> str:
    """
    Return the system prompt string, optionally augmented with visitor context.

    Builds a fresh string each call so the per-request injection is never
    shared across requests (SYSTEM_PROMPT remains a pristine module constant).
    """
    system_prompt = SYSTEM_PROMPT
    if visitor_context is not None:
        lines = []
        if getattr(visitor_context, "name", None):
            lines.append(f"Visitor name: {visitor_context.name}")
        if getattr(visitor_context, "company", None):
            lines.append(f"Company: {visitor_context.company}")
        if getattr(visitor_context, "role", None):
            lines.append(f"Role being considered: {visitor_context.role}")
        if lines:
            system_prompt = system_prompt + "\n\nVisitor context:\n" + "\n".join(lines)
            system_prompt += (
                "\nTailor your responses to explain why Vaughn is a great fit for "
                "this specific role and company when relevant."
            )
    return system_prompt


def load_vectorstore(settings: Settings) -> Chroma:
    """Open the persisted Chroma collection created by ingest.py."""
    os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)

    embeddings = OpenAIEmbeddings(model=settings.embedding_model)

    vectorstore = Chroma(
        collection_name=settings.collection_name,
        embedding_function=embeddings,
        persist_directory=settings.chroma_dir,
    )
    logger.info(
        "Opened Chroma collection '%s' at %s",
        settings.collection_name,
        settings.chroma_dir,
    )
    return vectorstore


def chunk_count(vectorstore: Chroma) -> int | None:
    """Return the number of vectors in the collection, or None on failure."""
    try:
        return vectorstore._collection.count()  # type: ignore[attr-defined]
    except Exception as exc:  # pragma: no cover
        logger.warning("Could not read chunk count: %s", exc)
        return None


# ---------- Query expansion ----------
#
# Appends synonym/entity lists to the query so the embedding model can find
# chunks whose wording differs from the question (e.g. "real-time middleware"
# → TrackSync). Multiple groups can fire on the same query.
#
# Format: (set of trigger words, expansion string)

EXPANSION_GROUPS: list[tuple[set[str], str]] = [
    # Generic behavioral triggers
    (
        {"efficient", "efficiency", "efficiently"},
        "optimized performance faster improved streamlined reduced enhanced",
    ),
    (
        {"project", "projects"},
        "work built developed created implemented system",
    ),
    (
        {"personal", "side", "hobby", "own", "outside"},
        "VaughnKey smartlock ESP32 BLE firmware IoT AI chatbot RAG portfolio personal website job tracker Gmail OAuth SQLite",
    ),
    (
        {"tracker", "gmail", "oauth", "hunt", "hunting", "applying"},
        "job application tracker Gmail OAuth SQLite Python scraping dashboard status applying companies",
    ),
    (
        {"problem", "problems", "solve", "solved", "solving"},
        "challenge issue edge case bug fixed resolved",
    ),
    (
        {"time", "when", "example", "instance"},
        "specific story case experience",
    ),
    (
        {"system", "systems"},
        "architecture infrastructure platform service",
    ),
    (
        {"work", "worked", "working", "employer", "employment",
         "company", "companies", "where", "experience", "career", "history",
         "role", "roles", "position"},
        "DraftKings SRC Inc software engineer daily fantasy sports defense contractor TrackSync COMET",
    ),
    # Company-specific triggers — boost exact entity recall in BM25
    (
        {"src", "tracksync", "military", "defense", "clearance", "tak", "cop"},
        "TrackSync COMET TAK COP translation middleware Java Spring Boot "
        "defense contractor Secret clearance military tracks",
    ),
    (
        {"draftkings", "dfs", "fantasy", "sports", "ohtani"},
        "DraftKings daily fantasy sports C# .NET Orleans microservices "
        "Redis RabbitMQ Kubernetes Ohtani Abacus Titan Scoreboard",
    ),
    (
        {"smartlock", "lock", "iot", "embedded", "firmware", "esp32", "ble"},
        "ESP32 BLE servo capacitive touch firmware deep-sleep VaughnKey "
        "smart lock 3D-printed Bluetooth",
    ),
    (
        {"marsh", "mclennan", "swampfox", "intern", "internship"},
        "Marsh McLennan Swampfox internship Python Pandas clustering "
        "K-Means BIRCH SFValid CCXML VXML",
    ),
]

_WORD_RE = re.compile(r"[a-z0-9]+")


def expand_query(question: str) -> tuple[str, list[str]]:
    """
    Append synonym lists to a question when trigger words fire.

    Returns (expanded_query, triggered_groups).
    """
    tokens = set(_WORD_RE.findall(question.lower()))
    appended: list[str] = []
    for triggers, expansion in EXPANSION_GROUPS:
        if tokens & triggers:
            appended.append(expansion)
    if not appended:
        return question, []
    return question + " " + " ".join(appended), appended


def build_retrieval_query(
    question: str,
    history: list[Message],
    max_turns: int = 4,
) -> str:
    """
    Build the text used to embed for similarity search.

    Short follow-ups ("tell me more", "what else?") carry almost no semantic
    signal alone, so we include recent USER messages for context. Assistant
    messages are deliberately excluded — they are long and verbose, and
    including them biases the embedding toward whatever was last discussed,
    causing the same chunks to be retrieved repeatedly across turns.
    """
    if not history:
        return question

    recent_user = [m for m in history[-max_turns * 2:] if m.role == "user"][-max_turns:]
    if not recent_user:
        return question

    parts = [m.content for m in recent_user]
    parts.append(question)
    return "\n".join(parts)


# ---------- Metadata filtering ----------
#
# When a query clearly targets a specific employer or project, we pass a
# ChromaDB `where` filter to restrict the vector search to matching chunks.
# This improves precision for company-scoped questions without an LLM call.

_COMPANY_KEYWORDS: dict[str, str] = {
    # SRC / military project
    "src": "src",
    "tracksync": "src",
    "comet": "src",
    "military": "src",
    "tak": "src",
    "cop": "src",
    "clearance": "src",
    # DraftKings
    "draftkings": "draftkings",
    "draftking": "draftkings",
    "dfs": "draftkings",
    "ohtani": "draftkings",
    # Internships
    "swampfox": "swampfox",
    "marsh": "marsh_mclennan",
    "mclennan": "marsh_mclennan",
    # Personal / side projects (VaughnKey, AI chatbot, Job Tracker)
    "smartlock": "personal",
    "vaughnkey": "personal",
    "esp32": "personal",
    "chatbot": "personal",
    "job tracker": "personal",
    "gmail": "personal",
}

# Multi-word phrases that indicate a personal-project query.
# Checked separately since dict key matching is single-word only.
_PERSONAL_PROJECT_PHRASES = [
    "personal project",
    "side project",
    "personal projects",
    "side projects",
    "own project",
    "built on my own",
    "built outside",
]


def detect_company_filter(query: str) -> dict | None:
    """
    Return a ChromaDB metadata filter dict if the query mentions a specific
    employer or project, otherwise return None (no pre-filtering).

    Checks single-word keywords first, then multi-word personal-project phrases.
    """
    lower = query.lower()
    # Single-word keyword check
    for keyword, company in _COMPANY_KEYWORDS.items():
        if keyword in lower:
            return {"company": company}
    # Multi-word phrase check for personal/side project queries
    for phrase in _PERSONAL_PROJECT_PHRASES:
        if phrase in lower:
            return {"company": "personal"}
    return None


# ---------- Retrieval trace ----------

@dataclass
class RetrievalTrace:
    """Diagnostic record describing a single retrieval call."""

    original_query: str
    expanded_query: str
    retrieval_query: str
    expansions_applied: list[str] = field(default_factory=list)
    k: int = 0
    min_score: float | None = None
    results: list[tuple[Document, float]] = field(default_factory=list)
    dropped_below_threshold: int = 0
    label: str = "retrieval"
    company_filter: dict | None = None


def retrieve(
    vectorstore: Chroma,
    question: str,
    k: int,
    history: list[Message] | None = None,
    min_score: float | None = None,
    enable_expansion: bool = True,
    where_filter: dict | None = None,
) -> RetrievalTrace:
    """
    Run similarity search with relevance scores and return a full trace.

    Pipeline:
      1. Optionally expand `question` via synonym groups.
      2. Merge with recent chat history.
      3. Optionally apply a metadata pre-filter (`where_filter`).
      4. Call Chroma's similarity_search_with_relevance_scores.
      5. Optionally drop results below `min_score`.
    """
    if enable_expansion:
        expanded, applied = expand_query(question)
    else:
        expanded, applied = question, []

    retrieval_query = build_retrieval_query(expanded, history or [])

    search_kwargs: dict = {"k": k}
    if where_filter:
        search_kwargs["filter"] = where_filter

    raw_results: list[tuple[Document, float]] = (
        vectorstore.similarity_search_with_relevance_scores(
            retrieval_query, **search_kwargs
        )
    )

    if min_score is not None:
        kept = [(d, s) for d, s in raw_results if s >= min_score]
        dropped = len(raw_results) - len(kept)
    else:
        kept, dropped = raw_results, 0

    trace = RetrievalTrace(
        original_query=question,
        expanded_query=expanded,
        retrieval_query=retrieval_query,
        expansions_applied=applied,
        k=k,
        min_score=min_score,
        results=kept,
        dropped_below_threshold=dropped,
        label="vector",
        company_filter=where_filter,
    )

    _log_trace(trace)
    return trace


def _log_trace(trace: RetrievalTrace) -> None:
    """Emit a structured, human-readable dump of a retrieval call."""
    logger.info("---- %s trace ----", trace.label)
    logger.info("original_query : %r", trace.original_query)
    if trace.company_filter:
        logger.info("company_filter : %s", trace.company_filter)
    if trace.expansions_applied:
        logger.info("expanded_query : %r", trace.expanded_query)
        logger.info("expansions     : %s", trace.expansions_applied)
    else:
        logger.info("expansions     : (none fired)")
    if trace.retrieval_query != trace.expanded_query:
        logger.info("retrieval_query: %r (history-merged)", trace.retrieval_query)
    logger.info(
        "k=%d min_score=%s returned=%d dropped=%d",
        trace.k,
        trace.min_score,
        len(trace.results),
        trace.dropped_below_threshold,
    )
    for i, (doc, score) in enumerate(trace.results, start=1):
        filename = doc.metadata.get("filename", "unknown")
        chunk_id = doc.metadata.get("chunk_id", "?")
        company = doc.metadata.get("company", "")
        preview = doc.page_content.strip().replace("\n", " ")[:100]
        logger.info(
            "  #%2d  score=%.4f  %s#%s  company=%r  %s",
            i, score, filename, chunk_id, company, preview,
        )
    logger.info("-------------------------")


def build_prompt(
    question: str,
    scored_docs: list[tuple[Document, float]],
) -> str:
    """Assemble the user-facing prompt with inlined context blocks."""
    if not scored_docs:
        context_block = "(no relevant context was found in the knowledge base)"
    else:
        parts: list[str] = []
        for doc, _score in scored_docs:
            filename = doc.metadata.get("filename", "unknown")
            chunk_id = doc.metadata.get("chunk_id", "?")
            doc_name = doc.metadata.get("doc_name", "")
            label = f"{filename}#{chunk_id}" + (f" | {doc_name}" if doc_name else "")
            parts.append(
                f"[source: {label}]\n{doc.page_content.strip()}"
            )
        context_block = "\n\n---\n\n".join(parts)

    return (
        f"Use the following context to answer the question.\n\n"
        f"<context>\n{context_block}\n</context>\n\n"
        f"Question: {question}"
    )


def format_sources(
    scored_docs: list[tuple[Document, float]],
) -> list[SourceChunk]:
    """Convert retrieved (Document, score) pairs into SourceChunk payloads."""
    out: list[SourceChunk] = []
    for doc, score in scored_docs:
        preview = doc.page_content.strip().replace("\n", " ")
        if len(preview) > 200:
            preview = preview[:200] + "..."
        out.append(
            SourceChunk(
                filename=doc.metadata.get("filename", "unknown"),
                chunk_id=doc.metadata.get("chunk_id"),
                preview=preview,
                score=round(float(score), 4),
            )
        )
    return out


# ---------- BM25 retrieval ----------

def retrieve_bm25(
    bm25_index,
    question: str,
    k: int,
    history: list[Message] | None = None,
    enable_expansion: bool = True,
) -> RetrievalTrace:
    """BM25-only retrieval. Same query-prep pipeline as vector retrieve()."""
    if enable_expansion:
        expanded, applied = expand_query(question)
    else:
        expanded, applied = question, []

    retrieval_query = build_retrieval_query(expanded, history or [])
    results = bm25_index.search(retrieval_query, k=k)

    trace = RetrievalTrace(
        original_query=question,
        expanded_query=expanded,
        retrieval_query=retrieval_query,
        expansions_applied=applied,
        k=k,
        min_score=None,
        results=results,
        dropped_below_threshold=0,
        label="bm25",
    )
    _log_trace(trace)
    return trace


# ---------- Reciprocal Rank Fusion (RRF) ----------
#
# True hybrid search: run both vector and BM25 retrievers independently, then
# fuse their ranked lists using Reciprocal Rank Fusion. This avoids the
# score-normalization problem (vector and BM25 scores live on different scales)
# by using only rank position: contribution = 1 / (rrf_k + rank + 1).
#
# A chunk appearing in both lists scores twice, so results surfaced by both
# retrievers float to the top. rrf_k=60 is the standard default from the
# original RRF paper.

def retrieve_rrf(
    vectorstore: Chroma,
    bm25_index,
    question: str,
    k: int,
    history: list[Message] | None = None,
    enable_expansion: bool = True,
    where_filter: dict | None = None,
    rrf_k: int = 60,
) -> RetrievalTrace:
    """
    Reciprocal Rank Fusion of vector and BM25 retrieval.

    Both retrievers fetch a wider candidate pool (k*3, capped at 30), then
    RRF re-ranks the union and returns the top k results.
    """
    if enable_expansion:
        expanded, applied = expand_query(question)
    else:
        expanded, applied = question, []

    retrieval_query = build_retrieval_query(expanded, history or [])
    candidate_k = min(k * 3, 30)

    # Vector retrieval (with optional company pre-filter)
    vec_kwargs: dict = {"k": candidate_k}
    if where_filter:
        vec_kwargs["filter"] = where_filter

    vector_raw: list[tuple[Document, float]] = (
        vectorstore.similarity_search_with_relevance_scores(
            retrieval_query, **vec_kwargs
        )
    )

    # BM25 retrieval (no pre-filter — it sees all chunks, but company-specific
    # chunks naturally rank higher when the query contains company keywords)
    bm25_raw: list[tuple[Document, float]] = bm25_index.search(
        retrieval_query, k=candidate_k
    )

    # RRF fusion — key: (doc_id, chunk_id) uniquely identifies each chunk
    rrf_scores: dict[str, float] = {}
    doc_map: dict[str, tuple[Document, float]] = {}

    def _key(doc: Document) -> str:
        return f"{doc.metadata.get('doc_id', 'x')}_{doc.metadata.get('chunk_id', 0)}"

    for rank, (doc, score) in enumerate(vector_raw):
        key = _key(doc)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)
        if key not in doc_map or score > doc_map[key][1]:
            doc_map[key] = (doc, score)

    for rank, (doc, score) in enumerate(bm25_raw):
        key = _key(doc)
        rrf_scores[key] = rrf_scores.get(key, 0.0) + 1.0 / (rrf_k + rank + 1)
        if key not in doc_map or score > doc_map[key][1]:
            doc_map[key] = (doc, score)

    sorted_keys = sorted(rrf_scores, key=lambda kk: rrf_scores[kk], reverse=True)[:k]
    fused_results: list[tuple[Document, float]] = [
        (doc_map[key][0], rrf_scores[key]) for key in sorted_keys
    ]

    candidate_total = len(set(
        [_key(d) for d, _ in vector_raw] + [_key(d) for d, _ in bm25_raw]
    ))

    trace = RetrievalTrace(
        original_query=question,
        expanded_query=expanded,
        retrieval_query=retrieval_query,
        expansions_applied=applied,
        k=k,
        min_score=None,
        results=fused_results,
        dropped_below_threshold=max(0, candidate_total - len(fused_results)),
        label="rrf",
        company_filter=where_filter,
    )
    _log_trace(trace)
    return trace


# ---------- BM25 → Claude rerank (legacy hybrid) ----------
#
# Kept for the /api/debug/compare endpoint so operators can still compare all
# three retrieval modes side-by-side. The default chat path uses RRF instead.

async def rerank_candidates(
    llm,
    question: str,
    scored_candidates: list[tuple[Document, float]],
    top_k: int,
) -> list[tuple[Document, float]]:
    """Re-rank candidates by asking Claude to score each for relevance."""
    if not scored_candidates:
        return []

    texts = [doc.page_content for doc, _ in scored_candidates]
    ranked = await llm.rerank(question=question, candidates=texts, top_k=top_k)
    return [(scored_candidates[idx][0], score) for idx, score in ranked]


async def retrieve_hybrid(
    bm25_index,
    llm,
    question: str,
    candidates_k: int,
    final_k: int,
    history: list[Message] | None = None,
    enable_expansion: bool = True,
) -> RetrievalTrace:
    """BM25 first stage → Claude rerank → top final_k (legacy mode)."""
    first_stage = retrieve_bm25(
        bm25_index,
        question,
        k=candidates_k,
        history=history,
        enable_expansion=enable_expansion,
    )

    reranked = await rerank_candidates(
        llm,
        question=question,
        scored_candidates=first_stage.results,
        top_k=final_k,
    )

    trace = RetrievalTrace(
        original_query=first_stage.original_query,
        expanded_query=first_stage.expanded_query,
        retrieval_query=first_stage.retrieval_query,
        expansions_applied=first_stage.expansions_applied,
        k=final_k,
        min_score=None,
        results=reranked,
        dropped_below_threshold=max(0, len(first_stage.results) - len(reranked)),
        label="reranked",
    )
    _log_trace(trace)
    return trace
