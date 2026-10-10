import type { Artifact, ChatSession, Message, ProviderStatus, Receipt, SourceRef } from "./types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

type ChatResponse = {
  session_id: string;
  message_id: string;
  answer_markdown: string;
  sources: SourceRef[];
  receipt: Receipt;
  counterpoint?: string | null;
  suggested_actions: string[];
};

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers ?? {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => undefined) as { error?: { message?: string } } | undefined;
    throw new Error(body?.error?.message ?? `Request failed with ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  config: () => request<ProviderStatus>("/config"),
  sessions: () => request<ChatSession[]>("/sessions"),
  session: (id: string) => request<ChatSession & { messages: Message[]; artifacts: Artifact[] }>(`/sessions/${id}`),
  chat: (message: string, sessionId?: string) => request<ChatResponse>("/chat", { method: "POST", body: JSON.stringify({ message, session_id: sessionId }) }),
  artifact: (sessionId: string, kind: "markdown" | "html", title: string, instruction: string) =>
    request<Artifact>(`/sessions/${sessionId}/artifacts`, { method: "POST", body: JSON.stringify({ kind, title, instruction }) }),
  ship30: (sessionId: string) =>
    request<Artifact>(`/sessions/${sessionId}/ship30`, { method: "POST", body: JSON.stringify({ audience: "product and growth practitioners", lens: "actionable", structure: "steps" }) }),
};
