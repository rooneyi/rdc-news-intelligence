"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity,
  Database,
  Globe,
  Layers,
  LogOut,
  MessageSquare,
  Play,
  RefreshCw,
  Server,
  Shield,
  Tags,
  Zap,
} from "lucide-react";
import { useAdminBranding } from "@/app/admin/admin-branding-context";
import { SourcesPieChart } from "../SourcesPieChart";

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
    articles_without_category?: number;
  };
  top_sources: Array<{ source: string; count: number }>;
  sources_breakdown: Array<{ source: string; count: number; in_catalog?: boolean }>;
  latest_articles: Array<{ id: number; title: string; source: string; link: string }>;
};

type CrawlerJob = {
  running: boolean;
  status: string;
  started_at: string | null;
  finished_at: string | null;
  source_id: string;
  limit: number;
  run_reembedding: boolean;
  crawl_exit_code: number | null;
  message: string;
  error: string | null;
};

type MaintenanceJob = {
  running: boolean;
  status: string;
  job_type: string;
  force_all: boolean;
  only_without_category: boolean;
  backfill_categories_first: boolean;
  categories_result?: { scanned?: number; updated?: number; skipped?: number } | null;
  reembed_result?: { processed?: number; reembedded?: number } | null;
  message: string;
  error: string | null;
};

type MonitoringData = {
  circuit_breaker: {
    name: string;
    state: "CLOSED" | "HALF_OPEN" | "OPEN";
    failures: number;
    threshold: number;
  };
  messages: {
    total: number;
    by_channel: { telegram: number; whatsapp: number; whapi: number };
  };
  cache: {
    hits: number;
    misses: number;
    total: number;
    hit_rate_pct: number;
  };
};

export default function AdminPage() {
  const { appName, adminEmail } = useAdminBranding();
  const router = useRouter();
  const [data, setData] = useState<AdminOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [crawlerJob, setCrawlerJob] = useState<CrawlerJob | null>(null);
  const [crawlLimit, setCrawlLimit] = useState(30);
  const [crawlReembed, setCrawlReembed] = useState(true);
  const [crawlerStarting, setCrawlerStarting] = useState(false);
  const [crawlerError, setCrawlerError] = useState<string | null>(null);
  const [maintenanceJob, setMaintenanceJob] = useState<MaintenanceJob | null>(null);
  const [reembedForceAll, setReembedForceAll] = useState(false);
  const [reembedOnlyNoCategory, setReembedOnlyNoCategory] = useState(false);
  const [reembedBackfillCategories, setReembedBackfillCategories] = useState(true);
  const [reembedFetchHtml, setReembedFetchHtml] = useState(false);
  const [maintenanceStarting, setMaintenanceStarting] = useState(false);
  const [maintenanceError, setMaintenanceError] = useState<string | null>(null);
  const [monitoring, setMonitoring] = useState<MonitoringData | null>(null);
  const [monitoringLoading, setMonitoringLoading] = useState(true);
  const [monitoringRefreshing, setMonitoringRefreshing] = useState(false);

  const adminJobBusy = Boolean(crawlerJob?.running || maintenanceJob?.running);

  const logout = useCallback(async () => {
    await fetch("/api/admin/logout", { method: "POST" });
    router.push("/admin/login");
    router.refresh();
  }, [router]);

  const loadOverview = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setError(null);

    try {
      const res = await fetch("/api/fastapi/admin/overview", { cache: "no-store" });
      const payload = await res.json();
      if (res.status === 401) {
        router.push("/admin/login");
        return;
      }
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
  }, [router]);

  const loadCrawlerStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/fastapi/admin/crawler", { cache: "no-store" });
      const payload = await res.json();
      if (res.status === 401) {
        router.push("/admin/login");
        return;
      }
      if (!res.ok) return;
      const job = payload?.job as CrawlerJob | undefined;
      if (job) setCrawlerJob(job);
    } catch {
      /* ignore polling errors */
    }
  }, [router]);

  const startCrawler = useCallback(async () => {
    setCrawlerStarting(true);
    setCrawlerError(null);
    try {
      const res = await fetch("/api/fastapi/admin/crawler", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          source_id: "all",
          limit: crawlLimit,
          run_reembedding: crawlReembed,
        }),
      });
      const payload = await res.json();
      if (res.status === 401) {
        router.push("/admin/login");
        return;
      }
      if (!res.ok) {
        throw new Error(
          typeof payload?.error === "string"
            ? payload.error
            : "Impossible de démarrer le crawl.",
        );
      }
      const job = payload?.job as CrawlerJob | undefined;
      if (job) {
        setCrawlerJob({ ...job, running: true, status: "running", message: "Collecte en cours…" });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur inconnue.";
      setCrawlerError(message);
    } finally {
      setCrawlerStarting(false);
    }
  }, [router, crawlLimit, crawlReembed]);

  const loadMaintenanceStatus = useCallback(async () => {
    try {
      const res = await fetch("/api/fastapi/admin/reembed", { cache: "no-store" });
      const payload = await res.json();
      if (res.status === 401) {
        router.push("/admin/login");
        return;
      }
      if (!res.ok) return;
      const job = payload?.job as MaintenanceJob | undefined;
      if (job) setMaintenanceJob(job);
    } catch {
      /* ignore polling errors */
    }
  }, [router]);

  const startMaintenance = useCallback(async () => {
    setMaintenanceStarting(true);
    setMaintenanceError(null);
    try {
      const res = await fetch("/api/fastapi/admin/reembed", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          force_all: reembedForceAll,
          only_without_category: reembedOnlyNoCategory,
          backfill_categories_first: reembedBackfillCategories,
          fetch_html_for_categories: reembedFetchHtml,
          category_limit: 0,
        }),
      });
      const payload = await res.json();
      if (res.status === 401) {
        router.push("/admin/login");
        return;
      }
      if (!res.ok) {
        throw new Error(
          typeof payload?.error === "string"
            ? payload.error
            : "Impossible de démarrer la maintenance.",
        );
      }
      const job = payload?.job as MaintenanceJob | undefined;
      if (job) {
        setMaintenanceJob({ ...job, running: true, status: "running", message: "Maintenance en cours…" });
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : "Erreur inconnue.";
      setMaintenanceError(message);
    } finally {
      setMaintenanceStarting(false);
    }
  }, [
    router,
    reembedForceAll,
    reembedOnlyNoCategory,
    reembedBackfillCategories,
    reembedFetchHtml,
  ]);

  useEffect(() => {
    void loadOverview();
    void loadCrawlerStatus();
    void loadMaintenanceStatus();
  }, [loadOverview, loadCrawlerStatus, loadMaintenanceStatus]);

  useEffect(() => {
    if (!crawlerJob?.running) return;
    const id = window.setInterval(() => {
      void loadCrawlerStatus();
    }, 4000);
    return () => window.clearInterval(id);
  }, [crawlerJob?.running, loadCrawlerStatus]);

  useEffect(() => {
    if (!maintenanceJob?.running) return;
    const id = window.setInterval(() => {
      void loadMaintenanceStatus();
    }, 4000);
    return () => window.clearInterval(id);
  }, [maintenanceJob?.running, loadMaintenanceStatus]);

  useEffect(() => {
    if (crawlerJob?.running) return;
    if (crawlerJob?.status === "success") {
      void loadOverview(true);
    }
  }, [crawlerJob?.running, crawlerJob?.status, loadOverview]);

  useEffect(() => {
    if (maintenanceJob?.running) return;
    if (maintenanceJob?.status === "success") {
      void loadOverview(true);
    }
  }, [maintenanceJob?.running, maintenanceJob?.status, loadOverview]);

  const loadMonitoring = useCallback(async (isRefresh = false) => {
    if (isRefresh) setMonitoringRefreshing(true);
    else setMonitoringLoading(true);
    try {
      const res = await fetch("/api/fastapi/admin/monitoring", { cache: "no-store" });
      if (res.status === 401) { router.push("/admin/login"); return; }
      if (!res.ok) return;
      const payload = await res.json() as MonitoringData;
      setMonitoring(payload);
    } catch { /* ignore */ } finally {
      setMonitoringLoading(false);
      setMonitoringRefreshing(false);
    }
  }, [router]);

  useEffect(() => {
    void loadMonitoring();
    const id = window.setInterval(() => { void loadMonitoring(true); }, 30_000);
    return () => window.clearInterval(id);
  }, [loadMonitoring]);

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
      {
        icon: <Tags size={15} />,
        label: "Sans catégorie",
        value: data?.stats.articles_without_category ?? "—",
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
      <header className="rdc-card mb-5 flex flex-wrap items-center justify-between gap-3 rounded-2xl px-5 py-3">
        <div className="flex items-center gap-3">
          <div className="rdc-icon-badge rounded-lg p-2">
            <Shield size={15} />
          </div>
          <div>
            <p className="rdc-brand-text text-[11px] font-semibold uppercase tracking-[0.28em]">
              {appName}
            </p>
            <p className="text-[10px] text-slate-500">Administration · {adminEmail}</p>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void logout()}
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-500/40 px-3 py-1.5 text-xs text-slate-200 transition hover:border-slate-400/60"
          >
            <LogOut size={14} /> Déconnexion
          </button>
          <Link href="/admin/corpus" className="rdc-btn-primary rounded-xl px-3 py-1.5 text-xs font-semibold">
            Corpus détaillé
          </Link>
          <Link href="/" className="rdc-btn-ghost rounded-xl px-3 py-1.5 text-xs">
            Accueil
          </Link>
        </div>
      </header>

      <section className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {loading
          ? [1, 2, 3, 4, 5, 6].map((n) => <div key={n}>{skeletonCard}</div>)
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

      <section className="rdc-card mb-4 rounded-2xl p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-200">Collecte des sources (crawler)</p>
            <p className="mt-1 text-xs text-slate-500">
              Lance le même pipeline que le cron (toutes les sources, limite par source), puis le
              re-embedding si activé.
            </p>
          </div>
          {crawlerJob?.running ? (
            <span className="inline-flex items-center gap-1.5 rounded-lg border border-amber-400/30 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-200">
              <RefreshCw size={12} className="animate-spin" /> En cours…
            </span>
          ) : crawlerJob?.status === "success" ? (
            <span className="rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-200">
              Dernier crawl : OK
            </span>
          ) : crawlerJob?.status === "error" ? (
            <span className="rounded-lg border border-red-400/30 bg-red-500/10 px-2.5 py-1 text-xs text-red-200">
              Dernier crawl : erreur
            </span>
          ) : null}
        </div>

        {crawlerError && (
          <div className="mb-3 rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {crawlerError}
          </div>
        )}

        {crawlerJob?.message && !crawlerJob.running ? (
          <p className="mb-3 text-xs text-slate-400">{crawlerJob.message}</p>
        ) : null}
        {crawlerJob?.error ? (
          <p className="mb-3 text-xs text-red-300">{crawlerJob.error}</p>
        ) : null}

        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-xs text-slate-400">
            Articles max / source
            <select
              value={crawlLimit}
              onChange={(e) => setCrawlLimit(Number(e.target.value))}
              disabled={adminJobBusy || crawlerStarting}
              className="rounded-lg border border-slate-600/40 bg-slate-900/60 px-3 py-2 text-sm text-slate-200"
            >
              {[10, 20, 30, 50, 100, 1000, 2000].map((n) => (
                <option key={n} value={n}>
                  {n}
                </option>
              ))}
            </select>
          </label>
          <label className="flex cursor-pointer items-center gap-2 pb-2 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={crawlReembed}
              onChange={(e) => setCrawlReembed(e.target.checked)}
              disabled={adminJobBusy || crawlerStarting}
              className="rounded border-slate-500"
            />
            Re-embedding après crawl
          </label>
          <button
            type="button"
            onClick={() => void startCrawler()}
            disabled={adminJobBusy || crawlerStarting}
            className="rdc-btn-primary inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Play size={14} />
            {crawlerStarting
              ? "Démarrage…"
              : crawlerJob?.running
                ? "Crawl en cours…"
                : "Lancer le crawl"}
          </button>
        </div>
      </section>

      <section className="rdc-card mb-4 rounded-2xl p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-200">
              Index vectoriel & catégories (Chroma)
            </p>
            <p className="mt-1 text-xs text-slate-500">
              Re-synchronise les embeddings vers Chroma après un changement de base. Peut d’abord
              remplir les catégories manquantes (depuis l’URL), puis ré-indexer.
            </p>
          </div>
          {maintenanceJob?.running ? (
            <span className="inline-flex items-center gap-1.5 rounded-lg border border-amber-400/30 bg-amber-500/10 px-2.5 py-1 text-xs text-amber-200">
              <RefreshCw size={12} className="animate-spin" /> Maintenance…
            </span>
          ) : maintenanceJob?.status === "success" ? (
            <span className="rounded-lg border border-emerald-400/30 bg-emerald-500/10 px-2.5 py-1 text-xs text-emerald-200">
              Dernière maintenance : OK
            </span>
          ) : maintenanceJob?.status === "error" ? (
            <span className="rounded-lg border border-red-400/30 bg-red-500/10 px-2.5 py-1 text-xs text-red-200">
              Dernière maintenance : erreur
            </span>
          ) : null}
        </div>

        {maintenanceError && (
          <div className="mb-3 rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {maintenanceError}
          </div>
        )}

        {maintenanceJob?.message && !maintenanceJob.running ? (
          <p className="mb-2 text-xs text-slate-400">{maintenanceJob.message}</p>
        ) : null}
        {maintenanceJob?.categories_result ? (
          <p className="mb-2 text-xs text-slate-500">
            Catégories : {maintenanceJob.categories_result.updated ?? 0} mis à jour /{" "}
            {maintenanceJob.categories_result.scanned ?? 0} scannés.
          </p>
        ) : null}
        {maintenanceJob?.reembed_result ? (
          <p className="mb-2 text-xs text-slate-500">
            Embeddings : {maintenanceJob.reembed_result.reembedded ?? 0} vectorisés /{" "}
            {maintenanceJob.reembed_result.processed ?? 0} traités.
          </p>
        ) : null}
        {maintenanceJob?.error ? (
          <p className="mb-3 text-xs text-red-300">{maintenanceJob.error}</p>
        ) : null}

        <div className="flex flex-col gap-3">
          <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={reembedForceAll}
              onChange={(e) => setReembedForceAll(e.target.checked)}
              disabled={adminJobBusy || maintenanceStarting}
              className="rounded border-slate-500"
            />
            Tout le corpus (après changement BDD / reset Chroma)
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={reembedOnlyNoCategory}
              onChange={(e) => setReembedOnlyNoCategory(e.target.checked)}
              disabled={adminJobBusy || maintenanceStarting}
              className="rounded border-slate-500"
            />
            Re-embedding uniquement sur les articles sans catégorie
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-300">
            <input
              type="checkbox"
              checked={reembedBackfillCategories}
              onChange={(e) => setReembedBackfillCategories(e.target.checked)}
              disabled={adminJobBusy || maintenanceStarting}
              className="rounded border-slate-500"
            />
            Remplir les catégories manquantes avant (inférence URL)
          </label>
          <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-500">
            <input
              type="checkbox"
              checked={reembedFetchHtml}
              onChange={(e) => setReembedFetchHtml(e.target.checked)}
              disabled={adminJobBusy || maintenanceStarting || !reembedBackfillCategories}
              className="rounded border-slate-500"
            />
            Re-télécharger les pages pour les catégories (lent, optionnel)
          </label>
          <button
            type="button"
            onClick={() => void startMaintenance()}
            disabled={adminJobBusy || maintenanceStarting}
            className="rdc-btn-primary inline-flex w-fit items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed disabled:opacity-60"
          >
            <Layers size={14} />
            {maintenanceStarting
              ? "Démarrage…"
              : maintenanceJob?.running
                ? "Maintenance en cours…"
                : "Lancer re-embedding / catégories"}
          </button>
        </div>
      </section>

      <section className="rdc-card rounded-2xl p-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <p className="text-sm font-semibold text-slate-200">Vue système réelle (backend)</p>
          <button
            onClick={() => void loadOverview(true)}
            disabled={refreshing}
            className="rdc-btn-primary inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold disabled:cursor-not-allowed"
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
                    <span className="rdc-brand-text">{row.count}</span>
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
                  <span className="text-red-300">{data?.stats.missing_source_articles ?? 0}</span>
                </li>
                <li className="flex items-center justify-between">
                  <span>Articles sans lien</span>
                  <span className="text-red-300">{data?.stats.missing_link_articles ?? 0}</span>
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
                          className={`h-2 rounded transition-all duration-500 ${orphan ? "bg-slate-500/50" : "rdc-accent-bar"}`}
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

      {/* ── Monitoring temps réel ────────────────────────────── */}
      <section className="rdc-card mt-4 rounded-2xl p-4">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Activity size={15} className="text-slate-400" />
            <p className="text-sm font-semibold text-slate-200">Monitoring temps réel</p>
            <span className="rounded-md border border-slate-600/40 px-1.5 py-0.5 text-[10px] text-slate-500">
              Métriques depuis le dernier démarrage
            </span>
          </div>
          <button
            onClick={() => void loadMonitoring(true)}
            disabled={monitoringRefreshing}
            className="rdc-btn-primary inline-flex items-center gap-2 rounded-xl px-3 py-1.5 text-xs font-semibold disabled:cursor-not-allowed"
          >
            <RefreshCw size={12} className={monitoringRefreshing ? "animate-spin" : ""} />
            {monitoringRefreshing ? "…" : "Rafraîchir"}
          </button>
        </div>

        {monitoringLoading ? (
          <div className="grid gap-3 md:grid-cols-3">
            {[1, 2, 3].map((n) => (
              <div key={n} className="h-24 animate-pulse rounded-xl bg-slate-700/40" />
            ))}
          </div>
        ) : monitoring ? (
          <div className="grid gap-3 md:grid-cols-3">

            {/* Circuit breaker */}
            <div className="rounded-xl border border-slate-600/30 bg-slate-800/40 p-4">
              <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-slate-500">
                Circuit breaker Ollama
              </p>
              {(() => {
                const s = monitoring.circuit_breaker.state;
                const palette =
                  s === "CLOSED"
                    ? "border-emerald-400/30 bg-emerald-500/10 text-emerald-200"
                    : s === "HALF_OPEN"
                    ? "border-amber-400/30 bg-amber-500/10 text-amber-200"
                    : "border-red-400/30 bg-red-500/10 text-red-200";
                const dot =
                  s === "CLOSED" ? "bg-emerald-400" : s === "HALF_OPEN" ? "bg-amber-400" : "bg-red-400";
                return (
                  <div className={`inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-sm font-semibold ${palette}`}>
                    <span className={`h-2 w-2 rounded-full ${dot}`} />
                    {s}
                  </div>
                );
              })()}
              <p className="mt-2 text-xs text-slate-500">
                {monitoring.circuit_breaker.failures} échec
                {monitoring.circuit_breaker.failures !== 1 ? "s" : ""} /{" "}
                seuil&nbsp;{monitoring.circuit_breaker.threshold}
              </p>
            </div>

            {/* Messages par canal */}
            <div className="rounded-xl border border-slate-600/30 bg-slate-800/40 p-4">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Messages reçus
                </p>
                <span className="rdc-brand-text text-lg font-semibold">
                  {monitoring.messages.total}
                </span>
              </div>
              <ul className="space-y-1.5">
                {(
                  [
                    { key: "telegram", label: "Telegram", icon: <MessageSquare size={11} /> },
                    { key: "whatsapp", label: "WhatsApp", icon: <MessageSquare size={11} /> },
                    { key: "whapi", label: "Whapi", icon: <MessageSquare size={11} /> },
                  ] as const
                ).map(({ key, label, icon }) => {
                  const count = monitoring.messages.by_channel[key];
                  const total = monitoring.messages.total || 1;
                  const w = Math.max(4, (count / total) * 100);
                  return (
                    <li key={key}>
                      <div className="mb-1 flex items-center justify-between text-xs text-slate-400">
                        <span className="flex items-center gap-1">{icon} {label}</span>
                        <span className="text-slate-300">{count}</span>
                      </div>
                      <div className="h-1.5 rounded bg-slate-700/60">
                        <div className="rdc-accent-bar h-1.5 rounded transition-all duration-500" style={{ width: `${w}%` }} />
                      </div>
                    </li>
                  );
                })}
              </ul>
            </div>

            {/* Cache RAG */}
            <div className="rounded-xl border border-slate-600/30 bg-slate-800/40 p-4">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                  Cache RAG
                </p>
                <span className={`text-lg font-semibold ${monitoring.cache.hit_rate_pct >= 50 ? "text-emerald-300" : monitoring.cache.hit_rate_pct >= 20 ? "text-amber-300" : "text-slate-400"}`}>
                  {monitoring.cache.hit_rate_pct}%
                </span>
              </div>
              <div className="mb-3 h-2 rounded bg-slate-700/60">
                <div
                  className="h-2 rounded bg-emerald-500/70 transition-all duration-500"
                  style={{ width: `${Math.min(100, monitoring.cache.hit_rate_pct)}%` }}
                />
              </div>
              <ul className="space-y-1 text-xs text-slate-400">
                <li className="flex justify-between">
                  <span>Hits (cache)</span>
                  <span className="text-emerald-300">{monitoring.cache.hits}</span>
                </li>
                <li className="flex justify-between">
                  <span>Misses (Ollama)</span>
                  <span className="text-slate-300">{monitoring.cache.misses}</span>
                </li>
                <li className="flex justify-between">
                  <span>Total requêtes</span>
                  <span className="text-slate-300">{monitoring.cache.total}</span>
                </li>
              </ul>
            </div>

          </div>
        ) : (
          <p className="text-xs text-slate-500">Impossible de charger les métriques de monitoring.</p>
        )}
      </section>
    </main>
  );
}
