"""
FastAPI entrypoint for the Vaughn RAG backend.

Endpoints:
    GET  /health    - liveness + vector store status
    POST /api/chat  - answer a question using RAG over Vaughn's personal docs

Run with:
    uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware

from .bm25 import BM25Index
from .config import Settings, get_settings
from .llm import ClaudeClient, LLMError
from .rag import (
    SYSTEM_PROMPT,
    build_prompt,
    chunk_count,
    detect_company_filter,
    format_sources,
    load_vectorstore,
    retrieve,
    retrieve_bm25,
    retrieve_hybrid,
    retrieve_rrf,
)
from .schemas import (
    ChatRequest,
    ChatResponse,
    CompareRequest,
    CompareResponse,
    DebugRetrieveRequest,
    DebugRetrieveResponse,
    HealthResponse,
    Message,
)

# Hard cap on how many prior messages we forward to Claude. Keeps the request
# bounded so a long-running thread can't blow past Claude's context window.
MAX_HISTORY_MESSAGES = 20

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("vaughn-rag")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load expensive resources (vector store, LLM client) once at startup."""
    settings = get_settings()
    app.state.settings = settings
    app.state.vectorstore = None
    app.state.chunk_count = None
    app.state.llm = None
    app.state.bm25 = None

    try:
        app.state.vectorstore = load_vectorstore(settings)
        app.state.chunk_count = chunk_count(app.state.vectorstore)
        logger.info("Vectorstore loaded: %s chunks", app.state.chunk_count)
    except Exception:
        # Don't crash the process — /health will report the failure so the
        # operator can diagnose without losing the rest of the app.
        logger.exception("Failed to load vector store at startup")

    # BM25 index is built from the same Chroma collection. If Chroma failed
    # above, skip BM25 too — its requests will 503 cleanly.
    if app.state.vectorstore is not None:
        try:
            app.state.bm25 = BM25Index.from_vectorstore(app.state.vectorstore)
        except Exception:
            logger.exception("Failed to build BM25 index at startup")

    try:
        app.state.llm = ClaudeClient(settings)
        logger.info("Anthropic client initialized (model=%s)", settings.claude_model)
    except Exception:
        logger.exception("Failed to initialize Anthropic client")

    yield
    # Nothing to clean up — Chroma persists to disk and the HTTP client is GC'd.


app = FastAPI(
    title="Vaughn RAG API",
    description="Retrieval-augmented chat over Vaughn's personal documents.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow the frontend(s) configured via env var.
_settings_for_cors: Settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings_for_cors.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", response_model=HealthResponse, tags=["meta"])
async def health(request: Request) -> HealthResponse:
    """Lightweight readiness probe."""
    vs_loaded = request.app.state.vectorstore is not None
    return HealthResponse(
        status="ok" if vs_loaded else "degraded",
        vectorstore_loaded=vs_loaded,
        chunk_count=request.app.state.chunk_count,
    )


@app.post(
    "/api/chat",
    response_model=ChatResponse,
    tags=["chat"],
    summary="Ask a question about Vaughn",
)
async def chat(
    payload: ChatRequest,
    request: Request,
    use_bm25: bool | None = Query(
        default=None,
        description=(
            "Retriever override. None = use settings.enable_bm25 default. "
            "true = BM25 first stage + Claude rerank. false = vector only."
        ),
    ),
) -> ChatResponse:
    """Answer a question by retrieving relevant chunks and calling Claude."""
    settings: Settings = request.app.state.settings
    vectorstore = request.app.state.vectorstore
    llm: ClaudeClient | None = request.app.state.llm
    bm25_index: BM25Index | None = request.app.state.bm25

    if vectorstore is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store is not loaded. Check server logs.",
        )
    if llm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM client is not initialized. Check server logs.",
        )

    # Decide which retriever to use for this request.
    use_hybrid = settings.enable_bm25 if use_bm25 is None else use_bm25
    if use_hybrid and bm25_index is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BM25 index is not loaded. Check server logs.",
        )

    question = payload.question.strip()
    # Truncate history to the most recent N messages so the prompt stays bounded.
    history: list[Message] = payload.conversation_history[-MAX_HISTORY_MESSAGES:]
    # Anthropic requires the messages array to start with a user turn. If
    # truncation left a leading assistant message, drop it.
    while history and history[0].role != "user":
        history = history[1:]
    logger.info(
        "chat request: %r (history=%d turns, truncated from %d, retriever=%s)",
        question,
        len(history),
        len(payload.conversation_history),
        "rrf" if use_hybrid else "vector",
    )

    # Detect company-specific queries and pre-filter metadata accordingly.
    company_filter = detect_company_filter(question)
    if company_filter:
        logger.info("chat: company filter detected: %s", company_filter)

    try:
        if use_hybrid:
            # RRF hybrid: fuses vector + BM25 without an extra LLM rerank call.
            trace = retrieve_rrf(
                vectorstore,
                bm25_index,
                question,
                k=settings.top_k,
                history=history,
                enable_expansion=settings.enable_query_expansion,
                where_filter=company_filter,
            )
        else:
            trace = retrieve(
                vectorstore,
                question,
                k=settings.top_k,
                history=history,
                min_score=settings.min_similarity_score,
                enable_expansion=settings.enable_query_expansion,
                where_filter=company_filter,
            )

        # The current user turn carries the freshly-retrieved RAG context.
        # Prior turns are forwarded as-is so Claude sees the full thread.
        user_prompt = build_prompt(question, trace.results)
        messages: list[dict] = [
            {"role": m.role, "content": m.content} for m in history
        ]
        messages.append({"role": "user", "content": user_prompt})

        answer_text = llm.answer(system=SYSTEM_PROMPT, messages=messages)
        sources = format_sources(trace.results)
        return ChatResponse(answer=answer_text, sources=sources)

    except LLMError as exc:
        logger.exception("LLM call failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Upstream LLM error: {exc}",
        ) from exc
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unhandled error while answering chat request")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error while processing the question.",
        )


@app.post(
    "/api/debug/retrieve",
    response_model=DebugRetrieveResponse,
    tags=["debug"],
    summary="Inspect what retrieval would return (no LLM call)",
)
async def debug_retrieve(
    payload: DebugRetrieveRequest,
    request: Request,
) -> DebugRetrieveResponse:
    """
    Run the retrieval pipeline and return the full trace — original query,
    expanded query, per-chunk scores, and source filenames — WITHOUT calling
    Claude. Use this to verify that the chunks you expect are being retrieved
    and ranked correctly.
    """
    settings: Settings = request.app.state.settings
    vectorstore = request.app.state.vectorstore

    if vectorstore is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store is not loaded. Check server logs.",
        )

    history: list[Message] = payload.conversation_history[-MAX_HISTORY_MESSAGES:]
    while history and history[0].role != "user":
        history = history[1:]

    k = payload.k if payload.k is not None else settings.top_k
    min_score = (
        payload.min_score
        if payload.min_score is not None
        else settings.min_similarity_score
    )
    enable_expansion = (
        payload.enable_expansion
        if payload.enable_expansion is not None
        else settings.enable_query_expansion
    )

    trace = retrieve(
        vectorstore,
        payload.question.strip(),
        k=k,
        history=history,
        min_score=min_score,
        enable_expansion=enable_expansion,
    )

    return _trace_to_response(trace)


def _trace_to_response(trace) -> DebugRetrieveResponse:
    """Convert a RetrievalTrace into the JSON-ready debug response shape."""
    return DebugRetrieveResponse(
        original_query=trace.original_query,
        expanded_query=trace.expanded_query,
        retrieval_query=trace.retrieval_query,
        expansions_applied=trace.expansions_applied,
        k=trace.k,
        min_score=trace.min_score,
        returned=len(trace.results),
        dropped_below_threshold=trace.dropped_below_threshold,
        chunks=format_sources(trace.results),
    )


@app.post(
    "/api/debug/compare",
    response_model=CompareResponse,
    tags=["debug"],
    summary="Run vector, BM25, and BM25+rerank side-by-side for one question",
)
async def debug_compare(
    payload: CompareRequest,
    request: Request,
) -> CompareResponse:
    """
    Run all three retrievers on the same question and return their traces
    side-by-side so you can diff which chunks each approach surfaces.

    Makes exactly one LLM call (the rerank pass). Does NOT call the answer
    model, so this is safe to hammer while tuning retrieval.
    """
    settings: Settings = request.app.state.settings
    vectorstore = request.app.state.vectorstore
    bm25_index: BM25Index | None = request.app.state.bm25
    llm: ClaudeClient | None = request.app.state.llm

    if vectorstore is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Vector store is not loaded. Check server logs.",
        )
    if bm25_index is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BM25 index is not loaded. Check server logs.",
        )
    if llm is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLM client is not initialized. Check server logs.",
        )

    history: list[Message] = payload.conversation_history[-MAX_HISTORY_MESSAGES:]
    while history and history[0].role != "user":
        history = history[1:]

    candidates_k = (
        payload.candidates_k
        if payload.candidates_k is not None
        else settings.bm25_candidates
    )
    final_k = (
        payload.final_k if payload.final_k is not None else settings.rerank_top_k
    )
    enable_expansion = (
        payload.enable_expansion
        if payload.enable_expansion is not None
        else settings.enable_query_expansion
    )
    question = payload.question.strip()

    # 1) Vector-only (uses settings.top_k or final_k override for fair comparison)
    vector_trace = retrieve(
        vectorstore,
        question,
        k=final_k,
        history=history,
        min_score=None,
        enable_expansion=enable_expansion,
    )

    # 2) BM25-only (candidate pool size)
    bm25_trace = retrieve_bm25(
        bm25_index,
        question,
        k=candidates_k,
        history=history,
        enable_expansion=enable_expansion,
    )

    # 3) BM25 → Claude rerank → final_k
    hybrid_trace = retrieve_hybrid(
        bm25_index,
        llm,
        question,
        candidates_k=candidates_k,
        final_k=final_k,
        history=history,
        enable_expansion=enable_expansion,
    )

    return CompareResponse(
        question=question,
        vector=_trace_to_response(vector_trace),
        bm25=_trace_to_response(bm25_trace),
        hybrid_reranked=_trace_to_response(hybrid_trace),
    )
