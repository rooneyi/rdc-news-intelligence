# Chapitre 3 : Modélisation et architecture du système RAG et intégration multicanale

## 3.1. Introduction

Le projet **RDC News Intelligence** repose sur une architecture orientée services dont l'objectif est de transformer un corpus d'actualité en base de connaissance exploitable à la demande. Contrairement à une approche centrée sur le classement statique des sujets, le système proposé combine la recherche sémantique, la récupération ciblée de documents et la génération de réponses contextualisées. Cette combinaison correspond au paradigme **Retrieval-Augmented Generation (RAG)**, qui permet d'ancrer la réponse produite par le modèle de langage dans des sources réelles et actualisées.

L'intérêt d'une telle architecture est particulièrement fort dans un contexte comme celui de la RDC, où les sources sont nombreuses, les contenus redondants et les usages fortement mobiles. Le système doit être capable de répondre rapidement, de fonctionner sur des canaux familiers et d'intégrer des données nouvelles sans redéploiement lourd.

## 3.2. Spécifications du système

### 3.2.1. Spécifications fonctionnelles
Le système doit répondre à plusieurs besoins fonctionnels majeurs :
- **Soumission de requêtes** : Permettre à un utilisateur de soumettre une requête textuelle et d'obtenir une synthèse structurée.
- **Analyse Multimédia** : Accepter une image, extraire le texte par **OCR**, et l'utiliser comme base de recherche.
- **Intégration Multicanale** : Exposer les fonctionnalités via le Web, Telegram et WhatsApp.
- **Intelligence Contextuelle** : Dans les groupes, le bot n'intervient que sur mention ou thématique détectée (Politique, Sport, Santé, Guerre).

### 3.2.2. Spécifications non fonctionnelles
- **Réactivité** : Fournir des réponses rapides pour un usage conversationnel.
- **Confidentialité** : Traitement local (OCR, LLM) pour la souveraineté des données.
- **Robustesse** : Tolérance à l'ajout massif de sources et flexibilité du modèle d'embedding.
- **Maintenabilité** : Séparation stricte entre collecte, indexation et génération.

## 3.3. Cas d'utilisation majeurs

### 3.3.1. Interaction directe (Web)
L'utilisateur interroge directement le système via l'application Web. La question est transmise via l'API REST au composant RAG pour une recherche vectorielle immédiate.

### 3.3.2. Vérification en groupe (Trigger @NewsBot)
Le bot observe les discussions et n'intervient que sur **déclencheur (Trigger)**. Lorsqu'une information douteuse est partagée, un membre mentionne le bot (ex: `@NewsBot vérifie`). Le système renvoie alors un rapport de fact-checking structuré (Verdict, Explication, Sources).

### 3.3.3. Requête par image
L'utilisateur envoie une affiche ou une capture d'écran. Le système extrait le texte sémantique et lance le pipeline de vérification instantanément, atténuant les rumeurs basées sur de faux visuels.

## 3.4. Architecture logicielle

### 3.4.1. Vue d'ensemble de l'architecture

L'application est orchestrée par un noyau **FastAPI** centralisant les flux de données, les routes REST et les Webhooks de messagerie.

> [!NOTE]
> **Architecture Haut Niveau**
> **Type** : Flowchart (Vue logique)
> **Description** : Structure globale montrant la communication entre les canaux d'accès, la couche logique métier et l'infrastructure de données/IA.

```mermaid
graph TD
    subgraph CANAUX
        W[Interface Web]
        WA[WhatsApp API]
        TG[Telegram Bot]
    end

    subgraph LOGIQUE_METIER
        WH[Gestionnaire Webhooks & Triggers]
        CLS[Classifieur Thematique]
        OCR[Service Vision OCR]
        RAG[Moteur RAG]
    end

    subgraph INFRASTRUCTURE
        DB[(PostgreSQL)]
        LLM[Mistral-7B]
        CR[Crawler]
    end

    W -.-> WH
    WA --> WH
    TG --> WH
    
    WH --> CLS
    WH --> OCR
    WH --> RAG
    
    RAG --> DB
    RAG --> LLM
    CR --> DB
```

## 3.5. Modélisation UML détaillée

### 3.5.1. Diagramme des Cas d'Utilisation

> [!TIP]
> **Modèle d'Interaction Acteurs-Services**
> **Description** : Cartographie fonctionnelle montrant comment les utilisateurs web et messagerie déclenchent les fonctions de Fact-Checking et comment l'administrateur gère le corpus.

```mermaid
flowchart LR
    UserWeb("👤 Utilisateur Web")
    UserMsg("👤 Utilisateur Messagerie")
    Admin("👤 Admin / Planificateur")
    Sources("🌐 Sources d'actualité")

    subgraph RDC_News_Intelligence
        UC1([Poser une question directe])
        UC2([Declencher verification bot])
        UC3([Fact-Checking via RAG])
        UC4([Generer reponse structuree])
        
        UC7([Crawler et Collecter actualite])
        UC8([Vectorisation automatique])
        UC9([Mise a jour de la Base])
    end

    UserWeb --> UC1
    UserMsg --> UC2
    UC1 -. "include" .-> UC3
    UC2 -. "include" .-> UC3
    UC3 -. "include" .-> UC4
    Admin --> UC7
    UC7 --> Sources
    UC7 -. "include" .-> UC8
    UC8 -. "include" .-> UC9
```

### 3.5.2. Séquence de déploiement et de démarrage

> [!IMPORTANT]
> **Cycle de vie initial**
> **Description** : séquence critique de démarrage, de l'initialisation de pgvector à l'exposition des Webhooks et au lancement du premier crawl automatisé.

```mermaid
sequenceDiagram
    participant Admin
    participant API as FastAPI
    participant DB as PostgreSQL
    participant WH as Webhooks_Routes
    participant CR as Crawler

    Admin->>API: Demarrer_service
    API->>DB: Init_tables_pgvector
    API->>WH: Exposer_Endpoints (TG & WA)
    API->>CR: Demarrer_tache_CRON
    CR-->>API: JSONL_ready (Batch)
    API->>DB: Insert_articles_embeddings
    DB-->>API: Base_Vectorielle_A_Jour
```

### 3.5.3. Séquence d'une requête RAG (Fact-Checking)

> [!NOTE]
> **Pipeline Sémantique**
> **Description** : Flux de traitement d'une question, incluant l'encodage, la recherche vectorielle, la synthèse par Ollama (Mistral-7B) et la restitution des sources.

```mermaid
sequenceDiagram
    participant User
    participant CH as Channel
    participant API as FastAPI
    participant EMB as EmbeddingService
    participant RET as RetrievalService
    participant DB as PostgreSQL
    participant RAG as RAGService
    participant LLM as Ollama

    User->>CH: Envoyer_question
    CH->>API: POST_rag
    API->>EMB: Encode_query
    EMB-->>API: Query_vector
    API->>RET: Search_similar
    RET->>DB: Query_top_k
    DB-->>RET: Articles
    RET-->>RAG: Context
    RAG->>LLM: Generate_answer
    LLM-->>API: Answer
    API-->>CH: Answer_plus_sources
```

### 3.5.4. Diagramme de classes (Formalisme UML)

> [!TIP]
> **Architecture Logicielle Statique**
> **Description** : Organisation modulaire du code respectant le formalisme UML (attributs typés, méthodes avec types de retour et relations de composition).

```mermaid
classDiagram
    direction TB
    class ArticleCreate {
        + title : str
        + content : str
        + link : str
        + source_id : str
        + hash : str
    }

    class ArticleOut {
        + id : int
        + title : str
        + content : str
        + similarity : float
    }

    class RAGRequest {
        + query : str
        + top_k : int
        + min_score : float
    }

    class RAGResponse {
        + query : str
        + summary : str
        + num_sources : int
    }

    class ArticleService {
        + create_article(data : ArticleCreate) : ArticleOut
        + save_crawled_article(data : ArticleCreate) : bool
        + search_similar(query : str, k : int) : ArticleOut[]
    }

    class EmbeddingService {
        + generate(text : str) : float[]
    }

    class RetrievalService {
        + get_similar_articles(vector : float[], k : int) : ArticleOut[]
    }

    class RAGService {
        + generate_full_answer(query : str, channel : str) : RAGResponse
        + check_and_verify(message : str) : RAGResponse
    }

    class LLMService {
        + generate_completion(prompt : str) : str
    }

    class OCRService {
        + extract_text(image_bytes : bytes) : str
    }

    ArticleService *-- EmbeddingService : compose
    RAGService *-- EmbeddingService : compose
    RAGService *-- RetrievalService : compose
    RAGService *-- LLMService : compose
    RAGService *-- OCRService : compose
```

### 3.5.5. Schéma de la base de données (ERD)

> [!IMPORTANT]
> **Architecture de Persistance**
> **Description** : Modélisation des tables PostgreSQL, soulignant la colonne vectorielle `embedding` et la traçabilité des entraînements.

```mermaid
erDiagram
    ARTICLES ||--o{ TRAINING_RUNS : "reembedding_updates"
    ARTICLES {
        int id
        string title
        string content
        string source_id
        string link
        string hash
        string categories
        string embedding
        datetime created_at
    }

    TRAINING_RUNS {
        int id PK
        datetime started_at
        datetime ended_at
        string status
        string model_name
        int processed_count
        int reembedded_count
        string note
        datetime created_at
    }
```

### 3.5.6. Diagramme de Séquence du Crawler

> [!NOTE]
> **Ingestion continue**
> **Description** : Processus automatisé de collecte web, vectorisation et synchronisation de la base de connaissances.

```mermaid
sequenceDiagram
    participant Admin as CRON
    participant Crawler as Service de Crawling
    participant Web as Sources Web
    participant NLP as Modèle d'Embedding
    participant VectorDB as Base Vectorielle

    Admin->>Crawler: Déclenche la collecte
    Crawler->>Web: Récupère derniers articles
    Web-->>Crawler: Contenu brut
    Crawler->>Crawler: Nettoyage du texte
    Crawler->>NLP: Envoi pour vectorisation
    NLP-->>Crawler: Embeddings (Vecteurs)
    Crawler->>VectorDB: Sauvegarde Texte + Vecteurs
    VectorDB-->>Crawler: Succès
    Crawler-->>Admin: Fin de routine
```

### 3.5.7. Séquence d'Interception et Classification

> [!TIP]
> **Intelligence de Groupe**
> **Description** : Logique décisionnelle filtrant les messages par thématique et traitant les images via OCR avant déclenchement du RAG.

```mermaid
sequenceDiagram
    participant User as Utilisateur
    participant Webhook as API Webhook
    participant Vision as Service OCR
    participant Classifier as Classifieur
    
    User->>Webhook: Envoie texte ou image
    
    opt Si contenu visuel (Image)
        Webhook->>Vision: Extraire texte
        Vision-->>Webhook: Texte extrait
    end

    Webhook->>Classifier: Évaluation du thème
    Classifier-->>Webhook: Retourne catégorie
    
    alt Thème pertinent (Politique/Santé)
        Webhook->>Webhook: Déclenche vérification RAG
    else Thème non ciblé
        Webhook-->>User: Ignore le message
    end
```

### 3.5.8. Séquence de Vérification et Verdict Final

> [!IMPORTANT]
> **Scénarios de réponse**
> **Description** : Confrontation factuelle entre la question et le corpus, menant soit à un verdict sourcé, soit à un flag d'incertitude.

```mermaid
sequenceDiagram
    participant Webhook as Orchestrateur RAG
    participant VectorDB as Base Vectorielle
    participant LLM as Service Mistral-7B
    participant User as Utilisateur / Groupe

    Webhook->>VectorDB: Requête de similarité
    VectorDB-->>Webhook: Documents proches + Sources
    
    alt Faits trouvés
        Webhook->>LLM: Générer verdict (Prompt + Contexte)
        LLM-->>Webhook: Verdict explicatif + Sources
        Webhook-->>User: Réponse avec Verdict et URLs
    else Manque de sources
        Webhook->>LLM: Demander réponse prudente
        LLM-->>Webhook: Avertissement d'incertitude
        Webhook-->>User: Bot signale le manque de sources
    end
```

## 3.6. Analyse comparative et stratégie d'apport

### 3.6.1. Comparaison avec les IA existantes (ChatGPT, Perplexity)
Le système RDC News Intelligence se distingue par trois points majeurs :
1. **Élimination des hallucinations** : En bridant l'IA sur un corpus clos, on évite les "inventions" des modèles généralistes.
2. **Curation locale** : Contrairement à Perplexity, le moteur ne cherche que dans des sources vérifiées de la presse congolaise.
3. **Fact-Checking adaptatif** : Si l'info n'est pas dans la base, le système renvoie un flag "NON VÉRIFIABLE" au lieu de tenter de deviner.

### 3.6.2. Stratégie de "Surinformation Contrôlée"
Face à l'immensité de la désinformation, notre approche consiste à occuper l'espace par la **surinformation**. Puisque nous ne pouvons pas arrêter chaque rumeur, nous diffusons massivement des faits vérifiés, rendus ultra-accessibles sur les canaux favoris (WhatsApp/Telegram). En contrôlant la qualité du corpus, nous créons un contre-poids informationnel indispensable pour éduquer et protéger les utilisateurs.

## 3.7. Limites et perspectives futures
Actuellement, le système ne traite pas les **statuts (Stories)** éphémères ou les deepfakes audios. Ces défis constituent les axes de recherche pour les versions futures du projet.

## 3.8. Conclusion partielle
La modélisation montre que RDC News Intelligence est une architecture robuste alliant collecte, sémantique et génération. Le chapitre suivant détaillera l'implémentation technique de ces services.
