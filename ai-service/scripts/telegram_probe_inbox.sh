#!/usr/bin/env bash
# Teste si Telegram envoie bien des messages à CE bot (sans conflit 409).
# Arrête PM2 le temps du test pour être le seul client getUpdates.
#
# Usage :
#   1. Lance ce script
#   2. Quand il affiche « Envoie un message… », écris au bot @dcerfrefrebot
#   3. Lis le résultat
#
# Si des messages apparaissent ici mais pas dans pm2 logs → conflit 409 / mauvais mode.
# Si rien n'apparaît → mauvais bot ou message pas envoyé au bon @username.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

TOKEN="$("${ROOT}/scripts/read_env_var.sh" TELEGRAM_BOT_TOKEN)"
if [[ -z "${TOKEN}" ]]; then
  echo "ERREUR : TELEGRAM_BOT_TOKEN absent" >&2
  exit 1
fi

BOT_USER="$(curl -sS "https://api.telegram.org/bot${TOKEN}/getMe" | node -e "
let s='';process.stdin.on('data',d=>s+=d);process.stdin.on('end',()=>{
  try{const j=JSON.parse(s);process.stdout.write(j.result?.username||'?')}catch{process.stdout.write('?')}
})")"

echo "=============================================="
echo "  Probe inbox Telegram — @${BOT_USER}"
echo "=============================================="
echo ""
echo "Arrêt PM2 (seul ce script pollera pendant ~30s)…"
pm2 stop rdc-ai-service 2>/dev/null || true
sleep 2

# Tuer autres pollers connus
pkill -f "scripts/telegram_polling.py" 2>/dev/null || true

echo "Suppression webhook + attente messages (25s)…"
echo ""
echo ">>> ENVOIE MAINTENANT un message au bot @${BOT_USER} sur Telegram <<<"
echo ""

curl -sS "https://api.telegram.org/bot${TOKEN}/deleteWebhook?drop_pending_updates=false" >/dev/null

RESULT="$(curl -sS --max-time 30 "https://api.telegram.org/bot${TOKEN}/getUpdates?timeout=25&limit=5")"
echo "Réponse getUpdates :"
echo "${RESULT}" | head -c 2000
echo ""

if echo "${RESULT}" | grep -q '"ok":false'; then
  echo ""
  echo "ERREUR API — autre machine poll encore ce token (PC local ?)."
  echo "Arrête uvicorn sur ton PC : pkill -f 'uvicorn app.main:app'"
elif echo "${RESULT}" | grep -q '"result":\[\]'; then
  echo ""
  echo "Aucun message reçu — as-tu bien écrit à @${BOT_USER} (pas un autre bot) ?"
elif echo "${RESULT}" | grep -q '"text"'; then
  echo ""
  echo "OK — Telegram a bien reçu ton message. Le VPS peut le traiter."
  echo "Recommandation : passe en mode WEBHOOK (évite les conflits 409) :"
  echo "  ./scripts/fix_telegram.sh --webhook"
else
  echo ""
  echo "Réponse inattendue — voir JSON ci-dessus."
fi

echo ""
echo "Redémarrage PM2…"
pm2 start rdc-ai-service 2>/dev/null || pm2 start ecosystem.config.cjs --update-env
pm2 save 2>/dev/null || true
