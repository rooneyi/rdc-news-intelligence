import { cookies } from "next/headers";
import { NextResponse } from "next/server";
import {
  ADMIN_COOKIE_NAME,
  getAdminEmail,
  getAdminPassword,
  getAdminSessionSecret,
  verifyAdminSession,
} from "@/lib/admin-auth";
import {
  getFastApiBaseUrl,
  readFastApiJson,
  wrapFastApiContactError,
} from "@/lib/fastapi-upstream";

export const dynamic = "force-dynamic";

export async function GET() {
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

  try {
    const upstream = await fetch(`${getFastApiBaseUrl()}/admin/overview`, {
      cache: "no-store",
    });
    const payload = await readFastApiJson(upstream);

    if (!upstream.ok) {
      return NextResponse.json(
        { error: payload?.detail ?? payload?.error ?? "Erreur FastAPI." },
        { status: upstream.status },
      );
    }

    return NextResponse.json(payload, { status: 200 });
  } catch (err) {
    const message = wrapFastApiContactError(err);
    return NextResponse.json(
      { error: `Impossible de contacter FastAPI: ${message}` },
      { status: 502 },
    );
  }
}
