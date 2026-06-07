#!/usr/bin/env bash
# Libère le port 3000 et démarre rdc-frontend sous PM2.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"
PORT="${PORT:-3000}"

echo "=== Port ${PORT} ==="
ss -tln 2>/dev/null | grep ":${PORT} " || echo "(libre)"
if command -v fuser >/dev/null 2>&1; then
  sudo fuser -v "${PORT}/tcp" 2>/dev/null || fuser -v "${PORT}/tcp" 2>/dev/null || true
fi

if [[ ! -f "${ROOT}/.next/BUILD_ID" ]]; then
  echo "ERREUR : build manquant. Lance : npm run build" >&2
  exit 1
fi

echo ""
echo "=== Arrêt PM2 rdc-frontend ==="
pm2 delete rdc-frontend 2>/dev/null || pm2 stop rdc-frontend 2>/dev/null || true
sleep 1

echo ""
echo "=== Libération port ${PORT} ==="
if command -v fuser >/dev/null 2>&1; then
  sudo fuser -k "${PORT}/tcp" 2>/dev/null || fuser -k "${PORT}/tcp" 2>/dev/null || true
fi
pkill -f "next start.*-p ${PORT}" 2>/dev/null || true
pkill -f "next-server.*${PORT}" 2>/dev/null || true
sleep 2

mkdir -p "${ROOT}/logs"
pm2 start ecosystem.config.cjs
pm2 save

echo ""
sleep 3
pm2 list
curl -sI "http://127.0.0.1:${PORT}/" | head -3
echo ""
pm2 logs rdc-frontend --lines 15 --nostream 2>/dev/null | tail -15 || true
