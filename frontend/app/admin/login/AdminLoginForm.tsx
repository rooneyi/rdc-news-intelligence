"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Lock, Shield } from "lucide-react";

type Props = { appName: string; adminEmail: string };

export default function AdminLoginForm({ appName, adminEmail }: Props) {
  const router = useRouter();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      const res = await fetch("/api/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      const data = (await res.json()) as { error?: string };
      if (!res.ok) {
        setError(data.error ?? "Connexion refusée.");
        return;
      }
      router.push("/admin");
      router.refresh();
    } catch {
      setError("Erreur réseau.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-5 py-12">
      <div className="rdc-card rounded-2xl p-8">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <div className="rounded-xl border border-blue-400/30 bg-blue-500/15 p-3 text-blue-300">
            <Shield size={28} />
          </div>
          <h1 className="text-lg font-semibold text-slate-100">{appName}</h1>
          <p className="text-xs text-slate-500">Administration</p>
          <p className="text-sm text-slate-400">
            Compte : <span className="text-slate-300">{adminEmail}</span>
          </p>
          <p className="text-sm text-slate-400">Saisis le mot de passe pour accéder au tableau de bord.</p>
        </div>

        <form onSubmit={(e) => void onSubmit(e)} className="space-y-4">
          <label className="block">
            <span className="mb-1.5 flex items-center gap-2 text-xs font-medium text-slate-400">
              <Lock size={14} /> Mot de passe
            </span>
            <input
              type="password"
              name="password"
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-xl border border-slate-600/50 bg-slate-900/60 px-4 py-3 text-slate-100 outline-none ring-blue-500/40 placeholder:text-slate-600 focus:border-blue-500/50 focus:ring-2"
              placeholder="••••••••"
              disabled={pending}
              required
            />
          </label>

          {error && (
            <div className="rounded-lg border border-red-400/30 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={pending}
            className="w-full rounded-xl bg-blue-600 py-3 text-sm font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:bg-slate-600"
          >
            {pending ? "Connexion…" : "Se connecter"}
          </button>
        </form>

        <p className="mt-6 text-center">
          <Link href="/" className="text-sm text-slate-400 underline-offset-4 hover:text-slate-200 hover:underline">
            Retour à l&apos;accueil
          </Link>
        </p>
      </div>
    </main>
  );
}
