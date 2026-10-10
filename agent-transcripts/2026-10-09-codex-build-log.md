# Redacted Coding Agent Build Log

This is a concise, redacted development log retained for handoff. It contains no API keys, user data, or local absolute paths.

## Objective

Build an evaluator-ready Forward Deployed Engineer take-home: FastAPI, PostgreSQL, Pi Coding Agent SDK, Ollama/local model path, Lenny transcript retrieval, safe artifacts, and operational documentation.

## Decisions made

1. Used a Pi SDK sidecar with `tools: []`, rather than letting a coding agent access files or shell commands. Retrieval and citation validation remain in FastAPI.
2. Used PostgreSQL/pgvector plus lexical fallback so initial model pulls do not make evaluator feedback opaque.
3. Made corpus version, model, source count, and latencies visible in an Evidence Receipt.
4. Used a split-pane artifact workspace, with HTML treated as untrusted content.

## Failed attempt and correction

| Attempt | Result | Correction |
| --- | --- | --- |
| Rendered the supplied Word brief with headless LibreOffice | The available runtime lacked `soffice`; no layout render was produced | Extracted all paragraphs, tables, and links structurally with `python-docx`; preserved the complete requirements in the implementation plan. |
| Considered embedding an unrestricted agent in FastAPI | It would give a user-facing research assistant inappropriate filesystem/shell capability | Moved Pi to an isolated sidecar and expose no agent tools; FastAPI provides only retrieved evidence in the prompt. |
| Considered raw generated HTML in the application DOM | This violates the brief's untrusted-HTML security expectation | Added server sanitization, client sanitization, restrictive CSP, empty iframe sandbox, and no external network assets. |

## Verification ledger

- Python source compiled successfully after initial backend implementation.
- Automated tests cover sanitizer behavior, citation validation, lexical-term filtering, and session persistence isolation.
- Remaining verification commands and manual UI walkthrough are documented in the README and manual test plan.
