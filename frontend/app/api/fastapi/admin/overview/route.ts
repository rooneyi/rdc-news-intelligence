import { NextResponse } from "next/server";

const FASTAPI_BASE_URL = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const upstream = await fetch(`${FASTAPI_BASE_URL}/admin/overview`, {
      cache: "no-store",
    });
    const payload = await upstream.json();

    if (!upstream.ok) {
      return NextResponse.json(
        { error: payload?.detail ?? payload?.error ?? "Erreur FastAPI." },
        { status: upstream.status },
      );
    }

    return NextResponse.json(payload, { status: 200 });
  } catch (err) {
    const message = err instanceof Error ? err.message : "Erreur inconnue";
    return NextResponse.json(
      { error: `Impossible de contacter FastAPI: ${message}` },
      { status: 502 },
    );
  }
}
