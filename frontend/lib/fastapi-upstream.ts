export function getFastApiBaseUrl(): string {
  return (process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://127.0.0.1:8000").replace(
    /\/$/,
    "",
  );
}

function isHtmlBody(text: string): boolean {
  const trimmed = text.trimStart().toLowerCase();
  return trimmed.startsWith("<!doctype") || trimmed.startsWith("<html");
}

export function fastApiMisconfigMessage(status: number, baseUrl = getFastApiBaseUrl()): string {
  return (
    `FastAPI a renvoyé une page HTML (HTTP ${status}) au lieu de JSON. ` +
    `Vérifie que rdc-ai-service tourne (pm2 status) et que ` +
    `NEXT_PUBLIC_FASTAPI_URL=${baseUrl} vaut http://127.0.0.1:8000 sur le VPS — ` +
    `pas le domaine public (sinon nginx renvoie Next/Hestia, pas /rag ni /admin).`
  );
}

export async function readFastApiJson<T = Record<string, unknown>>(
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
    return (
      `FastAPI injoignable sur ${getFastApiBaseUrl()}. ` +
      `Redémarre: pm2 restart rdc-ai-service — test: curl -s http://127.0.0.1:8000/health`
    );
  }
  return message;
}
