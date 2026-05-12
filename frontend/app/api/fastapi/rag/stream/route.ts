import { NextRequest, NextResponse } from "next/server";
import { Agent, fetch as undiciFetch } from "undici";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const FASTAPI_BASE_URL = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://127.0.0.1:8000";

/**
 * Le fetch global Node (Undici) coupe le flux après ~300 s (UND_ERR_BODY_TIMEOUT).
 * Ollama peut mettre bien plus longtemps : agent sans limite sur les timeouts de corps / en-têtes.
 */
const ragUpstreamAgent = new Agent({
  connectTimeout: 60_000,
  headersTimeout: 0,
  bodyTimeout: 0,
});

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const query = typeof body?.query === "string" ? body.query.trim() : "";

    if (!query) {
      return NextResponse.json({ error: "Question vide." }, { status: 400 });
    }

    const upstream = await undiciFetch(`${FASTAPI_BASE_URL}/rag/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: 5, channel: "web" }),
      dispatcher: ragUpstreamAgent,
    });

    if (!upstream.ok) {
      const text = await upstream.text();
      return NextResponse.json(
        { error: text || "Erreur FastAPI." },
        { status: upstream.status }
      );
    }

    if (!upstream.body) {
      return NextResponse.json(
        { error: "Flux FastAPI indisponible." },
        { status: 502 }
      );
    }

    // Undici et les types Web `ReadableStream` doublonnent ; le flux reste valide pour Next.
    return new Response(upstream.body as unknown as ReadableStream<Uint8Array>, {
      status: 200,
      headers: {
        "Content-Type": "application/x-ndjson; charset=utf-8",
        "Cache-Control": "no-cache, no-transform",
      },
    });
  } catch (err) {
    const msg = err instanceof Error ? err.message : "Erreur inconnue.";
    return NextResponse.json(
      { error: `Impossible de contacter FastAPI: ${msg}` },
      { status: 502 }
    );
  }
}
