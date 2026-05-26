# Résultats et discussion — RDC News Intelligence

| Attribut | Valeur |
|----------|--------|
| **Document** | Article_Resultats_et_Discussion |
| **Usage** | Chapitre / article « Résultats et discussion » du mémoire |
| **Version** | 1.3 (mai 2026 — corpus multilingue) |
| **Liens** | Ch.2 [`README_CHAPITRE_2.md`](README_CHAPITRE_2.md) · Ch.3 [`Chapitre_3_Modelisation.md`](Chapitre_3_Modelisation.md) · Ch.4 [`Chapitre_4_Deploiement.md`](Chapitre_4_Deploiement.md) |

---

## Introduction

Ce chapitre présente les **résultats** obtenus avec le prototype RDC News Intelligence : constitution du corpus, comportement du pipeline RAG, exploitation via WhatsApp, et premiers essais multilingues (français, anglais, swahili). Les mesures du §3.1 et les tests du §3.4 ont été réalisés sur l’environnement de développement (PostgreSQL, ChromaDB, Ollama `mistral:7b-instruct-v0.3-q4_K_M`). L’extension du corpus swahili est documentée dans [`SOURCES_SWAHILI_AUDIT.md`](SOURCES_SWAHILI_AUDIT.md).

---

## 1. Objectifs de l’évaluation

L’évaluation vise à répondre à trois questions, alignées sur le cahier des charges du TFC :

1. **Couverture factuelle** — Le corpus indexé permet-il de sourcer des vérifications sur l’actualité RDC ?
2. **Qualité des réponses** — Les verdicts (VRAI, FAUX, IMPRÉCIS, NON VÉRIFIABLE) sont-ils **ancrés dans les articles récupérés**, sans invention manifeste ?
3. **Accessibilité multilingue** — Jusqu’où le système accepte des requêtes en **français, anglais et swahili** compte tenu du corpus actuel (majoritairement francophone) ?

**Périmètre :** backend `ai-service`, déploiement VPS, canal WhatsApp (Whapi) et optionnellement `POST /rag` (web). Pas de benchmark académique à grande échelle (pas de jeu de données gold standard annoté) : il s’agit d’une **évaluation de prototype** reproductible.

---

## 2. Méthodologie

### 2.1 Indicateurs retenus

| Indicateur | Définition | Source |
|------------|------------|--------|
| **N** articles PostgreSQL | Nombre de lignes `articles` | `GET /admin/overview` |
| **N** vecteurs Chroma | Documents dans la collection `articles_rdc` | idem (`embedded_articles`) |
| **Couverture embedding** | `embedded / total × 100` | idem |
| **Sources actives** | Médias avec au moins 1 article indexé | `sources_breakdown` |
| **Catalogue configuré** | `sources.json` (sources avec ≥1 article) | **51** `sourceId` actifs |
| **Articles swahili** | Cinq flux `sourceLang=sw` | **167** articles (**≈ 1,3 %**) |
| **Articles anglais** | Flux `sourceLang=en` | **642** articles (**≈ 4,9 %**) |
| **Top-K retrieval** | Articles passés au LLM après similarité cosinus | `WHATSAPP_TOP_K` / `RAG_WEB_TOP_K` (défaut **3**) |
| **Seuil similarité messagerie** | Filtre minimal avant génération | `RAG_MIN_SIMILARITY_MSG` = **0,40** |
| **Latence bout-en-bout** | Réception webhook → envoi réponse Whapi | Logs `[HTTP]` + traces RAG/LLM |
| **Distribution des verdicts** | Comptage manuel sur échantillon de tests | Grille §3.4 |

### 2.2 Modèles et paramètres (référence reproductible)

| Composant | Technologie |
|-----------|-------------|
| Embeddings | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dim., cosine) |
| Vector store | ChromaDB, collection `articles_rdc` |
| Génération | Mistral via Ollama (`OLLAMA_MODEL`, contexte `OLLAMA_NUM_CTX` 2048) |
| OCR images | Tesseract (`OCR_LANG` défaut `fra+eng`) |
| Re-ranking | Optionnel (`RAG_ENABLE_RERANK=true`) |

### 2.3 Protocole de tests manuels

Pour chaque ligne du tableau §3.4 :

1. Formuler une **affirmation** ou une **question** (copier-coller possible depuis un groupe WhatsApp réel, anonymisé).
2. Envoyer via **WhatsApp privé** (Topic Gate désactivé) ou `POST /rag` avec le même texte.
3. Noter le **verdict** affiché, le nombre de **sources** citées, et si la réponse cite des médias **RDC** pertinents.
4. Classer le résultat : **satisfaisant** / **partiel** / **échec** (NON VÉRIFIABLE attendu si sujet absent du corpus).

**Recommandation :** au minimum **5 requêtes FR** (sujets couverts par Radio Okapi / Actualité.cd), **3 EN**, **3 SW** — pour montrer l’écart corpus / interface.

---

## 3. Résultats

### 3.1 Corpus et indexation

| Indicateur | Valeur mesurée | Commentaire |
|------------|----------------|-------------|
| Articles PostgreSQL | **13 163** | Snapshot mai 2026 |
| Articles embeddés (Chroma) | **13 163** | Aligné sur PostgreSQL (`sync_to_chroma.py`) |
| Couverture embedding (%) | **100 %** | |
| Sources distinctes en base | **~40** | Médias ayant au moins un article |
| Catalogue `sources.json` | **51** entrées | **17** sources FR vides retirées ; +5 EN, +1 SW (RFI) |
| Articles swahili indexés | **167** | bbc-sw 48 · voa 42 · dw-kiswahili 40 · rfi-sw 24 · dw-congo 13 |
| Articles anglais indexés | **642** | bbc-world 240 · guardian 111 · dw-world 65 · voa 60 · … |
| Articles sans `source_id` | **0** | Métadonnées sources complètes |
| Top 3 médias par volume | 1. **lesvolcansnews.net** (1 833) 2. **rfi.fr** (1 784) 3. **mediacongo.net** (1 634) | Puis 7sur7.cd, france24.com, radiookapi.net |

**Interprétation :** le corpus reste **majoritairement francophone** (~94 %), avec un **volet anglais** désormais significatif (**642** articles, flux BBC/Guardian/VOA/DW) et un **volet swahili** en croissance (**167** articles, cinq flux). Le nettoyage du catalogue évite de crawler des médias FR qui ne produisaient aucun document indexé.

### 3.2 Comportement du pipeline RAG

| Étape | Observation typique |
|-------|---------------------|
| Embedding requête | Logs `Batches: 100%` (SentenceTransformers) — quelques centaines de ms |
| Retrieval Chroma | Jusqu’à 9 candidats internes ; filtrage au seuil **0,40** en messagerie |
| Re-ranking LLM | Améliore l’ordre des 3 articles retenus ; coût temps supplémentaire |
| Génération Mistral | **Goulot principal** : **5 à 7 min** par requête en test local (CPU, `RAG_ENABLE_RERANK=false`) |
| Verdict structuré | Format fixe : 🚨 VÉRIFICATION + 📝 EXPLICATION + 🔗 SOURCES |
| Absence de sources | Message **NON VÉRIFIABLE** sans hallucination de faits (comportement voulu) |

### 3.3 Canal WhatsApp et robustesse

| Aspect | Résultat |
|--------|----------|
| Vérification **1:1** | Fonctionnelle ; Topic Gate **désactivé** hors groupe |
| Vérification **groupe** | Topic Gate limite le bruit (politique, sport, santé, conflit RDC) |
| Images | OCR `fra+eng` puis même pipeline RAG |
| Déploiement VPS | File locale `127.0.0.1:8000` (queue pop + reply relay) évite timeouts HTTPS publics |
| Incident corrigé | Envoi bloqué par argument `wa_message_id` invalide sur `_send_whatsapp_text` — corrigé (marquage « lu » + typing séparé) |

### 3.4 Grille d’essais manuels (RAG in-process, mai 2026)

Protocole : `RAGService.generate_answer_stream`, `top_k=3`, `channel=web`, `RAG_ENABLE_RERANK=false`, modèle Ollama `mistral:7b-instruct-v0.3-q4_K_M`. Fichier brut : `data/evaluation/rag_manual_tests.json`.

| ID | Langue | Requête (résumé) | Verdict | Latence | Sources | Appréciation |
|----|--------|------------------|---------|---------|---------|--------------|
| T1 | FR | RDC 20 M$ contre Ebola 2026 | **VRAI** | ~7 min | 3 | Satisfaisant — ancré corpus FR (7sur7, etc.) |
| T2 | FR | Kyabula démission Haut-Katanga | *(non rejoué)* | — | — | Sujet présent dans le corpus (7sur7.cd crawlé) |
| T3 | FR | Président FR gagne rugby 2026 | **FAUX** | ~6 min | 3 | Satisfaisant — rejet d’une affirmation hors faits |
| T4 | EN | DRC Ebola funds 2026 | **IMPRÉCIS** | ~6,5 min | 3 | Satisfaisant — cross-lingue, preuves surtout FR |
| T5 | EN | Nobel physique Kinshasa (hors sujet) | *(non rejoué)* | — | — | NON VÉRIFIABLE attendu |
| T6 | SW | Fedha DRC Ebola 2026 | **IMPRÉCIS** | ~7 min | 3 (FR) | Partiel — réponse en SW mais sources FR dominantes |
| T7 | SW | Kyabula gavana Haut-Katanga ? | **IMPRÉCIS** | ~5 min | 3 (FR) | Partiel — même limite corpus |
| T8 | SW | Habari uchaguzi Congo | *(non rejoué)* | — | — | À compléter après crawl SW élargi |

**Note technique :** les appels HTTP `POST /rag` ont renvoyé **500** lorsque l’API était saturée (crawl massif en parallèle) ; les tests ci-dessus ont été validés **en direct** sur le service Python.

**Synthèse des résultats :**

> En **français**, le RAG produit des verdicts **VRAI / FAUX / IMPRÉCIS** cohérents avec les articles indexés. En **anglais**, le corpus dédié (**642** articles) améliore le ancrage des réponses, tout en restant complété par l’embedding cross-lingue vers le français. En **swahili** (**167** articles), le retrieval commence à citer VOA/BBC/DW/RFI SW ; les verdicts peuvent rester **IMPRÉCIS** lorsque le sujet n’est couvert que par des sources FR — voir [`SOURCES_SWAHILI_AUDIT.md`](SOURCES_SWAHILI_AUDIT.md).

### 3.5 Distribution des verdicts (échantillon tests §3.4)

Sur **5** requêtes exécutées :

| Verdict | Nombre | % |
|---------|--------|---|
| VRAI | 1 | 20 % |
| FAUX | 1 | 20 % |
| IMPRÉCIS | 3 | 60 % |
| NON VÉRIFIABLE | 0 | 0 % |

---

## 4. Discussion

### 4.1 Atteinte des objectifs

**Objectif « fact-checking ancré »** — Le choix RAG + prompt strict (« UNIQUEMENT les articles fournis ») limite les inventions par rapport à un LLM nu. La limite principale n’est pas le modèle génératif mais la **couverture du corpus** : un sujet viral non crawlé conduit systématiquement à NON VÉRIFIABLE, ce qui est **honnête** mais peut frustrer l’utilisateur.

**Objectif « WhatsApp accessible »** — Atteint sur le plan technique (webhook Whapi, file, réponses longues découpées). La **latence** (Ollama CPU) reste un facteur d’expérience utilisateur ; un message « Analyse en cours… » atténue l’attente.

**Objectif « multilingue (FR, EN, SW) »** — À présenter en **trois niveaux** (recommandation pour la soutenance) :

| Niveau | Français | Anglais | Swahili |
|--------|----------|---------|---------|
| **L1 — Interface** | Complet | Complet | Complet (requête comprise, réponse générée en SW possible) |
| **L2 — Preuves (corpus)** | Fort | Partiel (articles FR/EN internationaux) | **Faible aujourd’hui** |
| **L3 — Produit promis** | Oui | Oui avec transparence | **Non** tant que sources SW non indexées |

### 4.2 Multilinguisme : argument pour le mémoire

Le modèle d’embedding **multilingue** aligne requête et documents dans un même espace vectoriel : une question en anglais peut retrouver un article français pertinent (et inversement). Cela ne constitue pas une « traduction du corpus », mais une **recherche sémantique cross-lingue**.

Pour le swahili, la barrière reste **documentaire** mais réduite : **167** articles SW (**1,3 %**), cinq flux actifs. Pour l’anglais, **642** articles (**4,9 %**) permettent une **L2** plus solide qu’avec le seul cross-lingue. `habarirdc.net` reste en **français** malgré le nom.

**Position sur le multilinguisme :** **FR** — L3 opérationnel ; **EN** — L2 solide, L3 partiel ; **SW** — L2 amorcé (objectif ≥ 500 articles SW pour L3).

### 4.3 Limites techniques

| Limite | Impact | Piste |
|--------|--------|-------|
| Corpus FR dominant (≈ 99 %) | SW encore minoritaire | [`SOURCES_SWAHILI_AUDIT.md`](SOURCES_SWAHILI_AUDIT.md) |
| Historique couverture Chroma partielle | Risque de retrieval incomplet | `python scripts/sync_to_chroma.py` (résolu : 100 %) |
| Pas de jeu de test annoté | Pas de précision / rappel chiffrés | 20–30 paires (rumeur, verdict attendu) en travail futur |
| Topic Gate Telegram en privé | Plus strict que WhatsApp | Harmoniser `require_topic_gate` (évolution code) |
| Anti-surinformation M10 | Regroupement doublons partiel (Redis) | §6.4 chapitre 2 — consolidation à compléter |
| OCR sans `swa` | Images swahili mal lues | `OCR_LANG=fra+eng+swa` après install pack tesseract |

### 4.4 Comparaison avec l’état de l’art (narratif court)

Les chatbots généralistes répondent vite mais **sans garantie de source RDC**. RDC News Intelligence inverse le compromis : **latence plus élevée**, **traçabilité** (liens médias), verdicts catégorisés. C’est cohérent avec les exigences de lutte contre la désinformation en contexte **faible confiance médias / forte viralité WhatsApp**.

### 4.5 Éthique et responsabilité

- Le système **ne remplace pas** un journaliste : il agrège des articles déjà publiés.
- Le verdict IMPRÉCIS reflète des sources **contradictoires ou incomplètes**, pas une neutralité absolue.
- Les groupes WhatsApp : le bot ne supprime pas les messages tiers ; il limite surtout **ses propres** répétitions (objectif anti-surinformation).

---

## 5. Perspectives (après soutenance)

1. **Corpus swahili** — crawl `dw.com-sw-kiswahili` + volumes VOA/BBC ; colonne `articles.lang` (annexe B).
2. **Métriques formelles** — précision verdict vs annotateurs sur échantillon stratifié.
3. **GPU / modèle quantifié** — réduire latence Ollama sur VPS.
4. **Table `verifications`** — audit, statistiques automatiques pour un futur chapitre résultats quantitatif.

---

## Annexe A — Récupérer les chiffres du corpus (5 minutes)

```bash
# API locale (adapter host si VPS)
curl -s http://127.0.0.1:8000/admin/overview | jq '.stats, .top_sources[:5]'
```

Ou console admin frontend : page **Overview** (`/admin`).

Champs à recopier dans §3.1 :

- `total_articles`
- `embedded_articles`
- `embedding_coverage`
- `total_sources`
- `top_sources`

**Requête SQL complémentaire (langue non stockée aujourd’hui) :**

```sql
-- Le schéma actuel n'a pas de colonne lang ; comptage par source uniquement
SELECT COALESCE(source_id, 'unknown') AS source, COUNT(*) AS n
FROM articles
GROUP BY source
ORDER BY n DESC
LIMIT 15;
```

---

## Annexe B — Comment chercher des sites d’articles en swahili (RDC / région)

Objectif : identifier des **sources crawlables** (HTML, WordPress, RSS) dont le **corps d’article** est rédigé en kiswahili, priorité **Est de la RDC**, **Katanga**, **groupements frontaliers**, diaspora.

### B.1 Critères de sélection (checklist)

| Critère | Pourquoi |
|---------|----------|
| Langue principale = **sw** | Sinon le RAG n’apporte pas de preuves SW |
| Actualité **RDC / Grands Lacs** | Alignement mission projet |
| **RSS ou WordPress** | Déjà supportés par le crawler (`sourceKind`) |
| Licence / accès public | Éviter paywalls sans accord |
| Volume ≥ quelques articles / semaine | Justifier l’indexation |
| Stabilité HTML | Sélecteurs CSS reproductibles (comme `sources.json`) |

### B.2 Pistes de recherche (mots-clés et requêtes)

| Canal | Exemple |
|-------|---------|
| Google | `habari congo swahili`, `gazeti congo swahili`, `habari za congo leo` |
| Google | `sauti ya congo swahili`, `ukurasa wa habari congo` |
| Répertoires médias | [MediaCloud](https://www.mediacloud.org/), [Mondoblog](https://mondoblog.org/) (filtre RDC / sw) |
| ONG / UN | UNICEF, MONUSCO, OCHA — pages **kiswahili** sur la RDC |
| Radios | Radios communautaires Est (Goma, Bukavu, Uvira) — sites avec archive texte |

### B.3 Statut des candidats (audit mai 2026)

| Source | Statut | `sourceId` |
|--------|--------|------------|
| **VOA Swahili** | ✅ Intégré, crawl OK | `voaswahili.com` |
| **BBC News Swahili** | ✅ Intégré (RSS) | `bbc.com-swahili` |
| **DW — Congo** | ✅ Intégré | `dw.com-sw-congo` |
| **DW — Kiswahili** | ⏳ Configuré, crawl à lancer | `dw.com-sw-kiswahili` |
| **habarirdc.net** | ❌ Français (`lang=fr-FR`) | déjà catalogue |
| **bukavufm.com** | ⚠️ Contenu faible / placeholder | déjà catalogue |
| **Radio Okapi /sw** | ❌ RSS 410 Gone | — |

Détail complet : [`SOURCES_SWAHILI_AUDIT.md`](SOURCES_SWAHILI_AUDIT.md).

### B.4 Procédure technique d’intégration (quand une source est validée)

1. **Test manuel** — 5 URLs d’articles SW, copier titre + extrait.
2. **Test sémantique** — `POST /rag` avec requête SW sur le sujet ; noter si NON VÉRIFIABLE.
3. **Entrée `sources.json`** — copier un bloc `wordpress` ou `html` existant ; renseigner `sourceId` unique (ex. `voaswahili.com`).
4. **Crawl pilote** — `python -m app.services.crawler.scripts.sync --source-id <id> --limit 20`
5. **Sync Chroma** — `python scripts/sync_to_chroma.py` (ou pipeline admin).
6. **Re-test** — rejouer T6–T8 du tableau §3.4.

**Évolution schéma (recommandée) :** colonne `articles.lang` (`fr` | `en` | `sw`) + filtre retrieval `where lang=sw` pour ne pas mélanger les preuves.

### B.5 Indicateurs de succès corpus swahili

| Indicateur | Cible indicative |
|------------|------------------|
| Articles `lang=sw` indexés | ≥ **500** (pilote) puis ≥ **2 000** |
| Part SW dans Chroma | ≥ **10 %** du corpus total |
| Tests T6–T8 | ≥ **2/3** « satisfaisant » avec sources SW citées |
| OCR | Pack `tesseract-ocr-swa` + `OCR_LANG` mis à jour |

---

## Annexe C — Paragraphe prêt à coller dans l’article (Discussion)

> Les résultats confirment la faisabilité d’un assistant de vérification sur WhatsApp fondé sur un corpus journalistique indexé en base vectorielle. En conditions réelles (VPS, Whapi, Ollama local), le pipeline enchaîne réception, recherche sémantique et génération de verdicts structurés, avec refus explicite de répondre lorsque aucune source locale n’est trouvée. La performance perçue est dominée par le temps de génération du LLM ; la qualité factuelle dépend avant tout de l’étendue du corpus. Le multilinguisme illustre une distinction importante : l’interface et l’embedding multilingue permettent des requêtes en anglais et en swahili, mais la **valeur probatoire** reste liée aux langues effectivement présentes dans la base — aujourd’hui le français. L’extension vers un corpus swahili, alimenté par des médias de l’Est de la RDC et des radios régionales, constitue la priorité scientifique et opérationnelle pour honorer la promesse trilingue au-delà de la démonstration technique.

---

## Documents associés

| Document | Contenu |
|----------|---------|
| [`Chapitre_4_Deploiement.md`](Chapitre_4_Deploiement.md) §10 | Tableau FR / EN / SW déploiement |
| [`BROUILLON_ANTI_SURINFORMATION_WHATSAPP.md`](BROUILLON_ANTI_SURINFORMATION_WHATSAPP.md) | Pistes anti-submersion |
| [`SOURCES_SWAHILI_AUDIT.md`](SOURCES_SWAHILI_AUDIT.md) | Audit et commandes crawl SW |
| `data/crawler/sources.json` | Catalogue (64 sources, dont 4 SW) |
| `data/evaluation/rag_manual_tests.json` | Résultats bruts des tests RAG |

---

*Fin du chapitre — Résultats et discussion (v1.2).*
