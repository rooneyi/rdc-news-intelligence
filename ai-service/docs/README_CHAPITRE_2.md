# Chapitre 2 — Architecture du flux : un serveur, Orchestrateur et Engine

| Attribut | Valeur |
|----------|--------|
| **Document** | README_CHAPITRE_2 |
| **Projet** | RDC News Intelligence |
| **Version** | 3.3 |
| **Statut** | Aligné schéma cible : **1 serveur** · blocs **Orchestrateur** + **Engine** |
| **Diagrammes sources** | Architecture Orchestrateur / Engine · Pipeline crawler (7 étapes) |
| **Normes de référence** | IEEE 830 (exigences), IEEE 1016 (description de conception), ISO/IEC/IEEE 42010 (architecture) |

---

## Table des matières

1. [Introduction](#1-introduction)  
2. [Références et conformité IEEE](#2-références-et-conformité-ieee)  
3. [Définitions, acronymes et abréviations](#3-définitions-acronymes-et-abréviations)  
4. [Vue d’ensemble du système](#4-vue-densemble-du-système)  
&nbsp;&nbsp;&nbsp;&nbsp;4.4 [Architecture Orchestrateur + Engine (schéma cible)](#44-architecture-globale--orchestrateur-et-engine-diagramme-de-référence)  
5. [Un seul serveur : Orchestrateur et Engine](#5-un-seul-serveur--orchestrateur-et-engine)  
6. [Description générale du flux bout en bout](#6-description-générale-du-flux-bout-en-bout)  
&nbsp;&nbsp;&nbsp;&nbsp;6.4 [Fonctionnement détaillé : du crawler à la réception (fake news & surinformation)](#64-fonctionnement-détaillé--du-crawler-à-la-réception-fake-news--surinformation)  
7. [Description détaillée des sous-modules](#7-description-détaillée-des-sous-modules)  
8. [Données, corpus et recherche sémantique](#8-données-corpus-et-recherche-sémantique)  
&nbsp;&nbsp;&nbsp;&nbsp;8.2 [Architecture mémoire duale : PostgreSQL et ChromaDB](#82-architecture-mémoire-duale--postgresql-et-chromadb)  
&nbsp;&nbsp;&nbsp;&nbsp;8.2.8 [Fonctionnement des deux BDD du début à la fin](#828-fonctionnement-des-deux-bdd-du-début-à-la-fin)  
&nbsp;&nbsp;&nbsp;&nbsp;8.4 [Pipeline crawler — alimentation du corpus (7 étapes)](#84-pipeline-crawler--alimentation-du-corpus-7-étapes)  
9. [Interfaces et points d’intégration](#9-interfaces-et-points-dintégration)  
10. [Évolutions prévues (anti-surinformation)](#10-évolutions-prévues-anti-surinformation)  
11. [Conclusion du chapitre](#11-conclusion-du-chapitre)  
12. [Documents et diagrammes associés](#12-documents-et-diagrammes-associés)

---

## 1. Introduction

### 1.1 Objet du document

Le présent document décrit, selon une structuration inspirée des normes **IEEE** en ingénierie logicielle, l’**architecture opérationnelle** du service **RDC News Intelligence** : un backend unique (`ai-service`, FastAPI) qui assure la vérification d’informations sur l’actualité de la République démocratique du Congo (RDC), notamment via **WhatsApp**.

Il complète le chapitre méthodologique sur la collecte et la préparation des données en précisant **comment les composants s’enchaînent** en production : du message utilisateur jusqu’à la réponse factuelle sourcée.

L’architecture cible retenue pour le chapitre 2 est celle du **schéma Orchestrateur / Engine** : **un seul serveur** (une instance `ai-service`) héberge deux blocs logiques — l’**Orchestrateur**, qui **transmet** les requêtes et les réponses vers WhatsApp/Telegram, et l’**Engine** (*Moteur*), qui **exécute** tout le traitement IA (OCR, Topic Gate, déduplication, RAG, LLM). Le **pipeline crawler** alimente le corpus en amont.

### 1.2 Portée (scope)

**Inclus :**

- Vue globale du flux (messagerie → **Orchestrateur** → **Engine** → Orchestrateur → utilisateur).
- Architecture détaillée **2.1–2.4** (Orchestrateur) et **4.1–4.9** (Engine) selon le schéma de référence.
- Pipeline **crawler** (sources → indexation ChromaDB).
- Rôle de chaque **sous-module** logiciel au sein de l’Engine et de l’Orchestrateur.
- Déploiement sur **un seul serveur** (les deux blocs coexistent dans `ai-service`).
- Architecture **mémoire duale** PostgreSQL + ChromaDB (§8.2).
- **Explication détaillée** du fonctionnement (§6.4) : crawler → corpus → message WhatsApp → fake news & surinformation.

**Hors portée :**

- Spécification détaillée de l’interface web Next.js (voir documentation frontend).
- Contrats juridiques Whapi / Meta.
- Spécification d’implémentation ligne à ligne du module M10 (la logique produit est en §6.4.5 et §10).

### 1.3 Public visé

- Lecteurs du mémoire / rapport (chapitre 2).
- Développeurs et intégrateurs du projet.
- Évaluateurs souhaitant une traçabilité **exigence → composant → flux**.

### 1.4 Contexte métier

Le système répond à deux problèmes liés :

1. **Désinformation** — vérifier une affirmation à partir d’un corpus local d’articles congolais.
2. **Surinformation** — éviter d’ajouter du bruit (réponses répétitives du bot) lorsque plusieurs messages portent le même sens (voir §6.4.5 et §10).

Le cœur rédactionnel du chapitre est la **section 6.4** : elle explique, dans l’ordre chronologique du système, comment chaque mécanisme contribue à la lutte contre les **fake news** (désinformation) et la **surinformation** (surcharge informationnelle).

---

## 2. Références et conformité IEEE

| Référence | Titre / usage dans ce document |
|-----------|--------------------------------|
| **IEEE Std 830-1998** | Structure des sections *Introduction, Description générale, Spécifications* — adaptée ici en description architecturale et flux. |
| **IEEE Std 1016-1998** | *Software Design Descriptions* — décomposition en sous-systèmes, interfaces, comportements. |
| **ISO/IEC/IEEE 42010:2022** | Description d’architecture : **parties prenantes**, **préoccupations**, **vues** (logique, déploiement, traitement). |
| **IEEE Std 1471-2000** (historique) | Précurseur des vues architecturales — conservé comme référence pédagogique. |

### 2.1 Préoccupations des parties prenantes (ISO/IEC/IEEE 42010)

| Partie prenante | Préoccupation | Vue / section |
|-----------------|---------------|---------------|
| Utilisateur WhatsApp | Réponse rapide, compréhensible, sourcée | §6, §7.7, §7.8 |
| Opérateur système | Disponibilité du webhook public 24h/24 | §5.1, §7.2 |
| Développeur | Un seul serveur, deux blocs logiques clairs | §5 |
| Analyste données | Corpus à jour, recherche pertinente | §8.2, §8.4 |
| Responsable contenu | Traçabilité des sources (liens articles) | §7.8 |

### 2.2 Vues architecturales fournies

| Vue | Description | Support |
|-----|-------------|---------|
| **Logique** | Services et dépendances (RAG, embedding, Chroma) | §4.4, §7 |
| **Déploiement** | Un serveur : Orchestrateur + Engine + Ollama | §4.4, §5, §6 |
| **Traitement données** | Crawler → Postgres → Chroma | §8.2, §8.4 |
| **Traitement** | Enchaînement des étapes sur un message | §6, §6.4, §7 |

---

## 3. Définitions, acronymes et abréviations

| Terme | Définition |
|-------|------------|
| **Serveur unique** | Une seule machine / une seule instance FastAPI (`ai-service`) exposée en HTTPS ; héberge **Orchestrateur** et **Engine**. |
| **Orchestrateur** | Bloc logique chargé de **transmettre** les requêtes : webhooks entrants, **file d’attente**, API résultats, **dispatch** sortant vers Whapi/Telegram. Ne fait pas le RAG. |
| **Engine (Moteur)** | Bloc logique chargé du **traitement** : récupération depuis la file, OCR, prétraitement, Topic Gate, déduplication conversationnelle, recherche sémantique, LLM, logs. |
| **Pont interne (3 / 9)** | Communication **à l’intérieur du même serveur** : polling de la file (étape 3) et envoi des résultats vers l’API résultats (étape 9). |
| **RAG** | *Retrieval-Augmented Generation* — récupération d’articles puis génération bornée par ces sources. |
| **Embedding** | Représentation vectorielle (384 dim.) du sens d’un texte. |
| **ChromaDB** | Base vectorielle locale persistante (`data/chroma_db`), collection `articles_rdc`. |
| **Topic Gate** | Filtre thématique (groupes) : politique, sport, santé, guerre/sécurité. |
| **Whapi** | Passerelle WhatsApp (Whapi.Cloud) utilisée pour webhooks et envoi. |
| **Polling (étape 3)** | L’Engine consomme la file de l’Orchestrateur via `queue/pop` (appel interne ou localhost). |
| **Envoi résultats (étape 9)** | L’Engine renvoie le verdict à l’Orchestrateur via `reply-relay` / API résultats. |
| **Déduplication conversationnelle** | Étape Engine **4.5** : clustering sémantique + cache court terme pour la **surinformation**. |
| **Top-K** | Nombre d’articles les plus proches retournés par la recherche vectorielle (ex. K=3 en messagerie). |
| **Similarité cosinus** | Mesure de proximité entre vecteurs ; ChromaDB utilise l’espace métrique `cosine`. |
| **Seuil de similarité** | Score minimal (ex. 0,40) pour qu’un article entre dans le contexte RAG. |
| **Re-ranking** | Réordonnancement des candidats par un LLM après la recherche vectorielle. |
| **FIFO** | Structure de file d’attente : premier message entrant, premier message distribué (`deque`). |
| **Webhook** | Callback HTTP déclenché par Whapi/Meta à chaque événement messagerie. |
| **OCR** | *Optical Character Recognition* — extraction de texte depuis une image (Tesseract). |
| **NLP / NER** | Traitement du langage ; extraction d’entités (cible évolutive du prétraitement). |
| **Chunking** | Découpage du texte en segments (cible architecture ; corpus actuel = article entier). |
| **Upsert** | Insertion ou mise à jour idempotente dans ChromaDB (`collection.upsert`). |
| **Fake news / désinformation** | Information fausse ou trompeuse diffusée comme une actualité ; objet principal de la **vérification** RAG. |
| **Surinformation** | Excès d’informations redondantes ou contradictoires ; le système vise à **ne pas l’amplifier** par des réponses bot répétées. |

---

## 4. Vue d’ensemble du système

### 4.1 Mission

RDC News Intelligence transforme un **corpus d’articles** (médias congolais) en **service de vérification** accessible par messagerie. Pour chaque question pertinente, le système :

1. Identifie les **articles les plus proches sémantiquement** (ChromaDB).
2. Produit un **verdict structuré** (VRAI, FAUX, IMPRÉCIS, NON VÉRIFIABLE) via un LLM local (Mistral / Ollama).
3. Cite les **sources** (titres et liens).

### 4.2 Composants majeurs (vue logique — schéma cible)

Le système est déployé sur **un seul serveur**. Deux blocs logiques coopèrent à l’intérieur de la même application FastAPI :

```
┌──────────────────────────────────────────────────────────────────────────┐
│  CANAUX : WhatsApp · Telegram (Whapi / Meta)                             │
└───────────────────────────────┬──────────────────────────────────────────┘
                                │ messages / réponses
┌───────────────────────────────▼──────────────────────────────────────────┐
│  SERVEUR UNIQUE — ai-service (FastAPI)                                   │
│  ┌─────────────────────────────┐    ┌─────────────────────────────────┐  │
│  │  ORCHESTRATEUR              │    │  ENGINE (Moteur)                │  │
│  │  · 2.1 API & Webhook        │◄──►│  · 4.1 Récupération             │  │
│  │  · 2.2 File d’attente       │ ③⑨ │  · 4.2 OCR · 4.3 Prétraitement  │  │
│  │  · 2.4 API Résultats        │    │  · 4.4 Topic Gate               │  │
│  │  · 2.3 Dispatch sortant     │    │  · 4.5 Dédup conversationnelle  │  │
│  └─────────────────────────────┘    │  · 4.6 RAG · 4.7–4.8 LLM        │  │
│                                     │  · 4.9 Journalisation           │  │
│                                     └──────────┬──────────────────────┘  │
│                                                │                           │
│                          PostgreSQL · ChromaDB · Ollama / Mistral        │
└──────────────────────────────────────────────────────────────────────────┘
         ▲
         │ alimentation corpus (hors flux message)
    [ Crawler → indexation ]
```

| Bloc | Rôle en une phrase | Ne fait pas |
|------|-------------------|-------------|
| **Orchestrateur** | **Transmet** : reçoit les webhooks, met en file, renvoie les verdicts aux utilisateurs | OCR, embeddings, RAG, verdict LLM |
| **Engine** | **Traite** : transforme chaque requête en réponse vérifiable sourcée | Envoi direct Whapi (passe par l’Orchestrateur) |

### 4.3 Hypothèse architecturale centrale

**Un serveur, deux responsabilités.**

- Physiquement : **une** instance déployée (VPS ou machine dédiée), **un** codebase `ai-service`.
- Logiquement : séparation nette **Orchestrateur** (couche transport / messagerie) vs **Engine** (couche intelligence).

Les étapes **③ Polling** et **⑨ Envoi des résultats** du schéma ne relient plus deux machines distantes : ce sont des **échanges internes** (même processus ou `localhost`) entre la file de l’Orchestrateur et le pipeline de l’Engine.

*Note historique :* une première version du projet séparait un VPS (webhook public) et un poste local (Ollama). L’architecture **cible** du chapitre 2 regroupe tout sur **un seul serveur** pour simplifier le déploiement ; les noms de routes (`queue/pop`, `reply-relay`) conservent la même sémantique qu’avant, mais comme **contrat interne** entre les deux blocs.

---

### 4.4 Architecture globale — Orchestrateur et Engine (diagramme de référence)

Cette section formalise le **schéma cible** du chapitre 2 : **un serveur unique** avec deux blocs — l’**Orchestrateur** (transmission) et l’**Engine** (traitement). Numérotation **2.x**, **③**, **4.x**, **⑨** = diagramme de référence.

#### 4.4.1 Acteurs et canaux

| Acteur | Canal | Rôle |
|--------|-------|------|
| **Utilisateur** | WhatsApp, Telegram (privé ou groupe) | Envoie une question, une rumeur ou une image à vérifier |
| **Passerelle** | Whapi.Cloud / Meta Cloud API | Transport ; webhooks entrants |
| **Orchestrateur** | Bloc du **même serveur** | **Transmet** requêtes et réponses — pas de RAG |
| **Engine** | Bloc du **même serveur** | **Traite** : OCR, Gate, dédup, RAG, LLM, logs |

#### 4.4.2 Bloc Orchestrateur — transmission des requêtes

| Réf. | Composant | Rôle | Implémentation |
|------|-----------|------|----------------|
| **2.1** | API & Webhook | Réception messages / questions | `POST /webhooks/whapi`, `/webhooks/whatsapp` |
| **2.2** | File d’attente | Buffer en attente de l’Engine | `_enqueue_whapi_payload`, FIFO |
| **2.4** | API Résultats | Réception réponse traitée ; statut « traité » | `POST /webhooks/whapi/reply-relay` |
| **2.3** | Dispatch sortant | Envoi verdict + sources à l’utilisateur | `whapi_send_text` |

**Propriété clé :** `200 OK` immédiat au webhook — l’Engine travaille en arrière-plan.

#### 4.4.3 Pont interne — étapes ③ et ⑨

| Étape | Sens | Endpoint |
|-------|------|----------|
| **③ Polling** | Engine ← file Orchestrateur | `POST …/queue/pop` (~1–2 s) |
| **⑨ Envoi résultats** | Engine → API résultats Orchestrateur | `POST …/reply-relay` |

Appels **internes** au même serveur (localhost ou même processus). Tokens : `X-RDC-Queue-Token`, `X-RDC-Relay-Token`.

#### 4.4.4 Bloc Engine (Moteur)

```
[4.1] → [4.2 OCR?] → [4.3] → [4.4 Topic Gate] → [4.5 Dédup conv.]
    → [4.6 RAG] → [4.7 Seuil] → [4.8 LLM] → [4.9 Logs] → ⑨
```

| Réf. | Étape | Rôle | Fake news / surinformation |
|------|-------|------|----------------------------|
| **4.1** | Récupération | Pop file ; éviter retraitement doublon technique | Anti-doublon file |
| **4.2** | OCR | Tesseract — texte depuis image | Rumeurs en capture |
| **4.3** | Prétraitement | Nettoyage, langue, NER | Requête stable |
| **4.4** | Topic Gate | Thèmes RDC ; sinon **ignorer** | Moins de bruit en groupe |
| **4.5** | **Dédup conversationnelle** | Embeddings + clustering + cache `chat_id` | **Surinformation** |
| **4.6** | Recherche sémantique | ChromaDB, Top-K | **Fake news** — corpus |
| **4.7** | Filtrage seuil | `RAG_MIN_SIMILARITY` → NON VÉRIFIABLE | Pas d’hallucination |
| **4.8** | Génération LLM | Mistral/Ollama — verdict + sources | Fact-check |
| **4.9** | Journalisation | Logs, métriques, historique | Audit |

*4.5 : cible §10 ; 4.1–4.4, 4.6–4.9 : opérationnels ou partiels (§7).*

#### 4.4.5 Flux utilisateur (schéma)

1. Message utilisateur → **2.1** webhook → file **2.2**  
2. **③** Engine consomme → **4.1…4.9**  
3. **⑨** → **2.4** → dispatch **2.3** → utilisateur  

#### 4.4.6 Un seul serveur (déploiement)

```
┌────────────────────────────────────────────────────┐
│  SERVEUR UNIQUE — ai-service                        │
│  ORCHESTRATEUR  ◄── ③ Polling · ⑨ Résultats ──►  ENGINE │
│  2.1·2.2·2.4·2.3              4.1 … 4.9              │
│              PostgreSQL · ChromaDB · Ollama           │
└────────────────────────────────────────────────────┘
```

---

## 5. Un seul serveur : Orchestrateur et Engine

### 5.1 Principe

Le chapitre 2 décrit **une machine**, **une application** (`ai-service`), **deux blocs logiques** :

| Bloc | Métaphore | Responsabilité |
|------|-----------|----------------|
| **Orchestrateur** | « Guichet messagerie » | **Transmet** : entrant (webhook, file) et sortant (API résultats, dispatch Whapi) |
| **Engine** | « Usine de vérification » | **Traite** : tout le pipeline IA jusqu’au verdict |

Cette séparation n’impose **pas** deux serveurs physiques. Les étapes **③** et **⑨** sont le **contrat interne** entre les deux blocs sur le **même hôte**.

### 5.2 Orchestrateur — ce qu’il fait et ne fait pas

| Fait ✓ | Ne fait pas ✗ |
|--------|----------------|
| Recevoir webhooks Whapi/Telegram | Embeddings, ChromaDB, Ollama |
| Mettre les payloads en file | Topic Gate, OCR, verdict LLM |
| Exposer `queue/pop` pour l’Engine | Décider VRAI/FAUX |
| Recevoir les résultats (`reply-relay`) | Crawler (hors file message) |
| Envoyer les bulles aux utilisateurs | |

### 5.3 Engine — ce qu’il fait et ne fait pas

| Fait ✓ | Ne fait pas ✗ |
|--------|----------------|
| Polling **③** de la file | Appeler Whapi directement (passe par Orchestrateur **⑨**) |
| OCR, prétraitement, Topic Gate | Répondre au webhook entrant (délégué à l’Orchestrateur) |
| Dédup conversationnelle **4.5** (cible) | |
| RAG + LLM (fake news) | |
| Envoyer le verdict à **2.4** via **⑨** | |

### 5.4 Table de répartition (vue logique — un serveur)

| Fonction | Orchestrateur | Engine |
|----------|---------------|--------|
| Webhook entrant **2.1** | ✓ | — |
| File **2.2** | ✓ | — |
| Polling **③** / `queue/pop` | expose | consomme |
| OCR · Gate · RAG · LLM **4.x** | — | ✓ |
| Envoi résultats **⑨** / `reply-relay` | reçoit | envoie |
| Dispatch sortant **2.3** | ✓ | — |
| PostgreSQL · Chroma · Ollama | — | ✓ (partagés sur le serveur) |
| Crawler (corpus) | — | ✓ (même serveur, hors file) |

### 5.5 Évolution par rapport au prototype deux machines

Une première version séparait VPS (webhook public) et poste local (Ollama). L’architecture **cible du mémoire** regroupe **Orchestrateur + Engine + bases + Ollama** sur **un serveur HTTPS unique**, ce qui correspond exactement au schéma fourni. Les routes `queue/pop` et `reply-relay` restent utiles comme **frontière logicielle** testable entre les deux blocs.

---

## 6. Description générale du flux bout en bout

Cette section correspond à la **vue de traitement** (IEEE 1016 — comportement global). Elle reprend le schéma manuscrit du projet ([`rdc news .jpeg`](rdc%20news%20.jpeg)) : six étapes numérotées.

### 6.1 Diagramme de flux (niveau 0 — un serveur)

```
[Utilisateur] ──①──► [WhatsApp / Telegram] ──②──► [Whapi]
                              │
                              ▼
              ┌───────────────────────────────────────┐
              │         SERVEUR UNIQUE               │
              │  [Orchestrateur] 2.1 webhook → 2.2 file
              │        ▲              │              │
              │        │ ⑨            │ ③            │
              │        │         [Engine] 4.1→4.9    │
              │        └──────── 2.4 · 2.3 dispatch  │
              └───────────────────────────────────────┘
                              │
                              ▼
                        [Utilisateur]
```

### 6.2 Table des étapes (traçabilité)

| Étape | Bloc | Action | Résultat attendu |
|-------|------|--------|------------------|
| ① | Utilisateur | Envoie message (texte / image) | Événement messagerie |
| ② | Orchestrateur **2.1** | Webhook Whapi reçu | Payload en file **2.2** |
| ③ | Engine | Polling interne `queue/pop` | Un message à traiter |
| ④ | Engine **4.1–4.9** | Pipeline IA complet | Verdict + sources |
| ⑤ | Orchestrateur **2.4** | Réception via `reply-relay` (**⑨**) | Statut traité |
| ⑥ | Orchestrateur **2.3** | Dispatch Whapi | Bulle(s) utilisateur |

### 6.3 Flux parallèles (hors WhatsApp)

Le même backend sert :

- **Interface web** : `POST /rag`, `POST /rag/stream` (canal `web`).
- **Telegram** : webhooks ou polling selon configuration.
- **Alimentation corpus** : crawler → `POST /crawler/articles` → Postgres + Chroma.

Ces flux **partagent** les modules RAG, embedding et Chroma (section 7.6–7.8), sans repasser par la file Whapi.

---

### 6.4 Fonctionnement détaillé : du crawler à la réception (fake news & surinformation)

Cette section constitue le **fil conducteur** du chapitre 2. Elle décrit le système dans l’**ordre réel d’exécution** : d’abord la construction d’une **mémoire factuelle** (corpus), puis la **réception** des messages utilisateurs, enfin les mécanismes qui traitent la **désinformation** (fake news) et limitent la **surinformation**.

#### 6.4.1 Deux problèmes, deux réponses techniques

Sur WhatsApp, l’utilisateur est confronté à deux phénomènes distincts mais souvent confondus :

| Phénomène | Définition | Exemple concret | Réponse du système |
|-----------|------------|-----------------|-------------------|
| **Fake news (désinformation)** | Affirmation fausse ou non étayée présentée comme un fait | « Le président a démissionné cette nuit » (sans source fiable) | **Vérification RAG** : comparer l’affirmation au corpus d’articles congolais et produire un **verdict** sourcé |
| **Surinformation** | Trop de messages sur le **même sujet**, répétés par plusieurs personnes ou le bot | Cinq amis envoient la même capture ; le bot répondrait cinq fois la même analyse | **Filtrage et consolidation** : ne pas multiplier les réponses ; regrouper le même **sens** (voir §6.4.5) |

Le système ne peut pas supprimer les messages des autres participants dans un groupe WhatsApp. En revanche, il peut (1) **ne pas inventer** de faits lorsqu’il répond, et (2) **ne pas devenir une source supplémentaire de bruit** en répétant la même vérification à chaque message quasi identique.

#### 6.4.2 Phase A — Alimentation du corpus (crawler → PostgreSQL → ChromaDB)

**Objectif :** disposer d’une base de **référence journalistique** sur l’actualité de la RDC, exploitable par recherche sémantique. Sans cette phase, toute réponse sur une fake news serait une simple opinion du modèle de langage — ce que le projet refuse explicitement.

**Étape A.1 — Définition des sources**

Les médias cibles sont déclarés dans `data/crawler/sources.json` (Radio Okapi, Actualité.cd, 7sur7.cd, etc.). Chaque entrée possède un `source_id`, des URLs de départ et des critères implicites : langue française, périmètre géographique RDC, thématiques d’actualité.

**Étape A.2 — Collecte HTTP**

Le script `python -m app.services.crawler.scripts.sync` instancie un `SyncCrawler` qui parcourt les URLs configurées. Pour chaque lien, une requête HTTP est exécutée via `SyncHttpClient`. Les erreurs réseau (timeout, 404) sont journalisées sans interrompre l’ensemble du lot : le crawler est **résilient** par conception.

**Étape A.3 — Extraction structurée**

Le HTML est analysé avec BeautifulSoup. Le titre provient des balises Open Graph ou du `<title>` ; le corps est extrait prioritairement depuis la balise `<article>`, sinon depuis les paragraphes `<p>`. Les métadonnées (URL canonique, image OG) accompagnent l’article. Cette étape transforme une page web en un objet `Article` structuré (titre, corps, lien, hash).

**Étape A.4 — Prétraitement et premier anti-doublon (niveau corpus)**

Le texte est nettoyé (`sanitize_text`). Un **hash** dérivé de l’URL garantit l’unicité : si le même article est crawlé deux fois, PostgreSQL rejette le doublon (`ON CONFLICT` sur le lien ou le hash). Ce mécanisme lutte contre une forme de **surinformation dans la base** : indexer dix fois le même communiqué fausserait la recherche vectorielle (poids artificiel du même contenu).

**Étape A.5 — Persistance et injection**

Chaque article valide est d’abord écrit en JSONL local (`JsonlPersistor`), puis transmis au backend via `BackendForwarder` (`POST /crawler/articles` ou équivalent batch). Le service `article_service` insère la ligne en base relationnelle.

**Étape A.6 — Vectorisation et index ChromaDB**

À l’insertion (ou via `sync_to_chroma.py` / `train_pipeline`), le contenu est encodé par le modèle **paraphrase-multilingual-MiniLM-L12-v2** (vecteur de **384 dimensions**). Le vecteur et les métadonnées (titre, lien, source) sont **upsertés** dans la collection Chroma `articles_rdc`, avec métrique **cosinus**. C’est la **mémoire sémantique** du système : elle permet de retrouver des articles « proches en sens » d’une question utilisateur, même si les mots diffèrent.

```
[Crawler] → JSONL → API articles → [PostgreSQL] → Embedding → [ChromaDB]
                                      ↑
                         référence catalogue + admin + Topic Gate dynamique
```

**Lien avec les fake news :** le corpus n’est pas une vérité absolue, mais un **ensemble de sources journalistiques identifiées**. Le RAG ne « invente » pas : il **raisonne à partir de ces extraits**. Si aucun article du corpus ne traite du sujet, le système doit répondre **NON VÉRIFIABLE** plutôt que de confirmer ou infirmer une rumeur.

#### 6.4.3 Phase B — Réception du message (Orchestrateur → Engine, même serveur)

**Objectif :** faire entrer la requête utilisateur par l’**Orchestrateur**, la mettre en file, puis la confier à l’**Engine** pour traitement — le tout sur **un seul serveur**.

**Étape B.1 — Émission côté utilisateur**

L’utilisateur envoie un message dans un **groupe** ou en **message privé** (texte, rumeur, capture). WhatsApp / Telegram transporte ; **Whapi** déclenche un webhook vers le serveur.

**Étape B.2 — Orchestrateur : webhook et file (2.1 → 2.2)**

L’**Orchestrateur** reçoit `POST /webhooks/whapi`. Il **ne lance pas** le RAG : il place le JSON dans la **file d’attente** et répond `200 OK` immédiatement. Son rôle est uniquement de **transmettre** et de **bufferiser** les requêtes.

**Étape B.3 — Engine : récupération via polling ③ (4.1)**

L’**Engine** consomme la file par `POST /webhooks/whapi/queue/pop` (boucle ~2 s, `run_whapi_queue_polling`). C’est l’étape **③** du schéma : communication **interne** entre les deux blocs sur le même hôte. `_dispatch_whapi_payload` parse le message et route vers texte ou image.

**Étape B.4 — Parsing et périmètre**

Extraction de `chat_id`, texte, distinction groupe / privé. En groupe : `require_topic_gate=True` (phase C, étape **4.4**).

**Lien surinformation :** tant que l’étape Engine **4.5** (dédup conversationnelle) n’est pas active, chaque message en file peut encore déclencher un passage RAG complet (§6.4.5, §10).

#### 6.4.4 Phase C — Traitement dans l’Engine (4.2 → 4.9)

**Objectif :** tout le travail IA s’exécute dans le bloc **Engine** : fake news (RAG + LLM) et surinformation (Gate + dédup **4.5**).

**Étape C.1 — OCR — Engine 4.2 (si image)**

Les fake news circulent souvent sous forme d’**affiches** ou de **captures** sans texte sélectionnable. `OCRService` (Tesseract) extrait les caractères de l’image (URL Whapi ou données `data:image` inline). Le texte OCR est fusionné avec une éventuelle légende WhatsApp, puis soumis aux étapes suivantes comme un message texte classique.

**Étape C.2 — Topic Gate — Engine 4.4 (thématisation)**

`TopicGateService.classify` évalue si le message relève de l’actualité RDC dans les thèmes **politique**, **sport**, **santé**, **guerre/sécurité**. La décision combine :

1. des **mots-clés statiques** par thème ;
2. des **mots-clés dynamiques** tirés des titres récents en PostgreSQL ;
3. une **classification LLM** (Mistral via Ollama, sortie JSON) ;
4. un seuil de confiance `TOPIC_GATE_MIN_CONFIDENCE` (défaut **0,6**).

Si `should_activate=false`, le message est **ignoré** (log uniquement, ou message d’information court si `TOPIC_GATE_REPLY_WHEN_IGNORED` est activé). Ce filtre réduit la **surinformation générée par le bot** : pas de fact-check sur les blagues, les salutations ou les sujets hors périmètre RDC.

**Étape C.2 bis — Déduplication conversationnelle — Engine 4.5 (surinformation, cible)**

Avant le RAG coûteux, l’Engine compare l’embedding du message aux messages récents du même `chat_id` (**clustering sémantique**, cache court terme). Si le sujet a déjà été traité : réponse courte « déjà vérifié » sans rappeler Mistral sur tout le contexte. C’est le cœur anti-**surinformation** du schéma ; implémentation en cours (§10).

**Étape C.3 — Recherche sémantique RAG — Engine 4.6**

La question (texte ou OCR) est vectorisée avec le **même modèle** que le corpus. `RetrievalService` interroge ChromaDB et récupère les **K** articles les plus proches (K=3 par défaut sur WhatsApp via `WHATSAPP_TOP_K`). La similarité est calculée par `similarity = 1 - distance_cosinus`.

**Point crucial pour les fake news :** deux formulations différentes d’une même rumeur (« il a démissionné » / « le chef de l’État quitte le pouvoir ») peuvent pointer vers les **mêmes articles** du corpus, car la recherche est **sémantique**, pas lexicale.

**Étape C.4 — Filtrage par seuil — Engine 4.7**

`RAGService._filter_relevant_articles` écarte les articles dont `similarity < RAG_MIN_SIMILARITY_MSG` (défaut **0,40** sur messagerie). Si **aucun** article ne passe le seuil, le pipeline n’envoie pas de contexte au LLM : la réponse attendue est **NON VÉRIFIABLE** — le système refuse de « deviner » la vérité d’une fake news non couverte par les médias indexés.

**Étape C.5 — Re-ranking (optionnel)**

Si `RAG_ENABLE_RERANK=true` et plusieurs candidats subsistent, Mistral réordonne les articles par pertinence factuelle par rapport à la question. Cela améliore la qualité du contexte avant génération, sans changer le principe d’**ancrage corpus**.

**Étape C.6 — Génération du verdict — Engine 4.8 (LLM)**

`LLMService.summarize_stream` construit un prompt de type **fact-checker** : consignes strictes, extraits des articles retenus, interdiction d’hallucination. Le modèle produit en streaming :

- **VÉRIFICATION** : VRAI, FAUX, IMPRÉCIS ou NON VÉRIFIABLE ;
- **EXPLICATION** : synthèse en français, calée sur les sources ;
- **SOURCES** : titres et liens des articles utilisés.

Le verdict est une **décision qualitative** du LLM sur des preuves textuelles, distincte du seuil numérique de l’étape C.4 (qui ne contrôle que l’**admission** des articles dans le prompt).

**Étape C.7 — Journalisation — Engine 4.9**

Traces, latence, succès/échec — historique des requêtes pour le monitoring.

**Étape C.8 — Retour Orchestrateur (⑨ → 2.4 → 2.3)**

L’Engine envoie le verdict à l’**Orchestrateur** via `reply-relay` (étape **⑨**). L’Orchestrateur met à jour l’API **résultats 2.4**, puis **dispatch 2.3** vers Whapi/Telegram (découpage si > ~3800 caractères).

```
Utilisateur → Orchestrateur (2.1·2.2) → ③ Engine : OCR? → 4.4 Gate → 4.5 Dédup?
    → 4.6 Chroma → 4.7 Seuil → 4.8 LLM → 4.9 Logs → ⑨ Orchestrateur (2.4·2.3) → Utilisateur
```

#### 6.4.5 Phase D — Surinformation : mécanismes actuels et cible

La **surinformation** n’est pas traitée par un seul module : elle est adressée à **plusieurs niveaux** du système.

**Niveau 1 — Corpus (déjà en place)**

| Mécanisme | Rôle anti-surinformation |
|-----------|--------------------------|
| Dédoublonnage à l’ingestion (`hash`, lien unique) | Un même article média n’occupe pas plusieurs places dans l’index |
| Un embedding par article | Évite une redondance vectorielle artificielle |
| Top-K limité (3) | La réponse cite peu de sources, lecture plus courte |

**Niveau 2 — Filtrage à l’entrée (déjà en place)**

| Mécanisme | Rôle |
|-----------|------|
| Topic Gate en groupe | Le bot ne répond pas à tous les messages du fil |
| Seuil de similarité RAG | Pas de longues réponses « inventées » hors sujet corpus |
| NON VÉRIFIABLE | Évite de rajouter une fausse certitude sur une rumeur non documentée |

**Niveau 3 — Conversation (partiellement prévu, pas encore complet)**

Aujourd’hui, si **dix personnes** envoient la même rumeur dans un groupe en dix minutes, le bot peut encore produire **dix réponses** quasi identiques — il traite **chaque message** indépendamment. La vision produit (détaillée en §10) prévoit :

1. **Fusion à l’entrée** — buffer par `chat_id` (30–60 s) : plusieurs messages de même sens → **un seul** passage RAG ;
2. **Mémoire de chat** — embedding de la question déjà traitée → réponse courte « déjà vérifié » + lien vers une fiche stable ;
3. **Sortie consolidée** — une **story card** par sujet (verdict + sources), sans répéter le long texte Mistral.

**Insertion dans l’Engine (schéma étape 4.5) :**

```
4.4 Topic Gate → [4.5 Dédup conversationnelle] → 4.6 RAG → 4.7 Seuil → 4.8 LLM → ⑨ Orchestrateur
```

**Ce que le chapitre doit retenir :** la lutte contre les **fake news** repose sur le **RAG ancré corpus** (phases A et C) ; la lutte contre la **surinformation** combine déjà le Topic Gate et les seuils, et s’achèvera par la **déduplication conversationnelle** (phase D niveau 3).

#### 6.4.6 Chronologie de synthèse (vue unique)

| Ordre | Phase | Composant principal | Problème adressé |
|-------|-------|---------------------|------------------|
| 1 | Sources & crawl | `SyncCrawler`, `sources.json` | Constituer une base factuelle RDC |
| 2 | Indexation | PostgreSQL + ChromaDB | Mémoire sémantique pour le retrieval |
| 3 | Message entrant | Orchestrateur **2.1** → file **2.2** | Réception HTTPS |
| 4 | Pont **③** | Engine **4.1** `queue/pop` | Même serveur |
| 5 | OCR | `OCRService` | Fake news en image |
| 6 | Topic Gate | `TopicGateService` | Réduire le bruit en groupe |
| 7 | Retrieval + seuil | Chroma + `RAG_MIN_SIMILARITY_MSG` | Ancrage et refus hors corpus |
| 8 | Verdict LLM | Ollama / Mistral | Fake news : VRAI/FAUX/IMPRÉCIS/NON VÉRIFIABLE |
| 9 | Relay sortant | `reply-relay` | Réponse sourcée à l’utilisateur |
| *10* | *Dédup chat* | *M10 (prévu)* | *Surinformation : une réponse par sujet* |

#### 6.4.7 Exemple narratif (scénario de bout en bout)

*Contexte :* un groupe WhatsApp reçoit le message « Le gouvernement aurait signé un décret secret sur la monnaie ».

1. **Corpus (en amont)** — Le crawler a déjà indexé des articles de Actualité.cd et Radio Okapi sur la politique monétaire ; ils sont dans ChromaDB.
2. **Orchestrateur** — Whapi → webhook **2.1** → file **2.2**.
3. **Engine** — Polling **③** ; Topic Gate **4.4** détecte *politique* + *RDC* (confiance > 0,6).
4. **RAG** — La requête est embeddée ; Chroma retourne trois articles dont deux dépassent le seuil 0,40 (débat parlementaire, pas de « décret secret »).
5. **Verdict** — Mistral répond **IMPRÉCIS** : les sources parlent de réforme discutée, pas d’un décret secret ; liens cités.
6. **Surinformation** — Si quatre autres messages reformulent la même rumeur, **aujourd’hui** quatre réponses similaires partent ; **demain** (M10) une seule fiche serait renvoyée, les suivants recevant « 📌 Déjà vérifié — IMPRÉCIS : … ».

Ce scénario illustre la **complémentarité** des deux volets : le RAG combat la **fausseté** par les sources ; la dédup future combat la **répétition** du service.

---

## 7. Description détaillée des sous-modules

Chaque sous-module est décrit selon le canevas IEEE 1016 : **Objectif**, **Entrées**, **Sorties**, **Traitement**, **Dépendances**, **Déploiement typique**.

**Correspondance avec le diagramme architecture RAG (§4.4) :**

| Module projet | Bloc | Réf. Engine |
|---------------|------|-------------|
| M2 Orchestrateur | Orchestrateur | 2.1–2.4, 2.3 |
| M3 Pont polling | Engine ↔ Orchestrateur | ③ · 4.1 |
| M9 OCR | Engine | 4.2 |
| M4 Topic Gate | Engine | 4.4 |
| M10 Dédup (cible) | Engine | 4.5 |
| M6 Retrieval | Engine | 4.6 |
| M7 RAG + LLM | Engine | 4.7 + 4.8 |
| M8 Restitution | Orchestrateur | ⑨ → 2.4 → 2.3 |
| M5 Corpus | Engine (crawler) | alimente 4.6 |

---

### 7.1 Module M1 — Messagerie (entrée / sortie)

| Attribut | Description |
|----------|-------------|
| **Objectif** | Être l’interface utilisateur : recevoir les messages et délivrer les réponses. |
| **Entrées** | Événements Whapi (`messages[]`) : texte, image, métadonnées `chat_id`, groupe/DM. |
| **Sorties** | Payload normalisé vers orchestrateur ou traitement ; messages utilisateur finaux. |
| **Traitement** | Parsing (`parse_whapi_payload`), distinction groupe (`is_group`) vs privé, routage texte/image. |
| **Dépendances** | Whapi.Cloud ; optionnel Meta Cloud API. |
| **Déploiement** | Externe au backend ; le backend ne fait que réagir aux webhooks. |

**Règle métier :** en **groupe**, le Topic Gate (M4) s’applique avant le RAG ; en **privé**, le traitement est en général plus permissif.

**Diagramme :** `tdraw/01-module-messagerie.tldr`

---

### 7.2 Module M2 — Orchestrateur (transmission)

| Attribut | Description |
|----------|-------------|
| **Objectif** | **Transmettre** les requêtes et réponses messagerie ; ne pas exécuter l’Engine. |
| **Entrées** | Webhooks Whapi/Telegram ; `reply-relay` depuis l’Engine (**⑨**). |
| **Sorties** | File **2.2** ; bulles utilisateur via **2.3** ; `queue/pop` pour l’Engine (**③**). |
| **Traitement** | `_enqueue_whapi_payload` ; `queue/pop` ; `whapi_send_text`. |
| **Dépendances** | `WHAPI_TOKEN` ; HTTPS public. |
| **Déploiement** | Bloc logique sur le **serveur unique** (§5). |

**Diagramme :** `tdraw/02-module-serveur-ligne.tldr`

---

### 7.3 Module M3 — Pont Engine ↔ Orchestrateur (③ et ⑨)

| Attribut | Description |
|----------|-------------|
| **Objectif** | Lier la file de l’Orchestrateur au pipeline de l’Engine sur le **même serveur**. |
| **Entrées** | File **2.2** ; verdict produit par l’Engine. |
| **Sorties** | Item consommé (**4.1**) ; POST `reply-relay` (**⑨**). |
| **Traitement** | `run_whapi_queue_polling` ; `_dispatch_whapi_payload`. |
| **Dépendances** | M2 (Orchestrateur) ; M4–M7 (Engine). |
| **Déploiement** | Même instance `ai-service` ; appels internes possibles en localhost. |

**Diagramme :** `tdraw/03-module-polling-local.tldr`

---

### 7.4 Module M4 — Topic Gate (thématisation du message)

| Attribut | Description |
|----------|-------------|
| **Objectif** | Décider si un message de **groupe** mérite une vérification (actualité RDC). |
| **Entrées** | Texte utilisateur (ou OCR). |
| **Sorties** | `TopicDecision` : `should_activate`, `theme`, `confidence`, `reason`. |
| **Traitement** | (1) Mots-clés statiques par thème ; (2) mots-clés **dynamiques** issus des derniers articles Postgres ; (3) classification Mistral/Ollama (JSON) ; (4) seuil `TOPIC_GATE_MIN_CONFIDENCE` (défaut 0,6). |
| **Dépendances** | Ollama ; Postgres (mots-clés dynamiques). |
| **Déploiement** | Bloc **Engine**, même serveur (Ollama local au serveur). |

**Thèmes autorisés :** `politique`, `sport`, `santé`, `guerre` (sécurité / conflit).

**Si `should_activate=false` :** pas de RAG ; message ignoré (ou message d’information si configuré).

**Diagramme :** `tdraw/04-module-topic-gate.tldr`

---

### 7.5 Module M5 — Corpus, ingestion et mémoire sémantique

| Attribut | Description |
|----------|-------------|
| **Objectif** | Maintenir une base d’articles exploitable pour la recherche de proximité. |
| **Entrées** | URLs médias (`sources.json`), articles crawlés, chargements dataset. |
| **Sorties** | Lignes Postgres ; vecteurs dans ChromaDB. |
| **Traitement** | Crawler → nettoyage → `INSERT` Postgres (sans doublon lien/hash) → `EmbeddingService` → `upsert` Chroma ; maintenance via `train_pipeline` / `sync_to_chroma`. |
| **Dépendances** | PostgreSQL ; ChromaDB ; SentenceTransformers. |
| **Déploiement** | Bloc **Engine** sur le serveur unique ; crawler et Chroma co-localisés. |

**Séparation des rôles de stockage :**

| Stockage | Contenu | Rôle dans le flux |
|----------|---------|-------------------|
| **PostgreSQL** | Titre, contenu, lien, source, hash, dates, `training_runs` | Source de vérité, admin, Topic Gate (§8.2) |
| **ChromaDB** | Embeddings 384D + métadonnées + texte | Retrieval RAG, seuil similarité (§8.2) |

**Diagrammes :** `tdraw/05-module-corpus-chroma.tldr` · BDD `assets/image-5ef0032c-*.png`

---

### 7.6 Module M6 — Recherche des articles les plus proches (retrieval)

| Attribut | Description |
|----------|-------------|
| **Objectif** | Sélectionner les **k** articles du corpus dont le **sens** est le plus proche de la question. |
| **Entrées** | Texte de la requête utilisateur. |
| **Sorties** | Liste ordonnée d’`ArticleOut` avec score `similarity` ∈ [0, 1]. |
| **Traitement** | (1) Embedding de la question (même modèle que le corpus) ; (2) requête Chroma (distance cosinus) ; (3) conversion distance → similarité ; (4) récupération d’environ `3 × top_k` candidats pour la marge de filtrage. |
| **Dépendances** | M5 (Chroma à jour) ; `EmbeddingService`. |
| **Déploiement** | Bloc **Engine**, serveur unique. |

**Détail technique (étape diagramme 4.5) :**

1. **Encodage** — la requête utilisateur est transformée en vecteur ℝ³⁸⁴ par SentenceTransformers (modèle multilingue, adapté au français congolais).
2. **Requête ANN** — ChromaDB exécute une recherche approximative des plus proches voisins (index HNSW, espace `cosine`).
3. **Top-K** — paramètre `WHATSAPP_TOP_K` (défaut **3**) : les K articles avec la plus forte similarité sont candidats au contexte LLM.
4. **Score** — `similarity = 1 - distance` ; plus le score est proche de **1**, plus le sens de l’article est aligné avec la question.

**En bref :** ce n’est pas une recherche par mots-clés SQL (`LIKE`, full-text) ; c’est une **proximité sémantique** dans l’espace vectoriel — deux formulations différentes d’une même rumeur peuvent converger vers les mêmes articles.

**Seuil ultérieur :** voir M7 — seuls les articles avec `similarity ≥ RAG_MIN_SIMILARITY_MSG` (défaut **0,40** sur WhatsApp) sont conservés.

---

### 7.7 Module M7 — Pipeline RAG (génération du verdict)

| Attribut | Description |
|----------|-------------|
| **Objectif** | Produire une réponse **bornée aux sources** récupérées en M6. |
| **Entrées** | Requête ; liste d’articles filtrés (souvent 3). |
| **Sorties** | Flux texte : VÉRIFICATION, EXPLICATION, SOURCES ; événements `sources` pour l’UI. |
| **Traitement** | (1) Rerank optionnel (Mistral, `RAG_ENABLE_RERANK`) ; (2) filtre seuil similarité ; (3) `summarize_stream` — prompt fact-checker strict ; (4) si aucun article : **NON VÉRIFIABLE** sans hallucination. |
| **Dépendances** | Ollama ; M6. |
| **Déploiement** | Bloc **Engine**, serveur unique. |

**Détail technique (étapes diagramme 4.6–4.7) :**

| Sous-étape | Mécanisme | Paramètre |
|------------|-----------|-----------|
| **Filtrage similarité** | Rejette les articles dont `similarity < seuil` | `RAG_MIN_SIMILARITY_MSG=0.40` (WhatsApp) |
| **Re-ranking** | Le LLM réordonne les candidats par pertinence factuelle | `RAG_ENABLE_RERANK` (désactivable si RAM limitée) |
| **Prompt engineering** | Contexte = extraits Top-K ; consignes anti-hallucination | `LLMService.summarize_stream` |
| **Génération** | Inférence locale Mistral via Ollama (`/api/generate`, stream) | `OLLAMA_HOST`, modèle quantifié |
| **Verdict** | Classification qualitative sur les preuves fournies | VRAI · FAUX · IMPRÉCIS · NON VÉRIFIABLE |

**Distinction importante :** le **seuil numérique** (4.6) contrôle *quels articles* entrent dans le prompt ; le **verdict** (4.7) est une *décision sémantique* du LLM sur ces articles — un article au-dessus du seuil peut quand même mener à IMPRÉCIS si les sources sont contradictoires.

**Diagramme :** `tdraw/06-module-pipeline-rag.tldr`

---

### 7.8 Module M8 — Restitution (relay et messagerie)

| Attribut | Description |
|----------|-------------|
| **Objectif** | Renvoyer la réponse à l’utilisateur sans exposer `WHAPI_TOKEN` sur le local. |
| **Entrées** | Texte agrégé du stream RAG ; `chat_id` destinataire. |
| **Sorties** | Message WhatsApp (éventuellement découpé si > ~3800 caractères). |
| **Traitement** | Engine envoie via **⑨** ; Orchestrateur reçoit `reply-relay` et appelle Whapi (**2.3**). |
| **Dépendances** | M2 (Orchestrateur) ; M7 (Engine). |
| **Déploiement** | **⑨** interne au serveur unique. |

**Diagramme :** `tdraw/07-module-restitution.tldr`

---

### 7.9 Module M9 — OCR (images)

| Attribut | Description |
|----------|-------------|
| **Objectif** | Transformer une image (capture, affiche) en texte interrogeable par M4–M7. |
| **Entrées** | URL média Whapi ou `data:image` inline. |
| **Sorties** | Chaîne de caractères → même pipeline que le texte. |
| **Traitement** | Tesseract via `OCRService` ; puis Topic Gate et RAG. |
| **Dépendances** | Pillow, pytesseract. |
| **Déploiement** | Bloc **Engine** (après récupération **4.1**). |

---

### 7.10 Synthèse des enchaînements par module (table IEEE — traçabilité)

| Ordre | Module | Précédent | Suivant |
|-------|--------|-----------|---------|
| 1 | M1 Messagerie | Utilisateur | M2 ou M3 |
| 2 | M2 Orchestrateur | M1 | M3 (file) |
| 3 | M3 Pont | M2 | M4 / M9 |
| 4 | M9 OCR (si image) | M3 | M4 |
| 5 | M4 Topic Gate | M3/M9 | M6 ou fin |
| 6 | M6 Retrieval | M4 | M7 |
| 7 | M7 RAG | M6 | M8 |
| 8 | M8 Restitution | M7 | M1 (utilisateur) |

**Corpus (M5)** alimente M6 en continu, en parallèle du flux conversationnel.

---

## 8. Données, corpus et recherche sémantique

Le système s’appuie sur une **mémoire duale** : **PostgreSQL** pour le stockage structuré et la gouvernance des données, **ChromaDB** pour la recherche sémantique et les mécanismes IA (fake news, surinformation). Les deux résident sur le **même serveur** que l’Engine et l’Orchestrateur (§5).

### 8.1 Méthodologie (alignement chapitre 2 académique)

La chaîne données suit quatre étapes :

1. **Collecte** — crawler, sources déclarées dans `data/crawler/sources.json`.
2. **Préparation** — normalisation, dédoublonnage (`hash`, `link`) en **PostgreSQL**.
3. **Vectorisation** — `paraphrase-multilingual-MiniLM-L12-v2` (384 dimensions).
4. **Indexation** — **upsert ChromaDB** après persistance Postgres (flèche **Postgres → Chroma** du schéma).

Le détail des deux bases est en **§8.2** ; le récit **du début à la fin** en **§8.2.8** ; l’alimentation par le crawler en **§8.4**.

---

### 8.2 Architecture mémoire duale : PostgreSQL et ChromaDB

Cette section formalise le diagramme **« PostgreSQL ↔ ChromaDB »** : rôles complémentaires, contenus stockés, et lien avec l’**Orchestrateur** et l’**Engine**.

#### 8.2.1 Principe de séparation (pourquoi deux bases ?)

| Critère | PostgreSQL | ChromaDB |
|---------|------------|----------|
| **Nature** | Base **relationnelle** (SQL, ACID) | Base **vectorielle** (embeddings, similarité) |
| **Rôle** | **Source de vérité** catalogue : texte intégral, métadonnées, unicité, stats | **Moteur de retrieval** : Top-K, cosinus, filtrage `RAG_MIN_SIMILARITY` |
| **Requêtes typiques** | `COUNT`, `GROUP BY source_id`, tri chronologique, mots-clés Topic Gate | `query_embeddings`, distance cosinus, HNSW |
| **Consommateur principal** | Orchestrateur (stats), Engine (Topic Gate dynamique, admin) | **Engine** (RAG **4.6**, dédup **4.5** cible) |

Une seule base ne suffit pas : le SQL excelle pour l’**intégrité** et le **reporting** ; Chroma excelle pour la **proximité sémantique** à grande échelle. La flèche du schéma **PostgreSQL → ChromaDB** représente le pipeline : *article validé en SQL → embedding → index vectoriel*.

```
┌─────────────────────┐     embedding + upsert      ┌─────────────────────┐
│    PostgreSQL       │ ──────────────────────────► │     ChromaDB        │
│  (vérité catalogue) │                             │  (recherche IA)    │
│  articles           │                             │  collection        │
│  training_runs      │                             │  articles_rdc      │
└─────────────────────┘                             └─────────────────────┘
         ▲                                                    │
         │ crawler / API                                      │ Engine RAG
         └────────────────────────────────────────────────────┘
```

#### 8.2.2 PostgreSQL — stockage structuré (source de vérité)

**Moteur :** PostgreSQL pour les métadonnées. En production actuelle, les **vecteurs de recherche** sont exclusivement dans ChromaDB. La colonne `embedding` en Postgres (pgvector) a été supprimée pour simplifier l'architecture, ChromaDB étant la source unique de vérité pour la recherche vectorielle.

##### Table `articles` (cœur du corpus)

| Colonne | Type | Rôle |
|---------|------|------|
| `id` | `SERIAL` | Clé primaire ; **identifiant partagé** avec Chroma (`ids = str(id)`) |
| `title` | `TEXT` | Titre de l’article (affichage, sources RAG) |
| `content` | `TEXT` | Corps intégral crawlé — base du texte embeddé |
| `source_id` | `TEXT` | Média d’origine (`radiookapi`, `actualite.cd`, …) |
| `link` | `TEXT` **UNIQUE** | URL canonique — dédoublonnage |
| `hash` | `TEXT` **UNIQUE** | Empreinte URL — second filet anti-doublon |
| `categories` | `TEXT[]` | Thèmes inférés (crawler) |
| `image` | `TEXT` | URL image Open Graph (optionnel) |
| `(Supprimé)` | - | La colonne `embedding` (pgvector) a été retirée au profit de ChromaDB |
| `created_at` | `TIMESTAMP` | Horodatage d’ingestion |

**Contraintes métier :**

- `ON CONFLICT DO NOTHING` sur `link` / `hash` : un même article média n’est pas dupliqué (**anti-surinformation corpus**).
- La recherche sémantique est déléguée à ChromaDB.

##### Table `training_runs` (métadonnées système)

| Colonne | Rôle |
|---------|------|
| `started_at` / `ended_at` | Fenêtre d’une passe d’indexation |
| `status` | `running`, `success`, … |
| `model_name` | Modèle d’embedding utilisé |
| `processed_count` / `reembedded_count` | Volumétrie sync Chroma |
| `note` | Commentaire opérateur |

Alimente le suivi des synchronisations Postgres → Chroma (`train_pipeline`).

##### Données cible du diagramme (hors implémentation complète)

Le schéma académique prévoit aussi en Postgres :

| Entité cible | Usage prévu | État projet |
|--------------|-------------|-------------|
| **Utilisateurs & groupes** (WhatsApp / Telegram) | Profils, opt-in, configuration par `chat_id` | **À créer** — aujourd’hui `chat_id` uniquement dans le flux webhook |
| **Cycle de vie des messages** | Message reçu, verdict, score similarité, réponse envoyée | **À créer** — logs fichier + mémoire process |
| **Historique vérifications fake news** | Audit, réutilisation « déjà vérifié » | **À créer** — lié à Engine **4.5** |
| **Données OCR** | Texte extrait persisté par `message_id` | **Partiel** — OCR en mémoire, pas de table dédiée |
| **Métriques / journaux** | Latence, succès/échec par requête | **Partiel** — logs FastAPI, pas de table `requests` |

##### Fonctionnalités PostgreSQL exploitées aujourd’hui

| Fonction | Composant | Exemple |
|----------|-----------|---------|
| Recherche par mots-clés / titres récents | `TopicGateService` | `SELECT title, content FROM articles ORDER BY id DESC LIMIT …` |
| Statistiques admin | `/admin/overview` | `COUNT(*)`, `GROUP BY source_id`, articles récents |
| Catalogue crawler | `sources.json` vs `source_id` | Breakdown par média |
| Dédoublonnage à l’ingestion | `article_service` | `ON CONFLICT` |
| Point de départ sync Chroma | `train_pipeline`, `sync_to_chroma.py` | `SELECT id, title, content, … FROM articles` |

#### 8.2.3 ChromaDB — stockage vectoriel (moteur sémantique)

**Déploiement :** client persistant local, chemin `data/chroma_db`, collection **`articles_rdc`**, métadonnée index **`hnsw:space: cosine`**.

##### Contenu d’un enregistrement vectoriel

| Champ Chroma | Source | Rôle |
|--------------|--------|------|
| `id` | `str(articles.id)` Postgres | Lien **1:1** avec la ligne SQL |
| `embedding` | `EmbeddingService.generate(content)` | Vecteur **384D**, même modèle que la requête utilisateur |
| `document` | `content` | Texte retrouvé pour le prompt LLM |
| `metadata.title` | Postgres | Affichage source |
| `metadata.link` | Postgres | URL citée dans la réponse |
| `metadata.source_id` | Postgres | Filtrage / traçabilité média |
| `metadata.hash` | Postgres | Cohérence avec dédup SQL |
| `metadata.categories` | Postgres (join `,`) | Filtres futurs |
| `metadata.image` | Postgres | Enrichissement UI |

**Chunking :** aujourd’hui **un vecteur par article entier** (pas de découpage multi-passages) — évolution possible pour longs dossiers.

##### Fonctionnalités IA (alignement diagramme)

| Fonction | Mécanisme technique | Paramètre |
|----------|---------------------|-----------|
| **Recherche sémantique Top-K** | `collection.query(query_embeddings, n_results=limit)` | `WHATSAPP_TOP_K=3`, `search_limit = 3×top_k` |
| **Score de similarité** | `similarity = 1 - distance_cosinus` | Affiché sur chaque `ArticleOut` |
| **Fake news (retrieval)** | Articles les plus proches du **sens** de la rumeur | Corpus = médias RDC indexés |
| **Seuil NON VÉRIFIABLE** | Filtrage après retrieval | `RAG_MIN_SIMILARITY_MSG` (défaut **0,40**) |
| **Anti-surinformation (cible 4.5)** | Comparer embedding **message entrant** vs cache requêtes récentes du `chat_id` | Seuil ~0,85–0,90 (*prévu*) — même moteur Chroma / embeddings |
| **Re-ranking** | LLM réordonne candidats Chroma | `RAG_ENABLE_RERANK` |

##### Migration pgvector -> ChromaDB (note d'architecture)

Le projet a migré de **pgvector** vers **ChromaDB** pour :
- **Simplifier le déploiement** : Pas d'extension système PostgreSQL à gérer.
- **Performance** : ChromaDB est optimisé pour les index HNSW et la recherche vectorielle.
- **Indépendance** : Découplage clair entre les métadonnées relationnelles (Postgres) et le moteur sémantique (Chroma).

Le script `scripts/sync_to_chroma.py` permet de reconstruire l'index ChromaDB à partir du contenu texte de PostgreSQL à tout moment.

#### 8.2.4 Pipeline de synchronisation Postgres → ChromaDB

Chaque nouvel article suit **obligatoirement** cette séquence (`create_article`, `save_crawled_article`) :

| Étape | Action | Résultat si échec / doublon |
|-------|--------|----------------------------|
| 1 | `INSERT` Postgres | Doublon → `RETURNING` vide, **pas** d’upsert Chroma |
| 2 | `EmbeddingService.generate(content)` | Vecteur 384D |
| 3 | `VectorStoreService.add_articles` → `upsert` | Index à jour ; id = `id` SQL |

**Synchronisation de masse :**

| Outil | Rôle |
|-------|------|
| `train_pipeline` | Relit tous (ou nouveaux) articles Postgres, re-embed, batch upsert Chroma, journalise `training_runs` |
| `scripts/sync_to_chroma.py` | Réindexation complète ou migration depuis colonne `embedding` pgvector |

**Cohérence attendue :** `COUNT(articles)` Postgres ≈ `collection.count()` Chroma (écart = articles non encore synchronisés ; visible dans `/admin/overview`).

#### 8.2.5 Qui lit quelle base ? (Orchestrateur vs Engine)

| Besoin | Base | Bloc |
|--------|------|------|
| Webhook, file messages | Mémoire process (`deque`) — *pas SQL* | Orchestrateur |
| Envoi Whapi, stats globales affichées | Postgres (optionnel) / Chroma count | Orchestrateur / admin |
| Topic Gate mots-clés dynamiques | **Postgres** `articles` | Engine **4.4** |
| Retrieval RAG, seuil similarité | **ChromaDB** | Engine **4.6–4.7** |
| Génération verdict LLM | Contexte issu de **Chroma** (+ métadonnées) | Engine **4.8** |
| Dédup conversationnelle (cible) | **Chroma** ou cache embeddings par `chat_id` | Engine **4.5** |
| Crawler → persistance | **Postgres** puis **Chroma** | Engine (hors file Whapi) |

#### 8.2.6 Lien fake news et surinformation par base

| Problème | PostgreSQL | ChromaDB |
|----------|------------|----------|
| **Fake news** | Corpus **identifié** (lien, source, date) ; refus d’inventer si retrieval vide | Top-K + seuil → contexte LLM **borné** ; verdict VRAI/FAUX/IMPRÉCIS/NON VÉRIFIABLE |
| **Surinformation (corpus)** | `UNIQUE(link, hash)` — pas 10× le même article | Un embedding par article — pas de poids redondant |
| **Surinformation (chat)** | *Cible* : table messages + verdicts par `chat_id` | *Cible* : similarité requête vs requêtes récentes (**4.5**) |

#### 8.2.7 Schéma récapitulatif (données ↔ briques Engine)

```
CRAWLER / API
     │
     ▼
┌──────────────┐    embed     ┌──────────────┐
│ PostgreSQL   │ ───────────► │  ChromaDB    │
│ · articles   │              │ · vectors    │
│ · training_  │              │ · metadata   │
│   runs       │              └──────┬───────┘
└──────┬───────┘                     │
       │ Topic Gate (titres)         │ RAG Top-K + seuil
       └──────────► Engine ◄─────────┘
                    └──► Ollama (verdict)
```

#### 8.2.8 Fonctionnement des deux BDD du début à la fin

Cette section explique, **dans l’ordre chronologique**, comment **PostgreSQL** et **ChromaDB** coopèrent depuis la mise en place du système jusqu’à la réponse à un utilisateur WhatsApp. C’est le fil narratif à reprendre dans le mémoire pour la partie « bases de données ».

**Diagramme associé :** [`architecture-bases-donnees-rdc-news.png`](architecture-bases-donnees-rdc-news.png)

---

##### Étape 0 — Mise en place (vide → schéma prêt)

Au démarrage du backend, les tables PostgreSQL sont créées ou migrées (`app/db/models.py`) :

- **`articles`** — prête à recevoir le corpus ;
- **`training_runs`** — prête à journaliser les synchronisations vers Chroma.

ChromaDB, lui, crée au premier accès le dossier persistant `data/chroma_db` et la collection **`articles_rdc`** (métrique **cosinus**). Les deux bases sont **vides** tant qu’aucun crawler ni import n’a tourné.

| Base | État initial |
|------|----------------|
| PostgreSQL | 0 ligne dans `articles` |
| ChromaDB | `collection.count() == 0` |

---

##### Étape 1 — Alimentation du corpus (crawler → PostgreSQL d’abord)

Le remplissage commence **toujours par PostgreSQL**. Chroma n’est pas la porte d’entrée des articles.

1. Le **crawler** (`SyncCrawler`) lit les URLs dans `data/crawler/sources.json`, extrait titre + corps + métadonnées.
2. Chaque article est envoyé au backend (`save_crawled_article` ou `POST /crawler/articles`).
3. **PostgreSQL** exécute :

```sql
INSERT INTO articles (title, content, source_id, link, hash, categories, image)
VALUES (...)
ON CONFLICT DO NOTHING
RETURNING id, ...;
```

4. **Si doublon** (`link` ou `hash` déjà présent) : la ligne n’est pas créée → **fin** pour cet article (rien n’est envoyé à Chroma). C’est le premier garde-fou **anti-surinformation corpus**.
5. **Si nouvel article** : Postgres attribue un `id` (ex. `4521`). Ce nombre deviendra l’identifiant commun aux deux bases.

À la fin de l’étape 1, **tout le catalogue textuel** est dans Postgres ; Chroma peut encore être en retard.

---

##### Étape 2 — Vectorisation et copie vers ChromaDB (chaque nouvel `id`)

Immédiatement après un `INSERT` réussi, le même traitement enchaîne **sans action manuelle** :

1. **`EmbeddingService`** lit le champ `content` et produit un vecteur de **384 floats** (modèle multilingue MiniLM).
2. **`VectorStoreService.add_articles`** appelle Chroma :

```text
upsert(
  ids = ["4521"],
  embeddings = [[0.12, -0.04, ...]],   # 384 dimensions
  documents = ["Corps intégral de l'article..."],
  metadatas = [{ title, link, source_id, hash, categories, image }]
)
```

3. Chroma enregistre l’entrée dans **`articles_rdc`**. L’`id` Chroma = `str(id)` Postgres → lien **1:1**.

| Moment | PostgreSQL | ChromaDB |
|--------|------------|----------|
| Après étape 1 seule | Article 4521 présent | — |
| Après étape 2 | Inchangé (texte déjà là) | Vecteur + document + metadata pour 4521 |

**Règle d’or :** pas de ligne Postgres validée ⇒ pas de vecteur Chroma pour cet article.

---

##### Étape 3 — Synchronisation de masse (rattrapage ou réindexation)

Quand des milliers d’articles sont importés d’un coup, ou après changement de modèle d’embedding, on utilise des outils **batch** :

1. **`train_pipeline`** ou **`sync_to_chroma.py`** lit **tout** (ou une partie de) Postgres :

```sql
SELECT id, title, content, link, source_id, hash, categories, image FROM articles;
```

2. Pour chaque lot (ex. 50 articles) : génération des embeddings + `upsert` Chroma.
3. Une ligne est ajoutée dans **`training_runs`** (`status`, `processed_count`, `model_name`, …).

Cette étape **ne remplace pas** l’étape 2 au quotidien : elle **réaligne** Chroma sur Postgres si les deux compteurs divergent (`/admin/overview` compare `COUNT(articles)` et `collection.count()`).

---

##### Étape 4 — Maintenance du corpus (vie continue)

Tant que le scheduler ou le script `sync --source-id all` tourne :

- de **nouveaux** articles passent par étapes **1 → 2** ;
- les **doublons** restent bloqués en Postgres ;
- Chroma **grandit** en parallèle, article par article.

PostgreSQL reste la **référence** : si on supprimait une entrée Chroma par erreur, on peut la **reconstruire** depuis Postgres + re-embedding (étape 3).

---

##### Étape 5 — Arrivée d’un message utilisateur (les deux BDD au travail)

Quand un utilisateur envoie une rumeur sur WhatsApp, **l’Orchestrateur** ne touche pas aux BDD (file en mémoire). C’est l’**Engine** qui interroge les bases :

**5a — Topic Gate (PostgreSQL uniquement)**

Avant le RAG coûteux, l’Engine peut lire les **derniers titres** en SQL pour enrichir les mots-clés dynamiques :

```sql
SELECT title, content FROM articles ORDER BY id DESC LIMIT N;
```

→ Décision : traiter ou ignorer le message (groupe, thème RDC). **Aucune requête Chroma** à ce stade.

**5b — Déduplication conversationnelle (cible — Chroma / embeddings)**

*Prévu §10 :* comparer l’embedding du message utilisateur à un cache de requêtes récentes du `chat_id`. Si similarité > seuil → réponse courte sans nouveau RAG. **Non persisté en Postgres aujourd’hui.**

**5c — Recherche RAG (ChromaDB en premier plan)**

1. L’Engine vectorise **la question utilisateur** (même modèle 384D que le corpus).
2. **ChromaDB** exécute une requête de plus proches voisins :

```text
query_embeddings = [vecteur_question]
n_results = 9   # souvent 3 × top_k
```

3. Chroma renvoie des `documents`, `metadatas`, `distances`.
4. L’Engine calcule `similarity = 1 - distance` pour chaque candidat.
5. Filtre : garde seulement ceux avec `similarity ≥ 0,40` (`RAG_MIN_SIMILARITY_MSG`).
6. Garde au plus **Top-K = 3** articles pour le prompt LLM.

**PostgreSQL n’est pas re-interrogé** pour le texte des articles en retrieval : le corps vient du champ `document` Chroma (copie du `content` à l’upsert). Les **liens et titres** viennent des **metadata** Chroma (elles-mêmes copiées depuis Postgres à l’indexation).

**5d — Verdict LLM (hors BDD)**

Mistral/Ollama produit VRAI / FAUX / IMPRÉCIS / NON VÉRIFIABLE à partir des extraits Chroma. Si **aucun** article n’a passé le seuil → **NON VÉRIFIABLE** sans lecture SQL supplémentaire.

| Sous-étape | PostgreSQL | ChromaDB |
|------------|------------|----------|
| Topic Gate | ✓ lecture titres récents | — |
| Retrieval | — (texte via `document`) | ✓ query Top-K |
| Seuil / NON VÉRIFIABLE | — | ✓ scores |
| Verdict + sources | métadonnées déjà dans Chroma | ✓ |

---

##### Étape 6 — Après la réponse (état des données)

Les bases **ne stockent pas encore** le message WhatsApp ni le verdict de la session (cible Postgres §8.2.2). Seuls les **logs** applicatifs trace l’événement.

Le **corpus** ne change pas à chaque message : Postgres et Chroma restent stables sauf si un **nouvel article** est crawlé entre-temps (retour étapes 1–2).

---

##### Synthèse chronologique (tableau mémoire)

| Ordre | Événement | PostgreSQL | ChromaDB |
|-------|-----------|------------|----------|
| 0 | Installation | Création tables | Création collection vide |
| 1 | Crawler ingest | `INSERT` article (+ dédup) | — |
| 2 | Indexation auto | `id` fixé | `upsert` embedding |
| 3 | Sync batch (optionnel) | `SELECT` masse | `upsert` lots + `training_runs` |
| 4 | Crawler continu | Nouveaux `INSERT` | Nouveaux `upsert` |
| 5a | Message user — Gate | `SELECT` titres | — |
| 5b | Message user — dédup (*cible*) | — | similarité requêtes |
| 5c | Message user — RAG | — | `query` Top-K + seuil |
| 6 | Réponse envoyée | pas d’écriture message (*cible*) | pas d’écriture message |

##### Exemple chiffré (une rumeur)

1. **Corpus** : 2 400 articles en Postgres, 2 398 vecteurs en Chroma (2 articles en attente de sync).
2. **Utilisateur** : « Le gouvernement a signé un décret secret sur la monnaie ».
3. **Postgres** : Topic Gate charge 30 derniers titres → thème *politique* activé.
4. **Chroma** : 9 voisins trouvés ; 3 dépassent 0,40 (articles sur réforme monétaire, pas « décret secret »).
5. **LLM** : **IMPRÉCIS** + 3 liens issus des metadata Chroma (`link`, `title`).
6. **Bases** : inchangées ; la vérification n’ajoute pas de ligne (sauf table messages *future*).

---

##### Ce qu’il faut retenir pour le jury / le lecteur

1. **PostgreSQL d’abord** — toute donnée article entre par le SQL ; Chroma est un **réplica sémantique** indexé.
2. **Un `id` = une vérité** — le même identifiant relie la ligne SQL et le vecteur Chroma.
3. **Deux vitesses** — ingestion corpus (étapes 1–4) vs requête utilisateur (étape 5) ; seule l’étape 5c interroge Chroma en intensif.
4. **Fake news** — Chroma trouve les preuves ; Postgres garantit qu’elles viennent de **vrais articles médias** identifiés à l’origine.
5. **Surinformation** — dédup à l’ingestion (Postgres) + dédup requêtes (*cible*, Chroma) ; pas de multiplication des entrées corpus.

---

### 8.3 Critères d’évaluation (IEEE — qualité)

| Critère | Mesure / observation |
|---------|----------------------|
| Pertinence retrieval | Score `similarity`, seuil 0,40 (msg) |
| Couverture corpus | Nombre d’articles indexés Chroma vs Postgres |
| Fidélité RAG | Présence de sources citées ; refus si hors corpus |
| Latence | Webhook rapide (Orchestrateur) ; génération dominée par Ollama (Engine) |

### 8.4 Pipeline crawler — alimentation du corpus (7 étapes)

Cette section décrit le diagramme **« Crawler — remplissage de la base de données d’actualités »**. Ce pipeline est **orthogonal** au flux conversationnel (§6) : il alimente le module **M5** en continu pour que la recherche sémantique (§4.4, étape **4.5**) dispose d’un corpus à jour.

#### 8.4.1 Vue linéaire (diagramme de référence)

```
[1 Sources] → [2 Crawling] → [3 Extraction] → [4 Prétraitement]
     → [5 OCR*] → [6 Indexation & Embeddings] → [7 Stockage]
```
\* *OCR crawler : optionnel sur images d’articles ; distinct de l’OCR WhatsApp (M9).*

#### 8.4.2 Détail technique par étape

| Étape | Intitulé diagramme | Actions techniques | Artefacts / code |
|-------|-------------------|--------------------|------------------|
| **1** | Définition des sources | Liste de médias RDC : flux RSS, sitemaps, URLs ciblées ; critères langue (FR), pays (CD), catégorie | `data/crawler/sources.json` ; identifiants `source_id` |
| **2** | Collecte (*crawling*) | Requêtes HTTP synchrones ; gestion timeouts et erreurs (`HttpError`) ; respect implicite des bonnes pratiques d’accès | `SyncHttpClient`, `SyncCrawler.crawl_urls` |
| **3** | Extraction du contenu | Parsing HTML (BeautifulSoup + lxml) ; titre (Open Graph / `<title>`) ; corps (`<article>` ou paragraphes) ; métadonnées URL, image OG | `OpenGraphParser`, `_extract_body` |
| **4** | Prétraitement | `sanitize_text` ; normalisation ; **dédoublonnage** par hash URL (`make_hash`) ; catégories inférées | `Article.hash`, `infer_categories` |
| **5** | OCR (si image) | Extraction texte des visuels d’article (*cible* architecture) | Non centralisé dans le crawler actuel ; OCR utilisateur = M9 |
| **6** | Indexation & embeddings | Vectorisation du **document entier** (pas de chunking multi-segments aujourd’hui) ; préparation recherche sémantique | `EmbeddingService` (`paraphrase-multilingual-MiniLM-L12-v2`, **384 dim.**) |
| **7** | Stockage | Persistance relationnelle + index vectoriel | **PostgreSQL** (catalogue) + **ChromaDB** (`articles_rdc`, métrique `cosine`, `upsert`) |

#### 8.4.3 Chaîne d’ingestion dans le backend

| Phase | Mécanisme | Endpoint / script |
|-------|-----------|-------------------|
| Persistance locale | Fichiers JSONL par source | `JsonlPersistor` → `data/crawler/*.jsonl` |
| Injection API | Forward HTTP vers le backend | `BackendForwarder` → `POST /crawler/articles` ou batch |
| Index vectoriel | Après insert Postgres | `article_service` → `VectorStoreService.add_articles` |
| Synchronisation | Réindexation complète ou migration | `scripts/sync_to_chroma.py`, `train_pipeline` |

#### 8.4.4 Lien avec le RAG (anti-surinformation côté corpus)

| Mécanisme | Effet |
|-----------|-------|
| **Dédoublonnage à l’ingestion** (`hash`, `link` unique) | Évite d’indexer deux fois le même article média |
| **Recherche sémantique** (Chroma, Top-K) | Retourne les articles **les plus proches en sens**, pas en mots exacts |
| **Seuil de similarité** (§4.4, **4.6**) | Empêche d’« inventer » une réponse si le corpus ne couvre pas le sujet |
| **Dédup conversationnelle** (§10) | Limite les réponses bot redondantes quand plusieurs utilisateurs envoient le même sens |

#### 8.4.5 Écart cible / implémentation (transparence IEEE)

| Fonctionnalité diagramme | État actuel |
|--------------------------|-------------|
| Chunking multi-passages par article | **Non** — un embedding par article (titre + contenu concaténé) |
| NER (dates, lieux, personnes) au prétraitement | **Partiel** — mots-clés Topic Gate dynamiques depuis Postgres |
| `robots.txt` explicite | **À renforcer** — dépend des politiques des sites sources |
| OCR images dans articles crawlés | **Hors scope** prioritaire — OCR WhatsApp opérationnel (M9) |

---

## 9. Interfaces et points d’intégration

### 9.1 Interfaces HTTP (orchestrateur)

| Interface | Méthode | Rôle |
|-----------|---------|------|
| `/webhooks/whapi` | POST | Entrée Whapi |
| `/webhooks/whapi/queue/pop` | POST | Consommation file par l’Engine (**③**) |
| `/webhooks/whapi/reply-relay` | POST | Entrée réponse Engine → Orchestrateur (**⑨**) |
| `/rag`, `/rag/stream` | POST | Canal web |
| `/admin/overview` | GET | Statistiques (Postgres + count Chroma) |
| `/health` | GET | État service |

### 9.2 Interfaces logiques internes

| Service | Consommateurs |
|---------|---------------|
| `EmbeddingService` | RAG, ingestion, (futur dédup) |
| `VectorStoreService` | `RetrievalService` |
| `RAGService` | Webhooks, routes `/rag` |
| `TopicGateService` | Webhooks groupes |

### 9.3 Variables d’environnement (profils)

| Profil | Variables clés |
|--------|------------------|
| **Orchestrateur** | `WHAPI_TOKEN`, enqueue webhook, tokens file |
| **Engine** | `ENABLE_WHAPI_QUEUE_POLLING`, `OLLAMA_HOST`, `RAG_*`, `TOPIC_GATE_*` |
| **Pont ③⑨** | `WHAPI_QUEUE_POP_URL`, `WHAPI_REPLY_RELAY_URL` (souvent `127.0.0.1`) |

---

## 10. Évolutions prévues (anti-surinformation)

La section **6.4** a montré que la lutte contre les **fake news** est opérationnelle via le RAG (phases A et C), tandis que la **surinformation conversationnelle** (réponses bot répétées) reste partiellement couverte. Cette section précise la feuille de route.

### 10.1 Limite actuelle

| Situation | Comportement aujourd’hui | Risque |
|-----------|-------------------------|--------|
| 10 messages « même sens » dans un groupe | 10 appels RAG possibles | Le bot **amplifie** la surcharge |
| Même rumeur 24 h plus tard | Nouvelle analyse complète | Coût LLM + lassitude utilisateur |
| Variante légère (« c’est vrai ??? ») | Traité comme message neuf | Doublons sémantiques non détectés |

### 10.2 Module cible M10 — Déduplication / cluster sémantique (Engine **4.5**)

**Insertion dans l’Engine (après Topic Gate **4.4**, avant RAG **4.6**) :**

```
4.4 Topic Gate → [4.5 Dédup / M10] → 4.6 Retrieval → 4.7–4.8 LLM → ⑨ Orchestrateur
```

**Principe :** calculer l’**embedding** du message entrant et le comparer à un cache par `chat_id` (seuil de similarité proche de 0,85–0,90). Si un cluster existe déjà :

- **ne pas** relancer Mistral sur tout le contexte ;
- renvoyer une **fiche courte** avec lien vers la vérification précédente.

### 10.3 Trois leviers produit (alignés §6.4.5)

| Levier | Description | Priorité |
|--------|-------------|----------|
| **Fusion à l’entrée** | Buffer 30–60 s par `chat_id` avant RAG | P1 |
| **Mémoire de chat** | Cache embedding + cooldown 24–72 h | P0 |
| **Story card** | Une fiche stable par sujet (`verdict` + sources + `story_id`) | P1 |

### 10.4 Message type après implémentation

```
📌 Sujet : [titre court du cluster]
🚨 VÉRIFICATION : IMPRÉCIS
📝 En bref : [2–3 phrases]
🔗 Sources : [liens]
ℹ️ 8 messages proches ont été regroupés. Déjà traité — pas de nouvelle analyse.
```

### 10.5 Référence détaillée

Spécifications produit et pistes techniques : [`BROUILLON_ANTI_SURINFORMATION_WHATSAPP.md`](BROUILLON_ANTI_SURINFORMATION_WHATSAPP.md).

---

## 11. Conclusion du chapitre

Ce chapitre a présenté l’architecture du flux **RDC News Intelligence** selon une structuration compatible avec les normes **IEEE** :

1. **Un seul serveur** FastAPI : blocs **Orchestrateur** (transmission) et **Engine** (traitement).
2. L’**architecture du schéma** (§4.4) : 2.1–2.4, ③, 4.1–4.9, ⑨ sur la même machine.
3. Un **enchaînement fonctionnel complet** (§6.4) : du **crawler** à la **réception WhatsApp**, en distinguant **fake news** (vérification RAG sourcée) et **surinformation** (mécanismes actuels + module M10).
4. Un **flux en six étapes** de la messagerie à la restitution (§6.1–6.2).
5. **Neuf sous-modules** (M1–M9) mappés aux blocs du diagramme technique (§7).
6. La **mémoire duale** (§8.2) et son fonctionnement **du début à la fin** (§8.2.8).
7. Le **pipeline crawler en sept étapes** (§8.4) alimentant les deux bases.
8. Une **feuille de route** anti-surinformation conversationnelle (§10).

Le chapitre suivant (modélisation UML, cas d’utilisation, diagrammes de séquence détaillés) s’appuie sur ce document et sur les fichiers `tdraw/*.tldr`.

---

## 12. Documents et diagrammes associés

### 12.1 Diagrammes de référence (images)

| Diagramme | Fichier (workspace) | Sections README |
|-----------|---------------------|-----------------|
| Orchestrateur + Engine (schéma cible) | `assets/image-68fa1fdd-cd3d-47cf-90a9-daa47aec6ecf.png` | §4.2–4.4, §5, §6 |
| Architecture globale RAG (historique) | `assets/Screenshot_from_2026-05-16_22-51-33-*.png` | §4.4 |
| **Bases de données (diagramme chapitre)** | [`architecture-bases-donnees-rdc-news.png`](architecture-bases-donnees-rdc-news.png) | **§8.2** |
| PostgreSQL ↔ ChromaDB (schéma utilisateur) | `assets/image-5ef0032c-e2ff-4079-93e2-00ba958c86ad.png` | §8.2 |
| Architecture complète 1 serveur + BDD | [`architecture-memoire-duale-rdc-news.png`](architecture-memoire-duale-rdc-news.png) | §4–§8 |
| Pipeline crawler (7 étapes) | `assets/Screenshot_from_2026-05-16_22-51-47-*.png` | §6.4.2, §8.4 |

### 12.2 Documents texte et tldraw

| Document | Contenu |
|----------|---------|
| [`tdraw/CHAPITRE_2_ENCHAINEMENT.md`](tdraw/CHAPITRE_2_ENCHAINEMENT.md) | Version narrative courte du flux |
| [`tdraw/README.md`](tdraw/README.md) | Index des diagrammes `.tldr` |
| [`tdraw/00-vue-generale.tldr`](tdraw/00-vue-generale.tldr) | Vue générale (tldraw) |
| [`FLUX_WHATSAPP_VERS_DRAWIO.md`](FLUX_WHATSAPP_VERS_DRAWIO.md) | Flux WhatsApp détaillé (texte) |
| [`BROUILLON_ANTI_SURINFORMATION_WHATSAPP.md`](BROUILLON_ANTI_SURINFORMATION_WHATSAPP.md) | Pistes anti-submersion |
| [`Chapitre_2_Redaction.md`](Chapitre_2_Redaction.md) | Brouillon académique données / méthodologie |
| [**`Chapitre_3_Modelisation.md`**](Chapitre_3_Modelisation.md) | **Chapitre III — UML, cas d’utilisation, séquences** |
| [**`Chapitre_4_Deploiement.md`**](Chapitre_4_Deploiement.md) | **Chapitre IV — VPS, stack, migration BDD** |
| [**`Article_Resultats_et_Discussion.md`**](Article_Resultats_et_Discussion.md) | **Résultats, discussion (données mesurées)** |
| [**`SOURCES_SWAHILI_AUDIT.md`**](SOURCES_SWAHILI_AUDIT.md) | **Audit + crawl sources kiswahili** |

---

*Fin du document — README Chapitre 2 (v3.3).*
