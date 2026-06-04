/**
 * PM2 — Next.js (production)
 *
 * Prérequis :
 *   cd frontend && npm ci && npm run build
 *   cp .env.production.example .env.local  # adapter
 *
 * Sur le VPS :
 *   pm2 start ecosystem.config.cjs
 *   pm2 save
 */
const path = require("path");

const root = __dirname;
const port = process.env.PORT || "3000";

module.exports = {
  apps: [
    {
      name: "rdc-frontend",
      cwd: root,
      script: "npm",
      args: `start -- -p ${port}`,
      interpreter: "none",
      instances: 1,
      autorestart: true,
      max_restarts: 20,
      min_uptime: "10s",
      env: {
        NODE_ENV: "production",
        PORT: String(port),
      },
      error_file: path.join(root, "logs", "pm2-frontend-error.log"),
      out_file: path.join(root, "logs", "pm2-frontend-out.log"),
      merge_logs: true,
      time: true,
    },
  ],
};
