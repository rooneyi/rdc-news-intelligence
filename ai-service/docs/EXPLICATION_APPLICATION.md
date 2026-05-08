# RDC News Intelligence — Explication Complète du Fonctionnement

## 1. Qu'est-ce que RDC News Intelligence ?

**RDC News Intelligence** est une plateforme intelligente de **fact-checking en temps réel** conçue spécifiquement pour la République Démocratique du Congo. Son objectif principal est double :

1. **Lutter contre la désinformation** : Vérifier automatiquement les informations douteuses partagées dans les groupes WhatsApp et Telegram.
2. **Réduire la surinformation** : Filtrer et synthétiser le flux massif d'actualités pour ne fournir que l'essentiel, vérifié et sourcé.

Le système fonctionne comme un **bot intelligent** qui s'intègre directement dans les canaux de communication quotidiens des Congolais (WhatsApp, Telegram) ainsi que via une interface Web.

---

## 2. Architecture Globale du Système

L'application est composée de **trois grandes couches** :

```
┌─────────────────────────────────────────────────────────────────┐
│                    CANAUX D'ACCÈS                               │
│   [Interface Web]    [WhatsApp Bot]    [Telegram Bot]           │
└──────────┬───────────────┬──────────────────┬───────────────────┘
           │               │                  │
           ▼               ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                 LOGIQUE MÉTIER (FastAPI)                         │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ Gestionnaire │  │ Classifieur  │  │   Service OCR      │    │
│  │  Webhooks    │  │ Thématique   │  │  (Lecture images)  │    │
│  └──────┬───────┘  └──────┬───────┘  └────────┬───────────┘    │
│         │                 │                    │                │
│         ▼                 ▼                    ▼                │
│  ┌──────────────────────────────────────────────────────┐      │
│  │              MOTEUR RAG (Fact-Checking)               │      │
│  │   Embedding → Recherche Vectorielle → Génération LLM │      │
│  └──────────────────────────────────────────────────────┘      │
└──────────┬──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│                    INFRASTRUCTURE                               │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ PostgreSQL   │  │ Mistral-7B   │  │     Crawler        │    │
│  │ + pgvector   │  │  (Ollama)    │  │  (Radio Okapi…)    │    │
│  └──────────────┘  └──────────────┘  └────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Comment fonctionne la Détection de la Désinformation ?

La détection de la désinformation repose sur un pipeline en **5 étapes** appelé **RAG (Retrieval-Augmented Generation)** :

### Étape 1 : Collecte des faits (Crawler)

Un robot de collecte automatique (**Crawler**) parcourt en continu les sites d'information fiables de la RDC (ex : Radio Okapi). Il :
- Récupère les articles récents
- Nettoie et normalise le texte
- Stocke chaque article dans la base de données PostgreSQL

> **Fichier source** : `app/services/crawler/`

### Étape 2 : Vectorisation (Embeddings)

Chaque article collecté est transformé en un **vecteur mathématique** (embedding) grâce au modèle multilingue `paraphrase-multilingual-MiniLM-L12-v2`. Ce vecteur capture le **sens sémantique** du texte, pas juste les mots exacts.

- **Modèle utilisé** : `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions)
- **Stockage** : Colonne `embedding` de type `VECTOR(384)` dans PostgreSQL via l'extension `pgvector`

> **Fichier source** : `app/services/embedding_service.py`

### Étape 3 : Réception et classification du message

Quand un utilisateur envoie un message (texte ou image), le système :

1. **Reçoit le message** via les Webhooks WhatsApp/Telegram
2. **Détecte le contexte** : message privé ou groupe ?
3. **Classifie la thématique** : Le **TopicGateService** analyse si le sujet est pertinent (Politique, Sport, Santé, Guerre)

> **Fichier source** : `app/services/topic_gate_service.py` et `app/api/routes/webhooks.py`

### Étape 4 : Recherche Sémantique (Retrieval)

La question de l'utilisateur est elle-même transformée en vecteur, puis comparée à tous les vecteurs d'articles de la base grâce à l'opérateur de **distance cosinus** (`<=>`) de pgvector. Les **5 articles les plus proches** sémantiquement sont extraits.

```sql
SELECT id, title, content, link
FROM articles
ORDER BY embedding <=> query_vector::vector
LIMIT 5
```

> **Fichier source** : `app/services/retrieval_service.py`

### Étape 5 : Génération du Verdict (LLM Mistral-7B)

Les articles trouvés servent de **contexte factuel** au modèle de langage Mistral-7B (exécuté localement via Ollama). Le LLM produit un verdict structuré :

- 🚨 **VÉRIFICATION** : VRAI / FAUX / IMPRÉCIS / NON VÉRIFIABLE
- 📝 **EXPLICATION** : Résumé factuel basé uniquement sur les sources
- 🔗 **SOURCES** : Liens vers les articles de référence

**Point crucial** : Si aucune source ne correspond dans la base, le bot **ne devine pas**. Il répond : `❌ NON VÉRIFIABLE — Je n'ai trouvé aucune source locale concernant cette information.`

> **Fichier source** : `app/services/llm_service.py` et `app/services/rag_service.py`

---

## 4. Comment fonctionne la Détection dans les Groupes WhatsApp ?

### 4.1. Mécanisme d'interception dans les groupes

Le comportement du bot change selon le **contexte** :

| Contexte | Comportement |
|---|---|
| **Message privé** (1-to-1) | Le bot répond **toujours** à chaque message |
| **Groupe WhatsApp/Telegram** | Le bot ne répond **que si le sujet est sensible** (Politique, Santé, Guerre, Sport) |

Le service `TopicGateService` est le **gardien** (gate) qui décide si le bot doit intervenir ou non dans un groupe.

### 4.2. Processus de classification (TopicGateService)

La classification fonctionne en mode **hybride** (IA + mots-clés) :

#### A) Classification par IA (Mistral-7B)
Le message est envoyé au modèle Mistral avec un prompt strict qui demande une réponse JSON :
```json
{
  "is_relevant": true,
  "theme": "politique",
  "confidence": 0.92,
  "reason": "Le message mentionne les élections présidentielles"
}
```

#### B) Classification par mots-clés (Fallback)
Si l'IA est indisponible ou incertaine, un dictionnaire de **mots-clés statiques** prend le relais :

| Thème | Mots-clés exemples |
|---|---|
| **Politique** | élection, gouvernement, ministre, parlement, président |
| **Santé** | hôpital, médecin, maladie, vaccin, épidémie |
| **Guerre** | conflit, attaque, armée, rebelle, violence, bombardement |
| **Sport** | football, match, tournoi, compétition, joueur |

#### C) Mots-clés dynamiques (Auto-apprentissage)
Le système enrichit automatiquement ses mots-clés en analysant les **2500 articles les plus récents** de la base. Il extrait les termes les plus fréquents par thème, élimine les stopwords, et les ajoute au dictionnaire. Ce rafraîchissement se fait toutes les **15 minutes**.

### 4.3. Seuil de confiance

Un message n'active le bot que si le score de confiance dépasse **0.6** (60%). En dessous, le message est ignoré silencieusement.

### 4.4. Détection du scope WhatsApp (Privé vs Groupe)

Le service `detect_whatsapp_scope()` analyse plusieurs champs du payload WhatsApp pour déterminer si le message vient d'un groupe :
- `message.chat_type`
- `message.recipient_type`
- `message.message_context.chat_type`
- `value.metadata.chat_type`
- `message.source == "group"`
- `message.is_group == true`

---

## 5. Comment fonctionne le Traitement des Images (Affiches, Captures d'écran) ?

Les fausses informations circulent souvent sous forme d'**images** (captures d'écran, affiches, montages). Le système les traite ainsi :

```
Image reçue (WhatsApp/Telegram)
        │
        ▼
┌──────────────────┐
│   Téléchargement │  ← API Meta/Telegram pour récupérer le fichier
│   du média       │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   OCR (Tesseract)│  ← Extraction du texte visible dans l'image
│   fra + eng      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Classification │  ← Le texte extrait est-il sur un sujet sensible ?
│   Thématique     │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│   Pipeline RAG   │  ← Recherche vectorielle + Verdict Mistral
│   Fact-Checking  │
└────────┬─────────┘
         │
         ▼
    Réponse envoyée au groupe/utilisateur
```

- **Technologie OCR** : Tesseract (langues : français + anglais)
- **Combinaison** : Le texte extrait de l'image est fusionné avec la légende (caption) éventuelle pour former la requête complète

> **Fichier source** : `app/services/ocr_service.py`

---

## 6. Stratégie contre la Surinformation

### 6.1. Le problème

En RDC, les utilisateurs WhatsApp sont submergés par un flux massif d'informations : articles, rumeurs, images virales, messages transférés. Cette **surinformation** rend difficile la distinction entre le vrai et le faux.

### 6.2. La solution : la « Surinformation Contrôlée »

L'approche du projet est inverse : plutôt que d'essayer de bloquer chaque rumeur, le système **occupe l'espace informationnel** avec des faits vérifiés :

1. **Filtrage thématique intelligent** : Le bot n'intervient que sur les 4 grands thèmes sensibles, évitant le bruit sur les conversations quotidiennes
2. **Synthèse condensée** : Au lieu de bombarder l'utilisateur d'articles entiers, Mistral-7B produit une **synthèse courte et structurée** (limitée à 160 tokens pour messagerie)
3. **Sources traçables** : Chaque réponse inclut les liens vers les articles originaux, permettant à l'utilisateur de vérifier par lui-même
4. **Corpus clos et curé** : Contrairement à ChatGPT ou Perplexity qui cherchent sur tout Internet, le système ne s'appuie que sur des **sources vérifiées de la presse congolaise**, éliminant les hallucinations

### 6.3. Avantages par rapport aux IA généralistes

| Critère | ChatGPT / Perplexity | RDC News Intelligence |
|---|---|---|
| **Source des données** | Internet entier | Corpus local vérifié (RDC) |
| **Hallucinations** | Possibles | Éliminées (corpus clos) |
| **Quand il ne sait pas** | Invente une réponse | Dit « NON VÉRIFIABLE » |
| **Langues / Contexte** | Généraliste | Optimisé pour le contexte congolais |
| **Accès** | App dédiée, payant | Directement dans WhatsApp/Telegram |

---

## 7. Les Statuts WhatsApp (Stories) — Limitation actuelle

> ⚠️ **Limitation importante** : Le système **ne traite pas encore les statuts (stories) WhatsApp**.

Les statuts éphémères constituent un vecteur majeur de désinformation en RDC. Cependant, la **WhatsApp Cloud API de Meta ne permet pas** d'accéder aux statuts des contacts. Il s'agit d'une limitation technique de l'API, pas de l'application.

### Pistes pour les versions futures :
- Permettre aux utilisateurs de **transférer manuellement** un statut suspect au bot (capture d'écran → OCR → RAG)
- Explorer des solutions complémentaires pour surveiller les flux visuels éphémères
- Intégration de la détection de **deepfakes audio** (pas encore supporté)

---

## 8. Résumé Technique des Services

| Service | Fichier | Rôle |
|---|---|---|
| **FastAPI (main)** | `app/main.py` | Point d'entrée, orchestration |
| **Webhooks** | `app/api/routes/webhooks.py` | Réception des messages WhatsApp/Telegram |
| **TopicGateService** | `app/services/topic_gate_service.py` | Classification thématique (garde du groupe) |
| **EmbeddingService** | `app/services/embedding_service.py` | Vectorisation sémantique des textes |
| **RetrievalService** | `app/services/retrieval_service.py` | Recherche vectorielle dans pgvector |
| **RAGService** | `app/services/rag_service.py` | Orchestration du pipeline Fact-Checking |
| **LLMService** | `app/services/llm_service.py` | Génération de réponses via Mistral-7B |
| **OCRService** | `app/services/ocr_service.py` | Extraction de texte depuis les images |
| **Crawler** | `app/services/crawler/` | Collecte automatique des actualités |
| **Scheduler** | `app/scheduler.py` | Tâches CRON (crawl + ré-embedding) |

---

## 9. Flux Complet — De la Rumeur au Verdict

```
1. Un utilisateur partage une rumeur dans un groupe WhatsApp
   │
   ▼
2. Le Webhook WhatsApp reçoit le message via l'API Meta
   │
   ▼
3. detect_whatsapp_scope() → C'est un GROUPE
   │
   ▼
4. TopicGateService.classify() → Thème: "politique", Confiance: 0.87
   │  (Résultat: should_activate = true → le bot intervient)
   ▼
5. EmbeddingService.generate(rumeur) → Vecteur [0.12, -0.34, 0.56, ...]
   │
   ▼
6. RetrievalService.search(vecteur) → 3 articles similaires trouvés
   │  (Radio Okapi, ACP, etc.)
   ▼
7. LLMService → Mistral-7B analyse les articles vs la rumeur
   │
   ▼
8. Réponse envoyée dans le groupe :

   🚨 VÉRIFICATION : FAUX
   📝 EXPLICATION : Selon Radio Okapi (12 mai 2026), cette
   information est inexacte. Les faits indiquent que...
   🔗 SOURCES :
   [1] Radio Okapi - Titre article - https://radiookapi.net/...
   [2] ACP - Titre article - https://acp.cd/...
```

---

## 10. Technologies Utilisées

| Composant | Technologie | Rôle |
|---|---|---|
| **Backend API** | FastAPI (Python) | Serveur asynchrone haute performance |
| **Base de données** | PostgreSQL + pgvector | Stockage relationnel + recherche vectorielle |
| **Modèle IA local** | Mistral-7B via Ollama | Génération de réponses (fact-checking) |
| **Embeddings** | SentenceTransformers (MiniLM) | Vectorisation multilingue des textes |
| **OCR** | Tesseract | Extraction de texte depuis les images |
| **Frontend** | Next.js 15 + React + TailwindCSS | Interface Web |
| **Messagerie** | WhatsApp Cloud API + Telegram Bot API | Intégration multicanale |
