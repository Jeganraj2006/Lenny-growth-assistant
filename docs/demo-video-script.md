# Two to Three Minute Demo Script

**0:00-0:20 — Problem**

“Product and growth teams have hundreds of hours of excellent expert interviews available, but retrieving a quote is not the same as making a trustworthy decision. Generic chat tools also flatten context into universal best practices.”

**0:20-0:45 — Product and local deployment**

“This is Lenny Lens, an evidence-to-action workspace. It runs locally with Docker Compose, PostgreSQL, pgvector, Pi Coding Agent SDK, and Ollama. The rail shows the current provider and model, so the deployment mode is never hidden.”

**0:45-1:25 — Grounded answer**

Ask: “How should a B2B team diagnose weak week-one retention?”

“The API retrieves evidence before calling the model. Every answer has an Evidence Receipt with model, corpus version, retrieval count, timings, confidence, and sources. The model can only cite source IDs from this retrieval set. If it emits another citation, the API rejects the response.”

**1:25-1:50 — Context, not generic consensus**

“The useful difference is that Lenny Lens separates what the sources support from recommendations and surfaces a counterpoint when advice depends on the situation. That makes it usable for a real decision rather than just a summary.”

**1:50-2:20 — Artifact and security**

Click **Decision canvas**.

“The team can turn the evidence into a decision canvas without leaving the product. HTML is not trusted: it is sanitized on server and client, then rendered in an iframe with no script or same-origin permission and a restrictive CSP. This is why the viewer supports self-contained HTML and CSS only.”

**2:20-2:40 — Trade-off and handoff**

“I deliberately chose a constrained agent rather than autonomous tools. Pi has no filesystem or shell tools in this product; FastAPI owns retrieval and validation. The README, PRD, architecture, health checks, tests, and troubleshooting path are included so a client engineer can run and extend it.”
