import type { SourceRef } from "../types";

export function SourceList({ sources }: { sources: SourceRef[] }) {
  if (!sources.length) return null;
  return (
    <section className="sources" aria-label="Retrieved sources">
      <p className="section-label">Retrieved evidence</p>
      <div className="source-list">
        {sources.map((source, index) => (
          <a className="source-card" href={source.source_url} target="_blank" rel="noreferrer" key={source.id}>
            <span className="source-index">S{index + 1}</span>
            <span className="source-body">
              <strong>{source.episode_title}</strong>
              <small>{source.guest}{source.timestamp_label ? ` · ${source.timestamp_label}` : ""} · {Math.round(source.relevance * 100)}% match</small>
              <em>{source.excerpt}</em>
            </span>
            <span className="source-arrow">↗</span>
          </a>
        ))}
      </div>
    </section>
  );
}

