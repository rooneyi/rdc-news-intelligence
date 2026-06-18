#!/usr/bin/env bash
# PM2 + services au reboot VPS + conseils swap.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== PM2 startup (utilisateur $(whoami)) ==="
pm2 save
pm2 startup systemd -u "$(whoami)" --hp "$HOME" || pm2 startup

echo ""
echo "Exécute la commande « sudo env PATH=... » affichée ci-dessus si PM2 l'a demandée."
echo ""

echo "=== Services système au boot ==="
for svc in ollama postgresql redis-server; do
  if systemctl list-unit-files "$svc.service" &>/dev/null 2>&1; then
    sudo systemctl enable "$svc" 2>/dev/null || systemctl enable "$svc" 2>/dev/null || true
    sudo systemctl start "$svc" 2>/dev/null || systemctl start "$svc" 2>/dev/null || true
    echo "  $svc : enable + start"
  fi
done

echo ""
echo "=== Redémarrage apps ==="
cd "${ROOT}"
if pm2 describe rdc-ai-service &>/dev/null; then
  pm2 restart ecosystem.config.cjs --update-env
else
  pm2 start ecosystem.config.cjs --update-env
fi

FE="${ROOT}/../frontend"
if [[ -f "${FE}/ecosystem.config.cjs" ]]; then
  cd "${FE}"
  if pm2 describe rdc-frontend &>/dev/null; then
    pm2 restart ecosystem.config.cjs --update-env
  else
    pm2 start ecosystem.config.cjs
  fi
fi

pm2 save
pm2 list

echo ""
echo "=== Swap (recommandé si RAM ≤ 8 Go) ==="
if swapon --show 2>/dev/null | grep -q .; then
  swapon --show
else
  echo "Pas de swap. Pour en créer 4 Go (une fois, en root) :"
  echo "  sudo fallocate -l 4G /swapfile"
  echo "  sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile"
  echo "  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab"
fi
