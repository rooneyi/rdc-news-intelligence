#!/usr/bin/env bash
# Affiche APP_PORT (défaut 8000) sans charger ecosystem.config.cjs (évite pollution stdout).
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
node -e "
const fs = require('fs');
const path = require('path');
const base = process.argv[1];
function load(file) {
  const out = {};
  const p = path.join(base, file);
  if (!fs.existsSync(p)) return out;
  for (const line of fs.readFileSync(p, 'utf8').split(/\\r?\\n/)) {
    const t = line.trim();
    if (!t || t.startsWith('#')) continue;
    const eq = t.indexOf('=');
    if (eq === -1) continue;
    const k = t.slice(0, eq).trim();
    let v = t.slice(eq + 1).trim();
    const hash = v.indexOf(' #');
    if (hash !== -1) v = v.slice(0, hash).trim();
    if ((v.startsWith('\"') && v.endsWith('\"')) || (v.startsWith(\"'\") && v.endsWith(\"'\"))) {
      v = v.slice(1, -1);
    }
    if (k) out[k] = v;
  }
  return out;
}
const merged = { ...load('.env_file'), ...load('.env') };
const port = merged.APP_PORT || '8000';
process.stdout.write(String(port));
" "${ROOT}"
