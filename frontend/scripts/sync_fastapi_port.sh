#!/usr/bin/env bash
# Aligne frontend/.env.local sur APP_PORT de ai-service, rebuild Next, redémarre PM2.
#
# Usage (VPS) :
#   cd frontend
#   ./scripts/sync_fastapi_port.sh
#   ./scripts/sync_fastapi_port.sh --no-build   # seulement .env.local + pm2 restart
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AI="${ROOT}/../ai-service"
cd "${ROOT}"

PORT="8001"
if [[ -x "${AI}/scripts/read_app_port.sh" ]]; then
  PORT="$("${AI}/scripts/read_app_port.sh")"
fi

NO_BUILD=false
for arg in "$@"; do
  [[ "${arg}" == "--no-build" ]] && NO_BUILD=true
done

ENV_FILE="${ROOT}/.env.local"
touch "${ENV_FILE}"
BASE="http://127.0.0.1:${PORT}"

set_kv() {
  local key="$1"
  local val="$2"
  if grep -q "^${key}=" "${ENV_FILE}" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" "${ENV_FILE}"
  else
    echo "${key}=${val}" >> "${ENV_FILE}"
  fi
}

echo "=== Sync FastAPI → ${BASE} ==="
set_kv "FASTAPI_URL" "${BASE}"
set_kv "NEXT_PUBLIC_FASTAPI_URL" "${BASE}"
grep -E '^(FASTAPI_URL|NEXT_PUBLIC_FASTAPI_URL)=' "${ENV_FILE}"

if [[ "${NO_BUILD}" != "true" ]]; then
  if [[ ! -f "${ROOT}/.next/BUILD_ID" ]] || [[ "${ROOT}/lib/fastapi-upstream.ts" -nt "${ROOT}/.next/BUILD_ID" ]]; then
    echo ""
    echo "=== npm run build (NEXT_PUBLIC_* figé au build) ==="
    npm run build
  else
    echo ""
    echo "=== Build existant — pour forcer : npm run build ==="
  fi
fi

echo ""
echo "=== PM2 rdc-frontend ==="
if pm2 describe rdc-frontend &>/dev/null; then
  pm2 restart ecosystem.config.cjs --update-env
else
  pm2 start ecosystem.config.cjs --update-env
fi
pm2 save

echo ""
echo "=== Test proxy admin (nécessite session admin dans le navigateur) ==="
echo "curl -s ${BASE}/health"
curl -sS --max-time 10 "${BASE}/health" | head -c 200
echo ""
echo ""
echo "OK — frontend → ${BASE}"
