# Modélisation du Système d'Intelligence et de Lutte contre la Désinformation

Voici l'ensemble des diagrammes demandés, modélisés avec la syntaxe **Mermaid**. 

> **Comment utiliser ces diagrammes dans Draw.io ?**
> 1. Ouvrez [Draw.io](https://app.diagrams.net/).
> 2. Allez dans le menu : **Plus (Arrange) > Insérer (Insert) > Avancé (Advanced) > Mermaid...**
> 3. Copiez-collez le code des blocs ci-dessous pour générer instantanément les diagrammes au format Draw.io, que vous pourrez éditer et enregistrer au format `.drawio`.

---

## 1. Diagramme des Cas d'Utilisation

Ce diagramme présente les interactions globales entre les acteurs et le système pour le Crawler et le Chatbot.

```mermaid
%%{init: {'theme': 'base', 'themeVariables': { 'primaryColor': '#ffffff', 'edgeLabelBackground':'#ffffff', 'tertiaryColor': '#fcfcfc'}}}%%
usecaseDiagram
direction LR

actor "Utilisateur Web" as UserWeb
actor "Utilisateur Messagerie (Groupes)" as UserMsg
actor "Admin / Planificateur (CRON)" as Admin
actor "Sources d'actualité (Web/RSS)" as Sources

rectangle "RDC News Intelligence (Moteur RAG)" {
    usecase "Poser une question directe" as UC1
    usecase "Déclencher vérification (@NewsBot / Trigger)" as UC2
    usecase "Fact-Checking via RAG (Contexte Vectoriel)" as UC3
    usecase "Générer réponse structurée (Vrai/Faux + Sources)" as UC4
    
    usecase "Crawler & Collecter l'actualité" as UC7
    usecase "Vectorisation automatique (Embedding)" as UC8
    usecase "Mise à jour de la Base (Continuous Learning)" as UC9
}

UserWeb --> UC1
UserMsg --> UC2 : Optionnel (Trigger-based)

UC1 ..> UC3 : include
UC2 ..> UC3 : include
UC3 ..> UC4 : include

UserWeb <-- UC4 : Réponse complète
UserMsg <-- UC4 : Verdict + Sources

Admin --> UC7
UC7 --> Sources : Collecte
UC7 ..> UC8 : include
UC8 ..> UC9 : include

UC3 --> UC9 : Recherche sémantique
```

---

## 2. Diagramme de Séquence du Crawler (Alimentation DB)

Ce diagramme montre les étapes pour le crawler.

```mermaid
sequenceDiagram
    autonumber
    actor Admin as Tâche Planifiée (CRON)
    participant Crawler as Service de Crawling
    participant Web as Sources Officielles / Web
    participant NLP as Modèle d'Embedding (LLM)
    participant VectorDB as Base de Données Vectorielle

    Admin->>Crawler: Déclenche la collecte de nouvelles actus
    Crawler->>Web: Requête pour récupérer les derniers articles
    Web-->>Crawler: Retourne le contenu (HTML brut)
    Crawler->>Crawler: Parsing et nettoyage du texte
    Crawler->>NLP: Envoi du texte pour Vectorisation
    NLP-->>Crawler: Retourne les vecteurs (Embeddings)
    Crawler->>VectorDB: Sauvegarde Texte + Vecteurs + URL (Source)
    VectorDB-->>Crawler: Succès de l'enregistrement
    Crawler-->>Admin: Fin de la routine
```

---

## 3. Diagramme de Séquence : Action d'Interception et de Classification

Action déclenchée dès qu'un utilisateur poste sur le groupe.

```mermaid
sequenceDiagram
    autonumber
    actor User as Utilisateur WhatsApp/Telegram
    participant Webhook as API Webhook
    participant Vision as Service OCR / Vision (Images)
    participant Classifier as Service de Classification
    
    User->>Webhook: Envoie un texte ou une image (Statut/Groupe)
    
    opt Si contenu visuel (Image)
        Webhook->>Vision: Extraire le texte de l'image
        Vision-->>Webhook: Texte extrait
    end

    Webhook->>Classifier: Évaluation du texte pour déterminer le thème
    Classifier-->>Webhook: Retourne la catégorie (Politique, Santé, Sport, Autre)
    
    alt Thème == Politique, Santé, ou Sport
        Webhook->>Webhook: Déclenche la vérification
    else Thème non ciblé
        Webhook-->>User: Ignore silencieusement le message
    end
```

---

## 4. Diagramme de Séquence : Action de Vérification et de Réponse (RAG)

Suite de l'action d'interception, si pertinente.

```mermaid
sequenceDiagram
    autonumber
    participant Webhook as Orchestrateur RAG
    participant VectorDB as Base de Données Vectorielle
    participant LLM as Service LLM (Génération)
    actor User as Groupe / Utilisateur

    Webhook->>VectorDB: Requête de similarité pour vérifier l'information
    VectorDB-->>Webhook: Retourne les documents proches + Sources
    
    alt Contexte trouvé (Articles existants)
        Webhook->>LLM: Générer la réponse (Prompt + Info utilisateur + Contexte VectorDB)
        LLM-->>Webhook: Retourne le résumé explicatif + Verdict vérifié/prouvé
        Webhook->>Webhook: Assemblage de la réponse texte avec les URLs
        Webhook-->>User: Répond au message avec le verdict et les sources
    else Aucune information source trouvée
        Webhook->>LLM: Demander de générer une réponse prudente
        LLM-->>Webhook: Retourne avertissement (Info non validée par les sources)
        Webhook-->>User: Bot répond qu'il manque de sources
    end
```

---

## 5. Diagramme de Séquence Générale (Vue Complète)

```mermaid
sequenceDiagram
    autonumber
    actor User as Utilisateur (Web/Group)
    participant WG as FastAPI Webhook Gateway
    participant Class as Classification (Trigger logic)
    participant DB as VectorDB (PostgreSQL)
    participant RAG as RAG Generator (Mistral)

    User->>WG: Message / Question (Texte/Image)
    
    alt Si Groupe
        WG->>Class: Analyser Trigger @NewsBot
        Class-->>WG: Indique si thématique pertinente (Pol/Santé)
    end
    
    opt Requête validée (Directe ou Triggered)
        WG->>DB: Recherche sémantique (Embeddings)
        DB-->>WG: Contexte documenté (Facts)
        WG->>RAG: Synthèse Fact-Checking + Sources
        RAG-->>WG: Résultat RAG structuré (Verdict)
        WG-->>User: Correction publiée avec Preuves/Links
    end
```
