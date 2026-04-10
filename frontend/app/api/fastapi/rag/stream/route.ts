import { NextRequest, NextResponse } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const FASTAPI_BASE_URL = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://127.0.0.1:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const query = typeof body?.query === "string" ? body.query.trim() : "";

    if (!query) {
      return NextResponse.json({ error: "Question vide." }, { status: 400 });
    }

    const upstream = await fetch(`${FASTAPI_BASE_URL}/rag/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: 5, channel: "web" }),
      cache: "no-store",
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

    return new Response(upstream.body, {
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
