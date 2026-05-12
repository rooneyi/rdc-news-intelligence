"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { AlertCircle, Bot, Loader2, Menu, Send, Shield, User } from "lucide-react";

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

/** Délai max avant abandon (génération locale Ollama souvent > 1 min sur CPU). */
const STREAM_TIMEOUT_MS = 300_000;

function parseNdjsonLines(buf: string, onEvent: (ev: { type: string; sources?: unknown[]; text?: string; message?: string }) => void) {
  const lines = buf.split("\n");
  const rest = lines.pop() ?? "";
  for (const line of lines) {
    if (!line.trim()) continue;
    try {
      onEvent(JSON.parse(line) as { type: string; sources?: unknown[]; text?: string; message?: string });
    } catch {
      /* ligne partielle ou bruit */
    }
  }
  return rest;
}

export default function ClientPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([WELCOME]);
  const [sideOpen, setSideOpen] = useState(true);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  const handleKey = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void handleSubmit();
    }
  };

  const handleSubmit = async () => {
    const trimmed = query.trim();
    if (!trimmed || loading) return;
    setError(null);
    setLoading(true);

    const userMsg: ChatMessage = { id: Date.now(), role: "user", content: trimmed, meta: "Toi" };
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
    const timeoutId = window.setTimeout(() => controller.abort(), STREAM_TIMEOUT_MS);

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
      let buf = "", summary = "", srcCount = 0;

      const update = (content: string, meta: string) =>
        setMessages(prev => prev.map(m => m.id === asstId ? { ...m, content, meta } : m));

      const handleEvent = (ev: { type: string; sources?: unknown[]; text?: string; message?: string }) => {
        if (ev.type === "sources") {
          srcCount = Array.isArray(ev.sources) ? ev.sources.length : 0;
          update(
            summary || "Sources trouvées. Génération de la réponse (Ollama peut prendre 1–3 min sur CPU)…",
            `${srcCount} source(s)`,
          );
        } else if (ev.type === "summary_chunk") {
          summary += ev.text ?? "";
          update(summary, `${srcCount} source(s)`);
        } else if (ev.type === "error") {
          setError(ev.message ?? "Erreur IA.");
          update(summary || "Erreur.", "Erreur");
        } else if (ev.type === "done") {
          update(summary || "Aucune réponse générée.", `${srcCount} source(s)`);
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        buf = parseNdjsonLines(buf, handleEvent);
      }
      buf = parseNdjsonLines(buf + "\n", handleEvent);
    } catch (err) {
      const message =
        err instanceof Error && err.name === "AbortError"
          ? `Délai dépassé (${Math.round(STREAM_TIMEOUT_MS / 60_000)} min). Vérifie qu'Ollama tourne (port 11434) ou réessaie avec une question plus courte.`
          : err instanceof Error
            ? err.message
            : "Impossible de joindre le service IA.";
      setError(message);
    } finally {
      window.clearTimeout(timeoutId);
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
          <div className="rounded-lg border border-blue-300/30 bg-blue-500/15 p-2 text-blue-300">
            <Shield size={14} />
          </div>
          <span className="text-[11px] font-semibold uppercase tracking-[0.28em] text-blue-300">
            Espace client
          </span>
        </div>
        <Link href="/" className="rounded-xl border border-slate-500/30 px-3 py-1.5 text-xs text-slate-200">
          Accueil
        </Link>
      </header>

      <div className="grid flex-1 gap-3 md:grid-cols-[240px_1fr]">
        {sideOpen && (
          <aside className="rdc-card rounded-2xl p-4">
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-slate-400">Raccourcis</p>
            <ul className="space-y-2 text-sm text-slate-300">
              {[
                "Nouveau chat",
                "Reprendre conversation",
                "Questions favorites",
                "Paramètres",
              ].map((item) => (
                <li key={item} className="rounded-lg border border-slate-600/30 bg-slate-800/40 px-3 py-2">
                  {item}
                </li>
              ))}
            </ul>
          </aside>
        )}

        <section className="rdc-card flex min-h-[75vh] flex-col rounded-2xl">
          <div className="border-b border-slate-600/30 px-4 py-3">
            <p className="text-xs uppercase tracking-wider text-slate-400">Conversation RAG</p>
          </div>

          <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
            {messages.map((msg) => (
              <div key={msg.id} className={msg.role === "user" ? "flex justify-end" : "flex"}>
                {msg.role === "assistant" && (
                  <div className="mr-2 mt-1 rounded-full border border-blue-300/30 bg-blue-500/15 p-2 text-blue-300">
                    <Bot size={13} />
                  </div>
                )}
                <div
                  className={
                    msg.role === "user"
                      ? "max-w-[82%] rounded-2xl rounded-br-md bg-blue-600 px-4 py-3 text-sm text-white"
                      : "max-w-[82%] rounded-2xl rounded-bl-md border border-slate-600/40 bg-slate-800/60 px-4 py-3 text-sm text-slate-200"
                  }
                >
                  <p className="whitespace-pre-wrap leading-6">{msg.content}</p>
                  {msg.meta && <p className="mt-2 text-xs text-slate-400">{msg.meta}</p>}
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
                <Loader2 size={14} className="animate-spin" /> Génération de la réponse...
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
                className="rounded-lg bg-blue-600 p-2 text-white transition disabled:cursor-not-allowed disabled:bg-slate-700"
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