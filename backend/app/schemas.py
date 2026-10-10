import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ErrorDetail(BaseModel):
    code: str
    message: str
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


class SourceRef(BaseModel):
    id: str = Field(min_length=4, max_length=64)
    episode_title: str
    guest: str
    excerpt: str
    source_url: str
    timestamp_label: str | None = None
    start_seconds: int | None = None
    relevance: float = Field(ge=0, le=1)


class EvidenceClaim(BaseModel):
    statement: str = Field(min_length=1, max_length=600)
    source_ids: list[str] = Field(min_length=1, max_length=4)
    support: Literal["supported", "qualified"]


class EvidenceReceipt(BaseModel):
    provider: Literal["ollama", "anthropic", "openai", "demo"]
    model: str
    corpus_sha: str
    retrieval_count: int
    retrieval_latency_ms: int
    agent_latency_ms: int
    confidence: Literal["high", "medium", "low", "insufficient"]
    demo_data: bool = False


class ChatRequest(BaseModel):
    message: str = Field(min_length=3, max_length=4000)
    session_id: uuid.UUID | None = None
    user_metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("user_metadata")
    @classmethod
    def only_small_metadata(cls, value: dict[str, str]) -> dict[str, str]:
        if len(value) > 10 or any(len(key) > 50 or len(str(item)) > 200 for key, item in value.items()):
            raise ValueError("user_metadata is limited to ten short, non-sensitive fields")
        return value


class ChatResponse(BaseModel):
    session_id: uuid.UUID
    message_id: uuid.UUID
    answer_markdown: str
    claims: list[EvidenceClaim]
    counterpoint: str | None = None
    suggested_actions: list[str] = Field(default_factory=list)
    sources: list[SourceRef]
    receipt: EvidenceReceipt


class SessionSummary(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime


class SessionDetail(SessionSummary):
    messages: list[dict]
    artifacts: list[dict]


class ArtifactRequest(BaseModel):
    kind: Literal["markdown", "html"]
    title: str = Field(min_length=3, max_length=160)
    instruction: str = Field(min_length=3, max_length=1000)


class ArtifactResponse(BaseModel):
    id: uuid.UUID
    kind: Literal["markdown", "html"]
    title: str
    content: str
    source_refs: list[SourceRef]
    created_at: datetime


class Ship30Request(BaseModel):
    audience: str = Field(default="product and growth practitioners", min_length=3, max_length=160)
    lens: Literal["actionable", "analytical", "aspirational", "anthropological"] = "actionable"
    structure: Literal["steps", "lessons", "mistakes", "framework"] = "steps"


class ProviderStatus(BaseModel):
    provider: str
    model: str
    available: bool
    detail: str | None = None


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: bool
    provider: ProviderStatus
