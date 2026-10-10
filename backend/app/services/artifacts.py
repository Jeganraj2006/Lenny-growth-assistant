import hashlib
import re
from html import escape

from bs4 import BeautifulSoup

from app.schemas import SourceRef


SANDBOX_CSP = "default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:; media-src 'none'; connect-src 'none'; form-action 'none'; base-uri 'none'"


def sanitize_html(raw_html: str) -> str:
    """Return self-contained presentation HTML safe enough for a sandboxed iframe.

    This is defense in depth. The client iframe has an empty sandbox and this
    function removes executable or network-capable markup before it gets there.
    """
    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup.find_all(["script", "iframe", "object", "embed", "form", "input", "button", "base", "link", "meta"]):
        tag.decompose()
    for tag in soup.find_all(True):
        for attribute in list(tag.attrs):
            value = str(tag.attrs[attribute])
            if attribute.lower().startswith("on") or attribute.lower() in {"src", "href", "action", "formaction"}:
                del tag.attrs[attribute]
            elif attribute.lower() == "style":
                tag.attrs[attribute] = re.sub(r"(?is)url\s*\([^)]*\)|expression\s*\([^)]*\)|@import[^;]*;", "", value)
    body = str(soup)
    return f"<!doctype html><html><head><meta charset='utf-8'><meta http-equiv='Content-Security-Policy' content=\"{SANDBOX_CSP}\"></head><body>{body}</body></html>"


def build_markdown_artifact(title: str, instruction: str, sources: list[SourceRef]) -> str:
    evidence = "\n".join(f"- **{source.episode_title}** ({source.guest}) [S{index + 1}]({source.source_url})" for index, source in enumerate(sources[:5]))
    return f"""# {title}

## Decision

{instruction.strip()}

## Evidence to use

{evidence or '- No grounded source was available. Validate before use.'}

## Suggested next step

Turn the strongest evidence into one testable hypothesis, define a leading metric, and agree on the decision that will follow the result.
"""


def build_html_artifact(title: str, instruction: str, sources: list[SourceRef]) -> str:
    cards = "".join(
        f"<li><strong>{escape(source.episode_title)}</strong><br><span>{escape(source.guest)} · {escape(source.timestamp_label or 'Transcript')}</span><p>{escape(source.excerpt[:180])}</p></li>"
        for source in sources[:4]
    ) or "<li>No grounded source was available. Validate before use.</li>"
    return sanitize_html(f"""
<main>
  <header><p class='eyebrow'>Lenny Lens · Evidence canvas</p><h1>{escape(title)}</h1><p>{escape(instruction)}</p></header>
  <section class='grid'>
    <article><h2>Question</h2><p>What decision should this evidence improve?</p></article>
    <article><h2>Hypothesis</h2><p>State the smallest meaningful change and expected user behaviour.</p></article>
    <article><h2>Leading metric</h2><p>Choose one measure that can change before the final outcome.</p></article>
    <article><h2>Decision rule</h2><p>Define what result means continue, revise, or stop.</p></article>
  </section>
  <section><h2>Evidence receipt</h2><ul>{cards}</ul></section>
</main>
<style>
  :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; color: #172234; background: #f7f8fb; }}
  body {{ margin: 0; padding: 36px; }} main {{ max-width: 1000px; margin: auto; }}
  header {{ border-bottom: 1px solid #dbe1ed; padding-bottom: 22px; }} .eyebrow {{ color: #4f46e5; font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: .1em; }}
  h1 {{ font-size: 34px; margin: 8px 0; }} h2 {{ font-size: 16px; }} .grid {{ display: grid; gap: 14px; grid-template-columns: repeat(2, minmax(0, 1fr)); margin: 24px 0; }}
  article, li {{ background: #fff; border: 1px solid #dbe1ed; border-radius: 12px; padding: 18px; }} ul {{ list-style: none; padding: 0; display: grid; gap: 12px; }} li p, li span {{ color: #586579; font-size: 14px; line-height: 1.5; }}
</style>
""")


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()

