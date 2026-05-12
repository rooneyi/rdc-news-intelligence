import { NextResponse } from "next/server";
import {
  ADMIN_COOKIE_NAME,
  createSessionToken,
  getAdminEmail,
  getAdminPassword,
  getAdminSessionSecret,
  timingSafePasswordEquals,
} from "@/lib/admin-auth";

export const dynamic = "force-dynamic";

export async function POST(request: Request) {
  const secret = getAdminSessionSecret();
  const expectedPassword = getAdminPassword();
  const adminEmail = getAdminEmail();
  if (!secret || !expectedPassword || !adminEmail) {
    return NextResponse.json(
      {
        error:
          "Serveur mal configuré : définir ADMIN_PASSWORD, ADMIN_SESSION_SECRET et ADMIN_EMAIL dans l'environnement.",
      },
      { status: 503 },
    );
  }

  let body: { password?: string };
  try {
    body = (await request.json()) as { password?: string };
  } catch {
    return NextResponse.json({ error: "Corps JSON invalide." }, { status: 400 });
  }

  const password = typeof body.password === "string" ? body.password : "";
  if (!timingSafePasswordEquals(password, expectedPassword)) {
    return NextResponse.json({ error: "Mot de passe incorrect." }, { status: 401 });
  }

  const token = createSessionToken(secret);
  const res = NextResponse.json({ ok: true }, { status: 200 });
  const secure = process.env.NODE_ENV === "production";
  res.cookies.set(ADMIN_COOKIE_NAME, token, {
    httpOnly: true,
    secure,
    sameSite: "lax",
    path: "/",
    maxAge: 7 * 24 * 60 * 60,
  });
  return res;
}
