import { NextRequest, NextResponse } from "next/server";

const FASTAPI_BASE_URL = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://127.0.0.1:8001";
const TIMEOUT_MS = 120_000; // 120s max (Mistral prend du temps)

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const query = typeof body?.query === "string" ? body.query.trim() : "";

    if (!query) {
      return NextResponse.json({ error: "Question vide." }, { status: 400 });
    }

    console.log(`[API/RAG] Web request: "${query.slice(0, 80)}..."`);

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), TIMEOUT_MS);

    try {
      const upstream = await fetch(`${FASTAPI_BASE_URL}/rag`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: 5, channel: "web" }),
        signal: controller.signal,
        cache: "no-store",
      });

      clearTimeout(timeoutId);
      const payload = await upstream.json();

      if (!upstream.ok) {
        console.error(`[API/RAG] FastAPI error:`, payload);
        return NextResponse.json(
          {
            error: payload?.detail ?? payload?.error ?? "Erreur FastAPI.",
          },
          { status: upstream.status }
        );
      }

      console.log(`[API/RAG] Success: ${payload?.sources?.length ?? 0} sources`);
      return NextResponse.json(payload, { status: 200 });
    } catch (err) {
      clearTimeout(timeoutId);
      if (err instanceof Error && err.name === "AbortError") {
        console.error(`[API/RAG] Timeout after ${TIMEOUT_MS}ms`);
        return NextResponse.json(
          { error: `Timeout: le service FastAPI met trop de temps à répondre.` },
          { status: 504 }
        );
      }
      throw err;
    }
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Erreur inconnue.";
    console.error(`[API/RAG] Proxy error:`, msg);
    return NextResponse.json(
      { error: `Impossible de contacter FastAPI: ${msg}` },
      { status: 502 }
    );
  }
}
