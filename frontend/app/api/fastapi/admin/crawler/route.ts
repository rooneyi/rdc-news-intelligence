import { cookies } from "next/headers";
import { NextRequest, NextResponse } from "next/server";
import {
  ADMIN_COOKIE_NAME,
  getAdminEmail,
  getAdminPassword,
  getAdminSessionSecret,
  verifyAdminSession,
} from "@/lib/admin-auth";

const FASTAPI_BASE_URL = process.env.NEXT_PUBLIC_FASTAPI_URL ?? "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

async function requireAdmin() {
  const secret = getAdminSessionSecret();
  if (!secret || !getAdminPassword() || !getAdminEmail()) {
    return NextResponse.json(
      {
        error:
          "Configuration admin manquante côté Next.js (ADMIN_PASSWORD, ADMIN_SESSION_SECRET, ADMIN_EMAIL).",
      },
      { status: 503 },
    );
  }
  const token = (await cookies()).get(ADMIN_COOKIE_NAME)?.value;
  if (!verifyAdminSession(token, secret)) {
    return NextResponse.json({ error: "Non authentifié." }, { status: 401 });
  }
  return null;
}

export async function GET() {
  const denied = await requireAdmin();
  if (denied) return denied;

  try {
    const upstream = await fetch(`${FASTAPI_BASE_URL}/admin/crawler/status`, {
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

export async function POST(request: NextRequest) {
  const denied = await requireAdmin();
  if (denied) return denied;

  let body: Record<string, unknown> = {};
  try {
    body = (await request.json()) as Record<string, unknown>;
  } catch {
    body = {};
  }

  try {
    const upstream = await fetch(`${FASTAPI_BASE_URL}/admin/crawler/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_id: typeof body.source_id === "string" ? body.source_id : "all",
        limit: typeof body.limit === "number" ? body.limit : 30,
        page_range: typeof body.page_range === "string" ? body.page_range : undefined,
        run_reembedding: body.run_reembedding !== false,
      }),
    });
    const payload = await upstream.json();
    if (!upstream.ok) {
      const detail =
        typeof payload?.detail === "string"
          ? payload.detail
          : (payload?.error ?? "Erreur FastAPI.");
      return NextResponse.json({ error: detail }, { status: upstream.status });
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
