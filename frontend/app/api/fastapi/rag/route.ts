import { NextRequest, NextResponse } from "next/server";
import {
  getFastApiBaseUrl,
  readFastApiJson,
  wrapFastApiContactError,
} from "@/lib/fastapi-upstream";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const query = typeof body?.query === "string" ? body.query.trim() : "";

    if (!query) {
      return NextResponse.json({ error: "Question vide." }, { status: 400 });
    }

    console.log(`[API/RAG] Web request: "${query.slice(0, 80)}..."`);

    const upstream = await fetch(`${getFastApiBaseUrl()}/rag`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query, top_k: 5, channel: "web" }),
      cache: "no-store",
    });

    const payload = await readFastApiJson(upstream);

    if (!upstream.ok) {
      console.error(`[API/RAG] FastAPI error:`, payload);
      return NextResponse.json(
        {
          error: payload?.detail ?? payload?.error ?? "Erreur FastAPI.",
        },
        { status: upstream.status }
      );
    }

    const sourceCount = Array.isArray(payload.sources) ? payload.sources.length : 0;
    console.log(`[API/RAG] Success: ${sourceCount} sources`);
    return NextResponse.json(payload, { status: 200 });
  } catch (err) {
    const msg = wrapFastApiContactError(err);
    console.error(`[API/RAG] Proxy error:`, msg);
    return NextResponse.json(
      { error: `Impossible de contacter FastAPI: ${msg}` },
      { status: 502 }
    );
  }
}
