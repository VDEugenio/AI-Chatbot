"""Pydantic models for request and response payloads."""

from typing import Literal

from pydantic import BaseModel, Field


class Message(BaseModel):
    """A single turn in a multi-turn conversation."""

    role: Literal["user", "assistant"]
    content: str = Field(..., min_length=1)


class VisitorContext(BaseModel):
    """Optional visitor identity collected from the intake form."""

    name: str | None = None
    company: str | None = None
    role: str | None = None


class IntakeRequest(BaseModel):
    """Frontend submits this when a visitor completes the intake form."""

    visitor_context: VisitorContext
    session_id: str | None = None


class ChatRequest(BaseModel):
    """Incoming chat request, optionally including prior conversation turns."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The user's current question.",
    )
    conversation_history: list[Message] = Field(
        default_factory=list,
        description=(
            "Prior turns in the conversation, oldest first. Empty for the first "
            "message. The backend is stateless — the frontend owns this list."
        ),
    )
    visitor_context: VisitorContext | None = None
    session_id: str | None = None


class SourceChunk(BaseModel):
    """A retrieved chunk surfaced back to the client for citation."""

    filename: str
    chunk_id: int | None = None
    preview: str
    score: float | None = Field(
        default=None,
        description="Chroma relevance score in [0,1]; higher = more similar.",
    )


class ChatResponse(BaseModel):
    """Successful chat response."""

    answer: str
    sources: list[SourceChunk] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """Service health snapshot."""

    status: str
    vectorstore_loaded: bool
    chunk_count: int | None = None


class DebugRetrieveRequest(BaseModel):
    """Debug endpoint: ask what retrieval would return, without calling Claude."""

    question: str = Field(..., min_length=1, max_length=2000)
    conversation_history: list[Message] = Field(default_factory=list)
    k: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description="Override top_k for this request only. Defaults to settings.top_k.",
    )
    min_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Override min_similarity_score for this request only.",
    )
    enable_expansion: bool | None = Field(
        default=None,
        description="Override query expansion on/off for this request only.",
    )


class DebugRetrieveResponse(BaseModel):
    """Full retrieval trace — everything the logger emits, in JSON form."""

    original_query: str
    expanded_query: str
    retrieval_query: str
    expansions_applied: list[str]
    k: int
    min_score: float | None
    returned: int
    dropped_below_threshold: int
    chunks: list[SourceChunk]


class CompareRequest(BaseModel):
    """Debug: run vector, BM25, and BM25+rerank on the same question."""

    question: str = Field(..., min_length=1, max_length=2000)
    conversation_history: list[Message] = Field(default_factory=list)
    candidates_k: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Override bm25_candidates for this request only.",
    )
    final_k: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description=(
            "Override the final chunk count for this request. Applies to "
            "vector top_k and rerank final_k. BM25-only uses candidates_k."
        ),
    )
    enable_expansion: bool | None = Field(
        default=None,
        description="Override query expansion on/off for this request only.",
    )


class CompareResponse(BaseModel):
    """Side-by-side retrieval traces so you can diff retriever behavior."""

    question: str
    vector: DebugRetrieveResponse
    bm25: DebugRetrieveResponse
    hybrid_reranked: DebugRetrieveResponse


class VisitRequest(BaseModel):
    """Frontend tells the backend a page was viewed; backend pings Telegram."""

    path: str = Field(
        default="/",
        max_length=512,
        description="Path that was visited (e.g. '/', '/projects'). No domain.",
    )
    referrer: str | None = Field(
        default=None,
        max_length=2048,
        description="document.referrer if available; null for direct visits.",
    )
    session_id: str | None = None
    path_chosen: str | None = None


class VisitResponse(BaseModel):
    """Acknowledgement only. The notification is sent in a background task."""

    ok: bool = True


# ---------------------------------------------------------------------------
# RAG Review
# ---------------------------------------------------------------------------

class RepoQuestions(BaseModel):
    repo_name: str
    questions: list[str]


class FormattedFile(BaseModel):
    filename: str
    content: str


class RagQuestionsRequest(BaseModel):
    run_id: str
    repos: list[RepoQuestions]
    files: list[FormattedFile]


class RepoAnswer(BaseModel):
    repo_name: str
    question: str
    answer: str  # empty string = skip


class RagAnswersRequest(BaseModel):
    run_id: str
    answers: list[RepoAnswer]


class RagQuestionsResponse(BaseModel):
    run_id: str
    created_at: float
    repos: list[RepoQuestions]
    status: str


class RagFilesResponse(BaseModel):
    files: list[FormattedFile]
