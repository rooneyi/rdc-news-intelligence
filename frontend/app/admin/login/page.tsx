import AdminConfigurationMissing from "@/app/admin/AdminConfigurationMissing";
import AdminLoginForm from "@/app/admin/login/AdminLoginForm";
import { getAppDisplayName } from "@/lib/app-config";
import { getAdminEmail, getAdminPassword, getAdminSessionSecret } from "@/lib/admin-auth";

export default function AdminLoginPage() {
  const secret = getAdminSessionSecret();
  const password = getAdminPassword();
  const email = getAdminEmail();

  if (!secret || !password || !email) {
    return <AdminConfigurationMissing />;
  }

  return <AdminLoginForm appName={getAppDisplayName()} adminEmail={email} />;
}
