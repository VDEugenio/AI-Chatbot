"""
FastAPI entrypoint for the Vaughn RAG backend.

Endpoints:
    GET  /health    - liveness + vector store status
    POST /api/chat  - answer a question using RAG over Vaughn's personal docs

Run with:
    uvicorn app.main:app --reload --port 8000
"""

import asyncio
import json
import logging
import time
import urllib.parse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, StreamingResponse

from .bm25 import BM25Index
from .config import Settings, get_settings
from . import db
from .geoip import lookup as geoip_lookup
from .llm import ClaudeClient, LLMError
from .notify import TelegramNotifier
from .rag import (
    SYSTEM_PROMPT,
    build_prompt,
    chunk_count,
    detect_company_filter,
    format_sources,
    get_system_prompt,
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
    IntakeRequest,
    Message,
    RagAnswersRequest,
    RagFilesResponse,
    RagQuestionsRequest,
    RagQuestionsResponse,
    VisitRequest,
    VisitResponse,
)
from .rag_review import synthesize_and_store
from .db import save_rag_run, get_latest_pending_run, get_run, mark_run_committed

# Hard cap on how many prior messages we forward to Claude. Keeps the request
# bounded so a long-running thread can't blow past Claude's context window.
MAX_HISTORY_MESSAGES = 20

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
# Silence httpx's per-request URL logging at INFO. Critical for security:
# Telegram's bot API encodes the bot token directly in the URL path, so
# letting httpx INFO-log every request would leak the token into CloudWatch.
# Real failures still surface at WARNING/ERROR.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("vaughn-rag")


def verify_admin_key(x_admin_key: str = Header(default="")) -> None:
    """Shared dependency for admin-protected endpoints."""
    settings = get_settings()
    if not settings.admin_key or x_admin_key != settings.admin_key:
        raise HTTPException(status_code=403, detail="Forbidden")


def _client_ip(request: Request) -> str:
    """
    Resolve the original client IP behind any proxy/load balancer.

    App Runner (and most reverse proxies) forward the real client IP via
    `X-Forwarded-For: client, proxy1, proxy2`. Falling back to
    `request.client.host` is correct for direct connections (local dev).
    """
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    return request.client.host if request.client else "unknown"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load expensive resources (vector store, LLM client) once at startup."""
    settings = get_settings()
    app.state.settings = settings
    app.state.vectorstore = None
    app.state.chunk_count = None
    app.state.llm = None
    app.state.bm25 = None
    app.state.notifier = TelegramNotifier(settings)

    try:
        db.init_db()
        logger.info("SQLite visitor DB initialised")
    except Exception:
        logger.exception("Failed to initialise SQLite DB")

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

    # Shutdown — close the Telegram HTTP client so we don't leak sockets.
    try:
        await app.state.notifier.aclose()
    except Exception:
        logger.exception("Failed to close Telegram notifier")


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
    background_tasks: BackgroundTasks,
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

    # Update last_seen for the session if the frontend provided one.
    if payload.session_id:
        asyncio.create_task(asyncio.to_thread(db.touch_session, payload.session_id))

    # Detect company-specific queries and pre-filter metadata accordingly.
    company_filter = detect_company_filter(question)
    if company_filter:
        logger.info("chat: company filter detected: %s", company_filter)

    started_at = time.perf_counter()

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

        system_prompt = get_system_prompt(payload.visitor_context)
        answer_text = await llm.answer(system=system_prompt, messages=messages)
        sources = format_sources(trace.results)

        # Fire-and-forget Telegram notification. No-op if creds aren't set.
        notifier: TelegramNotifier = request.app.state.notifier
        if notifier.enabled:
            background_tasks.add_task(
                notifier.notify_chat,
                question=question,
                answer_preview=answer_text,
                ip=_client_ip(request),
                retriever="rrf" if use_hybrid else "vector",
                sources_count=len(sources),
                elapsed_s=time.perf_counter() - started_at,
                user_agent=request.headers.get("user-agent"),
                visitor_context=payload.visitor_context,
            )

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
    hybrid_trace = await retrieve_hybrid(
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


async def _sse_chat_generator(
    llm: ClaudeClient,
    system: str,
    messages: list[dict],
    sources: list,
    notifier: "TelegramNotifier | None" = None,
    question: str = "",
    ip: str = "unknown",
    retriever: str = "vector",
    sources_count: int = 0,
    started_at: float = 0.0,
    user_agent: str | None = None,
    visitor_context=None,
) -> AsyncIterator[str]:
    """
    Async generator that drives the SSE stream for /api/chat/stream.

    Event types sent to the client:
      text_delta  — one or more characters of the answer as they arrive
      sources     — retrieved chunks, sent once after the stream finishes
      done        — signals the stream is complete; client should close
      error       — LLM failure; client should surface the message
    """
    chunks: list[str] = []
    try:
        async for text in llm.answer_stream(system, messages):
            chunks.append(text)
            yield f"data: {json.dumps({'type': 'text_delta', 'text': text})}\n\n"
        yield f"data: {json.dumps({'type': 'sources', 'sources': [s.model_dump() for s in sources]})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        if notifier is not None and notifier.enabled:
            asyncio.create_task(notifier.notify_chat(
                question=question,
                answer_preview="".join(chunks),
                ip=ip,
                retriever=retriever,
                sources_count=sources_count,
                elapsed_s=time.perf_counter() - started_at,
                user_agent=user_agent,
                visitor_context=visitor_context,
            ))
    except LLMError as exc:
        logger.exception("LLM streaming call failed")
        yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"


@app.post(
    "/api/chat/stream",
    tags=["chat"],
    summary="Stream an answer about Vaughn (SSE)",
    response_class=StreamingResponse,
)
async def chat_stream(
    payload: ChatRequest,
    request: Request,
    use_bm25: bool | None = Query(
        default=None,
        description=(
            "Retriever override. None = use settings.enable_bm25 default. "
            "true = RRF hybrid. false = vector only."
        ),
    ),
) -> StreamingResponse:
    """
    Same retrieval pipeline as /api/chat, but streams the answer token-by-token
    using Server-Sent Events. Sources are sent as a final 'sources' event after
    the text stream ends.

    SSE event shape: data: {"type": "text_delta"|"sources"|"done"|"error", ...}
    """
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

    use_hybrid = settings.enable_bm25 if use_bm25 is None else use_bm25
    if use_hybrid and bm25_index is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BM25 index is not loaded. Check server logs.",
        )

    question = payload.question.strip()
    history: list[Message] = payload.conversation_history[-MAX_HISTORY_MESSAGES:]
    while history and history[0].role != "user":
        history = history[1:]

    logger.info(
        "chat/stream request: %r (history=%d turns, retriever=%s)",
        question,
        len(history),
        "rrf" if use_hybrid else "vector",
    )

    # Update last_seen for the session if the frontend provided one.
    if payload.session_id:
        asyncio.create_task(asyncio.to_thread(db.touch_session, payload.session_id))

    company_filter = detect_company_filter(question)
    if company_filter:
        logger.info("chat/stream: company filter detected: %s", company_filter)

    if use_hybrid:
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

    started_at = time.perf_counter()
    user_prompt = build_prompt(question, trace.results)
    messages: list[dict] = [{"role": m.role, "content": m.content} for m in history]
    messages.append({"role": "user", "content": user_prompt})
    sources = format_sources(trace.results)
    system_prompt = get_system_prompt(payload.visitor_context)

    notifier: TelegramNotifier = request.app.state.notifier
    return StreamingResponse(
        _sse_chat_generator(
            llm,
            system_prompt,
            messages,
            sources,
            notifier=notifier,
            question=question,
            ip=_client_ip(request),
            retriever="rrf" if use_hybrid else "vector",
            sources_count=len(sources),
            started_at=started_at,
            user_agent=request.headers.get("user-agent"),
            visitor_context=payload.visitor_context,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disables nginx/proxy response buffering
        },
    )


@app.post(
    "/api/visit",
    response_model=VisitResponse,
    tags=["meta"],
    summary="Record a page visit (fires a Telegram notification)",
)
async def visit(
    payload: VisitRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> VisitResponse:
    """
    Frontend pings this on page load. Backend looks up the visitor's
    coarse location and sends a Telegram notification — throttled per
    (ip, path) so refreshes don't spam.

    Returns immediately; the notification is fired in a background task.
    Always returns 200 — the frontend doesn't need to know about
    notification failures, and we don't want errors here to break page
    load behavior.
    """
    client_ip = _client_ip(request)
    if payload.session_id:
        geo = await asyncio.to_thread(geoip_lookup, client_ip)
        asyncio.create_task(
            asyncio.to_thread(
                db.upsert_session,
                payload.session_id, client_ip, geo,
                payload.referrer, request.headers.get("user-agent"),
                payload.path_chosen,
            )
        )
    notifier: TelegramNotifier = request.app.state.notifier
    if notifier.enabled:
        background_tasks.add_task(
            notifier.notify_visit,
            ip=client_ip,
            path=payload.path,
            referrer=payload.referrer,
            user_agent=request.headers.get("user-agent"),
        )
    return VisitResponse(ok=True)


@app.post("/api/visit/intake", tags=["meta"], summary="Submit visitor intake form")
async def visit_intake(
    body: IntakeRequest,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Frontend submits this when the visitor completes the intake form.
    Persists session + intake data to SQLite and fires a Telegram notification.
    Always returns 200 — errors here must never break the user-facing flow.
    """
    client_ip = _client_ip(request)
    geo = await asyncio.to_thread(geoip_lookup, client_ip)
    ua = request.headers.get("user-agent", "")
    if body.session_id:
        await asyncio.to_thread(
            db.upsert_session,
            body.session_id, client_ip, geo,
            request.headers.get("referer"), ua, None,
        )
        await asyncio.to_thread(
            db.save_intake,
            body.session_id,
            body.visitor_context.name,
            body.visitor_context.company,
            body.visitor_context.role,
        )
    notifier: TelegramNotifier = request.app.state.notifier
    background_tasks.add_task(
        notifier.notify_intake, client_ip, geo, body.visitor_context, ua
    )
    return {"ok": True}


@app.get(
    "/api/admin/visitors",
    tags=["admin"],
    summary="List all visitor sessions with intake data",
)
async def admin_visitors(_=Depends(verify_admin_key)):
    """
    Returns all visitor sessions joined with intake submissions.
    Requires the X-Admin-Key header to match the ADMIN_KEY env var.
    """
    rows = await asyncio.to_thread(db.get_all_visitors)
    return rows


# ---------------------------------------------------------------------------
# Tracking link redirect
# ---------------------------------------------------------------------------

HOMEPAGE_URL = "https://vaughneugenio.com"
OUTREACH_BACKEND = "https://outreach-backend-production-326e.up.railway.app"


@app.get("/r/{uid}", tags=["meta"], summary="Tracking link redirect")
async def tracking_redirect(
    uid: str,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Hit the outreach backend to log the visit, then redirect to the homepage.
    The outreach backend records the timestamp and IP automatically.
    Never shows an error to the visitor — always redirects regardless.
    """
    client_ip = _client_ip(request)
    name: str | None = None

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{OUTREACH_BACKEND}/r/{uid}",
                headers={"X-Forwarded-For": client_ip},
            )
            if resp.status_code == 200:
                data = resp.json()
                first = data.get("first_name") or ""
                last = data.get("last_name") or ""
                name = f"{first} {last}".strip() or None
    except Exception:
        pass

    notifier: TelegramNotifier = request.app.state.notifier
    if notifier.enabled:
        background_tasks.add_task(
            notifier.notify_tracking_link,
            slug=name or uid,
            ip=client_ip,
            user_agent=request.headers.get("user-agent"),
        )

    redirect_url = f"{HOMEPAGE_URL}?ref={urllib.parse.quote(name)}" if name else HOMEPAGE_URL
    return RedirectResponse(url=redirect_url, status_code=302)


# ---------------------------------------------------------------------------
# RAG Review endpoints
# ---------------------------------------------------------------------------

@app.post("/api/rag-questions", tags=["rag-review"], summary="Store questions from DAG 1")
async def save_rag_questions(body: RagQuestionsRequest):
    """
    Called by the Airflow github_ingest DAG after Claude generates context questions.
    Stores the questions and baseline markdown files for later retrieval.
    Unauthenticated — data is not sensitive (write-only, no PII).
    """
    await asyncio.to_thread(
        save_rag_run,
        body.run_id,
        [r.model_dump() for r in body.repos],
        [f.model_dump() for f in body.files],
    )
    return {"ok": True}


@app.get(
    "/api/rag-questions",
    response_model=RagQuestionsResponse,
    tags=["rag-review"],
    summary="Fetch the latest pending review run",
)
async def get_rag_questions():
    """
    Returns the most recent pending RAG review run.
    Called by the /rag-review frontend page to display questions.
    Returns 404 if no pending runs exist.
    """
    run = await asyncio.to_thread(get_latest_pending_run)
    if run is None:
        raise HTTPException(status_code=404, detail="No pending RAG review runs")
    return run


@app.post("/api/rag-answers", tags=["rag-review"], summary="Submit answers and trigger DAG 2")
async def submit_rag_answers(body: RagAnswersRequest):
    """
    Called by the /rag-review frontend on submit.
    Synthesizes non-empty answers into enriched markdown via Claude,
    then triggers DAG 2 (rag_commit) to commit the enriched files to GitHub.
    Empty answers are treated as skips.
    """
    settings = get_settings()
    await synthesize_and_store(body.run_id, [a.model_dump() for a in body.answers], settings)
    if settings.airflow_url:
        from datetime import datetime, timezone
        logical_date = datetime.now(timezone.utc).isoformat()
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{settings.airflow_url}/api/v2/dags/rag_commit/dagRuns",
                json={"conf": {"run_id": body.run_id}, "logical_date": logical_date},
                headers={"Authorization": f"Bearer {settings.airflow_password}"},
                timeout=15,
            )
            resp.raise_for_status()
    await asyncio.to_thread(mark_run_committed, body.run_id)
    return {"ok": True}


@app.get(
    "/api/rag-run/{run_id}/files",
    response_model=RagFilesResponse,
    tags=["rag-review"],
    summary="Fetch enriched files for DAG 2 to commit",
)
async def get_enriched_files(run_id: str, _=Depends(verify_admin_key)):
    """
    Called by the rag_commit DAG to retrieve the enriched markdown files
    for a specific run before committing them to GitHub.
    Returns 404 if the run doesn't exist or hasn't been enriched yet.
    """
    run = await asyncio.to_thread(get_run, run_id)
    if run is None or run.get("enriched_json") is None:
        raise HTTPException(status_code=404, detail="Run not found or not yet enriched")
    return {"files": json.loads(run["enriched_json"])}
