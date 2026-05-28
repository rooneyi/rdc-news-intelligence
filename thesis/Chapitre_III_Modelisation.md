# CHAPITRE III : MODÉLISATION UML ET ARCHITECTURE SYSTÈME

### 3.1. Introduction partielle
La modélisation est une étape cruciale qui permet de traduire les besoins fonctionnels identifiés dans la méthodologie en une structure logicielle cohérente. Ce chapitre utilise le langage UML (Unified Modeling Language) pour décrire les interactions entre les utilisateurs et le système RDC News Intelligence, ainsi que l'organisation interne des données.

### 3.2. Identification des Acteurs
Le système interagit avec quatre acteurs principaux :
1.  **L'Utilisateur (Citoyen/Membre de groupe)** : Soumet des informations pour vérification via WhatsApp ou Telegram.
2.  **L'Administrateur (Journaliste/Fact-checker)** : Supervise le système, valide les sources du crawler et surveille les alertes de viralité.
3.  **Les APIs de Messagerie (WhatsApp Business/Telegram Bot API)** : Servent de passerelles de communication entre les utilisateurs et le serveur.
4.  **Le Moteur d'IA (Ollama/Mistral)** : Agit comme un acteur système traitant les requêtes de synthèse et de verdict.

### 3.3. Diagramme de Cas d'Utilisation
Le diagramme de cas d'utilisation synthétise les fonctionnalités offertes par la plateforme :
-   **Soumettre une information** (Texte, Image/Capture d'écran).
-   **Recevoir un verdict factuel** (RAG Response).
-   **Consulter une bulle de synthèse** (Pour les messages viraux ou redondants).
-   **Gérer la base de connaissances** (Acteur : Administrateur via le Crawler).
-   **Recevoir une alerte de viralité** (Notification automatique du système).

### 3.4. Diagramme de Séquence : Flux de Vérification RAG
Ce diagramme illustre le cycle de vie d'une requête, de l'envoi du message à la réception de la réponse :
1.  **Utilisateur** envoie un message (ex: rumeur sur WhatsApp).
2.  **API WhatsApp** transmet le message au **Webhook FastAPI** (VPS).
3.  **FastAPI** sollicite le **Service d'Embedding** pour vectoriser la requête.
4.  Le système interroge la **Mémoire Conversationnelle (Redis)** pour vérifier si le sujet est déjà traité (détection de bulle).
5.  *Si nouveau* : Le système effectue une recherche sémantique dans la **Base Vectorielle (ChromaDB)**.
6.  Les articles pertinents sont envoyés au **Modèle LLM (Mistral)** avec le prompt RAG.
7.  Le **LLM** génère le verdict.
8.  **FastAPI** renvoie la réponse finale à l'utilisateur via l'API de messagerie.

### 3.5. Diagramme de Classes
L'organisation des données repose sur les entités suivantes :
-   **Article** : Contenu, titre, source, date, lien URL.
-   **Embedding** : Représentation vectorielle liée à un Article ou à un Message utilisateur.
-   **Topic (Bulle)** : Regroupe plusieurs messages similaires, possède un message racine (pivot) et un score de viralité.
-   **Message** : Identifiant plateforme, contenu brut, verdict associé, timestamp.
-   **Source** : Niveau de fiabilité, nom du média, fréquence de scan.

### 3.6. Architecture Physique (Déploiement)
Le système est déployé sur un **Serveur Privé Virtuel (VPS)** sous Linux. L'architecture est composée de :
-   **Serveur Web** : FastAPI orchestrant les requêtes.
-   **Base de Données** : PostgreSQL pour les métadonnées et ChromaDB pour les vecteurs.
-   **Worker d'IA** : Instance Ollama exécutant le modèle Mistral-7B en local sur le VPS.
-   **Cache & Mémoire** : Redis pour la gestion des bulles en temps réel.

### 3.7. Conclusion partielle
La modélisation UML présentée dans ce chapitre confirme la robustesse de l'architecture choisie. En séparant clairement les responsabilités (collecte, stockage, orchestration et génération), nous assurons une scalabilité capable de répondre aux flux massifs de données des réseaux sociaux. Le chapitre suivant traitera de l'implémentation concrète et des résultats obtenus.
