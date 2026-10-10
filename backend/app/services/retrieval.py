"""Hybrid retrieval with a deterministic lexical fallback.

The fallback keeps a fresh evaluator demo useful while the local embedding model is
still downloading. It never fabricates a source: every result comes from a row in
``knowledge_chunks``.
"""

import hashlib
import re
import time
from dataclasses import dataclass

import httpx
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.models import KnowledgeChunk
from app.schemas import SourceRef


@dataclass
class RetrievalResult:
    sources: list[SourceRef]
    latency_ms: int
    corpus_sha: str | None


DEMO_CORPUS_SHA = "demo-corpus-2026-10-09"
DEMO_CHUNKS = [
    {
        "episode_title": "Demo product discovery evidence",
        "guest": "Lenny Lens sample corpus",
        "source_url": "https://github.com/ChatPRD/lennys-podcast-transcripts",
        "transcript_path": "DEMO_ONLY",
        "start_seconds": 0,
        "end_seconds": 90,
        "content": "A product team should identify the moment a new user receives value before optimising the surrounding funnel. Retention work begins by understanding the repeated behaviour that makes the product useful, then testing whether the first-use experience leads users to that behaviour.",
    },
    {
        "episode_title": "Demo growth experimentation evidence",
        "guest": "Lenny Lens sample corpus",
        "source_url": "https://github.com/ChatPRD/lennys-podcast-transcripts",
        "transcript_path": "DEMO_ONLY",
        "start_seconds": 95,
        "end_seconds": 180,
        "content": "Useful growth experiments begin with a named assumption, a narrow audience, and a leading metric. A team should prefer learning quickly over treating every experiment as a permanent launch. Results need a pre-defined success threshold and an explicit decision after the test.",
    },
    {
        "episode_title": "Demo context and counterpoint evidence",
        "guest": "Lenny Lens sample corpus",
        "source_url": "https://github.com/ChatPRD/lennys-podcast-transcripts",
        "transcript_path": "DEMO_ONLY",
        "start_seconds": 185,
        "end_seconds": 270,
        "content": "Optimising activation before acquisition is often a strong choice when new users leave before reaching value. But a team with weak demand may need customer research before it can diagnose onboarding. Advice about growth only applies after the relevant constraint has been identified.",
    },
]


def _chunk_id(content: str, source: str) -> str:
    return hashlib.sha256(f"{source}:{content}".encode()).hexdigest()


def _timestamp(seconds: int | None) -> str | None:
    if seconds is None:
        return None
    return f"{seconds // 60}:{seconds % 60:02d}"


def _terms(query: str) -> list[str]:
    return list(dict.fromkeys(token for token in re.findall(r"[a-zA-Z]{3,}", query.lower()) if token not in {"what", "with", "that", "this", "from", "about", "have", "should", "would"}))[:12]


async def ensure_demo_corpus(session: AsyncSession) -> None:
    existing = await session.scalar(select(KnowledgeChunk.id).limit(1))
    if existing:
        return
    for item in DEMO_CHUNKS:
        session.add(KnowledgeChunk(id=_chunk_id(item["content"], item["transcript_path"]), corpus_sha=DEMO_CORPUS_SHA, metadata_={"demo": True}, embedding=None, **item))
    await session.commit()


async def _embedding(query: str, settings: Settings) -> list[float] | None:
    try:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/embed",
                json={"model": settings.ollama_embed_model, "input": query, "truncate": True},
            )
            response.raise_for_status()
            vector = response.json().get("embeddings", [None])[0]
            return vector if isinstance(vector, list) and len(vector) == 768 else None
    except (httpx.HTTPError, ValueError, IndexError):
        return None


async def retrieve(session: AsyncSession, query: str, settings: Settings) -> RetrievalResult:
    started = time.perf_counter()
    terms = _terms(query)
    statement = select(KnowledgeChunk)
    if terms:
        statement = statement.where(or_(*[KnowledgeChunk.content.ilike(f"%{term}%") for term in terms]))
    rows = list((await session.scalars(statement.limit(settings.top_k * 3))).all())

    def lexical_score(chunk: KnowledgeChunk) -> float:
        content = chunk.content.lower()
        return sum(term in content for term in terms) / max(1, len(terms))

    scored: dict[str, tuple[KnowledgeChunk, float]] = {row.id: (row, lexical_score(row)) for row in rows}
    vector = await _embedding(query, settings)
    if vector:
        distance = KnowledgeChunk.embedding.cosine_distance(vector).label("distance")
        vector_rows = (await session.execute(select(KnowledgeChunk, distance).where(KnowledgeChunk.embedding.is_not(None)).order_by(distance).limit(settings.top_k))).all()
        for rank, (chunk, raw_distance) in enumerate(vector_rows, start=1):
            vector_score = max(0.0, 1.0 - float(raw_distance))
            lexical = scored.get(chunk.id, (chunk, 0.0))[1]
            # RRF-inspired blend that does not let either retriever dominate.
            scored[chunk.id] = (chunk, min(1.0, 0.58 * vector_score + 0.42 * lexical + 1 / (60 + rank)))

    ordered = sorted(scored.values(), key=lambda value: value[1], reverse=True)[: settings.top_k]
    sources = [
        SourceRef(
            id=chunk.id,
            episode_title=chunk.episode_title,
            guest=chunk.guest,
            excerpt=chunk.content[:600].rstrip() + ("..." if len(chunk.content) > 600 else ""),
            source_url=chunk.source_url,
            timestamp_label=_timestamp(chunk.start_seconds),
            start_seconds=chunk.start_seconds,
            relevance=round(max(0.01, min(1.0, score)), 2),
        )
        for chunk, score in ordered
    ]
    return RetrievalResult(sources=sources, latency_ms=int((time.perf_counter() - started) * 1000), corpus_sha=ordered[0][0].corpus_sha if ordered else None)
