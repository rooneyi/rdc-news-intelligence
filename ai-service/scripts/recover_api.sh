#!/usr/bin/env bash
# Remet rdc-ai-service en ligne quand le port 8000 est pris par un autre service (HTML 400)
# ou quand PM2 rooney est vide alors que l'API ne répond pas.
#
# Usage :
#   cd ai-service
#   ./scripts/recover_api.sh           # tente 8000, sinon bascule 8001
#   ./scripts/recover_api.sh --port 8001   # force le port
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="$(cd "${ROOT}/.." && pwd)"
cd "${ROOT}"

FORCE_PORT=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      FORCE_PORT="${2:-}"
      shift 2
      ;;
    --port=*)
      FORCE_PORT="${1#*=}"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

is_fastapi_health() {
  local p="$1"
  local body
  body="$(curl -sS --max-time 4 "http://127.0.0.1:${p}/health" 2>/dev/null || true)"
  echo "${body}" | grep -q '"service"[[:space:]]*:[[:space:]]*"rdc-ai-service"'
}

is_html_impostor() {
  local p="$1"
  curl -sS --max-time 4 "http://127.0.0.1:${p}/health" 2>/dev/null | grep -qi '<!doctype html'
}

kill_port_if_owned() {
  local p="$1"
  if command -v fuser >/dev/null 2>&1; then
    fuser -k "${p}/tcp" 2>/dev/null || return 1
    sleep 2
    return 0
  fi
  return 1
}

fix_starlette_venv() {
  local site="${ROOT}/venv/lib/python3.11/site-packages"
  if compgen -G "${site}/~tarlette*" >/dev/null 2>&1; then
    echo "=== Nettoyage pip corrompu (~tarlette) ==="
    rm -rf "${site}"/~tarlette*
    "${ROOT}/venv/bin/pip" install --force-reinstall 'starlette>=0.40.0,<1.0.0'
  fi
}

update_frontend_fastapi_url() {
  local p="$1"
  local fe="${REPO}/frontend/.env.local"
  mkdir -p "$(dirname "${fe}")"
  touch "${fe}"
  for key in FASTAPI_URL NEXT_PUBLIC_FASTAPI_URL; do
    if grep -q "^${key}=" "${fe}" 2>/dev/null; then
      sed -i "s|^${key}=.*|${key}=http://127.0.0.1:${p}|" "${fe}"
    else
      echo "${key}=http://127.0.0.1:${p}" >> "${fe}"
    fi
  done
  echo "frontend/.env.local → http://127.0.0.1:${p}"
}

set_app_port() {
  local p="$1"
  local env_file="${ROOT}/.env"
  touch "${env_file}"
  set_kv() {
    local key="$1"
    local val="$2"
    if grep -q "^${key}=" "${env_file}" 2>/dev/null; then
      sed -i "s|^${key}=.*|${key}=${val}|" "${env_file}"
    else
      echo "${key}=${val}" >> "${env_file}"
    fi
  }
  set_kv "APP_PORT" "${p}"
  set_kv "WHAPI_QUEUE_POP_URL" "http://127.0.0.1:${p}/webhooks/whapi/queue/pop"
  set_kv "WHAPI_REPLY_RELAY_URL" "http://127.0.0.1:${p}/webhooks/whapi/reply-relay"
  set_kv "WHATSAPP_QUEUE_POP_URL" "http://127.0.0.1:${p}/webhooks/whatsapp/queue/pop"
  set_kv "WHATSAPP_REPLY_RELAY_URL" "http://127.0.0.1:${p}/webhooks/whatsapp/reply-relay"
  set_kv "CRAWLER_BACKEND_ENDPOINT" "http://127.0.0.1:${p}"
  set_kv "BACKEND_ENDPOINT" "http://127.0.0.1:${p}"
  echo "ai-service/.env → APP_PORT=${p}"
}

PORT="${FORCE_PORT:-$("${ROOT}/scripts/read_app_port.sh")}"

echo "=============================================="
echo "  recover_api — port cible ${PORT}"
echo "=============================================="

echo ""
echo "=== PM2 (utilisateur $(whoami)) ==="
pm2 list 2>/dev/null || true
if command -v sudo >/dev/null 2>&1 && sudo -n pm2 list 2>/dev/null | grep -q rdc-ai; then
  echo ""
  echo "NOTE : rdc-ai-service tourne peut-être sous PM2 root."
  echo "  sudo pm2 list"
  echo "  sudo pm2 delete rdc-ai-service   # si doublon / crash"
fi

echo ""
if is_fastapi_health "${PORT}"; then
  echo "FastAPI OK déjà sur :${PORT} — relance PM2 seulement."
  fix_starlette_venv
  exec "${ROOT}/scripts/pm2_reload_env.sh"
fi

if ss -tln 2>/dev/null | grep -q ":${PORT} "; then
  echo "=== Port ${PORT} occupé ==="
  "${ROOT}/scripts/show_port_listener.sh" "${PORT}"
  if is_html_impostor "${PORT}"; then
    echo ""
    echo "→ Page HTML sur /health : ce n'est PAS rdc-ai-service (souvent Django/Gunicorn)."
  fi
  echo ""
  echo "=== Tentative libération (processus de ton utilisateur uniquement) ==="
  if kill_port_if_owned "${PORT}" && ! ss -tln 2>/dev/null | grep -q ":${PORT} "; then
    echo "Port ${PORT} libéré."
  else
    ALT=8001
    [[ "${PORT}" == "8001" ]] && ALT=8002
    if [[ -n "${FORCE_PORT}" ]]; then
      echo ""
      echo "ERREUR : impossible de libérer :${PORT} sans sudo." >&2
      echo "  sudo ss -tlnp | grep :${PORT}" >&2
      echo "  sudo fuser -k ${PORT}/tcp" >&2
      echo "  puis ./scripts/pm2_reload_env.sh" >&2
      exit 1
    fi
    if ss -tln 2>/dev/null | grep -q ":${ALT} "; then
      ALT=8002
    fi
    echo ""
    echo "Port ${PORT} toujours pris — bascule automatique vers ${ALT}."
    set_app_port "${ALT}"
    PORT="${ALT}"
    update_frontend_fastapi_url "${PORT}"
  fi
fi

fix_starlette_venv

echo ""
echo "=== Démarrage PM2 rdc-ai-service (port ${PORT}) ==="
if pm2 describe rdc-ai-service &>/dev/null; then
  pm2 delete rdc-ai-service 2>/dev/null || true
  sleep 1
fi
pm2 start ecosystem.config.cjs --update-env
pm2 save

echo ""
echo "=== Attente /health (max 30s) ==="
ok=false
for i in $(seq 1 6); do
  sleep 5
  if is_fastapi_health "${PORT}"; then
    curl -sS "http://127.0.0.1:${PORT}/health"
    echo ""
    ok=true
    break
  fi
  echo "  … ${i}/6"
done

if [[ "${ok}" != "true" ]]; then
  echo "ERREUR : FastAPI ne répond pas sur :${PORT}" >&2
  pm2 logs rdc-ai-service --lines 25 --nostream 2>/dev/null | tail -25 || true
  exit 1
fi

update_frontend_fastapi_url "${PORT}"

if [[ -f "${REPO}/frontend/ecosystem.config.cjs" ]]; then
  echo ""
  echo "=== Redémarrage rdc-frontend ==="
  cd "${REPO}/frontend"
  if pm2 describe rdc-frontend &>/dev/null; then
    pm2 restart ecosystem.config.cjs --update-env
  else
    pm2 start ecosystem.config.cjs
  fi
  pm2 save
fi

echo ""
echo "OK — API : http://127.0.0.1:${PORT}/health"
if [[ "${PORT}" != "8000" ]]; then
  echo ""
  echo "IMPORTANT : nginx/Hestia proxy /health et /webhooks/ → 127.0.0.1:${PORT}"
fi
pm2 list
