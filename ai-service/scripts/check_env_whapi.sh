#!/usr/bin/env bash
# Affiche les valeurs Whapi après fusion .env_file + .env (comme au runtime Python).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

echo "=== Whapi / file d'attente — valeurs EFFECTIVES (après fusion) ==="
node -e "
const path = require('path');
const fs = require('fs');

function loadDotEnv(filePath) {
  const out = {};
  if (!fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) return out;
  for (const line of fs.readFileSync(filePath, 'utf8').split(/\r?\n/)) {
    const t = line.trim();
    if (!t || t.startsWith('#')) continue;
    const eq = t.indexOf('=');
    if (eq === -1) continue;
    const k = t.slice(0, eq).trim();
    let v = t.slice(eq + 1).trim();
    const h = v.indexOf(' #');
    if (h !== -1) v = v.slice(0, h).trim();
    if (k) out[k] = v;
  }
  return out;
}

const base = loadDotEnv(path.join(process.cwd(), '.env_file'));
const over = loadDotEnv(path.join(process.cwd(), '.env'));
const m = { ...base, ...over };

const keys = [
  'ENABLE_WHAPI_QUEUE_POLLING',
  'WHAPI_WEBHOOK_PROXY_ONLY',
  'WHAPI_QUEUE_POP_URL',
  'WHAPI_REPLY_RELAY_URL',
  'WHAPI_TOKEN',
  'REDIS_URL',
];

for (const k of keys) {
  const inBase = base[k] !== undefined ? base[k] : '(absent)';
  const inOver = over[k] !== undefined ? over[k] : '(absent)';
  const eff = m[k] !== undefined ? m[k] : '(absent)';
  console.log('--- ' + k + ' ---');
  console.log('  .env_file :', k.includes('TOKEN') && inBase !== '(absent)' ? '(défini)' : inBase);
  console.log('  .env      :', k.includes('TOKEN') && inOver !== '(absent)' ? '(défini)' : inOver);
  console.log('  → EFFECTIF:', k.includes('TOKEN') && eff !== '(absent)' ? '(défini)' : eff);
}

const ok =
  ['1', 'true', 'yes', 'on'].includes(String(m.ENABLE_WHAPI_QUEUE_POLLING || '').toLowerCase()) &&
  ['1', 'true', 'yes', 'on'].includes(String(m.WHAPI_WEBHOOK_PROXY_ONLY || '').toLowerCase()) &&
  String(m.WHAPI_QUEUE_POP_URL || '').startsWith('http') &&
  String(m.WHAPI_REPLY_RELAY_URL || '').startsWith('http');

console.log('');
if (ok) console.log('OK : configuration Whapi cohérente pour VPS tout-en-un.');
else {
  console.log('PROBLÈME : .env sur le VPS écrase probablement .env_file avec false ou URLs vides.');
  console.log('Corrigez .env (voir scripts/env.vps.whapi.snippet) puis ./scripts/pm2_reload_env.sh');
}
"

echo ""
echo "=== Lignes Whapi dans vos fichiers (grep) ==="
grep -nE '^(ENABLE_WHAPI|WHAPI_)' .env_file 2>/dev/null || true
echo "--- .env ---"
grep -nE '^(ENABLE_WHAPI|WHAPI_)' .env 2>/dev/null || echo "(aucune ligne WHAPI dans .env)"
