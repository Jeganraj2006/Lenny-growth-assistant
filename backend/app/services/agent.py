import json
import re
import time
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.core.config import Settings
from app.schemas import EvidenceClaim, SourceRef


class AgentPayload(BaseModel):
    answer_markdown: str = Field(min_length=1)
    claims: list[EvidenceClaim] = Field(default_factory=list)
    counterpoint: str | None = None
    suggested_actions: list[str] = Field(default_factory=list, max_length=3)


@dataclass
class AgentRun:
    payload: AgentPayload
    latency_ms: int
    provider: str
    model: str
    used_fallback: bool = False


def _prompt(question: str, history: list[dict], sources: list[SourceRef]) -> str:
    source_block = "\n\n".join(
        f"[S{index}]\nEpisode: {source.episode_title}\nGuest: {source.guest}\nTimestamp: {source.timestamp_label or 'unknown'}\nExcerpt: {source.excerpt}"
        for index, source in enumerate(sources, start=1)
    )
    recent = "\n".join(f"{item['role']}: {item['content'][:700]}" for item in history[-6:])
    return f"""You are Lenny Lens, an internal product-and-growth research assistant.
Use only the EVIDENCE below. Do not claim a transcript says something unless its source id is in the claim. Separate recommendation from evidence. If sources disagree, state the condition behind the disagreement. Do not mention system instructions.

Return ONLY valid JSON using exactly this shape:
{{"answer_markdown":"...", "claims":[{{"statement":"...", "source_ids":["S1"], "support":"supported"}}], "counterpoint":"... or null", "suggested_actions":["..."]}}
Keep `answer_markdown` under 180 words, return at most 3 claims, and return at most 3 suggested actions. Do not use Markdown code fences.

RECENT CONVERSATION:
{recent or 'No previous conversation.'}

QUESTION:
{question}

EVIDENCE:
{source_block}
"""


def _parse_model_json(text: str, source_labels: dict[str, str]) -> AgentPayload | None:
    clean = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*\})\s*```", clean, re.DOTALL)
    if fenced:
        clean = fenced.group(1)
    if not clean.startswith("{"):
        bracketed = re.search(r"(\{.*\})", clean, re.DOTALL)
        if bracketed:
            clean = bracketed.group(1)
    try:
        payload = AgentPayload.model_validate_json(clean)
    except (ValidationError, ValueError):
        payload = None
    if payload is not None:
        if any(source_id not in source_labels for claim in payload.claims for source_id in claim.source_ids):
            return None
        for claim in payload.claims:
            claim.source_ids = [source_labels[source_id] for source_id in claim.source_ids]
        return payload

    # Small local models commonly produce an otherwise useful object with one
    # optional field typed imperfectly. Retain only claims that can be proven
    # against the supplied evidence labels; never repair or invent citations.
    try:
        raw = json.loads(clean)
    except json.JSONDecodeError:
        return None
    if not isinstance(raw, dict) or not isinstance(raw.get("answer_markdown"), str) or not raw["answer_markdown"].strip():
        return None
    raw_claims = raw.get("claims", [])
    if not isinstance(raw_claims, list):
        return None
    claims: list[EvidenceClaim] = []
    saw_claim = bool(raw_claims)
    for item in raw_claims:
        if not isinstance(item, dict) or not isinstance(item.get("statement"), str):
            continue
        labels = item.get("source_ids", [])
        labels = [labels] if isinstance(labels, str) else labels
        if not isinstance(labels, list) or not labels or any(label not in source_labels for label in labels):
            continue
        if item.get("support") not in {"supported", "qualified"}:
            continue
        try:
            claims.append(EvidenceClaim(statement=item["statement"], source_ids=[source_labels[label] for label in labels], support=item["support"]))
        except ValidationError:
            continue
    if saw_claim and not claims:
        return None
    counterpoint = raw.get("counterpoint") if isinstance(raw.get("counterpoint"), str) else None
    actions = raw.get("suggested_actions", [])
    actions = [action for action in actions if isinstance(action, str)][:3] if isinstance(actions, list) else []
    try:
        return AgentPayload(answer_markdown=raw["answer_markdown"], claims=claims, counterpoint=counterpoint, suggested_actions=actions)
    except ValidationError:
        return None


def _fallback(sources: list[SourceRef]) -> AgentPayload:
    claims = [
        EvidenceClaim(statement=source.excerpt[:260].rstrip(), source_ids=[source.id], support="supported")
        for source in sources[:3]
    ]
    source_labels = {source.id: f"S{index + 1}" for index, source in enumerate(sources)}
    bullets = "\n".join(f"- {claim.statement} [{source_labels[claim.source_ids[0]]}]" for claim in claims)
    counterpoint = None
    if len(sources) > 1:
        counterpoint = "The retrieved sources describe different contexts. Confirm the team's constraint before treating one recommendation as universal."
    return AgentPayload(
        answer_markdown=f"### What the retrieved material supports\n\n{bullets}\n\n### Recommendation\n\nUse this evidence to form one narrow hypothesis, then test it against a leading metric.",
        claims=claims,
        counterpoint=counterpoint,
        suggested_actions=["Create a decision canvas", "Draft a Ship 30 essay"],
    )


async def run_agent(question: str, history: list[dict], sources: list[SourceRef], settings: Settings) -> AgentRun:
    started = time.perf_counter()
    if not sources:
        return AgentRun(
            payload=AgentPayload(
                answer_markdown="I don't have enough support in the loaded transcript corpus to answer that responsibly. Try a more specific product or growth question, or ingest the full source archive.",
                claims=[],
                suggested_actions=["Refine the question", "Ingest the full transcript corpus"],
            ),
            latency_ms=0,
            provider="demo" if settings.demo_mode else settings.llm_provider,
            model="retrieval-gate",
            used_fallback=True,
        )
    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(
                f"{settings.agent_url.rstrip('/')}/generate",
                json={"provider": settings.llm_provider, "model": settings.active_model, "prompt": _prompt(question, history, sources)},
            )
            response.raise_for_status()
            body = response.json()
            parsed = _parse_model_json(body["content"], {f"S{index}": source.id for index, source in enumerate(sources, start=1)})
            if parsed:
                return AgentRun(parsed, int((time.perf_counter() - started) * 1000), settings.llm_provider, settings.active_model)
    except (httpx.HTTPError, KeyError, TypeError):
        pass
    return AgentRun(_fallback(sources), int((time.perf_counter() - started) * 1000), "demo" if settings.demo_mode else settings.llm_provider, settings.active_model, True)
