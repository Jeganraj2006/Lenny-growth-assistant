from app.services.artifacts import SANDBOX_CSP, sanitize_html


def test_html_sanitizer_removes_executable_and_network_markup() -> None:
    result = sanitize_html("<script>alert(1)</script><a href='https://evil.test' onclick='x()'>link</a><img src='https://evil.test/a.png'><div style='background:url(https://evil.test/x)'>safe</div>")
    assert "<script" not in result
    assert "onclick" not in result
    assert "https://evil.test" not in result
    assert "Content-Security-Policy" in result
    assert SANDBOX_CSP in result

