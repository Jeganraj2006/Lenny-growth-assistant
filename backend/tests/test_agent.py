from app.schemas import SourceRef
from app.services.agent import _parse_model_json, _fallback


SOURCE = SourceRef(
    id="source-1234",
    episode_title="Episode",
    guest="Guest",
    excerpt="Evidence excerpt",
    source_url="https://example.com",
    relevance=0.8,
)


def test_agent_payload_rejects_hallucinated_citation() -> None:
    payload = '{"answer_markdown":"Answer", "claims":[{"statement":"Claim", "source_ids":["invented"], "support":"supported"}]}'
    assert _parse_model_json(payload, {"S1": SOURCE.id}) is None


def test_agent_payload_maps_short_label_to_immutable_source_id() -> None:
    payload = '{"answer_markdown":"Answer", "claims":[{"statement":"Claim", "source_ids":["S1"], "support":"supported"}]}'
    response = _parse_model_json(payload, {"S1": SOURCE.id})
    assert response is not None
    assert response.claims[0].source_ids == [SOURCE.id]


def test_fallback_is_cited() -> None:
    response = _fallback([SOURCE])
    assert response.claims[0].source_ids == [SOURCE.id]
    assert "[S1]" in response.answer_markdown
