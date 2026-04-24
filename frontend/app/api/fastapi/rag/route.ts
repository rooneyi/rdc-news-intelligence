import { NextRequest, NextResponse } from "next/server";

const FASTAPI_BASE_URL = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const query = typeof body?.query === "string" ? body.query.trim() : "";

    if (!query) {
      return NextResponse.json({ error: "Question vide." }, { status: 400 });
    }

    console.log(`[API/RAG] Web request: "${query.slice(0, 80)}..."`);

    const upstream = await fetch(`${FASTAPI_BASE_URL}/rag`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: 5, channel: "web" }),
      cache: "no-store",
    });

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
    const msg = err instanceof Error ? err.message : "Erreur inconnue.";
    console.error(`[API/RAG] Proxy error:`, msg);
    return NextResponse.json(
      { error: `Impossible de contacter FastAPI: ${msg}` },
      { status: 502 }
    );
  }
}
