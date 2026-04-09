"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";

const historyItems = [
  {
    title: "Qui est en avance dans le programme de vaccination ?",
    status: "Répondu il y a 3 min",
  },
  {
    title: "Vérifier l'image partagée dans le groupe",
    status: "Analyse OCR + sources",
  },
  {
    title: "Dernières questions suivies",
    status: "Historique synchronisé",
  },
];

export default function ClientPage() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [answer, setAnswer] = useState<string | null>(null);
  const [sourceCount, setSourceCount] = useState<number>(0);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    const trimmed = query.trim();
    if (!trimmed) {
      setError("Saisis une question avant d'envoyer.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch("/api/fastapi/rag", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed }),
      });

      const payload = await response.json();

      if (!response.ok) {
        setAnswer(null);
        setSourceCount(0);
        setError(payload?.error ?? "Erreur pendant la requête.");
        return;
      }

      setAnswer(payload?.summary ?? "Aucune réponse générée.");
      setSourceCount(Array.isArray(payload?.sources) ? payload.sources.length : 0);
    } catch {
      setAnswer(null);
      setSourceCount(0);
      setError("Impossible de joindre le service IA.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,_rgba(29,78,216,0.18),_transparent_28%),linear-gradient(180deg,_#f8fbff_0%,_#ffffff_100%)] text-slate-950">
      <div className="mx-auto max-w-6xl px-6 py-6 md:px-10 lg:px-12 lg:py-10">
        <header className="flex items-center justify-between rounded-[28px] border border-white/80 bg-white/80 px-5 py-4 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur-xl">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-blue-700">Espace client</p>
            <h1 className="mt-1 text-lg font-semibold">Authentification, questions et historique</h1>
          </div>
          <Link href="/" className="rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-900">
            Retour accueil
          </Link>
        </header>

        <section className="mt-8 grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <article className="rounded-[30px] border border-white/80 bg-white/90 p-7 shadow-[0_22px_60px_rgba(15,23,42,0.08)] backdrop-blur">
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-blue-800">Question rapide</p>
            <h2 className="mt-3 text-3xl font-semibold">Poser une question au moteur RAG</h2>
            <p className="mt-4 max-w-2xl text-slate-600 leading-7">
              Un espace sobre et rapide pour interroger le système, recevoir une réponse sourcée et retrouver chaque échange dans l&apos;historique de compte.
            </p>

            <form className="mt-6 rounded-[24px] border border-slate-200 bg-slate-50 p-4" onSubmit={onSubmit}>
              <label className="text-sm font-medium text-slate-700" htmlFor="client-query">
                Votre question
              </label>
              <div className="mt-3 flex flex-col gap-3 md:flex-row">
                <input
                  id="client-query"
                  className="min-h-12 flex-1 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none ring-0 transition focus:border-blue-300 focus:shadow-[0_0_0_4px_rgba(59,130,246,0.10)]"
                  placeholder="Ex: Quelles sont les dernières informations sur la santé publique ?"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />
                <button
                  className="rounded-2xl bg-blue-900 px-5 py-3 text-sm font-semibold text-white shadow-[0_18px_40px_rgba(30,64,175,0.22)] disabled:cursor-not-allowed disabled:opacity-70"
                  type="submit"
                  disabled={loading}
                >
                  {loading ? "Envoi..." : "Envoyer"}
                </button>
              </div>
              {error ? <p className="mt-3 text-sm text-red-600">{error}</p> : null}
              {answer ? (
                <div className="mt-4 rounded-2xl border border-blue-100 bg-white p-4 text-sm text-slate-700">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-700">Reponse IA</p>
                  <p className="mt-2 whitespace-pre-wrap leading-7">{answer}</p>
                  <p className="mt-3 text-xs text-slate-500">Sources detectees: {sourceCount}</p>
                </div>
              ) : null}
            </form>

            <div className="mt-6 grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-blue-50 px-4 py-4 ring-1 ring-blue-100">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-700">Connexion</p>
                <p className="mt-2 text-sm text-slate-700">Authentification sécurisée par utilisateur.</p>
              </div>
              <div className="rounded-2xl bg-blue-50 px-4 py-4 ring-1 ring-blue-100">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-700">Historique</p>
                <p className="mt-2 text-sm text-slate-700">Conservation des requêtes et réponses.</p>
              </div>
              <div className="rounded-2xl bg-blue-50 px-4 py-4 ring-1 ring-blue-100">
                <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-700">Sources</p>
                <p className="mt-2 text-sm text-slate-700">Réponses traçables et vérifiables.</p>
              </div>
            </div>
          </article>

          <aside className="rounded-[30px] border border-white/80 bg-white/90 p-7 shadow-[0_22px_60px_rgba(15,23,42,0.08)] backdrop-blur">
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-blue-800">Historique</p>
            <h2 className="mt-3 text-2xl font-semibold">Dernières requêtes enregistrées</h2>
            <div className="mt-6 space-y-3">
              {historyItems.map((item) => (
                <article key={item.title} className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm font-medium text-slate-900">{item.title}</p>
                  <p className="mt-1 text-sm text-slate-500">{item.status}</p>
                </article>
              ))}
            </div>
          </aside>
        </section>
      </div>
    </main>
  );
}