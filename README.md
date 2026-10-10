# Lenny Lens

Lenny Lens is a local-first evidence-to-action workspace for product and growth teams. It turns Lenny's Podcast transcripts into source-grounded answers, Ship 30 for 30 style essays, and safe in-product Markdown or HTML/CSS artifacts.

Unlike a generic transcript chatbot, it returns an **Evidence Receipt** with supported claims, applicability context, counterpoints, source links, and an explicit distinction between source-backed evidence and recommendation.

## Why this design

Product advice is conditional. The system never presents a model synthesis as a transcript fact. The retrieval layer returns timestamped evidence, the agent receives only that evidence, and the API validates citations before a response is persisted.

## Quick start

1. Start native Windows Ollama and ensure `llama3.2:3b` and `nomic-embed-text:latest` are available (`ollama list`).
2. Copy `.env.example` to `.env`. The default `OLLAMA_BASE_URL` uses Docker Desktop's `host.docker.internal` bridge to reach native Ollama from both FastAPI and the Pi sidecar.
3. Run `docker compose up --build`.
3. Open `http://localhost:5173`.
4. Load the source corpus using the command below. It pins the transcript repository commit, parses metadata, chunks timestamped turns, generates embeddings, and records ingestion diagnostics.

```bash
docker compose run --rm api python -m app.services.ingest --repo-url https://github.com/ChatPRD/lennys-podcast-transcripts.git
```

For a fast evaluator walkthrough before ingestion, leave `DEMO_MODE=true`; the product seeds a small cited demo corpus on first startup. This is visibly labelled in the system receipt and is not presented as the complete source corpus.

## Architecture

```text
React workspace -> FastAPI -> Pi agent runtime -> configured LLM
                      |              |
                      |              +-- no filesystem or shell tools
                      +-> PostgreSQL + pgvector
                              |
                         corpus and evidence receipts
```

FastAPI owns the public API, validation, persistence, retrieval, safety checks, and observability. A small Node service embeds the Pi Coding Agent SDK, configured with zero built-in tools. It can call a cloud model or an Ollama-compatible local endpoint without application-code changes.

## Provider configuration

Set `LLM_PROVIDER` to `ollama`, `anthropic`, or `openai`. The selected provider and model appear in each response receipt. A provider failure is explicit; the app never silently sends a local request to a cloud model.

The native Windows configuration uses `llama3.2:3b` and `nomic-embed-text:latest` by default. Change these through `OLLAMA_MODEL` and `OLLAMA_EMBED_MODEL` before startup if your machine needs a different model. The optional `local` Compose profile remains available for a containerized Ollama runtime; use `OLLAMA_BASE_URL=http://ollama:11434` with that profile.

## Testing

```bash
docker compose run --rm -e RUN_DATABASE_TESTS=1 api pytest
```

Tests cover API validation, session isolation, citation validation, retrieval fallback, and HTML sanitisation behavior. A manual walkthrough is in `docs/manual-test-plan.md`.

## Security notes

Markdown is rendered with raw HTML disabled. HTML artifacts are sanitised and rendered inside an iframe with an empty sandbox, an inline restrictive CSP, no same-origin permission, and no external network access. The exported version is also sanitised.

## Repository guide

- `backend/` FastAPI application, persistence, retrieval, and ingestion.
- `agent/` Pi Coding Agent SDK sidecar with no filesystem or shell tools.
- `frontend/` evaluator-focused chat and artifact workspace.
- `docs/PRD.md` product and forward-deployment brief.
- `docs/architecture.md` technical design and operational decisions.
- `docs/design.md` UI/UX and accessibility decisions.
- `agent-transcripts/` redacted coding-agent execution log and corrections.

## Troubleshooting

- **Ollama unavailable:** first run `ollama list` on Windows, then confirm `OLLAMA_BASE_URL=http://host.docker.internal:11434` in `.env`. The status endpoint reports which provider failed.
- **No sources returned:** run ingestion, then verify `/api/health/ready`. The assistant should decline unsupported claims rather than invent an answer.
- **Database unavailable:** `docker compose logs db`; the API readiness endpoint returns a structured database status.
- **Cloud key missing:** either add the key to `.env`, or switch `LLM_PROVIDER=ollama`; no automatic fallback occurs.
