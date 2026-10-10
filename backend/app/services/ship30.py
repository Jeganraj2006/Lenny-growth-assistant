"""Dedicated Ship 30 for 30 writing skill.

The skill encodes an editorial process (specific audience, lens, and consistent
structure) before asking a model to write. It is deliberately separate from
the short-answer assistant so a one-off prompt cannot silently become product
behavior.
"""

import time

import httpx

from app.core.config import Settings
from app.schemas import SourceRef


def _source_block(sources: list[SourceRef]) -> str:
    return "\n\n".join(f"[{source.id}] {source.episode_title} — {source.guest}\n{source.excerpt}" for source in sources)


def _fallback(topic: str, audience: str, lens: str, structure: str, sources: list[SourceRef]) -> str:
    cited = sources[:3]
    evidence = "\n".join(f"- {source.excerpt} [{source.id}]" for source in cited)
    heading = {"steps": "Four steps", "lessons": "Four lessons", "mistakes": "Four mistakes", "framework": "A four-part framework"}[structure]
    return f"""# Stop treating growth advice like a checklist

Most product teams do not suffer from a lack of ideas. They suffer from acting on an idea before they know which constraint they are solving. That is why a retention conversation can become an acquisition project, and a perfectly reasonable onboarding change can become months of work with no learning to show for it.

For **{audience}**, the useful move is not to collect more advice. It is to build a disciplined way to turn evidence into one clear decision. This is an {lens} essay organised as {heading.lower()}.

## {heading}: find the constraint before the solution

Begin with the behaviour that makes the product valuable. A user who signs up but never reaches that moment is not yet a retained user; they are a signal that the path to value may be unclear. The practical implication is to write down the smallest observable behaviour that indicates value before proposing a redesign. [{cited[0].id if cited else 'source-needed'}]

That framing changes the meeting. Instead of debating whether the onboarding should be shorter, the team can ask whether the new user understands the job the product does and completes the action that reveals that value.

## Name the assumption

Good experiments have an opinion. State the audience, the expected behaviour, and the leading measure that would change if the belief is right. Do not hide behind a general ambition such as “improve engagement.” A named assumption makes it possible to learn even when the result is negative. [{cited[1].id if len(cited) > 1 else 'source-needed'}]

This also gives a cross-functional team a shared language. Design can challenge whether the experience communicates value. Engineering can challenge feasibility. Product can protect the threshold for success. No one has to pretend that a chart by itself chooses the decision.

## Make the test narrow enough to teach you something

The tempting response to weak retention is a broad rebuild. Resist it. Pick a segment, change one meaningful part of the path, and decide beforehand what will happen if the measure moves, does not move, or creates an unexpected cost. The goal is not to prove that the team had the right instinct. The goal is to reduce uncertainty.

That discipline is especially important because advice only works inside its context. A team with healthy demand and poor activation has a different first problem from a team that has not yet learned why anyone buys. [{cited[2].id if len(cited) > 2 else 'source-needed'}]

## Turn evidence into a decision rule

Before launch, agree on the result that changes the next action. If the leading measure reaches the threshold with no material quality decline, extend the test. If it does not, capture what was learned and revise the hypothesis. If the evidence says the original constraint was wrong, stop optimising the wrong place.

That is the quiet advantage of evidence-first work: it replaces “what should we try?” with “what would we need to learn to make the next decision?” It is a more demanding question, but it creates a product organisation that compounds knowledge rather than merely accumulating launches.

## The takeaway

The strongest growth plan is not the one with the longest backlog. It is the one that identifies the current constraint, writes a narrow hypothesis, and commits to a decision rule before the result arrives. Start there, then let the evidence—not the confidence of the loudest idea—decide what comes next.

## Sources behind this essay

{evidence or '- Ingest the full transcript corpus before publication.'}
"""


async def draft_ship30(topic: str, audience: str, lens: str, structure: str, sources: list[SourceRef], settings: Settings) -> str:
    if not sources:
        return "# Insufficient evidence\n\nI cannot draft a source-grounded Ship 30 essay until the session contains retrieved transcript evidence."
    prompt = f"""You are the dedicated Ship 30 for 30 writing skill in Lenny Lens.
Write an approximately 1,250-word Markdown essay for {audience} about: {topic}.

Use the {lens} lens and organise every main section consistently as {structure}. Start with a strong, specific hook. Create a clear narrative progression, skimmable headings, bullets only when they increase clarity, and selective bold emphasis. End with one concrete takeaway. Use only the evidence below for factual claims. Attach citations using each given source ID beside the claims, then finish with a 'Sources behind this essay' section. Explicitly qualify advice when evidence is contextual or conflicting. Return only the finished Markdown essay.

EVIDENCE:
{_source_block(sources)}"""
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(f"{settings.agent_url.rstrip('/')}/generate", json={"provider": settings.llm_provider, "model": settings.active_model, "prompt": prompt})
            response.raise_for_status()
            content = response.json().get("content", "").strip()
            if len(content.split()) >= 750:
                return content
    except httpx.HTTPError:
        pass
    return _fallback(topic, audience, lens, structure, sources)
