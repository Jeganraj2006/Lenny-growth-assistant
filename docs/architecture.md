# Lenny Lens Architecture

## Component boundaries

| Component | Responsibility | Does not own |
| --- | --- | --- |
| React frontend | Conversations, source visibility, artifact viewer, responsive states | Retrieval truth or provider secrets |
| FastAPI | Public contracts, validation, sessions, persistence, retrieval, source validation, artifacts, health and logs | Model credentials beyond configuration |
| Pi agent runtime | Constrained evidence synthesis against selected provider/model | File access, shell access, retrieval, database access |
| PostgreSQL + pgvector | Durable data, vector similarities, corpus provenance | LLM behavior |
| Ollama | Local generation and embeddings | Session state or user identity |

## Deployment topology

```text
Browser -> nginx React container -> FastAPI :8000 -> Pi SDK sidecar :3001
                                      |                |
                                      v                v
                              PostgreSQL + pgvector  Ollama / cloud model
```

`docker compose --profile local up --build` runs the local Ollama service and a one-shot model pull. Standard `docker compose up --build` assumes an accessible configured provider and is useful for cloud-provider development.

## Database schema

| Table | Key fields | Purpose |
| --- | --- | --- |
| `chat_sessions` | id, title, user_metadata, timestamps | Independent conversation boundary |
| `messages` | session_id, role, content, source_refs, receipt | Conversation and reproducibility metadata |
| `artifacts` | session_id, kind, content, content_hash, source_refs | Renderable/exportable artifacts |
| `knowledge_chunks` | source metadata, transcript location, timestamp, corpus SHA, content, embedding | Traceable retrieval unit |
| `ingestion_runs` | corpus SHA, counts, diagnostics, status | Operational record of corpus refresh |

## Public API

| Method | Endpoint | Contract |
| --- | --- | --- |
| GET | `/api/health/live` | Liveness plus selected provider state |
| GET | `/api/health/ready` | Database readiness plus provider state |
| GET | `/api/config` | UI-safe provider/model status |
| GET/POST | `/api/sessions` | List or start research sessions |
| GET | `/api/sessions/{id}` | Session conversation and artifacts |
| POST | `/api/chat` | Validated question, grounded answer, evidence receipt |
| POST | `/api/sessions/{id}/artifacts` | Markdown or HTML artifact from current cited session |
| GET | `/api/artifacts/{id}` | Stored artifact |

FastAPI publishes its automatic OpenAPI contract at `/docs`. Errors return a structured object with a code, message, and request ID where available.

## Ingestion and retrieval

1. Clone the source repository to a temporary directory and resolve the commit SHA.
2. Parse YAML frontmatter and timestamped transcript dialogue.
3. Create semantic, speaker-aware chunks with source path, guest, episode title, YouTube URL, and start/end time.
4. Generate a stable chunk ID from source identity and content.
5. Generate embeddings through Ollama and upsert into pgvector. Preserve the corpus SHA with every row.
6. At query time, run lexical matching and vector similarity. Blend the result with a reciprocal-rank-inspired score and cap the set sent to the model.
7. Return citations including source links and time labels.

Embedding dimensions are deliberately fixed to the configured `embeddinggemma`-compatible 768 dimensions. A changed embedding model requires a re-ingest rather than mixing incompatible vectors.

## Agent routing and grounding contract

FastAPI, not the model, owns retrieval. The agent receives:

- The user question.
- A small recent session history.
- Retrieved evidence with immutable source IDs.
- A JSON output contract for answer text, claims, source IDs, counterpoint, and suggested actions.

The Pi runtime has `tools: []`; it cannot read project files, browse, execute commands, or access the database. The API rejects a model response when a claim cites a source ID outside the current retrieved evidence. If parsing or validation fails, a deterministic cited fallback is used rather than an uncited answer.

## Model selection

The model provider is selected by configuration:

- `ollama`: local model via a Pi-compatible OpenAI endpoint.
- `anthropic`: cloud model using an API key.
- `openai`: cloud model using an API key.

The response receipt records provider, model, corpus version, source count, retrieval latency, synthesis latency, and confidence. Provider failures do not trigger automatic cross-provider fallback.

## Artifact security model

Generated HTML is treated as hostile input. Markdown uses a renderer with raw HTML disabled. HTML passes through server sanitization and client sanitization, then is assigned to an iframe with:

- Empty `sandbox` attribute; no `allow-same-origin` or script privileges.
- `referrerPolicy="no-referrer"`.
- CSP denying all default connections, scripts, external image/font/media loads, forms, and base URL changes.
- Removal of scripts, event handler attributes, forms, frames, embedded objects, link navigation, and CSS `url`, `@import`, or expression behavior.

This deliberately supports only self-contained HTML/CSS, which matches the take-home requirement without turning the parent application into a code execution host.

## Observability

FastAPI writes structured JSON logs for startup, request completion, chat completion, model provider, source count, retrieval and agent timing, and fallback use. Every response includes `X-Request-ID`. The liveness/readiness routes distinguish database availability from provider availability.

## Extension paths

- Add a background worker for large corpus refreshes and ingestion progress.
- Add a cross-encoder reranker behind the current retrieval interface.
- Implement user authentication before multi-tenant use.
- Add a review/approval workflow before sharing or publishing artifacts.
