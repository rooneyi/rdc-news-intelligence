/**
 * PM2 — Next.js (production)
 *
 * Charge `.env.local` dans l'environnement PM2 (FASTAPI_URL, ADMIN_*, etc.).
 *
 * Prérequis :
 *   cd frontend && npm ci && npm run build
 *   cp .env.production.example .env.local  # adapter
 *
 * Sur le VPS :
 *   ./scripts/pm2_clean_start.sh
 */
const fs = require("fs");
const path = require("path");

const root = __dirname;

function loadDotEnv(filePath) {
  const out = {};
  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    return out;
  }
  const raw = fs.readFileSync(filePath, "utf8");
  for (const line of raw.split(/\r?\n/)) {
    let trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) {
      continue;
    }
    const eq = trimmed.indexOf("=");
    if (eq === -1) {
      continue;
    }
    const key = trimmed.slice(0, eq).trim();
    let val = trimmed.slice(eq + 1).trim();
    const hash = val.indexOf(" #");
    if (hash !== -1) {
      val = val.slice(0, hash).trim();
    }
    if (
      (val.startsWith('"') && val.endsWith('"')) ||
      (val.startsWith("'") && val.endsWith("'"))
    ) {
      val = val.slice(1, -1);
    }
    if (key) {
      out[key] = val;
    }
  }
  return out;
}

const fileEnv = loadDotEnv(path.join(root, ".env.local"));
const port = fileEnv.PORT || process.env.PORT || "3000";
const nextBin = path.join(root, "node_modules", ".bin", "next");

if (!fs.existsSync(path.join(root, ".next", "BUILD_ID"))) {
  console.error(
    "[ecosystem] .next/BUILD_ID absent — lance d'abord : npm run build",
  );
}

if (Object.keys(fileEnv).length) {
  console.error(
    `[ecosystem] .env.local chargé — ${Object.keys(fileEnv).length} clés`,
  );
} else {
  console.error(
    "[ecosystem] .env.local absent — crée-le avec FASTAPI_URL=http://127.0.0.1:8000",
  );
}

module.exports = {
  apps: [
    {
      name: "rdc-frontend",
      cwd: root,
      script: fs.existsSync(nextBin) ? nextBin : "npx",
      args: fs.existsSync(nextBin) ? `start -p ${port}` : `next start -p ${port}`,
      interpreter: "none",
      instances: 1,
      autorestart: true,
      max_restarts: 20,
      min_uptime: "10s",
      env: {
        NODE_ENV: "production",
        PORT: String(port),
        ...fileEnv,
      },
      error_file: path.join(root, "logs", "pm2-frontend-error.log"),
      out_file: path.join(root, "logs", "pm2-frontend-out.log"),
      merge_logs: true,
      time: true,
    },
  ],
};
