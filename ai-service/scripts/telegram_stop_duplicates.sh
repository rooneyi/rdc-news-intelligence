#!/usr/bin/env bash
# Un seul client getUpdates par token Telegram — sinon erreur 409 et aucun message reçu.
#
# Causes fréquentes :
#   - PM2 root + PM2 rooney (deux rdc-ai-service)
#   - uvicorn local (PC) + VPS avec le même TELEGRAM_BOT_TOKEN
#   - scripts/telegram_polling.py lancé en parallèle de PM2
#
# Usage :
#   ./scripts/telegram_stop_duplicates.sh
#   ./scripts/telegram_stop_duplicates.sh --restart
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

RESTART=false
for arg in "$@"; do
  [[ "${arg}" == "--restart" ]] && RESTART=true
done

echo "=============================================="
echo "  Telegram — une seule instance de polling"
echo "=============================================="
echo ""

echo "=== Processus uvicorn / telegram_polling ==="
ps aux 2>/dev/null | grep -E '[u]vicorn app\.main:app|[t]elegram_polling' || echo "(aucun)"
echo ""

echo "=== PM2 utilisateur courant ($(whoami)) ==="
pm2 list 2>/dev/null || true
echo ""

if [[ "$(whoami)" == "root" ]] && id rooney &>/dev/null; then
  echo "=== PM2 utilisateur rooney ==="
  sudo -u rooney pm2 list 2>/dev/null || true
  echo ""
fi

if [[ "$(whoami)" != "root" ]] && command -v sudo &>/dev/null; then
  echo "=== PM2 root (si doublon) ==="
  sudo pm2 list 2>/dev/null | head -15 || echo "(sudo pm2 indisponible)"
  echo ""
fi

echo "=== Arrêt doublons PM2 rdc-ai-service (rooney) ==="
if [[ "$(whoami)" == "root" ]] && id rooney &>/dev/null; then
  sudo -u rooney pm2 delete rdc-ai-service 2>/dev/null || true
  echo "PM2 rooney : rdc-ai-service supprimé (si présent)"
fi

echo ""
echo "=== Arrêt script standalone telegram_polling.py ==="
pkill -f "scripts/telegram_polling.py" 2>/dev/null || true
pkill -f "telegram_polling.py" 2>/dev/null || true

echo ""
echo "=== uvicorn orphelins (hors PM2 actuel) ==="
# Ne tue pas le worker PM2 courant — liste seulement
pgrep -af "uvicorn app.main:app" 2>/dev/null || echo "(aucun uvicorn rdc)"

echo ""
if [[ "${RESTART}" == "true" ]]; then
  echo "=== Redémarrage unique rdc-ai-service (utilisateur courant) ==="
  pm2 delete rdc-ai-service 2>/dev/null || true
  sleep 2
  pm2 start ecosystem.config.cjs --update-env
  pm2 save
  sleep 5
  pm2 logs rdc-ai-service --lines 20 --nostream 2>/dev/null | grep -iE 'TelegramPolling|409|getUpdates' | tail -10 || true
fi

echo ""
echo "IMPORTANT : arrête aussi le FastAPI LOCAL sur ton PC s'il utilise le même TELEGRAM_BOT_TOKEN."
echo "  (uvicorn --reload avec le même token = conflit 409 sur le VPS)"
echo ""
echo "Puis teste : envoie un message au bot @dcerfrefrebot"
echo "  pm2 logs rdc-ai-service --lines 0 | grep -i 'Message texte reçu'"
