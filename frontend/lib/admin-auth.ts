import { createHmac, timingSafeEqual } from "crypto";

export const ADMIN_COOKIE_NAME = "rdc_admin_session";

export function getAdminEmail(): string {
  return process.env.ADMIN_EMAIL?.trim() ?? "";
}

export function getAdminPassword(): string {
  return process.env.ADMIN_PASSWORD ?? "";
}

export function getAdminSessionSecret(): string {
  return process.env.ADMIN_SESSION_SECRET?.trim() ?? "";
}

export function timingSafePasswordEquals(
  provided: string,
  expected: string,
): boolean {
  if (!provided || !expected) return false;
  const a = Buffer.from(provided);
  const b = Buffer.from(expected);
  if (a.length !== b.length) return false;
  try {
    return timingSafeEqual(a, b);
  } catch {
    return false;
  }
}

/** Jeton signé HMAC (cookie httpOnly admin). */
export function createSessionToken(secret: string): string {
  const payload = `${Date.now()}:${createHmac("sha256", secret).update("rdc-admin").digest("hex").slice(0, 16)}`;
  const sig = createHmac("sha256", secret).update(payload).digest("hex");
  return `${payload}.${sig}`;
}

export function verifyAdminSession(
  token: string | undefined,
  secret: string,
): boolean {
  if (!token?.trim() || !secret) return false;
  const dot = token.lastIndexOf(".");
  if (dot <= 0) return false;
  const payload = token.slice(0, dot);
  const sig = token.slice(dot + 1);
  const expected = createHmac("sha256", secret).update(payload).digest("hex");
  try {
    const a = Buffer.from(sig, "hex");
    const b = Buffer.from(expected, "hex");
    if (a.length !== b.length) return false;
    return timingSafeEqual(a, b);
  } catch {
    return false;
  }
}
