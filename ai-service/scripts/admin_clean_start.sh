#!/usr/bin/env bash
# Nettoyage VPS : libère le port FastAPI, arrête les processus parasites, relance rdc-ai-service.
# À lancer en admin (sudo pour fuser/lsof si besoin).
#
# Usage :
#   cd ~/web/rooney-rdc.rooneykalumba.tech/public_html/rdc-news-intelligence/ai-service
#   ./scripts/admin_clean_start.sh
#   ./scripts/admin_clean_start.sh --with-frontend   # relance aussi rdc-frontend

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "${ROOT}/.." && pwd)"
cd "${ROOT}"

WITH_FRONTEND=false
for arg in "$@"; do
  if [[ "${arg}" == "--with-frontend" ]]; then
    WITH_FRONTEND=true
  fi
done

PORT="$("${ROOT}/scripts/read_app_port.sh")"

echo "=============================================="
echo "  RDC — nettoyage port ${PORT} + redémarrage API"
echo "=============================================="

echo ""
echo "=== 1. Écoute sur le port ${PORT} (avant) ==="
ss -tln 2>/dev/null | grep ":${PORT} " || echo "(libre)"
if command -v lsof >/dev/null 2>&1; then
  sudo lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null || lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null || true
fi
if command -v fuser >/dev/null 2>&1; then
  sudo fuser -v "${PORT}/tcp" 2>/dev/null || fuser -v "${PORT}/tcp" 2>/dev/null || true
fi

echo ""
echo "=== 2. Arrêt PM2 rdc-ai-service (seulement) ==="
pm2 stop rdc-ai-service 2>/dev/null || true
pm2 delete rdc-ai-service 2>/dev/null || true
sleep 2

echo ""
echo "=== 3. Libération port ${PORT} (tout sauf ce qu'on relance après) ==="
# uvicorn / gunicorn / python orphelins sur ce port
pkill -f "uvicorn app.main:app.*--port ${PORT}" 2>/dev/null || true
pkill -f "gunicorn.*:${PORT}" 2>/dev/null || true
if command -v fuser >/dev/null 2>&1; then
  sudo fuser -k "${PORT}/tcp" 2>/dev/null || fuser -k "${PORT}/tcp" 2>/dev/null || true
fi
sleep 2

if ss -tln 2>/dev/null | grep -q ":${PORT} "; then
  echo ""
  echo "ERREUR : le port ${PORT} est ENCORE occupé :" >&2
  sudo lsof -nP -iTCP:"${PORT}" -sTCP:LISTEN 2>/dev/null || ss -tlnp | grep ":${PORT} " || true
  echo "" >&2
  echo "Tue manuellement le PID affiché ci-dessus :" >&2
  echo "  sudo kill -9 <PID>" >&2
  echo "Ou bascule de port : ./scripts/switch_fastapi_port.sh 8001" >&2
  exit 1
fi
echo "Port ${PORT} libre."

echo ""
echo "=== 4. Démarrage rdc-ai-service (PM2) ==="
pm2 start ecosystem.config.cjs --update-env
pm2 save

echo ""
echo "=== 5. Attente health (max 30s) ==="
ok=false
for i in $(seq 1 6); do
  sleep 5
  body="$(curl -sS --max-time 4 "http://127.0.0.1:${PORT}/health" 2>/dev/null || true)"
  if echo "${body}" | grep -q '"service"[[:space:]]*:[[:space:]]*"rdc-ai-service"'; then
    echo "${body}"
    ok=true
    break
  fi
  echo "  … tentative ${i}/6"
done

if [[ "${ok}" != "true" ]]; then
  echo "ERREUR : FastAPI ne répond pas sur :${PORT}/health" >&2
  pm2 logs rdc-ai-service --lines 30 --nostream 2>/dev/null | tail -30 || true
  exit 1
fi

echo ""
echo "=== 6. Test Whapi queue/pop ==="
TOKEN="$("${ROOT}/scripts/read_env_var.sh" WHAPI_QUEUE_TOKEN)"
[[ -z "${TOKEN}" ]] && TOKEN="$("${ROOT}/scripts/read_env_var.sh" WHATSAPP_QUEUE_TOKEN)"
ARGS=(-sS -X POST "http://127.0.0.1:${PORT}/webhooks/whapi/queue/pop" -H "Content-Type: application/json" -d '{}')
[[ -n "${TOKEN}" ]] && ARGS+=(-H "X-RDC-Queue-Token: ${TOKEN}")
curl "${ARGS[@]}"
echo ""

if [[ "${WITH_FRONTEND}" == "true" && -f "${REPO}/frontend/ecosystem.config.cjs" ]]; then
  echo ""
  echo "=== 7. Redémarrage rdc-frontend ==="
  pm2 restart rdc-frontend 2>/dev/null || pm2 start "${REPO}/frontend/ecosystem.config.cjs"
  pm2 save
fi

echo ""
echo "=== PM2 ==="
pm2 list
echo ""
echo "OK — API opérationnelle sur http://127.0.0.1:${PORT}"
