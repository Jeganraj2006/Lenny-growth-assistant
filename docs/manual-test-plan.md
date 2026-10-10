# Manual Test Plan

## Pre-flight

1. Copy `.env.example` to `.env`.
2. Run `docker compose --profile local up --build`.
3. Open `http://localhost:5173` and check the provider status in the left rail.
4. For full corpus behavior, run the documented ingestion command in a separate terminal.

## Core walkthrough

| Test | Action | Expected result |
| --- | --- | --- |
| New session | Select **New research**, ask a retention question | A new session appears after response; answer contains receipt and sources |
| Session isolation | Start a second session, ask a different question, reopen first session | Previous messages remain only in their original session |
| Evidence gate | Ask for a topic absent from demo corpus | Clear unsupported-material acknowledgement rather than a fabricated answer |
| Sources | Open a source card | Transcript source opens in a new, safe browser tab |
| Artifact | Select **Decision canvas** | Safe HTML/CSS artifact appears beside chat and can be downloaded |
| Markdown artifact | Select **Evidence brief** | Markdown artifact renders in-app with source links |
| HTML safety | Generate/open an artifact containing markup | No script execution, popup, navigation, external image, or parent access is possible |
| Provider failure | Stop Ollama / unset cloud key | UI/API identifies unavailable provider; no silent different-provider result |
| Health | Visit `/api/health/live` and `/api/health/ready` | Structured provider/database status appears |

## Required demo recording

1. Begin camera-on and frame the problem: product teams need expert research they can trust.
2. Show local Ollama configured in the UI and Docker services running.
3. Ask a retention/activation question and expand the Evidence Receipt.
4. Open two source cards and explain that claims are limited to retrieved source IDs.
5. Create an HTML Decision Canvas beside the chat.
6. Explain the artifact sandbox and the deliberate decision not to silently cloud-fallback.
