import { NextResponse } from "next/server";
import { getFastApiBaseUrl } from "@/lib/fastapi-upstream";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const res = await fetch(`${getFastApiBaseUrl()}/admin/overview`, {
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
