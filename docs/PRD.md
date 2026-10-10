# Lenny Lens Product Requirements Document

## Product decision

Build a local-first research workspace that turns Lenny's Podcast transcripts into decision-ready product and growth guidance. Lenny Lens is not positioned as an omniscient adviser. It retrieves evidence, states the conditions under which advice applies, surfaces a counterpoint where evidence diverges, and turns the result into a useful artifact.

## User and problem

The primary user is a product manager or growth lead preparing a decision, experiment, narrative, or internal brief. They have a practical question but lack time to search hours of expert interviews, compare competing views, and turn what they learn into a shareable artifact. Existing chat interfaces make advice sound universal and make it hard to inspect the source material.

Lenny Lens removes that friction by making evidence, scope, and uncertainty visible at the point a recommendation is made.

## Success measures

The first deployment is successful when:

- 90% of manually evaluated supported claims link only to retrieved source chunks.
- A new evaluator can complete the documented local startup and first grounded question in under 20 minutes, excluding initial model download.
- A product user can turn a grounded answer into a Markdown brief or safe HTML decision canvas in two interactions.
- A model/provider/database failure returns an actionable visible state instead of a blank result or hidden fallback.

## Product principles

1. Evidence before eloquence. A polished answer without traceable evidence is not a valid answer.
2. Advice is conditional. Show applicability and counterpoint rather than flattening experts into consensus.
3. Local means explicit. The app never silently sends a local request to a cloud provider.
4. Artifacts are part of the product, not a code export.
5. The system must be easy for another engineer to operate and extend.

## Primary flow

1. User starts a new research session and asks a product or growth question.
2. The API records the session and user message, retrieves hybrid lexical/vector evidence, and sends only those citations and the short conversation history to the Pi agent runtime.
3. The assistant returns source-backed claims, a qualified counterpoint when appropriate, next actions, source cards, and a Model/Evidence Receipt.
4. User selects **Decision canvas** or **Evidence brief**.
5. The artifact is stored with its sources and rendered beside the conversation.

## In scope

- FastAPI API with Pydantic validation and OpenAPI documentation.
- PostgreSQL persistence for sessions, messages, metadata, artifacts, chunks, and ingestion runs.
- Pi Coding Agent SDK sidecar with no file, shell, or network tools available to the agent.
- Ollama local demo path plus Anthropic/OpenAI configuration.
- Lenny transcript ingestion, chunking, metadata, embeddings, hybrid retrieval, citations, and source traceability.
- Grounded chat, Ship 30 essay-ready evidence flow, Markdown artifacts, HTML/CSS artifacts, and safe viewer.
- Docker Compose, health endpoints, structured logging, tests, troubleshooting, and evaluator handoff.

## Intentionally out of scope

- Authentication, roles, team workspaces, and external web search.
- Fine-tuning or a production-scale asynchronous indexing platform.
- Arbitrary JavaScript inside artifacts.
- Automatically deciding which product advice is objectively correct.
- Multi-provider automatic fallback; this would conceal cost, privacy, and data residency behavior.

## User stories and acceptance criteria

### Grounded research

As a growth lead, I can ask a follow-up question in a session and receive a source-backed response.

- Session context is isolated by session ID.
- Each response presents source cards with episode, guest, excerpt, relevance, and source link.
- The answer has no citation to a chunk absent from the retrieval result.
- When there is no support, the assistant explicitly says so.

### Model configuration

As an evaluator, I can tell which model ran a response and switch deployment configuration without code changes.

- `LLM_PROVIDER`, model names, and keys are environment variables.
- The UI shows provider state and receipt metadata.
- Missing Ollama or missing cloud keys return a visible status, with no silent fallback.

### Ship 30 for 30 skill

As a writer, I can turn evidence into a roughly 1,250-word essay with a hook, coherent narrative, headings, selected emphasis, a practical takeaway, and sources.

- The structured writing flow picks a specific audience, a Ship 30 lens, and one consistent organizing pattern before drafting.
- The draft treats source-derived observations differently from new recommendations.

### Artifact viewer

As a product user, I can see generated Markdown or HTML/CSS beside the chat.

- Markdown renders with raw HTML disabled.
- HTML is sanitized, rendered in a sandboxed iframe, and is downloadable.
- Unsafe script, event, form, iframe, object, external URL, and same-origin behavior is blocked.

## Risks and trade-offs

| Risk | Decision and mitigation |
| --- | --- |
| Hallucinated or decorative citations | Citation IDs are validated against the exact retrieval set before persistence. |
| Weak local-model JSON formatting | Pi prompts request an explicit contract; FastAPI validates it and falls back to a deterministic cited summary. |
| Local model unavailable | Health/config endpoints show the exact status. The demo fallback remains visibly labelled and never masquerades as full-corpus research. |
| Retrieval misses the right source | Hybrid lexical/vector retrieval, episode diversification, visible sources, and a user refinement path reduce but do not eliminate the risk. |
| Unsafe HTML artifact | Sanitization, no raw Markdown HTML, empty iframe sandbox, CSP, no remote assets, and safe export are layered defenses. |
| Corpus changes over time | Each chunk records a corpus Git SHA and every receipt identifies the corpus version. |
| Cost and latency | Local small model is the required demo default; the cloud configuration is opt-in. Retrieval/source snippets constrain context size. |

## Delivery plan

P0 is an operational grounded assistant with source cards, sessions, Ollama configuration, one-command startup, and evidence artifacts. P1 is an enhanced Ship 30 drafting workflow and richer ingestion monitoring. This sequencing favors evaluator trust over feature count.
