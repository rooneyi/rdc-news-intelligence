# CHAPITRE II : MÉTHODOLOGIE DU FRAMEWORK DE LUTTE CONTRE LA SURINFORMATION

### 2.1. Introduction partielle
La méthodologie développée dans ce travail vise à établir un équilibre entre le respect de la vie privée dans les espaces de communication chiffrés et la nécessité technique de limiter la propagation de la désinformation et de l'infobésité. Le framework proposé repose sur une détection rapide et une correction automatisée des fausses informations dans un environnement de diffusion à haute vitesse.

### 2.2. Architecture Globale du Framework
L'idée centrale de notre approche est double :
1.  **Détection précoce** : Identifier les rumeurs dès leur apparition pour stopper leur viralité.
2.  **Marquage et Groupement (Clustering)** : Identifier les réponses aux messages partagés plusieurs fois afin d'éviter de saturer les utilisateurs avec des informations redondantes ou déjà vérifiées.

Le système adopte une approche centrée sur l'utilisateur, permettant une interaction soit en mode privé (one-to-one), soit au sein de groupes de discussion. Une fois qu'un message est capturé par l'Orchestrateur, il est placé dans une file d'attente pour être traité par le Moteur (Engine), qui évalue sa popularité, son authenticité et sa pertinence thématique.

### 2.3. Algorithme de Traitement et Pipeline de Fact-Checking
Le traitement d'un message suit un pipeline rigoureux décrit par la logique suivante :
- **Réception** : Le message arrive via un Webhook (WhatsApp ou Telegram).
- **Analyse Sémantique** : Le système consulte les "embeddings" récents stockés dans une mémoire conversationnelle temporaire.
- **Calcul de Similarité** : Une comparaison vectorielle est effectuée. Si le score dépasse un seuil prédéfini (seuil de similarité), le message est considéré comme appartenant à une "bulle" (cluster) existante.
- **Gestion de la Redondance** :
    - Si une réponse existe déjà pour ce cluster, le système réutilise le verdict précédent ou génère un résumé contextuel court pour économiser les ressources et éviter le bruit.
    - Si le sujet est nouveau, le pipeline RAG complet est déclenché.
- **Consolidation** : Une seule réponse principale reste visible ou référencée dans le groupe, réduisant ainsi la charge cognitive des membres.

### 2.4. Détails des Composants Techniques

#### 2.4.1. Le Crawler (Collecte et Fraîcheur des Données)
Dans une architecture RAG, la précision des réponses dépend directement de la fraîcheur de la base documentaire. Nous avons implémenté un crawler automatisé qui :
- Scanne des sources identifiées comme fiables (flux RSS, sitemaps, sites de presse nationale et internationale).
- Filtre les sources selon des critères de crédibilité, de langue (Français, Anglais, Swahili) et de pertinence géographique (RDC).
- Assure un stockage en double couche : une **mémoire documentaire** (métadonnées structurées) et une **mémoire sémantique** (représentations vectorielles/embeddings).

#### 2.4.2. L'Orchestrateur (Gestion des Flux)
L'Orchestrateur fait le pont entre les applications de messagerie et le cœur du système. Il reçoit les données via des APIs sécurisées, identifie l'expéditeur et le contexte (groupe ou privé), et gère une file d'attente. Ce mécanisme est crucial pour éviter la surcharge du serveur lors de pics de viralité informationnelle.

#### 2.4.3. Le Moteur (Engine - Cœur du Système)
Le Moteur est responsable de l'analyse profonde. Ses fonctions incluent :
- **Prétraitement NLP** : Nettoyage, normalisation, détection de la langue et reconnaissance d'entités nommées.
- **Module OCR** : Extraction de texte à partir d'images ou de captures d'écran pour traiter les "posters" de désinformation.
- **Recherche Vectorielle** : Utilisation de l'approche RAG pour récupérer les documents les plus pertinents dans la base de données vectorielle.
- **Génération de Verdict** : Production d'une réponse structurée incluant un verdict (Vrai, Faux, Imprécis, Non Vérifiable), une explication contextuelle et les sources utilisées.

### 2.5. Conclusion partielle
Ce chapitre a décrit la structure méthodologique de notre solution, passant d'un framework théorique à une architecture de composants interconnectés. En combinant le crawling ciblé, l'analyse sémantique transverse et la génération augmentée, le système est capable de répondre aux défis de l'infobésité. Le chapitre suivant portera sur la modélisation UML de ces interactions techniques.
