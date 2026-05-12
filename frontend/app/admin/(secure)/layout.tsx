import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import AdminConfigurationMissing from "@/app/admin/AdminConfigurationMissing";
import { AdminBrandingProvider } from "@/app/admin/admin-branding-context";
import { getAppDisplayName } from "@/lib/app-config";
import {
  ADMIN_COOKIE_NAME,
  getAdminEmail,
  getAdminPassword,
  getAdminSessionSecret,
  verifyAdminSession,
} from "@/lib/admin-auth";

export default async function AdminSecureLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const secret = getAdminSessionSecret();
  const password = getAdminPassword();
  const email = getAdminEmail();

  if (!secret || !password || !email) {
    return <AdminConfigurationMissing />;
  }

  const cookieStore = await cookies();
  const token = cookieStore.get(ADMIN_COOKIE_NAME)?.value;
  if (!verifyAdminSession(token, secret)) {
    redirect("/admin/login");
  }

  return (
    <AdminBrandingProvider appName={getAppDisplayName()} adminEmail={email}>
      {children}
    </AdminBrandingProvider>
  );
}
