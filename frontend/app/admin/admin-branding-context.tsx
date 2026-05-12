"use client";

import { createContext, useContext } from "react";

type AdminBranding = { appName: string; adminEmail: string };

const AdminBrandingContext = createContext<AdminBranding | null>(null);

export function AdminBrandingProvider({
  appName,
  adminEmail,
  children,
}: AdminBranding & { children: React.ReactNode }) {
  return (
    <AdminBrandingContext.Provider value={{ appName, adminEmail }}>
      {children}
    </AdminBrandingContext.Provider>
  );
}

export function useAdminBranding(): AdminBranding {
  const v = useContext(AdminBrandingContext);
  if (!v) {
    throw new Error("useAdminBranding doit être utilisé sous AdminBrandingProvider.");
  }
  return v;
}
