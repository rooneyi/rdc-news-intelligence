export default function AdminConfigurationMissing() {
  return (
    <div className="mx-auto max-w-lg px-5 py-16 text-center text-slate-300">
      <p className="text-lg font-semibold text-amber-200">Configuration admin manquante</p>
      <p className="mt-2 text-sm text-slate-400">
        Définissez{" "}
        <code className="text-slate-300">ADMIN_PASSWORD</code>,{" "}
        <code className="text-slate-300">ADMIN_SESSION_SECRET</code> et{" "}
        <code className="text-slate-300">ADMIN_EMAIL</code> dans les variables d&apos;environnement du
        frontend. Pour le titre affiché, ajoutez aussi{" "}
        <code className="text-slate-300">NEXT_PUBLIC_APP_NAME</code>, puis redémarrez Next.js.
      </p>
    </div>
  );
}
