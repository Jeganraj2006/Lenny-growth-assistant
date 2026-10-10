from app.services.retrieval import _terms


def test_terms_excludes_stop_words_and_keeps_useful_product_terms() -> None:
    result = _terms("What should this product team do about weak week one retention?")
    assert "product" in result
    assert "retention" in result
    assert "what" not in result

