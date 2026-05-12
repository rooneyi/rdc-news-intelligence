"use client";

import Link from "next/link";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Activity, Database, Globe, RefreshCw, Server, Shield, Zap } from "lucide-react";
import { SourcesPieChart } from "./SourcesPieChart";

type AdminOverview = {
  status: string;
  stats: {
    total_articles: number;
    embedded_articles: number;
    total_sources: number;
    catalog_sources_configured?: number;
    embedding_coverage: number;
    missing_source_articles: number;
    missing_link_articles: number;
  };
  top_sources: Array<{ source: string; count: number }>;
  sources_breakdown: Array<{ source: string; count: number; in_catalog?: boolean }>;
  latest_articles: Array<{ id: number; title: string; source: string; link: string }>;
};

export default function AdminPage() {
  const [data, setData] = useState<AdminOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadOverview = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/fastapi/admin/overview", { cache: "no-store" });
      const payload = await res.json();
      if (!res.ok) {
        throw new Error(payload?.error ?? "Impossible de charger les stats admin.");
      }
      setData(payload as AdminOverview);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur inconnue.";
      setError(message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  const cards = useMemo(
    () => [
      {
        icon: <Database size={15} />,
        label: "Articles indexés",
        value: data?.stats.total_articles ?? 0,
      },
      {
        icon: <Zap size={15} />,
        label: "Articles vectorisés",
        value: data?.stats.embedded_articles ?? 0,
      },
      {
        icon: <Activity size={15} />,
        label: "Couverture embeddings",
        value: `${data?.stats.embedding_coverage ?? 0}%`,
      },
      {
        icon: <Globe size={15} />,
        label: "Sources distinctes (base)",
        value: data?.stats.total_sources ?? 0,
      },
      {
        icon: <Globe size={15} />,
        label: "Sources dans sources.json",
        value: data?.stats.catalog_sources_configured ?? "—",
      },
    ],
    [data],
  );

  const skeletonCard = (
    <article className="rdc-card animate-pulse rounded-2xl p-4">
      <div className="mb-2 h-4 w-32 rounded bg-slate-700/60" />
      <div className="h-8 w-20 rounded bg-slate-700/60" />
    </article>
  );

  const totalArticles = data?.stats.total_articles ?? 0;

  return (
    <main className="mx-auto min-h-screen w-full max-w-6xl px-5 py-5 md:px-8">
      <header className="rdc-card mb-5 flex items-center justify-between rounded-2xl px-5 py-3">
        <div className="flex items-center gap-3">
          <div className="rounded-lg border border-blue-300/30 bg-blue-500/15 p-2 text-blue-300">
            <Shield size={15} />
          </div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-blue-300">
            Console admin
          </p>
        </div>
        <Link href="/" className="rounded-xl border border-slate-500/30 px-3 py-1.5 text-xs text-slate-200">
          Retour accueil
        </Link>
      </header>

      <section className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {loading
          ? [1, 2, 3, 4, 5].map((n) => <div key={n}>{skeletonCard}</div>)
          : cards.map((s) => (
          <article key={s.label} className="rdc-card rounded-2xl p-4 transition hover:-translate-y-0.5 hover:border-slate-400/40">
            <div className="mb-2 flex items-center gap-2 text-slate-400">
              {s.icon}
              <p className="text-xs">{s.label}</p>
            </div>
            <p className="text-2xl font-semibold text-slate-100">{s.value}</p>
          </article>
        ))}
      </section>

      <section className="rdc-card rounded-2xl p-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm font-semibold text-slate-200">Vue système réelle (backend)</p>
          <button
            onClick={() => void loadOverview(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-700"
          >
            <RefreshCw size={14} className={refreshing ? "animate-spin" : ""} />{" "}
            {refreshing ? "Actualisation..." : "Rafraîchir"}
          </button>
        </div>
        {error && (
          <div className="mb-3 rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </div>
        )}
        <div className="grid gap-3 md:grid-cols-2">
          <div className="rounded-xl border border-slate-600/30 bg-slate-800/40 p-4">
            <p className="mb-2 text-sm font-semibold text-slate-100">Top sources en base</p>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((n) => (
                  <div key={n} className="h-5 w-full animate-pulse rounded bg-slate-700/60" />
                ))}
              </div>
            ) : (
              <ul className="space-y-1 text-sm text-slate-300">
                {(data?.top_sources ?? []).map((row) => (
                  <li key={row.source} className="flex items-center justify-between">
                    <span className="truncate">{row.source}</span>
                    <span className="text-blue-300">{row.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="rounded-xl border border-slate-600/30 bg-slate-800/40 p-4">
            <p className="mb-2 text-sm font-semibold text-slate-100">Qualité des données</p>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((n) => (
                  <div key={n} className="h-5 w-full animate-pulse rounded bg-slate-700/60" />
                ))}
              </div>
            ) : (
              <ul className="space-y-1 text-sm text-slate-300">
                <li className="flex items-center justify-between">
                  <span>Articles sans source</span>
                  <span className="text-amber-300">{data?.stats.missing_source_articles ?? 0}</span>
                </li>
                <li className="flex items-center justify-between">
                  <span>Articles sans lien</span>
                  <span className="text-amber-300">{data?.stats.missing_link_articles ?? 0}</span>
                </li>
                <li className="flex items-center justify-between">
                  <span>Backend IA</span>
                  <span className="inline-flex items-center gap-1 text-emerald-300">
                    <Server size={12} /> En ligne
                  </span>
                </li>
              </ul>
            )}
          </div>
        </div>

        <div className="mt-3 grid gap-3 lg:grid-cols-2">
          <div className="rounded-xl border border-slate-600/30 bg-slate-800/40 p-4">
            <p className="mb-1 text-sm font-semibold text-slate-100">Répartition des sources</p>
            <p className="mb-3 text-[11px] leading-snug text-slate-500">
              Toutes les entrées de <span className="font-mono text-slate-400">sources.json</span> avec leur
              volume en base (0 si pas encore crawlé). Les sources présentes en base mais absentes du fichier
              sont marquées « hors catalogue ».
            </p>

            <div className="mb-5 rounded-xl border border-slate-600/20 bg-slate-900/35 p-4">
              <p className="mb-3 text-center text-[11px] font-medium uppercase tracking-wide text-slate-500">
                Vue circulaire (ordre antihoraire · animation dans ce sens)
              </p>
              <SourcesPieChart breakdown={data?.sources_breakdown ?? []} loading={loading} />
            </div>

            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4].map((n) => (
                  <div key={n} className="h-8 w-full animate-pulse rounded bg-slate-700/60" />
                ))}
              </div>
            ) : (
              <div className="max-h-[28rem] space-y-2 overflow-y-auto pr-1">
                {(data?.sources_breakdown ?? []).map((row) => {
                  const width = totalArticles ? Math.max(4, (row.count / totalArticles) * 100) : 0;
                  const orphan = row.in_catalog === false;
                  return (
                    <div key={row.source}>
                      <div className="mb-1 flex items-center justify-between gap-2 text-xs text-slate-300">
                        <span className={`min-w-0 truncate ${orphan ? "text-slate-500" : ""}`}>
                          {row.source}
                          {orphan ? (
                            <span className="ml-1 text-[10px] font-normal text-slate-500">(hors catalogue)</span>
                          ) : null}
                        </span>
                        <span className={orphan ? "text-slate-500" : ""}>{row.count}</span>
                      </div>
                      <div className="h-2 rounded bg-slate-700/60">
                        <div
                          className={`h-2 rounded transition-all ${orphan ? "bg-slate-500/50" : "bg-blue-500/80"}`}
                          style={{ width: `${width}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <div className="rounded-xl border border-slate-600/30 bg-slate-800/40 p-4">
            <p className="mb-3 text-sm font-semibold text-slate-100">Derniers articles ingérés</p>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4].map((n) => (
                  <div key={n} className="h-10 w-full animate-pulse rounded bg-slate-700/60" />
                ))}
              </div>
            ) : (
              <ul className="space-y-2">
                {(data?.latest_articles ?? []).map((article) => (
                  <li key={article.id} className="rounded-lg border border-slate-600/20 bg-slate-900/40 p-2">
                    <p className="line-clamp-2 text-sm text-slate-200">{article.title}</p>
                    <div className="mt-1 flex items-center justify-between text-xs text-slate-400">
                      <span>{article.source}</span>
                      <span>#{article.id}</span>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}