import { useEffect, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { api } from "./api";
import { ArtifactViewer } from "./components/ArtifactViewer";
import { Composer } from "./components/Composer";
import { EvidenceReceipt } from "./components/EvidenceReceipt";
import { SourceList } from "./components/SourceList";
import type { Artifact, ChatSession, Message, ProviderStatus } from "./types";

const SUGGESTIONS = [
  "How should a B2B product team diagnose weak week-one retention?",
  "What makes an onboarding experiment worth running?",
  "How do product leaders decide between activation and acquisition work?",
];

function initialMessage(): Message {
  return {
    id: "welcome",
    role: "assistant",
    content: "## Research before recommendation\n\nAsk a product or growth question and I’ll retrieve evidence from the loaded Lenny transcript corpus, identify where advice is conditional, and leave you with sources you can inspect.\n\nI’ll say when the corpus does not support a conclusion.",
  };
}

export default function App() {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionId, setSessionId] = useState<string | undefined>();
  const [messages, setMessages] = useState<Message[]>([initialMessage()]);
  const [artifact, setArtifact] = useState<Artifact | null>(null);
  const [provider, setProvider] = useState<ProviderStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [artifactLoading, setArtifactLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void Promise.all([api.sessions(), api.config()])
      .then(([nextSessions, nextProvider]) => { setSessions(nextSessions); setProvider(nextProvider); })
      .catch((nextError: Error) => setError(nextError.message));
  }, []);

  const currentTitle = useMemo(() => sessions.find((session) => session.id === sessionId)?.title ?? "New research", [sessions, sessionId]);

  const selectSession = async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.session(id);
      setSessionId(id);
      setMessages(data.messages.length ? data.messages : [initialMessage()]);
      setArtifact(data.artifacts[0] ?? null);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Unable to load session.");
    } finally { setLoading(false); }
  };

  const newResearch = () => {
    setSessionId(undefined);
    setMessages([initialMessage()]);
    setArtifact(null);
    setError(null);
  };

  const send = async (question: string) => {
    setLoading(true);
    setError(null);
    const pending: Message = { id: `pending-${Date.now()}`, role: "user", content: question };
    setMessages((previous) => [...previous, pending]);
    try {
      const result = await api.chat(question, sessionId);
      const assistant: Message = {
        id: result.message_id,
        role: "assistant",
        content: result.counterpoint ? `${result.answer_markdown}\n\n### Context / counterpoint\n\n${result.counterpoint}` : result.answer_markdown,
        sources: result.sources,
        receipt: result.receipt,
      };
      setSessionId(result.session_id);
      setMessages((previous) => [...previous, assistant]);
      const latestSessions = await api.sessions();
      setSessions(latestSessions);
      setProvider(await api.config());
    } catch (nextError) {
      setMessages((previous) => previous.filter((message) => message.id !== pending.id));
      setError(nextError instanceof Error ? nextError.message : "Unable to complete research.");
    } finally { setLoading(false); }
  };

  const createArtifact = async (kind: "markdown" | "html") => {
    if (!sessionId) return;
    setArtifactLoading(true);
    setError(null);
    try {
      const next = await api.artifact(
        sessionId,
        kind,
        kind === "html" ? "Evidence to Decision Canvas" : "Evidence Brief",
        kind === "html" ? "Turn the current grounded conversation into a concise decision canvas for a product team." : "Summarise the current grounded conversation as a decision-ready evidence brief.",
      );
      setArtifact(next);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Unable to create artifact.");
    } finally { setArtifactLoading(false); }
  };

  const createShip30 = async () => {
    if (!sessionId) return;
    setArtifactLoading(true);
    setError(null);
    try {
      setArtifact(await api.ship30(sessionId));
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : "Unable to draft the essay.");
    } finally { setArtifactLoading(false); }
  };

  return (
    <main className={`app-shell ${artifact ? "artifact-open" : ""}`}>
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark">L</span><span>Lenny <b>Lens</b></span></div>
        <button className="new-research" onClick={newResearch}><span>＋</span> New research</button>
        <nav aria-label="Research sessions">
          <p className="nav-label">RECENT RESEARCH</p>
          {sessions.length ? sessions.map((session) => (
            <button key={session.id} className={`session-link ${session.id === sessionId ? "active" : ""}`} onClick={() => void selectSession(session.id)}>{session.title}</button>
          )) : <p className="empty-history">Your research history will appear here.</p>}
        </nav>
        <div className="sidebar-bottom">
          <span className={`provider-dot ${provider?.available ? "online" : "offline"}`} />
          <div><strong>{provider ? `${provider.provider} / ${provider.model}` : "Checking model…"}</strong><small>{provider?.available ? "Ready" : provider?.detail ?? "Status unknown"}</small></div>
        </div>
      </aside>

      <section className="chat-workspace">
        <header className="topbar">
          <div><p className="eyebrow">EVIDENCE TO ACTION</p><h1>{currentTitle}</h1></div>
          <div className="topbar-actions"><span className="privacy-badge">● Local-first</span><button className="help-button" title="Evidence is retrieved before the model writes">How it works</button></div>
        </header>

        {error && <div className="error-banner" role="alert"><span>!</span>{error}<button onClick={() => setError(null)} aria-label="Dismiss error">×</button></div>}

        <div className="conversation" aria-live="polite">
          {messages.map((message) => (
            <article key={message.id} className={`message message-${message.role}`}>
              <div className="avatar" aria-hidden="true">{message.role === "assistant" ? "L" : "You"}</div>
              <div className="message-body">
                {message.role === "assistant" ? <div className="markdown"><ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>{message.content}</ReactMarkdown></div> : <p>{message.content}</p>}
                {message.receipt && <EvidenceReceipt receipt={message.receipt} />}
                {message.sources && <SourceList sources={message.sources} />}
                {message.role === "assistant" && message.id !== "welcome" && <div className="artifact-actions">
                  <button disabled={!sessionId || artifactLoading} onClick={() => void createArtifact("html")}>◫ {artifactLoading ? "Building…" : "Decision canvas"}</button>
                  <button disabled={!sessionId || artifactLoading} onClick={() => void createArtifact("markdown")}>⌁ Evidence brief</button>
                  <button disabled={!sessionId || artifactLoading} onClick={() => void createShip30()}>✦ Ship 30 essay</button>
                </div>}
              </div>
            </article>
          ))}
          {messages.length === 1 && <div className="suggestions"><p>Try a research prompt</p>{SUGGESTIONS.map((suggestion) => <button key={suggestion} onClick={() => void send(suggestion)}>{suggestion}<span>↗</span></button>)}</div>}
        </div>
        <Composer onSend={send} disabled={loading} />
      </section>
      <ArtifactViewer artifact={artifact} onClose={() => setArtifact(null)} />
    </main>
  );
}
