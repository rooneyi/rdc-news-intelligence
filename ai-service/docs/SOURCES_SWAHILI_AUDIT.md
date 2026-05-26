# Sources swahili et anglaises — corpus RDC News Intelligence

| Date | 2026-05-26 |
| **Objectif** | Constituer un corpus multilingue (FR majoritaire, EN et SW en extension) |

---

## 1. Synthèse du corpus (après rééquilibrage)

| Langue | Articles | Part du corpus | Sources actives (catalogue `sourceLang`) |
|--------|----------|----------------|------------------------------------------|
| **Français** | ~12 350 | ~94 % | Médias RDC + RFI, France 24, etc. |
| **Anglais** | **642** | **~4,9 %** | BBC world/africa, Guardian, VOA, DW, WHO, etc. |
| **Swahili** | **167** | **~1,3 %** | VOA SW, BBC SW, DW SW×2, RFI SW |
| **Total** | **13 163** | 100 % | Chroma aligné (**100 %** couverture) |

Le catalogue `sources.json` a été **nettoyé** : **17** entrées francophones sans aucun article en base ont été retirées ; **5** flux anglais et **1** flux swahili (RFI) ont été ajoutés.

---

## 2. Sources swahili intégrées

| `sourceId` | URL / flux | Articles (approx.) |
|------------|------------|-------------------|
| `bbc.com-swahili` | RSS `feeds.bbci.co.uk/swahili` | 48 |
| `voaswahili.com` | Page d’accueil `/a/*.html` | 42 |
| `dw.com-sw-kiswahili` | Rubrique Kiswahili DW | 40 |
| `rfi.fr-swahili` | RSS `rfi.fr/sw/rss` | 24 |
| `dw.com-sw-congo` | Section RDC (SW) | 13 |

**Commandes crawl :**

```bash
cd ai-service && source venv/bin/activate
for s in voaswahili.com bbc.com-swahili dw.com-sw-congo dw.com-sw-kiswahili rfi.fr-swahili; do
  python -m app.services.crawler.scripts.sync --source-id "$s" --limit 80
done
```

---

## 3. Sources anglaises (ajouts récents)

| `sourceId` | Flux | Articles (approx.) |
|------------|------|-------------------|
| `bbc.com-africa-en` | BBC Africa RSS | 23+ |
| `theguardian.com-africa-en` | Guardian `/world/africa/rss` | 20+ |
| `dw.com-en-africa` | DW English Africa | 5+ |
| *(existants, `sourceLang: en`)* | `bbc-world`, `theguardian.com`, `voanews.com`, `dw.com-world`, … | voir admin |

---

## 4. Sources écartées ou retirées du catalogue

| Cas | Exemple |
|-----|---------|
| **0 article en BDD** | `actualite.cd`, `tf1info.fr`, `lemonde.fr`, … (**17** retirées) |
| **Nom « Habari » mais FR** | `habarirdc.net` (conservé, langue française) |
| **RSS indisponible** | Radio Okapi `/sw` (410) |
| **Crawl ONG sans corps** | `un.org-africa-en` (retiré si 0 article après test) |

Rééquilibrage automatique :

```bash
python scripts/rebalance_sources_catalog.py
```

---

## 5. Pistes d’enrichissement

- Porter `articles.lang` en base pour filtrer le retrieval par langue.
- Augmenter le volume SW (objectif **500+** articles) via crawl récurrent sur les 5 flux.
- OCR : `tesseract-ocr-swa` pour images WhatsApp en kiswahili.

---

*Voir [`Article_Resultats_et_Discussion.md`](Article_Resultats_et_Discussion.md).*
