# PLAN CORRIGÉ - RDC News Intelligence
*Aligné avec l'implémentation réelle du système FastAPI+RAG+Telegram+WhatsApp+OCR*

---

## INTRODUCTION GÉNÉRALE (Chapitre 0)

### 0.1. Contexte ✅
*À conserver du TXT original, avec ajout optionnel de statistiques sur mobile et messageries.*

- Explosion du numérique en RDC (62% de pénétration mobile en 2024).  
- Surcharge informationnelle (infobésité) : excès de contenus redondants, contradictoires.  
- Défis : désinformation, fermes de contenus, langues nationales peu couvertes.

---

### 0.2. Problématique ✅
*À adapter légèrement pour inclure le RAG comme solution centrale.*

**Original (à conserver):**
> "Comment concevoir une architecture de chatbot intelligent, s'activant à partir de requêtes simples par mots-clés, capable de transformer une recherche brute en une recommandation structurée pour réduire la surinformation en RDC?"

**Clarification ajoutée (RAG au lieu de Topic Modeling):**
> Au-delà de la simple détection de redondance, nous proposons un système **d'augmentation par récupération (RAG)** qui :
> 1. Collecte continuellement les articles via un crawler (HTML/WordPress).  
> 2. Les transforme en embeddings sémantiques (vecteurs 384-dim).  
> 3. Les stocke dans une base vectorielle PostgreSQL + pgvector.  
> 4. Les recommande ou les synthétise via un LLM local (Mistral/Ollama).  
> 5. Les expose via Telegram et WhatsApp pour un accès mobile-first.

---

### 0.3. Hypothèse ✅ (À corriger)

**Version originale (BERTopic/Topic Modeling):**
> "Un chatbot intelligent reposant sur une architecture de Génération Augmentée par Récupération (RAG)..."

**Version corrigée (RAG + Embeddings + pgvector):**
> Nous posons l'hypothèse qu'un système d'IA construit sur une architecture RAG (Retrieval-Augmented Generation), combinant :
> - Une base d'articles vectorisée (embeddings SentenceTransformers 384-dim).  
> - Une recherche sémantique via pgvector (PostgreSQL).  
> - Un modèle génératif local (Mistral/Ollama).  
> - Une alimentation continue par crawler (RadioOkapi, Actualité.cd, 7sur7.cd, etc.).  
> - Des interfaces mobiles (Telegram polling, WhatsApp Cloud API).  
> - Un pipeline OCR local (Tesseract) pour fact-checking d'images.  
> 
> ...permet de réduire significativement la surinformation en RDC en fournissant des réponses fiables, contextualisées et structurées (VÉRIFICATION, EXPLICATION, SOURCES).

---

### 0.4. Choix et intérêt du sujet ✅
*À conserver du TXT original, avec accent ajouté sur l'approche RAG locale.*

---

### 0.5. Délimitation du travail ✅
*À conserver, mais préciser :*
- "Limité aux contenus textuels" → Ajouter "et aux images (OCR local)".  
- "Chatbot conversationnel (WhatsApp)" → Ajouter "et Telegram".

---

### 0.6. État de l'Art ✅ (À réviser légèrement)

**À conserver :**
- 0.6.1 Systèmes de recommandation hybrides ✅  
- 0.6.2 Topic Modeling : **À nuancer** (on ne fait pas de Topic Modeling pur, mais de la recherche vectorielle + RAG).  
- 0.6.3 NLP Afro-centré et multilinguisme ✅  
- 0.6.4 Chatbots et agents conversationnels ✅  

**Nouveau à ajouter :**
- 0.6.5 **Retrieval-Augmented Generation (RAG)** : définition, avantages vs fine-tuning, applications.  
- 0.6.6 **Embeddings sémantiques et pgvector** : recherche vectorielle, similarité cosinus.  
- 0.6.7 **OCR local et Tesseract** : avantages (confidentialité, offline), applications aux réseaux sociaux.

---

### 0.7. Méthodologie ✅ (À adapter)

**Original :**
> "Approche analytique, utilisant Topic Modeling (Online BERTopic), modèles de classification multilingues (SERENGETI, Afro-XLMR), prototypage d'application mobile Flutter et chatbot WhatsApp."

**Corrigée :**
> "Approche d'ingénierie logicielle basée sur :  
> - **Collecte de données** : crawler HTML/WordPress pour sources RDC en continu.  
> - **Vect orisation** : modèles pré-entraînés (SentenceTransformers all-MiniLM-L6-v2, paraphrase-multilingual-MiniLM-L12-v2).  
> - **Indexation** : PostgreSQL + pgvector pour stockage vectoriel et recherche sémantique.  
> - **Génération** : Mistral via Ollama pour synthèse basée sur contexte récupéré.  
> - **OCR** : Tesseract local pour extraction de texte depuis images.  
> - **Intégrations** : Telegram (polling), WhatsApp Cloud API (webhooks).  
> - **Prototypage itératif** : déploiement progressif avec tests sur données réelles RDC."

---

### 0.8. Subdivision du travail ✅ (À corriger)

**Original :**
> Ch. 1 : IA et gestion de l'info | Ch. 2 : Topic Modeling | Ch. 3 : App + MobileNet_V2 | Ch. 4 : Deployment

**Corrigée :**
> - **Ch. 1 : L'intelligence artificielle au service de la gestion de l'information**  
>   Contexte médiatique RDC, défis (infobésité, désinformation, multilingue), solutions IA actuelles, limites, notre solution RAG.
>
> - **Ch. 2 : Méthodologie, collecte et préparation des données**  
>   Crawler HTML/WordPress, sources RDC, dataset HF (drc-news-corpus), vectorisation, index pgvector.
>
> - **Ch. 3 : Modélisation et architecture du système**  
>   Spécifications fonctionnelles/non-fonctionnelles, modèle de données, architecture microservices, RAGService, RetrievalService, LLMService, OCRService, webhooks Telegram/WhatsApp, diagrammes UML (cas d'utilisation, séquence, classes).
>
> - **Ch. 4 : Implémentation et déploiement**  
>   Stack technologique (FastAPI, PostgreSQL, SentenceTransformers, Ollama, Tesseract, Telegram polling, WhatsApp Cloud API), code clé, résultats tests, captures d'écran.

---

## CHAPITRE 1 : L'INTELLIGENCE ARTIFICIELLE AU SERVICE DE LA GESTION DE L'INFORMATION

### 1.1. Introduction partielle ✅
*À conserver du TXT original.*

---

### 1.2. Les défis de l'écosystème informationnel congolais ✅
*À conserver du TXT original.*

- 1.2.1 L'infobésité ou surcharge informationnelle ✅  
- 1.2.2 Le désordre de l'information (Information Disorder) ✅  
- 1.2.3 La redondance et les "fermes de contenus" ✅  
- 1.2.4 Le défi multilingue et l'exclusion numérique ✅

---

### 1.3. Les solutions actuelles au désordre informationnel ✅
*À conserver du TXT original (fact-checking manuel, initiatives UNESCO, etc.).*

---

### 1.4. Les limites des solutions actuelles ✅
*À conserver du TXT original.*

**À ajouter :** limitation des approches basées sur Topic Modeling seul → besoin de génération intelligente (RAG).

---

### 1.5. Solution proposée basée sur l'Intelligence Artificielle ✅ (À CORRIGER)

**Original (Focus Topic Modeling):**
> "Identification de Stories", "Réduction de Redondance (InFRSS)", "Clustering Sémantique (NEC_SRG)"

**Corrigée (Focus RAG + Embeddings + Crawler + Multicanal):**

Notre solution, **RDC News Intelligence**, repose sur quatre piliers :

1. **Collecte Continue (Crawler)**  
   - Scripts HTML/WordPress qui moissonnent les sources RDC (RadioOkapi, Actualité.cd, 7sur7.cd, etc.) toutes les 2h.  
   - Articles stockés en JSONL, puis injectés dans l'API.  
   - Cela alimente continuellement le moteur de recommandation.

2. **Vectorisation Intelligente (Embeddings)**  
   - Chaque article est transformé en vecteur sémantique (384 dimensions) via SentenceTransformers.  
   - Ces vecteurs complètent l'article dans la base de données.  
   - Permet une recherche non par mots-clés exacts, mais par *sens*.

3. **Recommandation Sémantique (RAG + pgvector)**  
   - Lorsqu'un utilisateur pose une question, elle est vectorisée de la même manière.  
   - On recherche les articles les plus proches (top-K) via cosinus similarity dans PostgreSQL + pgvector.  
   - Ces articles forment le *contexte* fourni au LLM.  
   - **Avantage:** pas de hallucination, réponses ancrées dans les données réelles de RDC.

4. **Génération Structurée (Mistral/Ollama Local)**  
   - Le LLM Mistral, exécuté localement via Ollama, synthétise la réponse en trois blocs structurés:  
     - 🚨 **VÉRIFICATION** (Vrai, Faux, Imprécis).  
     - 📝 **EXPLICATION** (contexte court adapté au mobile).  
     - 🔗 **SOURCES** (articles originaux).

5. **Océrisation d'Images (Tesseract Local)**  
   - Les utilisateurs peuvent envoyer des images contenant du texte (screenshots, affichages).  
   - Tesseract extrait le texte localement (sans données vers l'extérieur).  
   - Le texte extrait alimente le RAG.  
   - **Avantage:** confidentialité, adéquat pour les zones à faible débit.

6. **Intégration Multicanale (Telegram + WhatsApp)**  
   - **Telegram :** Polling natif intégré à FastAPI (pas de webhook HTTPS complexe).  
   - **WhatsApp :** Via Meta Cloud API (webhook HTTPS).  
   - Permet aux journalistes, citoyens, et fact-checkers d'accéder au système depuis leur messagerie habituelle.

---

### 1.6. Conclusion partielle ✅
*À adapter :*

> "Ce chapitre a présenté l'apport de l'IA à la gestion de l'information en RDC. Il a montré qu'au-delà de la détection de topic ou de désinformation manuelle, une approche **RAG distribuée et multicanale**, associée à un crawler continu et des embeddings vectoriels, offre une solution viable et locale pour réduire l'infobésité. Le chapitre suivant détaillera la collecte des données via le crawler, leur vectorisation et la préparation du système."

---

## CHAPITRE 2 : MÉTHODOLOGIE, COLLECTE ET PRÉPARATION DES DONNÉES

### 2.1. Introduction partielle

L'intelligence d'un système RAG dépend entièrement de la qualité et de la fraîcheur des données qui l'alimentent. Ce chapitre détaille comment nous construisons et mettons à jour continuellement le corpus d'articles qui sert de base de connaissance au moteur de recommandation.

---

### 2.2. Démarches méthodologiques

**Approche :**
- **Collecte active** via crawler (non passif, mais programmé).  
- **Vectorisation standardisée** (mêmes modèles pour tous les articles).  
- **Indexation optimisée** (pgvector pour recherche rapide et scalable).  
- **Évaluation continue** (mesure de pertinence des résultats RAG).

---

### 2.3. La collecte des données

#### 2.3.1 Sources de données

**Dataset initial :**
- Hugging Face : `drc-news-corpus` (bernard-ng) → ~1986 articles pré-indexés.

**Collecte continue via Crawler :**
- RadioOkapi (HTML). 
- Actualité.cd (HTML).  
- 7sur7.cd (HTML).  
- Divers sites WordPress (via scrapers génériques).

**Format :** JSONL (une ligne = un article avec titre, corps, URL, date, source).

#### 2.3.2 Infrastructure crawler

```bash
# Lance le crawler sur une source donnée
python -m app.services.crawler.scripts.sync --source-id radiookapi.net --limit 20

# Ou toutes les sources
python -m app.services.crawler.scripts.sync --source-id all --limit 20
```

**Résultat :** Fichiers JSONL dans `data/crawler/{source}.jsonl`.

#### 2.3.3 Intégration au backend

Les articles sont envoyés à l'API via `replay_jsonl` :

```bash
python -m app.services.crawler.scripts.replay_jsonl \
  --file data/crawler/radiookapi.net.jsonl \
  --endpoint http://127.0.0.1:8000 \
  --batch-size 50
```

---

### 2.4. La préparation des données

#### 2.4.1 Vectorisation

À l'insertion, le service `ArticleService` déclenche automatiquement :

1. **Récupération du texte** (titre + copie courte + corps complet).
2. **Passage dans `EmbeddingService`** avec le modèle SentenceTransformers.
3. **Calcul du vecteur** (384 dimensions).
4. **Stockage en BDD** dans la colonne `articles.embedding`.

**Modèles utilisés :**
- **Production :** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (multilingue, optimisé).
- **Dataset HF :** `sentence-transformers/all-MiniLM-L6-v2` (plus compacte).

#### 2.4.2 Nettoyage et normalisation

- Suppression des doublons : contrainte `ON CONFLICT DO NOTHING` sur URL.  
- Normalisation des caractères accentués en français et langues nationales.  
- Formatage standard des dates (ISO).

---

### 2.5. Entraînement et indexation

#### 2.5.1 Création et maintenance de l'index pgvector

```sql
-- Index IVFFLAT sur les embeddings
CREATE INDEX articles_embedding_idx 
ON articles USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

**Avantage :** Recherche par similarité cosinus ultra-rapide, même avec millions d'articles.

#### 2.5.2 Script de ré-embedding

Si le modèle d'embedding change ou après grosse mise à jour :

```python
from app.services.train_pipeline import run_reembedding
print(run_reembedding(batch_size=50, force_all=False))
```

- Recalcule les vecteurs.  
- Réindexe `articles_embedding_idx`.  
- Trace la run dans `training_runs`.

---

### 2.6. Interprétation et évaluation du modèle

#### 2.6.1 Métriques de pertinence RAG

- **Recall@K :** Sur l'ensemble test, % des articles pertinents dans top-K récupérés.  
- **Latence :** Temps requête → résultat RAG (cible < 5s pour Telegram/WhatsApp).  
- **Score de similarité moyen :** Distance cosinus moyenne des résultats (> 0.7 = bon).

#### 2.6.2 Evaluation qualitative

- **Tests utilisateurs** avec journalistes RDC (13–15 requêtes réelles).  
- Vérification que les sources recommandées sont pertinentes.  
- Mesure de satisfaction (réduction de surcharge informationnelle).

---

### 2.7. Conclusion partielle

Le système de collecte et vectorisation continu assure que le moteur de recommandation dispose toujours d'informations RDC à jour et fiables. Cette approche permet une "base de connaissance vivante" qui s'adapte au rythme de l'actualité congolaise sans intervention manuelle. Le chapitre suivant détaille comment ces données sont utilisées dans l'architecture complète du système.

---

## CHAPITRE 3 : MODÉLISATION ET ARCHITECTURE DU SYSTÈME

### 3.1. Introduction

Le projet RDC News Intelligence repose sur une architecture microservices distribuée, au cœur de laquelle se trouve un système RAG (Retrieval-Augmented Generation) capable d'interroger et de synthétiser l'information en temps quasi réel. Ce chapitre décrit la modélisation fonctionnelle et technique du système.

---

### 3.2. Spécifications fonctionnelles et non-fonctionnelles

#### Fonctionnelles :
1. **Requête textuelle** → recommandation d'articles + synthèse RAG.  
2. **Image avec texte** → OCR local → recommandation → synthèse.  
3. **Accès via Telegram** (polling) et WhatsApp (Cloud API).  
4. **Gestion de sources** (crawler, ajout manuel d'articles).

#### Non-fonctionnelles :
- **Latence :** < 5s pour réponse (Telegram/WhatsApp).  
- **Confidentialité :** Tout local (pas de données vers Google/Azure), sauf APIs Telegram/WhatsApp officielles.  
- **Disponibilité :** 24/7 (cron minimal pour crawler).  
- **Scalabilité :** Supporte 10k+ articles sans dégradation.

---

### 3.3. Cas d'utilisation (Use Cases)

#### UC1 : Utilisateur pose une question texte via Telegram
1. Utilisateur envoie un message type "Y a-t-il une épidémie?"  
2. Bot récupère le texte.  
3. Vectorise la question.  
4. Récupère top-3 articles pertinents.  
5. Passe aux prompts Mistral spécialisé.  
6. Reçoit réponse structurée (VÉRIFICATION, EXPLICATION, SOURCES).

#### UC2 : Utilisateur envoie une image via WhatsApp
1. Utilisateur envoie capture d'écran d'une rumeur.  
2. Webhook WhatsApp notifie le backend.  
3. Backend télécharge l'image via Meta Graph API.  
4. Tesseract extrait le texte.  
5. Idem UC1 (RAG sur texte extrait).

#### UC3 : Administrateur lance un crawl manuel
1. Exécute `python -m app.services.crawler.scripts.sync --source-id all`.  
2. Crawler récupère articles des sources.  
3. JSONL généré.  
4. Administrateur replay JSONL vers API (`replay_jsonl`).  
5. Articles vectorisés, indexés, disponibles pour RAG.

#### UC4 : Changement de modèle d'embedding
1. Met à jour la configuration (nouveau modèle).  
2. Exécute `run_reembedding(force_all=True)`.  
3. Tous les articles sont re-vectorisés.  
4. Index pgvector rafraîchi.

---

### 3.4. Modélisation des données

#### Schéma conceptuel

```
ARTICLE
├─ id (PK)
├─ title (text)
├─ body (text)
├─ url (string, unique)
├─ source_id (FK → SOURCE)
├─ published_at (timestamp)
├─ embedding (vector[384])  ← Cœur du RAG
├─ created_at (timestamp)
└─ updated_at (timestamp)

SOURCE
├─ id (PK)
├─ name (string)
├─ url (string)
└─ type (enum: 'html', 'wordpress', 'feed')

TRAINING_RUN (traçabilité du re-embedding)
├─ id (PK)
├─ status (enum: 'pending', 'success', 'failed')
├─ articles_count (int)
├─ started_at (timestamp)
└─ ended_at (timestamp)
```

#### Index critique

```sql
-- Recherche vectorielle rapide
CREATE INDEX articles_embedding_idx 
ON articles USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Accès rapide par source
CREATE INDEX articles_source_idx ON articles(source_id);

-- Éviter les doublons
CREATE UNIQUE INDEX articles_url_idx ON articles(url);
```

---

### 3.5. Architecture logicielle

#### 3.5.1 Composants principaux

```
┌─────────────────────────────────────────────────┐
│         FastAPI App (app.main)                  │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │       Routes FastAPI                       │ │
│  ├─────────────────────────────────────────┤ │
│  │ /query (POST)      → Query service       │ │
│  │ /rag (POST)        → RAG complet         │ │
│  │ /rag/stream (POST) → RAG streaming       │ │
│  │ /rag/image (POST)  → OCR → RAG          │ │
│  │ /articles (POST)   → Ingestion manuel    │ │
│  │ /webhooks/telegram → Telegram webhook   │ │
│  │ /webhooks/whatsapp → WhatsApp webhook   │ │
│  └─────────────────────────────────────────┘ │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │       Services internes                   │ │
│  ├─────────────────────────────────────────┤ │
│  │ RAGService           (orchestration)     │ │
│  │ EmbeddingService     (SentenceTransf.)   │ │
│  │ RetrievalService     (pgvector query)    │ │
│  │ LLMService           (Ollama/Mistral)    │ │
│  │ OCRService           (Tesseract)         │ │
│  │ ArticleService       (CRUD + embedding)  │ │
│  │ CrawlerService       (scheduling)        │ │
│  └─────────────────────────────────────────┘ │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │   Intégrations externes (polling/webhooks)│ │
│  ├─────────────────────────────────────────┤ │
│  │ TelegramPolling      (app.services)      │ │
│  │ Telegram Bot API (getUpdates)            │ │
│  │ WhatsApp Cloud API (webhooks)            │ │
│  └─────────────────────────────────────────┘ │
│                                                 │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│    PostgreSQL + pgvector                        │
│    (articles + embeddings + index IVFFLAT)      │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│    Ollama (local LLM server)                    │
│    ├─ Mistral (generate)                        │
│    └─ SentenceTransformers (embed)              │
└─────────────────────────────────────────────────┘
         ↓
┌─────────────────────────────────────────────────┐
│    Tesseract (local OCR)                        │
└─────────────────────────────────────────────────┘
```

---

#### 3.5.2 Flow principaux

##### **Flow 1 : Requête texte RAG**

```
Utilisateur (Telegram/Web) 
  ↓ "Quelle est la situation économique ?"
  ↓
FastAPI POST /rag
  ↓
RAGService.generate_full_answer(query, channel="whatsapp")
  ↓
EmbeddingService.encode(query) → vecteur 384-dim
  ↓
RetrievalService.get_similar_articles(vector, top_k=3) 
  → SELECT TOP 3 articles ORDER BY embedding <=> vector::vector
  ↓
Articles récupérés + contexte
  ↓
LLMService.summarize_full(context, query)
  → Appel Ollama /api/generate (Mistral)
  → Prompt : "Tu es fact-checker, voici les sources… résume en VÉRIFICATION|EXPLICATION|SOURCES"
  ↓
Réponse structurée
  ↓
Telegram/WhatsApp/Web
```

##### **Flow 2 : Image RAG (OCR)**

```
Utilisateur WhatsApp (image avec texte)
  ↓
WhatsApp Cloud API → webhook /webhooks/whatsapp
  ↓
process_whatsapp_image(media_id)
  ↓
Meta Graph API → Télécharge l'image
  ↓
OCRService.extract_text(image_bytes) → Tesseract
  ↓
Texte extrait → idem Flow 1 (RAG textile)
  ↓
Réponse via WhatsApp
```

##### **Flow 3 : Mise à jour du moteur (Crawler)**

```
Administrateur (cron ou manuel)
  ↓
$ python -m app.services.crawler.scripts.sync --source-id all
  ↓
Crawler scrape RadioOkapi, Actualité.cd, etc.
  ↓
Articles → JSONL file
  ↓
$ python -m app.services.crawler.scripts.replay_jsonl --file ...
  ↓
POST /crawler/articles/batch → ArticleService
  ↓
Pour chaque article :
  - EmbeddingService.encode(title + body) → vecteur
  - INSERT articles (title, body, url, embedding) 
  - ON CONFLICT DO NOTHING
  ↓
pgvector index auto-updated
  ↓
Moteur de recommandation enrichi
```

---

### 3.6. Diagrammes de séquence

#### 3.6.1 Vérification d'une information texte via Telegram

```
┌─────────────┐       ┌──────────┐       ┌─────────────┐       ┌─────────────┐       ┌────────┐
│  Utilisateur│       │ Telegram │       │ FastAPI App │       │ PostgreSQL  │       │ Ollama │
└──────┬──────┘       └────┬─────┘       └──────┬──────┘       └──────┬──────┘       └───┬────┘
       │                   │                    │                    │                   │
       │ Pose question     │                    │                    │                   │
       ├──────────────────>│                    │                    │                   │
       │                   │ Webhook POST       │                    │                   │
       │                   ├───────────────────>│                    │                   │
       │                   │                    │ Encode question    │                   │
       │                   │                    ├───────────────────>│ (via EmbeddingServ)
       │                   │                    │   (vectorize)      │                   │
       │                   │                    │<───────────────────┤                   │
       │                   │                    │                    │                   │
       │                   │                    │ Query by similarity│                   │
       │                   │                    ├───────────────────>│                   │
       │                   │                    │ SELECT TOP 3       │                   │
       │                   │                    │<───────────────────┤                   │
       │                   │                    │   (articles + contexte)                │
       │                   │                    │                    │                   │
       │                   │                    │ Call LLM           │                   │
       │                   │                    ├──────────────────────────────────────>│
       │                   │                    │ (contexte + prompt)│                   │
       │                   │                    │                    │                   │
       │                   │                    │                    │                   │ Mistral generate
       │                   │                    │                    │                   │
       │                   │                    │<──────────────────────────────────────┤
       │                   │                    │  (réponse structurée)                 │
       │                   │ Réponse éditée     │                    │                   │
       │<──────────────────┤<───────────────────┤                    │                   │
       │                   │                    │                    │                   │
```

---

#### 3.6.2 Vérification d'une information image via WhatsApp

```
┌─────────────┐       ┌──────────────┐       ┌─────────────┐       ┌─────────────┐       ┌────────┐
│  Utilisateur│       │ Meta Graph   │       │ FastAPI App │       │ PostgreSQL  │       │ Tesseract
└──────┬──────┘       └────┬─────────┘       └──────┬──────┘       └──────┬──────┘       └───┬──
       │                   │                    │                    │                   │
       │ Envoie image      │                    │                    │                   │
       │───────────────────>                    │                    │                   │
       │                   │ Webhook            │                    │                   │
       │                   ├───────────────────>│                    │                   │
       │                   │                    │ GET media_id       │                    │
       │                   │<───────────────────┤<───────────────────────── (via Meta API)
       │                   │  (image bytes)     │                    │                   │
       │                   │                    │ OCR extract        │                   │
       │                   │                    ├──────────────────────────────────────>│
       │                   │                    │  ( image)          │                   │
       │                   │                    │                    │                   │ Extract text
       │                   │                    │                    │                   │
       │                   │                    │<──────────────────────────────────────┤
       │                   │                    │  (extracted text)  │                   │
       │                   │                    │                    │                   │
       │                   │                    │ [Idem Flow 1 : RAG texte]              │
       │                   │                    │                    │                   │
       │                   │ Réponse texte      │                    │                   │
       │<──────────────────┤<───────────────────┤                    │                   │
       │                   │                    │                    │                   │
```

---

#### 3.6.3 Ingestion d'articles via crawler

```
┌──────────────┐        ┌────────────┐        ┌──────────────┐       ┌──────────────┐
│ Administrateur       │  Crawler   │        │  FastAPI API │       │ PostgreSQL   │
└────┬─────────┘        └────┬───────┘        └──────┬───────┘       └────┬─────────┘
     │                        │                      │                    │
     │ $ sync --source-id all │                      │                    │
     ├──────────────────────>│                      │                    │
     │                        │ Scrape RadioOkapi   │                    │
     │                        │ Scrape Actualité   │                    │
     │                        │ ...                │                    │
     │                        │ Generate JSONL     │                    │
     │                        │                      │                    │
     │ $ replay_jsonl --file  │                      │                    │
     ├──────────────────────────────────────────────>│                    │
     │                        │                      │ POST /crawler/articles/batch
     │                        │                      │                    │
     │                        │                      │ For each article:   │
     │                        │                      │  - Encode title+body
     │                        │                      │  - INSERT (title, embedding, ...)
     │                        │                      ├───────────────────>│
     │                        │                      │  ON CONFLICT DO NOTHING
     │                        │                      │<───────────────────┤
     │                        │                      │ Index auto-updated  │
     │                        │                      │                    │
     │ [Moteur enrichi, prêt pour RAG]              │                    │
     │                        │                      │                    │
```

---

### 3.7. Justification des choix d'architecture

#### **Pourquoi PostgreSQL + pgvector ?**
- Stockage local (données RDC en confiance).  
- Index IVFFLAT pour recherche vectorielle ultra-rapide sur millions d'articles.  
- Transactions ACID, gestion de charge évolutive.  
- Alternative locale à Pinecone, Weaviate, etc. (pas de dépendance SaaS).

#### **Pourquoi RAG et pas fine-tuning Mistral ?**
- **RAG :** Rapide, peu coûteux, met à jour aux dernières actualités (via crawler).  
- **Fine-tuning Mistral :** Nécessite données annotées, GPU coûteux, temps long, moins flexible.  
- **Choix RAG + crawler :** En 2 heures, système connaît les news RDC les plus récentes.

#### **Pourquoi OCR local (Tesseract) ?**
- **Confidentialité :** Pas de données vers Google Cloud Vision.  
- **Offline :** Fonctionne sans connexion stable (idéal RDC).  
- **Gratuit et open-source.**  
- **Limitation :** Plus lent que les services cloud, mais acceptable pour Telegram/WhatsApp.

#### **Pourquoi Telegram polling + WhatsApp webhooks ?**
- **Telegram polling :** Evite HTTPS complexe en local, exécution simple dans FastAPI.  
- **WhatsApp webhooks :** Meta impose webhooks, plus professionnel pour entreprises.  
- **Couverture :** 54% des internautes RDC utilisent WhatsApp, Telegram pour journalistes.

#### **Pourquoi SentenceTransformers (384-dim) ?**
- Modèle multilingue pré-entraîné (français + Lingala/Swahili/Kikongo).  
- Compact (384-dim) = stockage/perf optimisé.  
- Déjà optimisé par Meta/Facebook (AIRE).

#### **Pourquoi Ollama (Mistral local) ?**
- Exécution 100% locale, données non partagées.  
- Mistral 7B performant pour synthèse.  
- Coût GPU moindre qu'une API cloud.  
- Prompts ajustables pour fact-checking.

---

### 3.8. Conclusion partielle

L'architecture de RDC News Intelligence est conçue pour être :
- **Locale et souveraine** (données RDC protégées).  
- **Réactive** (RAG + crawler remet à jour continuellement).  
- **Accessible** (Telegram/WhatsApp, mobile-first).  
- **Scalable** (pgvector supporte millions d'articles).  
- **Indépendante de services cloud** (OCR local, LLM local, base local).

Le chapitre suivant détaille la mise en œuvre technique et les résultats empiriques.

---

## CHAPITRE 4 : IMPLÉMENTATION ET DÉPLOIEMENT

*(À développer en détail dans un document séparé ; ici résumé de la structure)*

### 4.1. Introduction

Ce chapitre détaille le déploiement de l'architecture décrite au Chapitre 3 : stack technologique, code clé, résultats tests, captures d'écran.

---

### 4.2. Stack technologique

- **Backend API :** FastAPI (Python 3.10+).  
- **Base de données :** PostgreSQL 13+ + pgvector.  
- **Embeddings :** SentenceTransformers (all-MiniLM-L6-v2, paraphrase-multilingual-MiniLM-L12-v2).  
- **LLM :** Mistral 7B via Ollama.  
- **OCR :** Tesseract 4.1+.  
- **Messaging :** Telegram Bot API (polling), WhatsApp Cloud API (webhooks).  
- **Crawler :** BeautifulSoup (HTML), WordPress REST API.  
- **DevOps :** Docker, docker-compose.

---

### 4.3. Code clé (structure)

```
ai-service/
├── app/
│   ├── main.py                  (FastAPI entrypoint)
│   ├── api/routes/
│   │   ├── articles.py          (endpoints RAG + image)
│   │   └── webhooks.py           (Telegram + WhatsApp)
│   └── services/
│       ├── rag_service.py        (orchestration RAG)
│       ├── embedding_service.py  (SentenceTransformers)
│       ├── retrieval_service.py  (pgvector queries)
│       ├── llm_service.py        (Ollama/Mistral)
│       ├── ocr_service.py        (Tesseract)
│       ├── article_service.py    (CRUD + embedding)
│       ├── train_pipeline.py     (re-embed, reindex)
│       ├── telegram_polling.py   (polling loop)
│       └── crawler/              (scraping scripts)
├── docs/
│   ├── README.md                 (guide opérationnel)
│   ├── MEMOIRE_CHAPITRE_...md    (intégration/automat.)
│   └── architecture.mmd          (diagrammes)
└── requirements.txt
```

---

### 4.4. Résultats tests

*À remplir après déploiement réel*

- Latence Query-to-Response.  
- Recall@3 (articles pertinents retrouvés).  
- Satisfaction utilisateurs (journalistes RDC).

---

### 4.5. Captures d'écran

*À ajouter :*
- Interface Telegram (conversation exemple).  
- Interface WhatsApp (message + réponse).  
- Tableau de bord administrateur (articles indexés, crawler status).

---

## CONCLUSION GÉNÉRALE

*À développer après implémentation complète.*

- Récapitulatif solution RAG multicanale.  
- Résultats de déploiement RDC.  
- Limites et futures directions (multi-lingue natif, fine-tuning avancé, etc.).

---

**FIN DU PLAN CORRIGÉ**
