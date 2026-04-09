import Link from "next/link";

export default function Home() {
  return (
    <main className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(29,78,216,0.20),_transparent_30%),radial-gradient(circle_at_top_right,_rgba(96,165,250,0.18),_transparent_26%),linear-gradient(180deg,_#f8fbff_0%,_#eef5ff_52%,_#ffffff_100%)] text-slate-950">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-6 py-6 md:px-10 lg:px-12">
        <header className="flex items-center justify-between rounded-[28px] border border-white/70 bg-white/70 px-5 py-4 shadow-[0_20px_60px_rgba(15,23,42,0.08)] backdrop-blur-xl">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.32em] text-blue-700">RDC News Intelligence</p>
            <h1 className="mt-1 text-lg font-semibold text-slate-950">Plateforme RAG multicanale</h1>
          </div>
          <div className="hidden items-center gap-3 md:flex">
            <span className="rounded-full bg-blue-900 px-4 py-2 text-sm font-medium text-white shadow-lg shadow-blue-900/20">Client</span>
            <span className="rounded-full border border-blue-200 bg-blue-50 px-4 py-2 text-sm font-medium text-blue-900">Admin</span>
          </div>
        </header>

        <section className="grid flex-1 items-center gap-10 py-14 lg:grid-cols-[1.2fr_0.8fr] lg:py-20">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-blue-200 bg-white/80 px-4 py-2 text-sm font-medium text-blue-900 shadow-sm">
              <span className="h-2 w-2 rounded-full bg-blue-600" />
              Interface client, authentification, historique et tableau admin
            </div>

            <h2 className="mt-7 text-5xl font-semibold leading-[1.02] tracking-tight text-slate-950 md:text-6xl">
              Une expérience premium pour poser des questions, suivre l&apos;historique et piloter le système.
            </h2>

            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600 md:text-xl">
              Le frontend doit offrir un espace client sécurisé pour interroger le moteur RAG, gérer l&apos;authentification et retrouver l&apos;historique des requêtes, ainsi qu&apos;un espace administrateur pour superviser le corpus, lancer le crawl et suivre l&apos;état du système.
            </p>

            <div className="mt-8 flex flex-col gap-4 sm:flex-row">
              <Link
                href="/client"
                className="inline-flex items-center justify-center rounded-2xl bg-blue-900 px-6 py-3.5 text-base font-semibold text-white shadow-[0_18px_40px_rgba(30,64,175,0.28)] transition-transform duration-200 hover:-translate-y-0.5 hover:bg-blue-800"
              >
                Ouvrir l&apos;espace client
              </Link>
              <Link
                href="/admin"
                className="inline-flex items-center justify-center rounded-2xl border border-blue-200 bg-white px-6 py-3.5 text-base font-semibold text-blue-900 shadow-sm transition-transform duration-200 hover:-translate-y-0.5 hover:border-blue-300 hover:bg-blue-50"
              >
                Voir le tableau admin
              </Link>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              {[
                ["Historique", "Conserver les questions, réponses et sources dans le compte utilisateur."],
                ["Sécurité", "Connexion et gestion de session pour les utilisateurs enregistrés."],
                ["Pilotage", "Lancer le crawl et superviser l&apos;indexation depuis l&apos;admin."],
              ].map(([title, text]) => (
                <article key={title} className="rounded-3xl border border-white/80 bg-white/85 p-5 shadow-[0_18px_50px_rgba(15,23,42,0.06)] backdrop-blur">
                  <h3 className="text-sm font-semibold uppercase tracking-[0.22em] text-blue-800">{title}</h3>
                  <p className="mt-3 text-sm leading-6 text-slate-600">{text}</p>
                </article>
              ))}
            </div>
          </div>

          <div className="relative">
            <div className="absolute -left-8 top-10 h-28 w-28 rounded-full bg-blue-400/20 blur-3xl" />
            <div className="absolute right-4 top-0 h-36 w-36 rounded-full bg-sky-300/20 blur-3xl" />

            <div className="relative rounded-[34px] border border-white/80 bg-white/80 p-4 shadow-[0_30px_80px_rgba(15,23,42,0.12)] backdrop-blur-xl">
              <div className="rounded-[28px] bg-[linear-gradient(180deg,_#0f172a_0%,_#1d4ed8_100%)] p-6 text-white">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-xs uppercase tracking-[0.28em] text-blue-100/80">Dashboard</p>
                    <h3 className="mt-2 text-2xl font-semibold">Centre de contrôle</h3>
                  </div>
                  <div className="rounded-full bg-white/15 px-3 py-1 text-xs font-medium text-white/90">Live</div>
                </div>

                <div className="mt-8 grid gap-3 sm:grid-cols-2">
                  <div className="rounded-3xl bg-white/12 p-4 ring-1 ring-white/15">
                    <p className="text-sm text-blue-100">Client</p>
                    <p className="mt-2 text-lg font-semibold">Questions, authentification, historique</p>
                  </div>
                  <div className="rounded-3xl bg-white/12 p-4 ring-1 ring-white/15">
                    <p className="text-sm text-blue-100">Admin</p>
                    <p className="mt-2 text-lg font-semibold">Sources, crawl, supervision, état système</p>
                  </div>
                </div>

                <div className="mt-4 rounded-3xl bg-white p-4 text-slate-900 shadow-inner shadow-blue-950/5">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-slate-500">Statut du moteur</span>
                    <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700">Opérationnel</span>
                  </div>
                  <div className="mt-4 space-y-3 text-sm">
                    <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                      <span>Indexation</span>
                      <span className="font-semibold text-blue-900">Actif</span>
                    </div>
                    <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                      <span>Historique utilisateur</span>
                      <span className="font-semibold text-blue-900">Synchronisé</span>
                    </div>
                    <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-4 py-3">
                      <span>Crawl</span>
                      <span className="font-semibold text-blue-900">Pilotable</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
