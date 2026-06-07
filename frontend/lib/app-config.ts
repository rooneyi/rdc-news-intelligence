/** Nom affiché dans l'UI (build + runtime). */
export function getAppDisplayName(): string {
  return process.env.NEXT_PUBLIC_APP_NAME?.trim() || "RDC News Intelligence";
}
