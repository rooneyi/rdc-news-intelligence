/**
 * PM2 — FastAPI (uvicorn), même service que la doc systemd `rdc-ai-service`.
 *
 * Prérequis :
 * - Être dans le dossier `ai-service` (là où se trouvent `app/` et ce fichier).
 * - Virtualenv Python : par défaut `.env/bin/python` (comme en local). Sinon édite `script` ci‑dessous
 *   (`venv/bin/python`, `.venv/bin/python`, etc.).
 * - Fichier `app/core/config.py` charge `ai-service/.env_file` — à renseigner sur le VPS.
 *
 * Commandes :
 *   cd .../ai-service
 *   pm2 start ecosystem.config.cjs
 *   pm2 save
 *   pm2 startup   # une fois, pour redémarrage au boot
 *
 * Logs PM2 : ./logs/pm2-ai-*.log (dossier logs/ créé si besoin par PM2)
 *
 * Nginx doit faire proxy_pass vers le même port que `APP_PORT` (défaut 8001).
 */
const path = require("path");

const root = __dirname;
const port = process.env.APP_PORT || "8001";

/** Interpréteur Python du venv — adapte si ton venv n’est pas `.env` */
const pythonBin =
  process.env.RDC_AI_PYTHON || path.join(root, ".env", "bin", "python");

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
      },
      error_file: path.join(root, "logs", "pm2-ai-error.log"),
      out_file: path.join(root, "logs", "pm2-ai-out.log"),
      merge_logs: true,
      time: true,
    },
  ],
};
