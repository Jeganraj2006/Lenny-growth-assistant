import uuid
from datetime import datetime

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import desc, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db import get_session
from app.models import Artifact, ChatSession, Message
from app.schemas import (
    ArtifactRequest,
    ArtifactResponse,
    ChatRequest,
    ChatResponse,
    EvidenceReceipt,
    HealthResponse,
    ProviderStatus,
    SessionDetail,
    SessionSummary,
    Ship30Request,
    SourceRef,
)
from app.services.agent import run_agent
from app.services.artifacts import build_html_artifact, build_markdown_artifact, content_hash
from app.services.retrieval import DEMO_CORPUS_SHA, ensure_demo_corpus, retrieve
from app.services.ship30 import draft_ship30

router = APIRouter(prefix="/api")
log = structlog.get_logger(__name__)


def _message_record(message: Message) -> dict:
    return {
        "id": str(message.id),
        "role": message.role,
        "content": message.content,
        "sources": message.source_refs,
        "receipt": message.receipt,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def _artifact_record(artifact: Artifact) -> dict:
    return {
        "id": str(artifact.id),
        "kind": artifact.kind,
        "title": artifact.title,
        "content": artifact.content,
        "source_refs": artifact.source_refs,
        "created_at": artifact.created_at.isoformat() if artifact.created_at else None,
    }


async def _session_or_404(db: AsyncSession, session_id: uuid.UUID) -> ChatSession:
    record = await db.get(ChatSession, session_id)
    if not record:
        raise HTTPException(status_code=404, detail={"code": "SESSION_NOT_FOUND", "message": "The requested session does not exist."})
    return record


async def _provider_status(settings: Settings) -> ProviderStatus:
    if settings.llm_provider == "ollama":
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
                response.raise_for_status()
                models = {model.get("name") for model in response.json().get("models", [])}
                available = settings.ollama_model in models
                detail = None if available else f"Ollama is reachable, but {settings.ollama_model} is not pulled."
                return ProviderStatus(provider="ollama", model=settings.ollama_model, available=available, detail=detail)
        except httpx.HTTPError:
            return ProviderStatus(provider="ollama", model=settings.ollama_model, available=False, detail="Ollama is unavailable. Start the local profile or check OLLAMA_BASE_URL.")
    if settings.llm_provider == "anthropic":
        return ProviderStatus(provider="anthropic", model=settings.anthropic_model, available=bool(settings.anthropic_api_key), detail=None if settings.anthropic_api_key else "ANTHROPIC_API_KEY is missing.")
    return ProviderStatus(provider="openai", model=settings.openai_model, available=bool(settings.openai_api_key), detail=None if settings.openai_api_key else "OPENAI_API_KEY is missing.")


@router.get("/health/live", response_model=HealthResponse, tags=["operations"])
async def health_live(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(status="ok", database=True, provider=await _provider_status(settings))


@router.get("/health/ready", response_model=HealthResponse, tags=["operations"])
async def health_ready(db: AsyncSession = Depends(get_session), settings: Settings = Depends(get_settings)) -> HealthResponse:
    database_ok = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        database_ok = False
    provider = await _provider_status(settings)
    return HealthResponse(status="ok" if database_ok else "degraded", database=database_ok, provider=provider)


@router.get("/config", response_model=ProviderStatus, tags=["operations"])
async def config(settings: Settings = Depends(get_settings)) -> ProviderStatus:
    return await _provider_status(settings)


@router.get("/sessions", response_model=list[SessionSummary], tags=["sessions"])
async def list_sessions(db: AsyncSession = Depends(get_session)) -> list[SessionSummary]:
    records = (await db.scalars(select(ChatSession).order_by(desc(ChatSession.updated_at)).limit(50))).all()
    return [SessionSummary(id=item.id, title=item.title, created_at=item.created_at, updated_at=item.updated_at) for item in records]


@router.post("/sessions", response_model=SessionSummary, status_code=status.HTTP_201_CREATED, tags=["sessions"])
async def create_session(db: AsyncSession = Depends(get_session)) -> SessionSummary:
    record = ChatSession()
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return SessionSummary(id=record.id, title=record.title, created_at=record.created_at, updated_at=record.updated_at)


@router.get("/sessions/{session_id}", response_model=SessionDetail, tags=["sessions"])
async def session_detail(session_id: uuid.UUID, db: AsyncSession = Depends(get_session)) -> SessionDetail:
    record = await _session_or_404(db, session_id)
    messages = (await db.scalars(select(Message).where(Message.session_id == session_id).order_by(Message.created_at))).all()
    artifacts = (await db.scalars(select(Artifact).where(Artifact.session_id == session_id).order_by(desc(Artifact.created_at)))).all()
    return SessionDetail(
        id=record.id,
        title=record.title,
        created_at=record.created_at,
        updated_at=record.updated_at,
        messages=[_message_record(message) for message in messages],
        artifacts=[_artifact_record(artifact) for artifact in artifacts],
    )


@router.post("/chat", response_model=ChatResponse, tags=["chat"])
async def chat(
    payload: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> ChatResponse:
    if settings.demo_mode:
        await ensure_demo_corpus(db)
    chat_session = await _session_or_404(db, payload.session_id) if payload.session_id else ChatSession(user_metadata=payload.user_metadata)
    if payload.session_id is None:
        db.add(chat_session)
        await db.flush()
    if chat_session.title == "New research":
        chat_session.title = payload.message[:72].strip() + ("..." if len(payload.message) > 72 else "")
    db.add(Message(session_id=chat_session.id, role="user", content=payload.message, source_refs=[], receipt={}))
    await db.flush()

    history_rows = (await db.scalars(select(Message).where(Message.session_id == chat_session.id).order_by(desc(Message.created_at)).limit(settings.max_history_messages))).all()
    history = [{"role": message.role, "content": message.content} for message in reversed(history_rows) if message.role in {"user", "assistant"}]
    retrieval = await retrieve(db, payload.message, settings)
    agent = await run_agent(payload.message, history, retrieval.sources, settings)

    if not retrieval.sources:
        confidence = "insufficient"
    elif retrieval.sources[0].relevance >= 0.7:
        confidence = "high"
    elif retrieval.sources[0].relevance >= settings.min_retrieval_score:
        confidence = "medium"
    else:
        confidence = "low"
    receipt = EvidenceReceipt(
        provider=agent.provider,
        model=agent.model,
        corpus_sha=retrieval.corpus_sha or settings.corpus_git_sha,
        retrieval_count=len(retrieval.sources),
        retrieval_latency_ms=retrieval.latency_ms,
        agent_latency_ms=agent.latency_ms,
        confidence=confidence,
        demo_data=any(source.episode_title.startswith("Demo") for source in retrieval.sources),
    )
    assistant_message = Message(
        session_id=chat_session.id,
        role="assistant",
        content=agent.payload.answer_markdown,
        source_refs=[source.model_dump() for source in retrieval.sources],
        receipt=receipt.model_dump(),
    )
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)
    log.info("chat_completed", request_id=getattr(request.state, "request_id", None), session_id=str(chat_session.id), provider=agent.provider, sources=len(retrieval.sources), retrieval_latency_ms=retrieval.latency_ms, agent_latency_ms=agent.latency_ms, fallback=agent.used_fallback)
    return ChatResponse(
        session_id=chat_session.id,
        message_id=assistant_message.id,
        answer_markdown=agent.payload.answer_markdown,
        claims=agent.payload.claims,
        counterpoint=agent.payload.counterpoint,
        suggested_actions=agent.payload.suggested_actions,
        sources=retrieval.sources,
        receipt=receipt,
    )


@router.post("/sessions/{session_id}/artifacts", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED, tags=["artifacts"])
async def create_artifact(session_id: uuid.UUID, payload: ArtifactRequest, db: AsyncSession = Depends(get_session)) -> ArtifactResponse:
    await _session_or_404(db, session_id)
    assistant_messages = (await db.scalars(select(Message).where(Message.session_id == session_id, Message.role == "assistant").order_by(desc(Message.created_at)).limit(4))).all()
    seen: set[str] = set()
    sources: list[SourceRef] = []
    for message in assistant_messages:
        for raw_source in message.source_refs:
            source = SourceRef.model_validate(raw_source)
            if source.id not in seen:
                seen.add(source.id)
                sources.append(source)
    content = build_html_artifact(payload.title, payload.instruction, sources) if payload.kind == "html" else build_markdown_artifact(payload.title, payload.instruction, sources)
    artifact = Artifact(session_id=session_id, kind=payload.kind, title=payload.title, content=content, content_hash=content_hash(content), source_refs=[source.model_dump() for source in sources])
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return ArtifactResponse(id=artifact.id, kind=artifact.kind, title=artifact.title, content=artifact.content, source_refs=sources, created_at=artifact.created_at)


@router.post("/sessions/{session_id}/ship30", response_model=ArtifactResponse, status_code=status.HTTP_201_CREATED, tags=["skills"])
async def create_ship30_essay(session_id: uuid.UUID, payload: Ship30Request, db: AsyncSession = Depends(get_session), settings: Settings = Depends(get_settings)) -> ArtifactResponse:
    """Run the dedicated structured writing skill on sources already used in the session."""
    await _session_or_404(db, session_id)
    rows = (await db.scalars(select(Message).where(Message.session_id == session_id).order_by(desc(Message.created_at)).limit(10))).all()
    sources: list[SourceRef] = []
    seen: set[str] = set()
    topic = "a product and growth decision"
    for message in rows:
        if message.role == "user" and topic == "a product and growth decision":
            topic = message.content
        for source_dict in message.source_refs:
            source = SourceRef.model_validate(source_dict)
            if source.id not in seen:
                sources.append(source)
                seen.add(source.id)
    content = await draft_ship30(topic, payload.audience, payload.lens, payload.structure, sources, settings)
    artifact = Artifact(session_id=session_id, kind="markdown", title="Ship 30 for 30 Essay", content=content, content_hash=content_hash(content), source_refs=[source.model_dump() for source in sources])
    db.add(artifact)
    await db.commit()
    await db.refresh(artifact)
    return ArtifactResponse(id=artifact.id, kind="markdown", title=artifact.title, content=artifact.content, source_refs=sources, created_at=artifact.created_at)


@router.get("/artifacts/{artifact_id}", response_model=ArtifactResponse, tags=["artifacts"])
async def get_artifact(artifact_id: uuid.UUID, db: AsyncSession = Depends(get_session)) -> ArtifactResponse:
    artifact = await db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail={"code": "ARTIFACT_NOT_FOUND", "message": "The requested artifact does not exist."})
    return ArtifactResponse(id=artifact.id, kind=artifact.kind, title=artifact.title, content=artifact.content, source_refs=[SourceRef.model_validate(source) for source in artifact.source_refs], created_at=artifact.created_at)
