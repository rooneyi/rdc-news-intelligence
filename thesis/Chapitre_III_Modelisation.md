# CHAPITRE III : MODELISATION UML ET ARCHITECTURE SYSTEME

## 3.1 Introduction du chapitre

La modelisation constitue la passerelle entre la problematique (chapitre I), la methode (chapitre II) et l'implementation (chapitre IV). Elle permet de formaliser le comportement attendu du systeme, les responsabilites de chaque composant et les interactions critiques entre les modules. Dans une architecture de fact-checking conversationnel, cette formalisation est essentielle pour trois raisons:

1. maitriser la complexite d'un pipeline multi-services;
2. garantir la coherence entre exigences fonctionnelles et choix techniques;
3. faciliter la maintenance, l'evolution et l'audit du systeme.

Le langage UML est retenu comme notation de reference pour representer les vues statique et dynamique du systeme [18], [19]. Nous adoptons une logique de modelisation par vues:

- vue metier (acteurs et cas d'utilisation);
- vue dynamique (diagrammes de sequence);
- vue structurelle (diagramme de classes);
- vue de deploiement (architecture physique VPS).

Cette demarche est conforme aux bonnes pratiques d'architecture logicielle centree qualite [20].

## 3.2 Vue metier: acteurs et responsabilites

### 3.2.1 Acteurs humains et systemes externes

Le systeme RDC News Intelligence interagit avec les acteurs suivants:

1. **Utilisateur final (citoyen, membre de groupe)**  
   Soumet des messages (texte/image) pour verification et consulte la reponse.

2. **Administrateur / operateur**  
   Supervise les sources, surveille les logs, pilote les jobs de crawl/reindexation et controle l'etat de sante du service.

3. **Passerelles de messagerie (Whapi, WhatsApp API, Telegram Bot API)**  
   Transportent les messages entrants/sortants entre les plateformes sociales et l'API.

4. **Moteur LLM (Ollama + modele Mistral)**  
   Fournit la generation de reponse conditionnee par le contexte documentaire.

5. **Services de donnees (PostgreSQL, ChromaDB, Redis)**  
   Conservent respectivement les metadonnees, les vecteurs semantiques et l'etat court terme des files/conversations.

### 3.2.2 Frontieres du systeme

La frontiere applicative couvre:

- ingestion webhook;
- traitement metier (topic gate, memoire, RAG);
- restitution reponse;
- administration de base (health, overview, jobs).

Les reseaux sociaux et les modeles externes ne sont pas modelises comme composants internes, mais comme dependances externes encapsulees par des adaptateurs.

## 3.3 Diagramme de cas d'utilisation

### 3.3.1 Cas d'utilisation principaux

Les cas d'utilisation metier identifies sont:

1. **Soumettre une information a verifier**  
   L'utilisateur envoie un texte ou une image depuis un canal de messagerie.

2. **Recevoir un verdict contextualise**  
   Le systeme retourne une reponse structuree (verdict, explication, sources).

3. **Recevoir une reponse non redondante**  
   Si le sujet est deja traite, le systeme reutilise un verdict existant pour eviter le bruit.

4. **Mettre a jour la base documentaire**  
   L'administrateur (ou cron) execute le crawler et les synchronisations.

5. **Superviser l'etat du service**  
   L'operateur verifie la sante de l'API, des files et des index.

### 3.3.2 Relations include/extend

Pour une lecture UML rigoureuse:

- "Soumettre une information" **inclut** "Normaliser le message";
- "Soumettre une information" **inclut** "Classer le theme";
- "Recevoir un verdict contextualise" **inclut** "Recuperer les sources";
- "Recevoir une reponse non redondante" **etend** "Recevoir un verdict contextualise";
- "Mettre a jour la base documentaire" **inclut** "Indexer en vectoriel".

Cette decomposition explicite les points de variabilite et de reutilisation.

## 3.4 Diagrammes de sequence

### 3.4.1 Sequence nominale: nouveau sujet (pipeline RAG complet)

Sequence cible:

1. **User -> Messaging API**: envoi du message.
2. **Messaging API -> Webhook FastAPI**: transmission du payload.
3. **FastAPI -> Topic Gate**: classification thematique.
4. **FastAPI -> Embedding Service**: vectorisation de la requete.
5. **FastAPI -> Memory Service (Redis/short-term store)**: recherche de similarite.
6. **FastAPI -> Vector Store (ChromaDB)**: retrieval Top-k.
7. **FastAPI -> LLM Service (Ollama)**: generation contextualisee.
8. **FastAPI -> Messaging API**: envoi de la reponse finale.
9. **FastAPI -> Memory Service**: memorisation de la requete/verdict.

Cette sequence garantit la tracabilite des sources et l'explicabilite minimale de la reponse.

### 3.4.2 Sequence alternative: sujet redondant (anti-surinformation)

Si la similarite depasse le seuil:

1. message rattache a un cluster existant;
2. recuperation du verdict precedent;
3. reponse courte de rappel au lieu d'une regeneration longue.

Ce chemin alternatif diminue latence, cout LLM et surcharge conversationnelle.

### 3.4.3 Sequence image/OCR

Pour les images:

1. extraction du fichier media;
2. OCR local;
3. fusion caption + texte OCR;
4. reprise du pipeline standard (topic gate -> memoire -> RAG).

Cette sequence etend la couverture aux rumeurs diffusees sous forme visuelle.

## 3.5 Diagramme de classes conceptuel

### 3.5.1 Classes metier principales

Le noyau conceptuel comporte les classes suivantes:

- **Article**
  - attributs: `id`, `title`, `content`, `source_id`, `link`, `hash`, `categories`, `created_at`.
  - role: unite documentaire de reference.

- **Source**
  - attributs: `source_id`, `source_url`, `source_kind`, `source_lang`, `scan_policy`.
  - role: gouvernance de collecte.

- **Message**
  - attributs: `platform_message_id`, `chat_id`, `author`, `content`, `timestamp`, `channel`.
  - role: entree conversationnelle.

- **TopicCluster**
  - attributs: `cluster_id`, `pivot_message`, `verdict_cache`, `last_seen`, `score`.
  - role: anti-redondance.

- **Verdict**
  - attributs: `label`, `explanation`, `sources`, `generated_at`, `confidence_proxy`.
  - role: sortie interpretable pour l'utilisateur.

### 3.5.2 Services applicatifs

Classes de service (niveau architecture logicielle):

- `CrawlerService`
- `VectorStoreService`
- `EmbeddingService`
- `RAGService`
- `LLMService`
- `MemoryService`
- `WebhookController`

Chaque service expose une responsabilite unique, ce qui limite le couplage et simplifie les tests.

### 3.5.3 Relations et cardinalites

Relations majeures:

- `Source 1..* -> Article`
- `Article 1..* -> EmbeddingRecord` (conceptuel, meme si le stockage vectoriel est externe)
- `Message *..1 -> TopicCluster` (optionnel si nouveau sujet)
- `TopicCluster 1..* -> Message`
- `Verdict 1..1 -> TopicCluster` (dernier verdict pivot)

## 3.6 Vue composants (architecture logique)

### 3.6.1 Composants internes

L'architecture logique est composee de:

1. **Interface Channels** (webhooks + adaptateurs transport)
2. **Core Processing** (topic gate, memoire, RAG orchestration)
3. **Knowledge Layer** (crawler + SQL + vector store)
4. **Inference Layer** (Ollama/LLM)
5. **Observability Layer** (logs, health, metrics operatoires)

### 3.6.2 Contrats d'interface

Contrats critiques:

- contrat webhook entrant (payload, auth, ack rapide);
- contrat queue pop/relay (token, timeout, retry);
- contrat RAG stream (chunks, sources, erreur);
- contrat admin/health (etat service, etat indexation).

Ces contrats stabilisent l'integration entre modules et reduisent les regressions.

## 3.7 Diagramme de deploiement (vue physique VPS)

### 3.7.1 Noeuds de deploiement

Le deploiement cible principal est un VPS unique sous Linux:

- **Nginx/Proxy**: terminaison HTTPS et routage vers API;
- **API Node (FastAPI + PM2)**: orchestration metier;
- **Data Node (PostgreSQL + ChromaDB + Redis)**: persistence hybride;
- **Inference Node (Ollama local)**: generation LLM.

### 3.7.2 Flux reseau internes et externes

- Externe: `Whapi/Telegram -> HTTPS /webhooks/* -> API`
- Interne: `API -> Redis/PostgreSQL/Chroma/Ollama` via `127.0.0.1`
- Sortant: `API -> Whapi/Telegram sendMessage`

Le choix `localhost` pour les appels inter-services sensibles reduit la surface d'exposition.

### 3.7.3 Contraintes de capacite

La modelisation integre des contraintes reelles:

- memoire limitee pour inference 7B quantized;
- necessite de batch control pour reindexation;
- besoin de file asynchrone en cas de pic de messages.

Ces contraintes justifient les choix de seuils et de modes d'execution presentes au chapitre II.

## 3.8 Points de qualite architecturale

### 3.8.1 Disponibilite

Assuree par:

- supervision PM2;
- relance automatique;
- separation des taches longues;
- endpoints de sante.

### 3.8.2 Maintenabilite

Assuree par:

- separation controllers/services;
- centralisation configuration environnement;
- journalisation explicite des etapes critiques.

### 3.8.3 Evolutivite

L'architecture est extensible vers:

- nouveaux canaux de messagerie;
- nouveaux modeles LLM;
- nouvelles langues/sources;
- distribution sur plusieurs noeuds si charge accrue.

## 3.9 Cohabitation UML - implementation reelle

Le chapitre III ne presente pas une UML "academique deconnectee", mais une UML de validation de conception. Les diagrammes ont ete alignes sur les flux effectivement observes en execution:

- reception webhook;
- pipeline RAG;
- anti-redondance;
- jobs de synchronisation documentaire.

Cette cohabitation entre modelisation et implementation renforce la valeur scientifique et pratique de l'artefact.

## 3.10 Conclusion partielle

Ce chapitre a formalise la structure du systeme RDC News Intelligence au moyen des vues UML essentielles: acteurs, cas d'utilisation, sequences, classes et deploiement. La modelisation confirme la coherence entre les objectifs du projet (verification factuelle + sobriete informationnelle) et les mecanismes techniques implementes.

La separation explicite des responsabilites (collecte, orchestration, retrieval, generation, restitution) fournit une base robuste pour l'implementation et l'evaluation experimentale. Le chapitre suivant presentera l'implementation concrete, les resultats observes et l'analyse critique des performances.

---

## References

Les references bibliographiques de ce chapitre sont centralisees dans `thesis/References.md` avec une numerotation IEEE unique et continue pour l'ensemble du memoire.
