# Chapitre 2 — Enchaînement théorique et pratique du mécanisme RDC News Intelligence

> **Support visuel :** diagrammes **tldraw** (`.tldr`) dans ce dossier, inspirés du schéma [`rdc news .jpeg`](../rdc%20news%20.jpeg).  
> **Objectif lecteur :** comprendre *pourquoi* le système est découpé en ligne / local, et *comment* chaque module s’enchaîne dans le code.

---

## 2.1. Problème adressé et principe d’architecture

### Surinformation et désinformation sur WhatsApp

Les utilisateurs reçoivent, dans des **conversations privées** et des **groupes**, des textes et des images qui **répètent la même information** (rumeurs, captures, liens). Le besoin est double :

1. **Vérifier** une affirmation par rapport à un **corpus d’actualités congolaises** fiable.
2. **Ne pas surcharger** le fil avec des réponses redondantes ou hors sujet.

### Principe retenu : séparation « ligne » / « local »

| Zone | Rôle théorique | Rôle pratique dans le projet |
|------|----------------|------------------------------|
| **Messagerie** | Point d’entrée et de sortie humain | WhatsApp via **Whapi.Cloud** (ou Meta Cloud API) |
| **Serveur en ligne** | Point d’accès **HTTPS public** stable | VPS `rooney-rdc.rooneykalumba.tech` — FastAPI, **file d’attente**, **relais** des réponses |
| **Machine locale** | Calcul intensif **sans exposer** Ollama / gros modèles | PC de dev : **polling**, **RAG**, **ChromaDB**, **Mistral** via `127.0.0.1:11434` |

**Pourquoi ne pas tout faire sur le VPS ?**  
La RAM nécessaire à Mistral (~4 Go+) et le chargement des modèles d’embedding sont plus simples en local ; le VPS reste une **passerelle légère** joignable par Whapi 24h/24.

**Pourquoi ne pas tout faire en local sans VPS ?**  
Whapi/Meta envoient les webhooks vers une **URL publique** ; une machine locale non exposée utilise le mode **PULL** : le local **demande** les messages en file sur le VPS.

→ Diagramme : **`00-vue-generale.tldr`**

---

## 2.2. Vue générale : les six étapes du schéma manuscrit

Le dessin [`rdc news .jpeg`](../rdc%20news%20.jpeg) numérote le flux ; voici la correspondance **théorie ↔ implémentation**.

| Étape | Schéma papier | Mécanisme | Code / endpoint |
|-------|---------------|-----------|-----------------|
| **①** | Message texte ou image | Utilisateur envoie dans WhatsApp (groupe ou classique) | — |
| **②** | Envoi en ligne | Whapi notifie le VPS | `POST /webhooks/whapi` |
| **③** | File d’attente | Payload stocké sans traitement IA lourd | `WHAPI_WEBHOOK_PROXY_ONLY=true` → `_enqueue_whapi_payload` |
| **④** | Polling + réponse | Local tire un message de la file | `ENABLE_WHAPI_QUEUE_POLLING` → `POST …/whapi/queue/pop` |
| **⑤** | Traiter | Topic gate + RAG + verdict | `process_whatsapp_message` → `RAGService` |
| **⑥** | Réponse | Texte renvoyé à l’utilisateur | `POST …/whapi/reply-relay` → API Whapi |

```
Utilisateur ──①──► WhatsApp ──► Whapi ──②──► VPS (enqueue ③)
                                              ▲      │
                                              │ ④ pop│
                                         Local (⑤ RAG)
                                              │
                                         relay ⑥ ──► Whapi ──► Utilisateur
```

---

## 2.3. Module 1 — Messagerie (entrée / sortie)

### Théorie

Le canal WhatsApp impose des contraintes : messages **texte**, **images**, groupes **bruyants**, pas d’accès direct à tout l’historique pour le bot. Le système doit **interpréter** chaque événement webhook comme une intention de vérification.

### Pratique

- **Groupe** : le **Topic Gate** filtre les sujets hors actualité RDC (`require_topic_gate=True`).
- **Discussion privée** : réponse plus systématique.
- **Image** : OCR (`OCRService` / Tesseract) puis le texte extrait alimente le même pipeline RAG.

→ Diagramme : **`01-module-messagerie.tldr`**  
→ Code : `parse_whapi_payload`, `process_whatsapp_message`, `process_whatsapp_image` dans `webhooks.py`.

---

## 2.4. Module 2 — Serveur en ligne (VPS)

### Théorie

Le serveur en ligne est un **répartiteur** : il authentifie les webhooks, **bufferise** les pics de messages et **détient les secrets** d’envoi Whapi (`WHAPI_TOKEN`) pour que la machine locale n’ait pas à les exposer.

### Pratique

| Fonction | Endpoint | Comportement |
|----------|----------|--------------|
| Réception | `POST /webhooks/whapi` | JSON Whapi → file si `PROXY_ONLY` |
| Distribution | `POST /webhooks/whapi/queue/pop` | Retourne un `item` ou vide |
| Restitution | `POST /webhooks/whapi/reply-relay` | Reçoit `{to, body}` du local → `whapi_send_text` |

Le schéma papier mentionne **OCR sur la ligne** : option possible sur le VPS ; dans l’implémentation actuelle, l’OCR est surtout exécuté **côté local** après récupération du payload (image URL ou `data:image`).

→ Diagramme : **`02-module-serveur-ligne.tldr`**

---

## 2.5. Module 3 — Pont local (polling)

### Théorie

Le **polling** transforme un modèle **push** (webhook) en modèle **pull** contrôlé : la machine locale décide quand elle est prête à traiter (RAM Ollama libre, file courte).

### Pratique

Au démarrage FastAPI (`main.py`), si `ENABLE_WHAPI_QUEUE_POLLING=true` :

1. Tâche asyncio `run_whapi_queue_polling()`.
2. Toutes les ~2 s : `POST WHAPI_QUEUE_POP_URL` avec `X-RDC-Queue-Token`.
3. Si `item` présent → `_dispatch_whapi_payload` → même logique que le webhook direct.

→ Diagramme : **`03-module-polling-local.tldr`**

---

## 2.6. Module 4 — Topic Gate (pertinence thématique)

### Théorie

Dans un groupe, la majorité des messages ne demandent pas une vérification factuelle. Le **Topic Gate** réduit le bruit : seuls les messages **liés à l’actualité RDC** (politique, sport, santé, guerre/sécurité) déclenchent le RAG.

### Pratique

1. Chargement de **mots-clés dynamiques** depuis Postgres (`TopicGateService`).
2. Heuristiques + appel **Ollama** pour classification si nécessaire.
3. `should_activate=False` → arrêt (option : message d’information si `TOPIC_GATE_REPLY_WHEN_IGNORED`).

**Lien chapitre 2 méthodologie :** c’est une forme de **filtrage amont** avant la recherche sémantique coûteuse.

→ Diagramme : **`04-module-topic-gate.tldr`**  
→ Code : `app/services/topic_gate_service.py`

---

## 2.7. Module 5 — Corpus, collecte et mémoire sémantique (ChromaDB)

### Théorie

Le RAG ne peut répondre que si un **corpus** d’articles structurés existe. La chaîne méthodologique du chapitre 2 s’applique ici :

1. **Collecte** (crawler, sources JSON).
2. **Nettoyage / dédoublonnage** (hash, lien unique).
3. **Vectorisation** (SentenceTransformers, 384 dimensions).
4. **Indexation** pour recherche par similarité.

### Pratique (évolution architecture)

| Donnée | Stockage | Rôle |
|--------|----------|------|
| Titre, contenu, lien, source | **PostgreSQL** | Source de vérité relationnelle |
| Embedding article | **ChromaDB** (`data/chroma_db`, collection `articles_rdc`) | Recherche cosinus à la volée |
| Ré-embedding | `train_pipeline.py`, `sync_to_chroma.py` | Maintenance du corpus |

Chaque nouvel article crawlé : `INSERT` Postgres + `vector_store_service.add_articles` (upsert Chroma).

→ Diagramme : **`05-module-corpus-chroma.tldr`**  
→ Code : `crawler/`, `article_service.py`, `vector_store_service.py`

---

## 2.8. Module 6 — Pipeline RAG (cœur du fact-checking)

### Théorie

Le **RAG** (Retrieval-Augmented Generation) enchaîne :

1. **Retrieval** — retrouver les passages les plus proches sémantiquement de la question.
2. **Augmentation** — injecter ces passages dans le prompt du LLM.
3. **Generation** — produire un verdict **borné** par les sources (anti-hallucination).

### Pratique (`RAGService.generate_answer_stream`, canal `whatsapp`)

| Ordre | Étape | Composant |
|-------|-------|-----------|
| 1 | Encoder la question | `EmbeddingService.generate` |
| 2 | Top-K articles | `RetrievalService` → ChromaDB |
| 3 | Re-ranking (optionnel) | `LLMService.rerank` (Mistral) |
| 4 | Filtrer par score | `RAG_MIN_SIMILARITY_MSG` (~0,40) |
| 5 | Garder 3 sources | `WHATSAPP_TOP_K` |
| 6 | Générer réponse | `LLMService.summarize_stream` |

Format imposé au modèle :

- 🚨 **VÉRIFICATION** : VRAI / FAUX / IMPRÉCIS / NON VÉRIFIABLE  
- 📝 **EXPLICATION**  
- 🔗 **SOURCES**

Si aucun article ne passe le seuil → message **NON VÉRIFIABLE** sans invention de faits.

→ Diagramme : **`06-module-pipeline-rag.tldr`**

---

## 2.9. Module 7 — Restitution vers WhatsApp

### Théorie

La réponse doit **retraverser** le VPS : seul le serveur en ligne possède le token Whapi pour l’envoi sortant. Le local ne contacte pas WhatsApp directement en mode relay.

### Pratique

1. Accumulation du texte streamé (`_stream_whatsapp_response`).
2. Découpage si > ~3800 caractères (`WHATSAPP_CHUNK_MAX_CHARS`).
3. `POST WHAPI_REPLY_RELAY_URL` avec `X-RDC-Relay-Token`.
4. VPS : `reply-relay` → `whapi_send_text` → utilisateur voit la bulle.

→ Diagramme : **`07-module-restitution.tldr`**

---

## 2.10. Synthèse : chaîne complète théorie → pratique

| Couche conceptuelle | Modules tldraw | Technologies |
|--------------------|----------------|--------------|
| Interface utilisateur | 01, 07 | WhatsApp, Whapi |
| Orchestration distribuée | 00, 02, 03 | FastAPI, file, polling HTTPS |
| Gouvernance du dialogue | 04 | Topic gate, Ollama |
| Données & mémoire | 05 | Crawler, Postgres, ChromaDB, embeddings |
| Intelligence vérifiable | 06 | RAG, Mistral, seuils similarité |

**Invariant du projet :** toute affirmation vérifiable doit être **ancrée** dans le corpus indexé ; le LLM **résume et juge** à partir des articles retrouvés, pas à partir de connaissances libres.

---

## 2.11. Pistes non implémentées (lien brouillon surinformation)

Voir [`../BROUILLON_ANTI_SURINFORMATION_WHATSAPP.md`](../BROUILLON_ANTI_SURINFORMATION_WHATSAPP.md) : cache par conversation, digest de groupe, fiches « histoire » — extensions possibles du même enchaînement pour **réduire la submersion** sans casser le flux ①–⑥.

---

## 2.12. Comment insérer ces diagrammes dans le mémoire

1. **Chapitre 2, § méthodologie** : figure `00-vue-generale.tldr` (export PNG depuis tldraw).
2. **§ collecte / préparation** : `05-module-corpus-chroma.tldr`.
3. **§ traitement messagerie** : enchaîner `01` → `03` → `04` → `06` → `07`.
4. **Annexe technique** : `02-module-serveur-ligne.tldr` (déploiement VPS).

Export tldraw : *File → Export as PNG/SVG* pour inclusion Word/LaTeX.

---

*Document de travail — aligné sur l’état du dépôt RDC News Intelligence (ChromaDB, mode Whapi PULL).*
