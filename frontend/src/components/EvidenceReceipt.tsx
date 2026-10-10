import type { Receipt } from "../types";

export function EvidenceReceipt({ receipt }: { receipt: Receipt }) {
  return (
    <details className="receipt">
      <summary>
        <span className={`confidence confidence-${receipt.confidence}`}>{receipt.confidence}</span>
        <span>Evidence receipt</span>
        <span className="receipt-summary">{receipt.retrieval_count} sources · {receipt.retrieval_latency_ms + receipt.agent_latency_ms} ms</span>
      </summary>
      <div className="receipt-grid">
        <div><span>Model</span><strong>{receipt.provider} / {receipt.model}</strong></div>
        <div><span>Corpus</span><strong className="mono">{receipt.corpus_sha.slice(0, 18)}</strong></div>
        <div><span>Retrieval</span><strong>{receipt.retrieval_count} chunks · {receipt.retrieval_latency_ms} ms</strong></div>
        <div><span>Synthesis</span><strong>{receipt.agent_latency_ms} ms</strong></div>
      </div>
      {receipt.demo_data && <p className="receipt-note">Demo corpus is active. Run ingestion before relying on this result for production research.</p>}
    </details>
  );
}

