import Link from "next/link";

const crawlSources = ["7sur7.cd", "actualite.cd", "congoindependant.com", "rfi.fr" ];

export default function AdminPage() {
  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_right,_rgba(96,165,250,0.18),_transparent_25%),linear-gradient(180deg,_#eef5ff_0%,_#ffffff_100%)] text-slate-950">
      <div className="mx-auto max-w-6xl px-6 py-6 md:px-10 lg:px-12 lg:py-10">
        <header className="flex items-center justify-between rounded-[28px] border border-white/80 bg-white/80 px-5 py-4 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur-xl">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-blue-700">Console admin</p>
            <h1 className="mt-1 text-lg font-semibold">Pilotage du crawl et supervision système</h1>
          </div>
          <Link href="/" className="rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-900">
            Retour accueil
          </Link>
        </header>

        <section className="mt-8 grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <article className="rounded-[30px] border border-white/80 bg-gradient-to-br from-slate-950 via-blue-950 to-blue-800 p-7 text-white shadow-[0_30px_80px_rgba(15,23,42,0.22)]">
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-blue-100/90">Contrôle rapide</p>
            <h2 className="mt-3 text-3xl font-semibold">Lancer le crawl, surveiller et stabiliser</h2>
            <p className="mt-4 max-w-xl text-blue-50/90 leading-7">
              L&apos;espace admin sert à orchestrer les sources, déclencher la collecte, vérifier l&apos;état du pipeline et garder le corpus à jour.
            </p>

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              <button className="rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-blue-950 shadow-lg shadow-black/10">Lancer le crawl</button>
              <button className="rounded-2xl border border-white/20 bg-white/10 px-5 py-3 text-sm font-semibold text-white backdrop-blur">Synchroniser l&apos;index</button>
              <button className="rounded-2xl border border-white/20 bg-white/10 px-5 py-3 text-sm font-semibold text-white backdrop-blur">Vérifier les sources</button>
              <button className="rounded-2xl border border-white/20 bg-white/10 px-5 py-3 text-sm font-semibold text-white backdrop-blur">Consulter les logs</button>
            </div>
          </article>

          <article className="rounded-[30px] border border-white/80 bg-white/90 p-7 shadow-[0_22px_60px_rgba(15,23,42,0.08)] backdrop-blur">
            <p className="text-sm font-semibold uppercase tracking-[0.28em] text-blue-800">Sources actives</p>
            <h2 className="mt-3 text-2xl font-semibold">Corpus configuré pour l&apos;ingestion</h2>
            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {crawlSources.map((source) => (
                <div key={source} className="rounded-3xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-sm font-medium text-slate-900">{source}</p>
                  <p className="mt-1 text-sm text-slate-500">Source prête pour le crawl automatique.</p>
                </div>
              ))}
            </div>

            <div className="mt-6 rounded-[24px] border border-blue-100 bg-blue-50 p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">Etat du système</span>
                <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">En ligne</span>
              </div>
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl bg-white px-4 py-3 ring-1 ring-blue-100">
                  <p className="text-xs text-slate-500">Articles indexés</p>
                  <p className="mt-1 text-lg font-semibold text-blue-950">~2000+</p>
                </div>
                <div className="rounded-2xl bg-white px-4 py-3 ring-1 ring-blue-100">
                  <p className="text-xs text-slate-500">Dernier crawl</p>
                  <p className="mt-1 text-lg font-semibold text-blue-950">Actif</p>
                </div>
                <div className="rounded-2xl bg-white px-4 py-3 ring-1 ring-blue-100">
                  <p className="text-xs text-slate-500">Pipeline</p>
                  <p className="mt-1 text-lg font-semibold text-blue-950">Stable</p>
                </div>
              </div>
            </div>
          </article>
        </section>
      </div>
    </main>
  );
}