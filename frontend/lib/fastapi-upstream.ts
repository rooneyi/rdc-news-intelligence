/** Réponse JSON typique renvoyée par FastAPI (RAG, admin, erreurs). */
export type FastApiJsonBody = {
  detail?: string;
  error?: string;
  sources?: unknown[];
  verdict?: string;
  [key: string]: unknown;
};

/** URL FastAPI pour les routes API Next (serveur uniquement). */
export function getFastApiBaseUrl(): string {
  // FASTAPI_URL = runtime (PM2 / .env.local), sans rebuild si le port change.
  const raw =
    process.env.FASTAPI_URL?.trim() ||
    process.env.NEXT_PUBLIC_FASTAPI_URL?.trim() ||
    "http://127.0.0.1:8000";
  return raw.replace(/\/$/, "");
}

function isHtmlBody(text: string): boolean {
  const trimmed = text.trimStart().toLowerCase();
  return trimmed.startsWith("<!doctype") || trimmed.startsWith("<html");
}

export function fastApiMisconfigMessage(status: number, baseUrl = getFastApiBaseUrl()): string {
  return (
    `FastAPI a renvoyé une page HTML (HTTP ${status}) au lieu de JSON. ` +
    `Vérifie que rdc-ai-service tourne (pm2 status) et que ` +
    `FASTAPI_URL / NEXT_PUBLIC_FASTAPI_URL=${baseUrl} doit pointer vers le port APP_PORT (ex. http://127.0.0.1:8001) — ` +
    `pas le domaine public (sinon nginx renvoie Next/Hestia, pas /rag ni /admin).`
  );
}

export async function readFastApiJson<T = FastApiJsonBody>(
  upstream: Response,
): Promise<T> {
  const baseUrl = getFastApiBaseUrl();
  const raw = await upstream.text();
  if (!raw.trim()) {
    return {} as T;
  }
  if (isHtmlBody(raw)) {
    throw new Error(fastApiMisconfigMessage(upstream.status, baseUrl));
  }
  try {
    return JSON.parse(raw) as T;
  } catch {
    const preview = raw.slice(0, 120).replace(/\s+/g, " ");
    throw new Error(
      `Réponse FastAPI non-JSON (HTTP ${upstream.status}): ${preview}`,
    );
  }
}

export function wrapFastApiContactError(err: unknown): string {
  const message = err instanceof Error ? err.message : "Erreur inconnue";
  const low = message.toLowerCase();
  if (
    low.includes("fetch failed") ||
    low.includes("econnrefused") ||
    low.includes("connect econnrefused")
  ) {
    const base = getFastApiBaseUrl();
    return (
      `FastAPI injoignable sur ${base} (connexion refusée — rien n'écoute sur ce port). ` +
      `Vérifie: pm2 status rdc-ai-service (doit être « online », pas « errored ») ; ` +
      `curl -s ${base}/health ; si APP_PORT≠8000, mets FASTAPI_URL=http://127.0.0.1:<port> dans frontend/.env.local puis pm2 restart rdc-frontend. ` +
      `Réparation: cd ai-service && ./scripts/fix_starlette_pin.sh ou ./scripts/admin_clean_start.sh`
    );
  }
  return message;
}
