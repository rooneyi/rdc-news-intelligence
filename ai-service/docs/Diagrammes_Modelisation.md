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

actor "Utilisateur (WhatsApp/Telegram)" as User
actor "Administrateur / Planificateur (CRON)" as Admin
actor "Sources d'actualité (Web/RSS)" as Sources

rectangle "Système de Recommandation et Vérification" {
    usecase "Envoyer un message ou statut (Texte/Image)" as UC1
    usecase "Intercepter et Analyser l'information" as UC2
    usecase "Classifier le thème (Politique, Santé, Sport)" as UC3
    usecase "Vérifier la véracité via Vector DB" as UC4
    usecase "Générer un résumé pertinent (RAG)" as UC5
    usecase "Répondre avec verdict et sources" as UC6
    
    usecase "Crawler les informations" as UC7
    usecase "Vectoriser les données (Embedding)" as UC8
    usecase "Mettre à jour la Base de Connaissances" as UC9
}

User --> UC1
User <-- UC6 : Reçoit la réponse argumentée

UC1 ..> UC2 : inclut
UC2 ..> UC3 : inclut
UC3 ..> UC4 : si thème du domaine (Polit., Santé, Sport)
UC4 ..> UC5 : inclut
UC5 ..> UC6 : inclut

Admin --> UC7
UC7 --> Sources : Collecte des faits
UC7 ..> UC8 : inclut
UC8 ..> UC9 : inclut

UC4 --> UC9 : Consulte la base
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
    actor User as Utilisateur 
    participant WG as Webhook Gateway
    participant Class as Classification Service
    participant DB as Vector Knowledge Base
    participant RAG as Génération RAG Service

    User->>WG: Envoie un contenu potentiellement faux
    WG->>Class: Analyser et classifier (Texte ou OCR)
    Class-->>WG: Indique "Politique / Santé / Sport"
    
    opt Theme pertinent
        WG->>DB: Interroger la vérité (Recherche sémantique)
        DB-->>WG: Fournir contexte et origines fiables
        WG->>RAG: Synthétiser "Fait" vs "Désinformation"
        RAG-->>WG: Résultat RAG généré
        WG-->>User: Publier la correction et les preuves (sources)
    end
```
