"use client";

import Link from "next/link";
import { ArrowRight, Database, Shield, Zap } from "lucide-react";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-5 py-6 md:px-8">
      <header className="rdc-card mb-8 flex items-center justify-between rounded-2xl px-5 py-3">
        <div className="flex items-center gap-3">
          <div className="rounded-lg border border-blue-300/30 bg-blue-500/15 p-2 text-blue-300">
            <Shield size={15} />
          </div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.28em] text-blue-300">
            RDC News Intelligence
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href="/client"
            className="rounded-xl border border-slate-500/30 bg-slate-700/30 px-4 py-1.5 text-xs font-medium text-slate-200 transition hover:bg-slate-700/50"
          >
            Espace client
          </Link>
          <Link
            href="/admin"
            className="rounded-xl bg-blue-600 px-4 py-1.5 text-xs font-semibold text-white transition hover:bg-blue-500"
          >
            Administration
          </Link>
        </div>
      </header>

      <section className="grid flex-1 items-center gap-6 pb-10 lg:grid-cols-2">
        <div>
          <span className="mb-5 inline-flex items-center rounded-full border border-blue-300/30 bg-blue-500/10 px-4 py-1 text-xs text-blue-200">
            Fact-checking WhatsApp et Telegram
          </span>
          <h1 className="mb-5 text-4xl font-semibold leading-tight text-slate-100 md:text-5xl">
            Vérifier une info avant qu&apos;elle ne devienne virale.
          </h1>
          <p className="rdc-muted mb-8 max-w-xl text-sm leading-7">
            Plateforme de vérification orientée RDC, alimentée par un corpus local de médias fiables.
            Le bot répond en langage clair, avec verdict et sources.
          </p>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/client"
              className="inline-flex items-center gap-2 rounded-2xl bg-blue-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-blue-500"
            >
              Poser une question <ArrowRight size={15} />
            </Link>
            <Link
              href="/admin"
              className="rounded-2xl border border-slate-500/30 bg-slate-700/30 px-5 py-3 text-sm font-semibold text-slate-100 transition hover:bg-slate-700/50"
            >
              Ouvrir la console admin
            </Link>
          </div>
        </div>

        <div className="rdc-card rounded-3xl p-5 md:p-6">
          <div className="mb-4 grid gap-3 sm:grid-cols-3">
            {[
              { icon: <Database size={14} />, label: "Sources", value: "12+" },
              { icon: <Zap size={14} />, label: "Verdict moyen", value: "< 8s" },
              { icon: <Shield size={14} />, label: "Thèmes", value: "4" },
            ].map((item) => (
              <div key={item.label} className="rounded-xl border border-slate-500/20 bg-slate-800/40 p-3">
                <div className="mb-2 flex items-center gap-2 text-slate-400">
                  {item.icon}
                  <span className="text-[11px] uppercase tracking-wider">{item.label}</span>
                </div>
                <p className="text-lg font-semibold text-slate-100">{item.value}</p>
              </div>
            ))}
          </div>
          <div className="rounded-xl border border-slate-500/20 bg-slate-900/50 p-4 text-sm leading-6 text-slate-300">
            <p className="mb-2 text-xs uppercase tracking-wider text-slate-400">Exemple de verdict</p>
            <p className="mb-2">
              <span className="font-semibold text-amber-300">IMPRÉCIS</span> — La déclaration ne
              correspond pas aux articles récents disponibles.
            </p>
            <p className="rdc-muted text-xs">Sources: Radio Okapi, ACP, actualite.cd</p>
          </div>
        </div>
      </section>
    </main>
  );
}