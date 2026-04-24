"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

type ChatMessage = {
  id: number;
  role: "user" | "assistant";
  content: string;
  meta?: string;
};

const historyItems = [
  "Constant Mutamba est mort ?",
  "Actualites sante RDC aujourd'hui",
  "Resume guerre a l'Est",
  "Points sport de la semaine",
  "Verifier une image recue",
];

const shortcuts = ["Nouveau chat", "Rechercher", "Bibliotheque", "Favoris", "Parametres"];

export default function ClientPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 1,
      role: "assistant",
      content:
        "Bienvenue sur ton espace client. Pose une question sur la politique, le sport, la sante ou la guerre en RDC, je reponds avec des sources.",
      meta: "Canal web",
    },
  ]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmed = query.trim();
    if (!trimmed) {
      setError("Saisis une question avant d'envoyer.");
      return;
    }

    setLoading(true);
    setError(null);
    const userMessage: ChatMessage = {
      id: Date.now(),
      role: "user",
      content: trimmed,
      meta: "Toi",
    };
    const assistantId = Date.now() + 1;
    setMessages((prev) => [...prev, userMessage]);
    setMessages((prev) => [
      ...prev,
      {
        id: assistantId,
        role: "assistant",
        content: "",
        meta: "Generation...",
      },
    ]);
    setQuery("");

    try {
      const response = await fetch("/api/fastapi/rag/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed }),
      });

      if (!response.ok) {
        const payload = await response.json().catch(() => ({}));
        setError(payload?.error ?? "Erreur pendant la requête.");
        return;
      }

      if (!response.body) {
        setError("Flux de reponse indisponible.");
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let summary = "";
      let sourceCount = 0;

      const updateAssistant = (content: string, meta: string) => {
        setMessages((prev) =>
          prev.map((message) =>
            message.id === assistantId
              ? {
                  ...message,
                  content,
                  meta,
                }
              : message
          )
        );
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";

        for (const line of lines) {
          if (!line.trim()) {
            continue;
          }

          let event: { type?: string; text?: string; sources?: unknown[]; message?: string };
          try {
            event = JSON.parse(line);
          } catch {
            continue;
          }

          if (event.type === "sources") {
            sourceCount = Array.isArray(event.sources) ? event.sources.length : 0;
            updateAssistant(summary || "Analyse des sources...", `${sourceCount} source(s)`);
            continue;
          }

          if (event.type === "summary_chunk") {
            summary += event.text ?? "";
            updateAssistant(summary, `${sourceCount} source(s)`);
            continue;
          }

          if (event.type === "error") {
            setError(event.message ?? "Erreur de generation IA.");
            updateAssistant(summary || "Erreur IA.", "Erreur");
            break;
          }

          if (event.type === "done") {
            updateAssistant(summary || "Aucune reponse generee.", `${sourceCount} source(s)`);
          }
        }
      }
    } catch {
      setError("Impossible de joindre le service IA.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(29,78,216,0.16),_transparent_30%),linear-gradient(180deg,_#f4f8ff_0%,_#ffffff_100%)] text-slate-950">
      <div className="mx-auto grid min-h-screen max-w-[1400px] grid-cols-1 gap-4 p-4 md:grid-cols-[270px_1fr]">
        <aside className="rounded-[28px] border border-white/80 bg-[#f3f7ff] p-4 shadow-[0_20px_55px_rgba(15,23,42,0.08)]">
          <div className="mb-4 flex items-center justify-between rounded-2xl bg-white px-3 py-2 ring-1 ring-blue-100">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.25em] text-blue-700">Client</p>
              <p className="text-sm font-semibold">RDC Assistant</p>
            </div>
            <Link href="/" className="text-xs font-medium text-blue-700 hover:text-blue-900">
              Accueil
            </Link>
          </div>

          <div className="space-y-2">
            {shortcuts.map((item) => (
              <button
                key={item}
                className="w-full rounded-xl bg-white px-3 py-2 text-left text-sm font-medium text-slate-700 ring-1 ring-blue-100 transition hover:bg-blue-50"
                type="button"
              >
                {item}
              </button>
            ))}
          </div>

          <div className="mt-6">
            <p className="mb-2 text-xs font-semibold uppercase tracking-[0.22em] text-blue-700">Recents</p>
            <div className="space-y-2">
              {historyItems.map((item) => (
                <button
                  key={item}
                  className="w-full rounded-xl border border-blue-100 bg-white px-3 py-2 text-left text-xs text-slate-600 transition hover:border-blue-200 hover:bg-blue-50"
                  type="button"
                >
                  {item}
                </button>
              ))}
            </div>
          </div>
        </aside>

        <section className="flex min-h-[85vh] flex-col rounded-[28px] border border-white/80 bg-white/90 shadow-[0_24px_70px_rgba(15,23,42,0.09)]">
          <header className="flex items-center justify-between border-b border-slate-100 px-5 py-4">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.25em] text-blue-700">Assistant Client</p>
              <h1 className="text-lg font-semibold">Conversation Web</h1>
            </div>
            <div className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700 ring-1 ring-blue-100">
              Canal: web
            </div>
          </header>

          <div className="flex-1 space-y-4 overflow-y-auto px-5 py-5">
            {messages.map((message) => (
              <div key={message.id} className={message.role === "user" ? "flex justify-end" : "flex justify-start"}>
                <article
                  className={
                    message.role === "user"
                      ? "max-w-[85%] rounded-2xl rounded-br-md bg-blue-900 px-4 py-3 text-sm text-white shadow-lg shadow-blue-900/15"
                      : "max-w-[85%] rounded-2xl rounded-bl-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-800"
                  }
                >
                  <p className="whitespace-pre-wrap leading-6">{message.content}</p>
                  {message.meta ? (
                    <p className={message.role === "user" ? "mt-2 text-[11px] text-blue-100" : "mt-2 text-[11px] text-slate-500"}>
                      {message.meta}
                    </p>
                  ) : null}
                </article>
              </div>
            ))}

            {loading ? (
              <div className="flex justify-start">
                <div className="rounded-2xl rounded-bl-md border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-600">
                  Generation en cours...
                </div>
              </div>
            ) : null}
          </div>

          <form className="border-t border-slate-100 p-4" onSubmit={onSubmit}>
            <div className="flex items-end gap-3 rounded-2xl border border-slate-200 bg-slate-50 px-3 py-3 focus-within:border-blue-300">
              <textarea
                id="client-query"
                className="max-h-40 min-h-[46px] flex-1 resize-y bg-transparent text-sm text-slate-800 outline-none"
                placeholder="Pose ta question ici..."
                value={query}
                onChange={(event) => setQuery(event.target.value)}
              />
              <button
                className="rounded-xl bg-blue-900 px-4 py-2 text-sm font-semibold text-white shadow-[0_14px_34px_rgba(30,64,175,0.25)] disabled:cursor-not-allowed disabled:opacity-70"
                type="submit"
                disabled={loading}
              >
                {loading ? "..." : "Envoyer"}
              </button>
            </div>
            {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}
          </form>
        </section>
      </div>
    </main>
  );
}