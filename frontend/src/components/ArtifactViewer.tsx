import DOMPurify from "dompurify";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Artifact } from "../types";

type Props = { artifact: Artifact | null; onClose: () => void };

export function ArtifactViewer({ artifact, onClose }: Props) {
  if (!artifact) {
    return (
      <aside className="artifact-pane empty-artifact" aria-label="Artifact viewer">
        <div className="empty-state compact">
          <span className="icon-chip">◫</span>
          <h2>Artifact viewer</h2>
          <p>Turn a grounded conversation into a decision canvas or a portable research brief.</p>
        </div>
      </aside>
    );
  }

  const download = () => {
    const extension = artifact.kind === "html" ? "html" : "md";
    const blob = new Blob([artifact.content], { type: artifact.kind === "html" ? "text/html" : "text/markdown" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `${artifact.title.toLowerCase().replace(/[^a-z0-9]+/g, "-")}.${extension}`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  const sanitizedArtifact = DOMPurify.sanitize(artifact.content, { FORBID_TAGS: ["script", "iframe", "object", "embed", "form", "input", "button", "base", "link"], FORBID_ATTR: ["src", "href", "action", "formaction"] });
  const safeSrcDoc = `<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:; media-src 'none'; connect-src 'none'; form-action 'none'; base-uri 'none'"></head><body>${sanitizedArtifact}</body></html>`;

  return (
    <aside className="artifact-pane" aria-label="Artifact viewer">
      <header className="artifact-header">
        <div>
          <p className="eyebrow">{artifact.kind === "html" ? "Interactive artifact" : "Markdown artifact"}</p>
          <h2>{artifact.title}</h2>
        </div>
        <div className="header-actions">
          <button className="icon-button" onClick={download} aria-label="Download artifact" title="Download artifact">⇩</button>
          <button className="icon-button" onClick={onClose} aria-label="Close artifact" title="Close artifact">×</button>
        </div>
      </header>
      <div className="artifact-content">
        {artifact.kind === "html" ? (
          <iframe
            title={artifact.title}
            className="artifact-frame"
            sandbox=""
            referrerPolicy="no-referrer"
            srcDoc={safeSrcDoc}
          />
        ) : (
          <article className="markdown artifact-markdown">
            <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>{artifact.content}</ReactMarkdown>
          </article>
        )}
      </div>
      <footer className="artifact-footer">Sandboxed preview · {artifact.source_refs.length} linked evidence source{artifact.source_refs.length === 1 ? "" : "s"}</footer>
    </aside>
  );
}
