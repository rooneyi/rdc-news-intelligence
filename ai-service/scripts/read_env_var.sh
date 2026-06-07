#!/usr/bin/env bash
# Lit une variable fusionnée (.env_file + .env). Usage: ./scripts/read_env_var.sh WHAPI_TOKEN
set -euo pipefail
KEY="${1:?nom de variable requis}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
node -e "
const fs = require('fs');
const path = require('path');
const key = process.argv[1];
const base = process.argv[2];
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
process.stdout.write(merged[key] ?? '');
" "${KEY}" "${ROOT}"
