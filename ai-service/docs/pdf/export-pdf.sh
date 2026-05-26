#!/usr/bin/env bash
# Exporte les markdown du mémoire en PDF (pandoc + wkhtmltopdf).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/pdf"
mkdir -p "$OUT"

export_one() {
  local name="$1"
  local toc="${2:-}"
  local title="${3:-$name}"
  local extra=()
  [[ "$toc" == "toc" ]] && extra+=(--toc --toc-depth=2)
  echo "→ $name.pdf"
  pandoc "$ROOT/${name}.md" -o "$OUT/${name}.pdf" \
    --pdf-engine=wkhtmltopdf \
    --pdf-engine-opt=--enable-local-file-access \
    -V margin-top=20mm -V margin-bottom=20mm -V margin-left=22mm -V margin-right=22mm \
    --metadata title="$title" \
    "${extra[@]}"
}

export_one "Article_Resultats_et_Discussion" toc "RDC News Intelligence — Résultats et discussion"
export_one "SOURCES_SWAHILI_AUDIT" "" "RDC News Intelligence — Corpus anglais et swahili"
export_one "Chapitre_3_Modelisation" toc "RDC News Intelligence — Chapitre III Modélisation"
export_one "Chapitre_4_Deploiement" toc "RDC News Intelligence — Chapitre IV Déploiement"

echo "→ Resultats_Corpus_Multilingue.pdf"
pandoc "$ROOT/Article_Resultats_et_Discussion.md" "$ROOT/SOURCES_SWAHILI_AUDIT.md" \
  -o "$OUT/Resultats_Corpus_Multilingue.pdf" \
  --pdf-engine=wkhtmltopdf \
  --pdf-engine-opt=--enable-local-file-access \
  --toc --toc-depth=2 \
  --metadata title="RDC News Intelligence — Résultats et corpus multilingue"

ls -lh "$OUT"/*.pdf
echo "OK — PDF dans $OUT"
