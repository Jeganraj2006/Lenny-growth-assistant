"""Corpus ingestion command for the public Lenny transcript repository.

Run with:
  python -m app.services.ingest --repo-url https://github.com/ChatPRD/lennys-podcast-transcripts.git
"""

import argparse
import asyncio
import hashlib
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import httpx
import yaml
from sqlalchemy import delete

from app.core.config import get_settings
from app.db import SessionLocal, initialize_database
from app.models import IngestionRun, KnowledgeChunk


@dataclass
class TranscriptTurn:
    speaker: str
    start_seconds: int | None
    text: str


def run_git(*args: str, cwd: str | None = None) -> str:
    completed = subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def parse_seconds(value: str) -> int | None:
    try:
        values = [int(part) for part in value.split(":")]
        if len(values) == 2:
            return values[0] * 60 + values[1]
        if len(values) == 3:
            return values[0] * 3600 + values[1] * 60 + values[2]
    except ValueError:
        pass
    return None


def read_transcript(path: Path) -> tuple[dict, list[TranscriptTurn]]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    metadata: dict = {}
    body = raw
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            metadata = yaml.safe_load(parts[1]) or {}
            body = parts[2]
    turns: list[TranscriptTurn] = []
    current: TranscriptTurn | None = None
    for line in body.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        import re
        match = re.match(r"^(.{1,80}?)\s*\((\d{1,2}:\d{2}(?::\d{2})?)\):\s*(.+)$", line)
        if match:
            if current:
                turns.append(current)
            current = TranscriptTurn(speaker=match.group(1).strip(), start_seconds=parse_seconds(match.group(2)), text=match.group(3).strip())
        elif current:
            current.text += " " + line
    if current:
        turns.append(current)
    if not turns and body.strip():
        turns.append(TranscriptTurn(speaker="Transcript", start_seconds=None, text=body.strip()))
    return metadata, turns


def semantic_chunks(turns: list[TranscriptTurn], target_words: int = 420) -> list[tuple[int | None, int | None, str]]:
    chunks: list[tuple[int | None, int | None, str]] = []
    buffer: list[TranscriptTurn] = []
    word_count = 0
    for turn in turns:
        buffer.append(turn)
        word_count += len(turn.text.split())
        if word_count >= target_words:
            chunks.append((buffer[0].start_seconds, buffer[-1].start_seconds, "\n".join(f"{item.speaker} ({item.start_seconds if item.start_seconds is not None else 'n/a'}): {item.text}" for item in buffer)))
            buffer = buffer[-2:]  # short speaker-aware overlap
            word_count = sum(len(item.text.split()) for item in buffer)
    if buffer:
        chunks.append((buffer[0].start_seconds, buffer[-1].start_seconds, "\n".join(f"{item.speaker} ({item.start_seconds if item.start_seconds is not None else 'n/a'}): {item.text}" for item in buffer)))
    return chunks


async def embed_many(texts: list[str]) -> list[list[float] | None]:
    settings = get_settings()
    if not texts:
        return []
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(f"{settings.ollama_base_url.rstrip('/')}/api/embed", json={"model": settings.ollama_embed_model, "input": texts, "truncate": True})
            response.raise_for_status()
            vectors = response.json().get("embeddings", [])
            return [vector if isinstance(vector, list) and len(vector) == 768 else None for vector in vectors]
    except httpx.HTTPError:
        return [None] * len(texts)


def make_id(corpus_sha: str, relative_path: str, start_seconds: int | None, content: str) -> str:
    return hashlib.sha256(f"{corpus_sha}:{relative_path}:{start_seconds}:{content}".encode()).hexdigest()


async def ingest(repo_url: str) -> tuple[int, int, str]:
    tmp_root = Path(tempfile.mkdtemp(prefix="lenny-lens-ingest-"))
    repo = tmp_root / "corpus"
    try:
        run_git("clone", "--depth", "1", repo_url, str(repo))
        corpus_sha = run_git("rev-parse", "HEAD", cwd=str(repo))
        documents: list[dict] = []
        for transcript in repo.glob("episodes/**/transcript.md"):
            metadata, turns = read_transcript(transcript)
            relative_path = transcript.relative_to(repo).as_posix()
            title = str(metadata.get("title") or transcript.parent.name.replace("-", " ").title())
            guest = str(metadata.get("guest") or "Unknown guest")
            base_url = str(metadata.get("youtube_url") or f"https://github.com/ChatPRD/lennys-podcast-transcripts/blob/{corpus_sha}/{relative_path}")
            for start, end, content in semantic_chunks(turns):
                source_url = f"{base_url}{'&' if '?' in base_url else '?'}t={start}" if start is not None and "youtube" in base_url else base_url
                documents.append({
                    "id": make_id(corpus_sha, relative_path, start, content),
                    "corpus_sha": corpus_sha,
                    "episode_title": title,
                    "guest": guest,
                    "source_url": source_url,
                    "transcript_path": relative_path,
                    "start_seconds": start,
                    "end_seconds": end,
                    "content": content,
                    "metadata_": {"publish_date": metadata.get("publish_date"), "video_id": metadata.get("video_id"), "demo": False},
                })
        await initialize_database()
        async with SessionLocal() as db:
            run = IngestionRun(corpus_sha=corpus_sha, status="running")
            db.add(run)
            await db.flush()
            # Retain other corpus versions for auditability, but make reruns idempotent.
            await db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.corpus_sha.in_([corpus_sha, "demo-corpus-2026-10-09"])))
            embedded_count = 0
            for offset in range(0, len(documents), 24):
                batch = documents[offset:offset + 24]
                vectors = await embed_many([item["content"] for item in batch])
                for item, vector in zip(batch, vectors, strict=True):
                    item["embedding"] = vector
                    embedded_count += int(vector is not None)
                    db.add(KnowledgeChunk(**item))
                await db.flush()
            run.status = "completed"
            run.document_count = len({item["transcript_path"] for item in documents})
            run.chunk_count = len(documents)
            run.diagnostics = {"embedded_chunks": embedded_count, "embedding_model": get_settings().ollama_embed_model}
            await db.commit()
        return len({item["transcript_path"] for item in documents}), len(documents), corpus_sha
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Lenny's Podcast transcript archive")
    parser.add_argument("--repo-url", required=True, help="Git repository containing transcript markdown files")
    args = parser.parse_args()
    documents, chunks, sha = asyncio.run(ingest(args.repo_url))
    print(f"Ingestion completed: {documents} transcripts, {chunks} chunks, corpus={sha}")


if __name__ == "__main__":
    main()
