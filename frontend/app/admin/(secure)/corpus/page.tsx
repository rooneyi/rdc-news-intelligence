"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import {
  BookOpen,
  ExternalLink,
  Globe2,
  Layers,
  LogOut,
  RefreshCw,
  Shield,
  Tags,
} from "lucide-react";
import { useAdminBranding } from "@/app/admin/admin-branding-context";

type ArticleSample = {
  id: number;
  title: string;
  source: string;
  link: string;
  categories: string[];
};

type LangRow = {
  code: string;
  label: string;
  count: number;
  percent: number;
  sources: Array<{ source: string; count: number }>;
  samples?: ArticleSample[];
};

type CategoryRow = {
  name: string;
  count: number;
  percent: number;
  samples?: ArticleSample[];
};

type CorpusPayload = {
  status: string;
  stats: {
    total_articles: number;
    embedded_articles: number;
    embedding_coverage: number;
    distinct_categories: number;
    catalog_sources: number;
    missing_source_articles: number;
    missing_link_articles: number;
  };
  languages: LangRow[];
  categories: CategoryRow[];
  sources_breakdown: Array<{ source: string; count: number; in_catalog?: boolean }>;
};

const LANG_FLAG: Record<string, string> = {
  fr: "FR",
  en: "EN",
  sw: "SW",
  unknown: "?",
};

export default function AdminCorpusPage() {
  const { appName, adminEmail } = useAdminBranding();
  const router = useRouter();
  const [data, setData] = useState<CorpusPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openLang, setOpenLang] = useState<string | null>("fr");
  const [openCat, setOpenCat] = useState<string | null>(null);

  const logout = useCallback(async () => {
    await fetch("/api/admin/logout", { method: "POST" });
    router.push("/admin/login");
    router.refresh();
  }, [router]);

  const load = useCallback(
    async (isRefresh = false) => {
      if (isRefresh) setRefreshing(true);
      else setLoading(true);
      setError(null);
      try {
        const res = await fetch("/api/fastapi/admin/corpus", { cache: "no-store" });
        const payload = await res.json();
        if (res.status === 401) {
          router.push("/admin/login");
          return;
        }
        if (!res.ok) throw new Error(payload?.error ?? "Chargement impossible.");
        setData(payload as CorpusPayload);
        if (!openCat && payload.categories?.[0]) {
          setOpenCat(payload.categories[0].name);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Erreur inconnue.");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [router],
  );

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (data?.categories?.[0] && openCat === null) {
      setOpenCat(data.categories[0].name);
    }
  }, [data, openCat]);

  const total = data?.stats.total_articles ?? 0;

  return (
    <main className="mx-auto min-h-screen w-full max-w-6xl px-5 py-5 md:px-8">
      <header className="rdc-card rdc-motion-in mb-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl px-5 py-3">
        <div className="flex items-center gap-3">
          <div className="rdc-icon-badge rounded-lg p-2">
            <BookOpen size={15} />
          </div>
          <div>
            <p className="rdc-brand-text text-[11px] font-semibold uppercase tracking-[0.28em]">
              {appName}
            </p>
            <p className="text-[10px] text-slate-500">Corpus · {adminEmail}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void load(true)}
            disabled={refreshing}
            className="rdc-btn-primary inline-flex items-center gap-1.5 rounded-xl px-3 py-1.5 text-xs font-semibold disabled:opacity-60"
          >
            <RefreshCw size={13} className={refreshing ? "animate-spin" : ""} />
            Actualiser
          </button>
          <Link href="/admin" className="rdc-btn-ghost rounded-xl px-3 py-1.5 text-xs">
            Tableau de bord
          </Link>
          <button
            type="button"
            onClick={() => void logout()}
            className="rdc-btn-ghost inline-flex items-center gap-1 rounded-xl px-3 py-1.5 text-xs"
          >
            <LogOut size={13} /> Sortir
          </button>
        </div>
      </header>

      {error && (
        <div className="mb-4 rounded-xl border border-red-400/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <section className="mb-5 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {[
          { icon: <Layers size={14} />, label: "Articles totaux", value: total },
          {
            icon: <Globe2 size={14} />,
            label: "Couverture Chroma",
            value: `${data?.stats.embedding_coverage ?? 0}%`,
          },
          {
            icon: <Tags size={14} />,
            label: "Catégories distinctes",
            value: data?.stats.distinct_categories ?? "—",
          },
          {
            icon: <Shield size={14} />,
            label: "Sources catalogue",
            value: data?.stats.catalog_sources ?? "—",
          },
        ].map((c) => (
          <article key={c.label} className="rdc-card rounded-2xl p-4">
            <div className="mb-2 flex items-center gap-2 text-slate-400">
              {c.icon}
              <p className="text-xs">{c.label}</p>
            </div>
            <p className="text-2xl font-semibold text-slate-100">
              {loading ? "…" : c.value}
            </p>
          </article>
        ))}
      </section>

      <div className="grid gap-5 lg:grid-cols-2">
        {/* Langues */}
        <section className="rdc-card rounded-2xl p-4">
          <h2 className="mb-1 flex items-center gap-2 text-sm font-semibold text-slate-100">
            <Globe2 size={16} className="text-blue-400" /> Par langue
          </h2>
          <p className="rdc-muted mb-4 text-xs">
            Déduit de <span className="font-mono text-slate-400">sourceLang</span> dans{" "}
            <span className="font-mono text-slate-400">sources.json</span> (défaut français).
          </p>
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((n) => (
                <div key={n} className="h-12 animate-pulse rounded-xl bg-slate-800/50" />
              ))}
            </div>
          ) : (
            <ul className="space-y-2">
              {(data?.languages ?? []).map((lang) => (
                <li key={lang.code} className="rounded-xl border border-slate-600/30 bg-slate-900/35">
                  <button
                    type="button"
                    onClick={() => setOpenLang(openLang === lang.code ? null : lang.code)}
                    className="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left"
                  >
                    <span className="flex items-center gap-2 text-sm text-slate-200">
                      <span className="rdc-pill rounded px-2 py-0.5 text-[10px] font-bold">
                        {LANG_FLAG[lang.code] ?? lang.code}
                      </span>
                      {lang.label}
                    </span>
                    <span className="tabular-nums text-sm rdc-brand-text">
                      {lang.count}{" "}
                      <span className="text-slate-500">({lang.percent}%)</span>
                    </span>
                  </button>
                  <div className="mx-3 mb-2 h-1.5 overflow-hidden rounded-full bg-slate-800">
                    <div
                      className="rdc-accent-bar h-full rounded-full transition-all duration-700"
                      style={{ width: `${Math.min(100, lang.percent)}%` }}
                    />
                  </div>
                  {openLang === lang.code && lang.count > 0 && (
                    <div className="border-t border-slate-700/40 px-3 py-3">
                      {lang.sources.length > 0 && (
                        <p className="mb-2 text-[10px] uppercase tracking-wide text-slate-500">
                          Principales sources
                        </p>
                      )}
                      <ul className="mb-3 space-y-1 text-xs text-slate-400">
                        {lang.sources.slice(0, 6).map((s) => (
                          <li key={s.source} className="flex justify-between">
                            <span className="truncate">{s.source}</span>
                            <span>{s.count}</span>
                          </li>
                        ))}
                      </ul>
                      {(lang.samples ?? []).length > 0 && (
                        <>
                          <p className="mb-2 text-[10px] uppercase tracking-wide text-slate-500">
                            Exemples récents
                          </p>
                          <ArticleList items={lang.samples ?? []} />
                        </>
                      )}
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Catégories */}
        <section className="rdc-card rounded-2xl p-4">
          <h2 className="mb-1 flex items-center gap-2 text-sm font-semibold text-slate-100">
            <Tags size={16} className="text-blue-400" /> Par catégorie
          </h2>
          <p className="rdc-muted mb-4 text-xs">
            Champ PostgreSQL <span className="font-mono text-slate-400">categories[]</span> (URL /
            métadonnées crawler).
          </p>
          {loading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((n) => (
                <div key={n} className="h-12 animate-pulse rounded-xl bg-slate-800/50" />
              ))}
            </div>
          ) : (
            <ul className="max-h-[32rem] space-y-2 overflow-y-auto pr-1">
              {(data?.categories ?? []).map((cat) => (
                <li key={cat.name} className="rounded-xl border border-slate-600/30 bg-slate-900/35">
                  <button
                    type="button"
                    onClick={() => setOpenCat(openCat === cat.name ? null : cat.name)}
                    className="flex w-full items-center justify-between gap-2 px-3 py-2.5 text-left"
                  >
                    <span className="truncate text-sm capitalize text-slate-200">{cat.name}</span>
                    <span className="shrink-0 tabular-nums text-sm rdc-brand-text">
                      {cat.count} ({cat.percent}%)
                    </span>
                  </button>
                  {openCat === cat.name && (cat.samples ?? []).length > 0 && (
                    <div className="border-t border-slate-700/40 px-3 py-3">
                      <ArticleList items={cat.samples ?? []} />
                    </div>
                  )}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      {/* Qualité + sources restantes */}
      <section className="rdc-card mt-5 rounded-2xl p-4">
        <h2 className="mb-4 text-sm font-semibold text-slate-100">Qualité & sources</h2>
        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-xl border border-slate-600/30 bg-slate-800/40 p-4 text-sm">
            <p className="mb-2 font-medium text-slate-200">Intégrité</p>
            <ul className="space-y-1 text-slate-400">
              <li className="flex justify-between">
                <span>Sans source_id</span>
                <span className="text-red-300">{data?.stats.missing_source_articles ?? 0}</span>
              </li>
              <li className="flex justify-between">
                <span>Sans lien</span>
                <span className="text-red-300">{data?.stats.missing_link_articles ?? 0}</span>
              </li>
              <li className="flex justify-between">
                <span>Vectorisés</span>
                <span className="text-emerald-300">{data?.stats.embedded_articles ?? 0}</span>
              </li>
            </ul>
          </div>
          <div className="md:col-span-2 rounded-xl border border-slate-600/30 bg-slate-800/40 p-4">
            <p className="mb-2 text-sm font-medium text-slate-200">
              Toutes les sources (volume décroissant)
            </p>
            {loading ? (
              <div className="h-24 animate-pulse rounded bg-slate-700/40" />
            ) : (
              <div className="max-h-48 space-y-1 overflow-y-auto text-xs text-slate-300">
                {(data?.sources_breakdown ?? []).map((row) => (
                  <div key={row.source} className="flex justify-between gap-2">
                    <span className={row.in_catalog === false ? "text-slate-500" : ""}>
                      {row.source}
                      {row.in_catalog === false ? " (hors catalogue)" : ""}
                    </span>
                    <span className="tabular-nums rdc-brand-text">{row.count}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </section>
    </main>
  );
}

function ArticleList({ items }: { items: ArticleSample[] }) {
  return (
    <ul className="space-y-2">
      {items.map((a) => (
        <li
          key={a.id}
          className="rounded-lg border border-slate-600/25 bg-slate-950/50 px-2.5 py-2 text-xs"
        >
          <p className="line-clamp-2 text-slate-200">{a.title}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-[10px] text-slate-500">
            <span>{a.source}</span>
            <span>#{a.id}</span>
            {a.categories.length > 0 && (
              <span className="text-blue-300/80">{a.categories.join(", ")}</span>
            )}
            {a.link ? (
              <a
                href={a.link}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-0.5 text-blue-400 hover:underline"
              >
                Lien <ExternalLink size={10} />
              </a>
            ) : null}
          </div>
        </li>
      ))}
    </ul>
  );
}
