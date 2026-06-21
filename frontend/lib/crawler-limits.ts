/** Fallback si l’API FastAPI ne renvoie pas encore limit_options. */
export const DEFAULT_CRAWL_LIMIT_OPTIONS = [10, 20, 30, 50, 100, 1000, 2000] as const;

export function normalizeCrawlLimitOptions(raw: unknown): number[] {
  if (!Array.isArray(raw)) {
    return [...DEFAULT_CRAWL_LIMIT_OPTIONS];
  }
  const nums = raw
    .map((v) => (typeof v === "number" ? v : Number(v)))
    .filter((n) => Number.isFinite(n) && n > 0);
  return nums.length ? [...new Set(nums)].sort((a, b) => a - b) : [...DEFAULT_CRAWL_LIMIT_OPTIONS];
}
