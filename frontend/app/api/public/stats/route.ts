import { NextResponse } from "next/server";

const FASTAPI_BASE_URL = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const res = await fetch(`${FASTAPI_BASE_URL}/admin/overview`, {
      cache: "no-store",
    });
    if (!res.ok) {
      return NextResponse.json({ sources: null, articles: null, coverage: null });
    }
    const payload = await res.json();
    const stats = payload?.stats ?? {};
    return NextResponse.json({
      sources: stats.catalog_sources_configured ?? stats.total_sources ?? null,
      articles: stats.total_articles ?? null,
      coverage: stats.embedding_coverage ?? null,
    });
  } catch {
    return NextResponse.json({ sources: null, articles: null, coverage: null });
  }
}
