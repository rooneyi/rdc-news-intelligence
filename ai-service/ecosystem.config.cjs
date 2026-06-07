/**
 * PM2 — FastAPI (uvicorn)
 *
 * Charge automatiquement les variables depuis :
 *   1. `.env_file` (base)
 *   2. `.env` (surcharge VPS — écrase les clés communes)
 * Même logique que `app/core/config.py`.
 *
 * Sur le VPS :
 *   cd .../ai-service
 *   ./scripts/pm2_reload_env.sh
 *
 * Ou manuellement :
 *   source scripts/load_env_production.sh
 *   pm2 restart ecosystem.config.cjs --update-env
 */
const fs = require("fs");
const path = require("path");

const root = __dirname;

function loadDotEnv(filePath) {
  const out = {};
  if (!fs.existsSync(filePath)) {
    return out;
  }
  if (!fs.statSync(filePath).isFile()) {
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

function loadMergedEnv(base) {
  const fromEnvFile = loadDotEnv(path.join(base, ".env_file"));
  const fromDotEnv = loadDotEnv(path.join(base, ".env"));

  const fileOnlyRaw =
    process.env.RDC_ENV_FILE_ONLY ||
    fromDotEnv.RDC_ENV_FILE_ONLY ||
    fromEnvFile.RDC_ENV_FILE_ONLY ||
    "";
  const fileOnly = ["1", "true", "yes", "on"].includes(
    String(fileOnlyRaw).trim().toLowerCase(),
  );

  if (fileOnly) {
    console.error("[ecosystem] Variables : .env_file uniquement (RDC_ENV_FILE_ONLY)");
    return { ...fromEnvFile };
  }

  const merged = { ...fromEnvFile, ...fromDotEnv };
  const sources = [];
  if (Object.keys(fromEnvFile).length) sources.push(".env_file");
  if (Object.keys(fromDotEnv).length) sources.push(".env");
  console.error(
    "[ecosystem] Variables chargées :",
    sources.length ? sources.join(" + ") : "(aucun fichier)",
    `— ${Object.keys(merged).length} clés`,
  );
  return merged;
}

const fileEnv = loadMergedEnv(root);
const port = fileEnv.APP_PORT || process.env.APP_PORT || "8000";

function resolvePythonBin(base) {
  const explicit = process.env.RDC_AI_PYTHON || fileEnv.RDC_AI_PYTHON;
  if (explicit && fs.existsSync(explicit)) {
    return explicit;
  }
  const dirs = ["venv", ".venv"];
  for (const d of dirs) {
    const candidate = path.join(base, d, "bin", "python");
    if (fs.existsSync(candidate)) {
      return candidate;
    }
  }
  console.error(
    "[ecosystem] Aucun Python dans venv/.venv. Crée :\n" +
      `  cd "${base}" && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt`,
  );
  return path.join(base, "venv", "bin", "python");
}

const pythonBin = resolvePythonBin(root);

module.exports = {
  apps: [
    {
      name: "rdc-ai-service",
      cwd: root,
      script: pythonBin,
      args: `-m uvicorn app.main:app --host 0.0.0.0 --port ${port} --workers 1`,
      interpreter: "none",
      instances: 1,
      autorestart: true,
      max_restarts: 30,
      min_uptime: "15s",
      max_memory_restart: "2G",
      env: {
        PYTHONUNBUFFERED: "1",
        ...fileEnv,
        APP_PORT: String(port),
      },
      error_file: path.join(root, "logs", "pm2-ai-error.log"),
      out_file: path.join(root, "logs", "pm2-ai-out.log"),
      merge_logs: true,
      time: true,
    },
  ],
};
