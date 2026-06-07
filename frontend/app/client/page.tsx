"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import {
  AlertCircle,
  Bot,
  ChevronDown,
  ChevronUp,
  Clock,
  Loader2,
  Menu,
  MessageSquarePlus,
  RotateCcw,
  Send,
  Settings,
  Shield,
  User,
} from "lucide-react";

type ChatMessage = {
  id: number;
  role: "assistant" | "user";
  content: string;
  meta?: string;
};

const WELCOME: ChatMessage = {
  id: 1,
  role: "assistant",
  content:
    "Bienvenue. Pose ta question sur l'actualité RDC et je réponds avec un verdict et des sources locales.",
  meta: "Canal web",
};

const STORAGE_KEY_MESSAGES = "rdc-chat-messages";
const STORAGE_KEY_RECENT = "rdc-chat-recent";
const MAX_RECENT = 5;

const STREAM_IDLE_MS = (() => {
  const raw = process.env.NEXT_PUBLIC_RAG_STREAM_IDLE_MS;
  const n = raw ? Number.parseInt(raw, 10) : NaN;
  if (Number.isFinite(n) && n >= 60_000) return Math.min(n, 3_600_000);
  return 1_200_000;
})();

function parseNdjsonLines(
  buf: string,
  onEvent: (ev: {
    type: string;
    sources?: unknown[];
    text?: string;
    message?: string;
  }) => void,
) {
  const lines = buf.split("\n");
  const rest = lines.pop() ?? "";
  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      onEvent(
        JSON.parse(line) as {
          type: string;
          sources?: unknown[];
          text?: string;
          message?: string;
        },
      );
    } catch {
      /* ligne partielle */
    }
  }
  return rest;
}

function loadStoredMessages(): ChatMessage[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_MESSAGES);
    if (!raw) return [WELCOME];
    const parsed = JSON.parse(raw) as ChatMessage[];
    return Array.isArray(parsed) && parsed.length > 0 ? parsed : [WELCOME];
  } catch {
    return [WELCOME];
  }
}

function loadRecentQueries(): string[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY_RECENT);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as string[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function addRecentQuery(query: string) {
  try {
    const prev = loadRecentQueries();
    const deduped = [query, ...prev.filter((q) => q !== query)].slice(
      0,
      MAX_RECENT,
    );
    localStorage.setItem(STORAGE_KEY_RECENT, JSON.stringify(deduped));
  } catch {
    /* ignore */
  }
}

export default function ClientPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [sideOpen, setSideOpen] = useState(true);
  const [recentOpen, setRecentOpen] = useState(true);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [recentQueries, setRecentQueries] = useState<string[]>([]);
  const [hasSavedSession, setHasSavedSession] = useState(false);
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const hydrated = useRef(false);

  /* Hydratation localStorage côté client uniquement */
  useEffect(() => {
    if (hydrated.current) return;
    hydrated.current = true;
    const stored = loadStoredMessages();
    setMessages(stored);
    setRecentQueries(loadRecentQueries());
    setHasSavedSession(stored.length > 1);
  }, []);

  /* Auto-save messages dès qu'ils changent */
  useEffect(() => {
    if (!hydrated.current) return;
    try {
      localStorage.setItem(STORAGE_KEY_MESSAGES, JSON.stringify(messages));
      setHasSavedSession(messages.length > 1);
    } catch {
      /* ignore */
    }
  }, [messages]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSubmit();
    }
  };

  const startNewChat = () => {
    setMessages([WELCOME]);
    setError(null);
    try {
      localStorage.removeItem(STORAGE_KEY_MESSAGES);
    } catch {
      /* ignore */
    }
    setHasSavedSession(false);
  };

  const restoreSession = () => {
    const stored = loadStoredMessages();
    setMessages(stored);
    setHasSavedSession(stored.length > 1);
  };

  const useRecentQuery = (q: string) => {
    setQuery(q);
  };

  const handleSubmit = async () => {
    const trimmed = query.trim();
    if (!trimmed || loading) return;
    setError(null);
    setLoading(true);

    addRecentQuery(trimmed);
    setRecentQueries(loadRecentQueries());

    const userMsg: ChatMessage = {
      id: Date.now(),
      role: "user",
      content: trimmed,
      meta: "Toi",
    };
    const asstId = Date.now() + 1;
    const assistantPlaceholder: ChatMessage = {
      id: asstId,
      role: "assistant",
      content: "",
      meta: "Génération…",
    };
    setMessages((prev) => [...prev, userMsg, assistantPlaceholder]);
    setQuery("");

    const controller = new AbortController();
    let idleAbortId: number | undefined;
    const resetIdleAbort = () => {
      if (idleAbortId !== undefined) window.clearTimeout(idleAbortId);
      idleAbortId = window.setTimeout(
        () => controller.abort(),
        STREAM_IDLE_MS,
      );
    };

    try {
      const res = await fetch("/api/fastapi/rag/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const p = await res.json().catch(() => ({}));
        throw new Error(p?.error ?? "Erreur serveur.");
      }

      const reader = res.body?.getReader();
      if (!reader) throw new Error("Aucun flux de réponse.");
      const decoder = new TextDecoder();
      let buf = "",
        summary = "",
        srcCount = 0;

      const update = (content: string, meta: string) =>
        setMessages((prev) =>
          prev.map((m) => (m.id === asstId ? { ...m, content, meta } : m)),
        );

      const handleEvent = (ev: {
        type: string;
        sources?: unknown[];
        text?: string;
        message?: string;
      }) => {
        resetIdleAbort();
        if (ev.type === "sources") {
          srcCount = Array.isArray(ev.sources) ? ev.sources.length : 0;
          update(
            summary ||
              "Sources trouvées. Génération de la réponse (Ollama peut prendre 1–3 min sur CPU)…",
            `${srcCount} source(s)`,
          );
        } else if (ev.type === "summary_chunk") {
          summary += ev.text ?? "";
          update(summary, `${srcCount} source(s)`);
        } else if (ev.type === "error") {
          const msg = ev.message ?? "Erreur IA.";
          setError(msg);
          update(msg, "Erreur");
        } else if (ev.type === "done") {
          update(summary || "Aucune réponse générée.", `${srcCount} source(s)`);
        }
      };

      resetIdleAbort();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (value?.byteLength) resetIdleAbort();
        buf += decoder.decode(value, { stream: true });
        buf = parseNdjsonLines(buf, handleEvent);
      }
      buf = parseNdjsonLines(buf + "\n", handleEvent);
    } catch (err) {
      const message =
        err instanceof Error && err.name === "AbortError"
          ? `Aucune donnée reçue depuis ${Math.round(STREAM_IDLE_MS / 60_000)} min (flux interrompu ou bloqué). Vérifie Ollama (port 11434), FastAPI, et augmente NEXT_PUBLIC_RAG_STREAM_IDLE_MS si besoin.`
          : err instanceof Error
            ? err.message
            : "Impossible de joindre le service IA.";
      setError(message);
    } finally {
      if (idleAbortId !== undefined) window.clearTimeout(idleAbortId);
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-7xl flex-col gap-3 px-3 py-4 md:px-6">
      <header className="rdc-card flex items-center justify-between rounded-2xl px-4 py-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setSideOpen((v) => !v)}
            className="rounded-lg border border-slate-500/30 bg-slate-700/40 p-2 text-slate-200 md:hidden"
            aria-label="Afficher la sidebar"
          >
            <Menu size={15} />
          </button>
          <div className="rdc-icon-badge rounded-lg p-2">
            <Shield size={14} />
          </div>
          <span className="rdc-brand-text text-[11px] font-semibold uppercase tracking-[0.28em]">
            Espace client
          </span>
        </div>
        <Link
          href="/"
          className="rounded-xl border border-slate-500/30 px-3 py-1.5 text-xs text-slate-200"
        >
          Accueil
        </Link>
      </header>

      <div className="grid flex-1 gap-3 md:grid-cols-[240px_1fr]">
        {sideOpen && (
          <aside className="rdc-card flex flex-col gap-3 rounded-2xl p-4">
            {/* Actions principales */}
            <div className="space-y-2">
              <button
                type="button"
                onClick={startNewChat}
                className="flex w-full items-center gap-2 rounded-lg border border-slate-600/30 bg-slate-800/40 px-3 py-2 text-left text-sm text-slate-200 transition hover:border-slate-500/50 hover:bg-slate-700/50"
              >
                <MessageSquarePlus size={14} className="shrink-0 text-slate-400" />
                Nouveau chat
              </button>
              <button
                type="button"
                onClick={restoreSession}
                disabled={!hasSavedSession}
                className="flex w-full items-center gap-2 rounded-lg border border-slate-600/30 bg-slate-800/40 px-3 py-2 text-left text-sm text-slate-200 transition hover:border-slate-500/50 hover:bg-slate-700/50 disabled:cursor-not-allowed disabled:opacity-40"
              >
                <RotateCcw size={14} className="shrink-0 text-slate-400" />
                Reprendre conversation
              </button>
            </div>

            {/* Questions récentes */}
            <div className="border-t border-slate-700/40 pt-3">
              <button
                type="button"
                onClick={() => setRecentOpen((v) => !v)}
                className="mb-2 flex w-full items-center justify-between text-xs font-semibold uppercase tracking-wider text-slate-400"
              >
                <span className="flex items-center gap-1.5">
                  <Clock size={11} /> Récentes
                </span>
                {recentOpen ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              </button>
              {recentOpen && (
                <ul className="space-y-1">
                  {recentQueries.length === 0 ? (
                    <li className="text-xs text-slate-600">Aucune question encore.</li>
                  ) : (
                    recentQueries.map((q, i) => (
                      <li key={i}>
                        <button
                          type="button"
                          onClick={() => useRecentQuery(q)}
                          className="w-full truncate rounded-md px-2 py-1.5 text-left text-xs text-slate-400 transition hover:bg-slate-800/60 hover:text-slate-200"
                          title={q}
                        >
                          {q}
                        </button>
                      </li>
                    ))
                  )}
                </ul>
              )}
            </div>

            {/* Paramètres */}
            <div className="mt-auto border-t border-slate-700/40 pt-3">
              <button
                type="button"
                onClick={() => setSettingsOpen((v) => !v)}
                className="flex w-full items-center gap-2 text-xs text-slate-500 transition hover:text-slate-300"
              >
                <Settings size={12} />
                Paramètres
                {settingsOpen ? (
                  <ChevronUp size={11} className="ml-auto" />
                ) : (
                  <ChevronDown size={11} className="ml-auto" />
                )}
              </button>
              {settingsOpen && (
                <div className="mt-2 rounded-lg border border-slate-700/40 bg-slate-900/50 p-3 text-[11px] text-slate-500">
                  <p className="mb-1 font-medium text-slate-400">Stream idle timeout</p>
                  <p className="font-mono text-slate-300">
                    {Math.round(STREAM_IDLE_MS / 60_000)} min
                  </p>
                  <p className="mt-2 leading-4">
                    Configurable via{" "}
                    <span className="font-mono text-slate-400">
                      NEXT_PUBLIC_RAG_STREAM_IDLE_MS
                    </span>
                  </p>
                </div>
              )}
            </div>
          </aside>
        )}

        <section className="rdc-card flex min-h-[75vh] flex-col rounded-2xl">
          <div className="border-b border-slate-600/30 px-4 py-3">
            <p className="text-xs uppercase tracking-wider text-slate-400">Conversation RAG</p>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={msg.role === "user" ? "flex justify-end" : "flex"}
              >
                {msg.role === "assistant" && (
                  <div className="rdc-icon-badge mr-2 mt-1 rounded-full p-2">
                    <Bot size={13} />
                  </div>
                )}
                <div
                  className={
                    msg.role === "user"
                      ? "rdc-user-bubble max-w-[82%] rounded-2xl rounded-br-md px-4 py-3 text-sm"
                      : "max-w-[82%] rounded-2xl rounded-bl-md border border-slate-600/40 bg-slate-800/60 px-4 py-3 text-sm text-slate-200"
                  }
                >
                  <p className="whitespace-pre-wrap leading-6">{msg.content}</p>
                  {msg.meta && (
                    <p className="mt-2 text-xs text-slate-400">{msg.meta}</p>
                  )}
                </div>
                {msg.role === "user" && (
                  <div className="ml-2 mt-1 rounded-full border border-slate-500/40 bg-slate-700/40 p-2 text-slate-300">
                    <User size={13} />
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-sm text-slate-400">
                <Loader2 size={14} className="animate-spin" /> Génération de la
                réponse...
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {error && (
            <div className="mx-4 mb-2 flex items-center gap-2 rounded-xl border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              <AlertCircle size={14} /> {error}
            </div>
          )}

          <div className="border-t border-slate-600/30 p-4">
            <div className="flex items-end gap-2 rounded-xl border border-slate-500/30 bg-slate-800/50 p-2">
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKey}
                rows={1}
                placeholder="Pose ta question (Entrée pour envoyer)"
                className="max-h-32 flex-1 resize-none bg-transparent px-2 py-1 text-sm text-slate-100 outline-none placeholder:text-slate-500"
              />
              <button
                onClick={() => void handleSubmit()}
                disabled={!query.trim() || loading}
                className="rdc-btn-primary rounded-lg p-2 disabled:cursor-not-allowed"
                aria-label="Envoyer"
              >
                <Send size={14} />
              </button>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
