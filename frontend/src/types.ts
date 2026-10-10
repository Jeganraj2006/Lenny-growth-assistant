export type SourceRef = {
  id: string;
  episode_title: string;
  guest: string;
  excerpt: string;
  source_url: string;
  timestamp_label?: string | null;
  start_seconds?: number | null;
  relevance: number;
};

export type Receipt = {
  provider: string;
  model: string;
  corpus_sha: string;
  retrieval_count: number;
  retrieval_latency_ms: number;
  agent_latency_ms: number;
  confidence: "high" | "medium" | "low" | "insufficient";
  demo_data: boolean;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceRef[];
  receipt?: Receipt;
  created_at?: string;
};

export type Artifact = {
  id: string;
  kind: "markdown" | "html";
  title: string;
  content: string;
  source_refs: SourceRef[];
  created_at: string;
};

export type ChatSession = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type ProviderStatus = {
  provider: string;
  model: string;
  available: boolean;
  detail?: string | null;
};
