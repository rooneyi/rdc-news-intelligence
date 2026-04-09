# Chapitre 2 : Méthodologie, collecte et préparation des données

## 2.1. Introduction partielle

La qualité d'un système de recherche augmentée par récupération dépend directement de la qualité du corpus sur lequel il repose. Un moteur RAG ne peut produire des résultats pertinents que si les documents qu'il interroge sont récents, bien structurés et suffisamment représentatifs du domaine traité. Dans le cadre de RDC News Intelligence, cette exigence est particulièrement importante, car le projet vise à traiter des contenus d'actualité congolais qui évoluent rapidement et qui sont publiés sur des sources hétérogènes.

Ce chapitre présente la méthodologie adoptée pour constituer, enrichir et maintenir ce corpus. Il décrit d'abord les sources de données et le rôle du crawler dans l'alimentation continue du système. Il explique ensuite la préparation des documents, leur vectorisation sémantique et leur indexation dans PostgreSQL avec pgvector. Enfin, il présente les mécanismes d'évaluation de la pertinence de la recherche sémantique et du pipeline RAG.

## 2.2. Démarches méthodologiques

L'approche retenue s'inscrit dans une logique d'ingénierie logicielle orientée données. Plutôt que de figer le système sur un corpus statique, nous avons choisi une architecture capable d'intégrer régulièrement de nouveaux articles et de recalculer les représentations nécessaires à la recherche sémantique. Cette approche permet de maintenir le moteur d'information à jour tout en limitant les opérations manuelles.

La méthodologie suit quatre étapes principales. La première consiste à collecter les articles à partir de sources médiatiques congolaises. La deuxième étape est le nettoyage et la normalisation des contenus afin d'obtenir des textes exploitables par les modèles de langage. La troisième étape est la vectorisation de chaque document, c'est-à-dire sa conversion en embedding numérique. La quatrième étape est l'indexation dans une base de données vectorielle pour permettre la recherche par similarité.

Cette organisation répond à deux objectifs. D'une part, elle assure la cohérence technique du système. D'autre part, elle prépare le terrain pour une alimentation continue du moteur de recommandation, ce qui est essentiel dans un contexte d'actualité.

## 2.3. La collecte des données

### 2.3.1. Sources de données

Le corpus du projet est constitué de deux couches complémentaires. La première couche est un jeu de données initial issu de sources ouvertes, utilisé pour lancer le système et disposer rapidement d'un volume suffisant d'articles. La seconde couche est alimentée en continu par un crawler qui collecte les contenus publiés sur plusieurs médias congolais.

Les sources retenues sont choisies selon plusieurs critères: la régularité de publication, la pertinence par rapport au contexte congolais, l'accessibilité technique du site et la diversité des sujets traités. Cette stratégie permet d'éviter une dépendance à une seule source et d'améliorer la couverture thématique du corpus.

### 2.3.2. Le rôle du crawler

Le crawler joue un rôle central dans la mise à jour du système. Il explore les sites ciblés, récupère les métadonnées essentielles des articles et stocke les résultats sous un format structuré. Ce mécanisme permet d'automatiser l'alimentation du corpus sans intervention manuelle constante.

Les articles collectés sont généralement exportés en JSONL, ce qui facilite leur traitement en ligne et leur injection dans le backend. Ce format présente l'avantage d'être simple, lisible et compatible avec un pipeline de réimportation par lots.

Le crawler n'est donc pas un simple outil de scraping. Dans l'architecture du projet, il constitue le premier maillon de la chaîne de recommandation. En mettant à jour les données d'entrée, il garantit que le moteur RAG travaille sur une base d'information récente, ce qui améliore la qualité des réponses et la pertinence des recommandations.

### 2.3.3. Intégration au backend

Une fois les articles collectés, ils sont injectés dans le backend du système. À cette étape, le texte est validé, nettoyé et préparé pour la vectorisation. Cette intégration permet de garder une séparation claire entre la phase de collecte et la phase d'indexation, tout en maintenant un flux continu entre les deux.

L'avantage de cette architecture est double. Elle permet d'une part de reconstituer le corpus en cas de mise à jour importante. Elle permet d'autre part d'ajouter de nouvelles sources sans modifier le fonctionnement général du système.

## 2.4. La préparation des données

### 2.4.1. Nettoyage et normalisation

Avant toute vectorisation, les données doivent être nettoyées. Cette étape consiste à supprimer les éléments inutiles, à harmoniser les champs textuels et à réduire les incohérences de format. Les doublons sont également filtrés afin de limiter l'enrichissement artificiel du corpus par des articles identiques ou très proches.

La normalisation s'applique notamment aux caractères accentués, à la ponctuation, aux espaces superflus et aux dates. L'objectif n'est pas de transformer le contenu sémantique des articles, mais de fournir un texte homogène et exploitable pour les étapes suivantes.

### 2.4.2. Vectorisation sémantique

La vectorisation transforme chaque document en représentation numérique. Cette représentation conserve l'information de sens tout en rendant possible le calcul de proximité entre documents. Dans le projet, cette opération est réalisée à l'aide de modèles SentenceTransformers adaptés au multilinguisme.

La logique est simple: deux textes qui parlent du même sujet doivent avoir des vecteurs proches dans l'espace de représentation. Grâce à cette propriété, le système peut retrouver des articles similaires même si les formulations diffèrent. Cette capacité est essentielle pour un corpus d'actualité où les mêmes événements peuvent être décrits avec des mots variés selon les médias.

### 2.4.3. Stockage vectoriel

Une fois calculés, les embeddings sont stockés dans une base PostgreSQL enrichie par pgvector. Cette extension permet d'effectuer des requêtes de similarité directement dans la base, ce qui simplifie l'architecture globale et limite le besoin de services externes pour la recherche sémantique.

Le stockage vectoriel joue un rôle fondamental dans le système. Il transforme la base de données en mémoire sémantique du projet. Chaque nouvel article enrichit cette mémoire, et chaque requête utilisateur peut y être comparée pour récupérer les contenus les plus pertinents.

## 2.5. Entraînement et indexation

### 2.5.1. Création de l'index pgvector

L'indexation est réalisée avec une structure adaptée à la recherche vectorielle de grande taille. Dans notre cas, l'index IVFFLAT est utilisé pour accélérer les recherches par similarité cosinus. Ce choix permet de conserver de bonnes performances même lorsque le nombre d'articles augmente de manière significative.

L'intérêt de cette indexation est d'équilibrer vitesse et pertinence. Le système peut ainsi interroger un corpus dense sans entraîner de dégradation importante des temps de réponse, ce qui est indispensable pour une utilisation via messagerie instantanée.

### 2.5.2. Ré-embedding et maintenance

Le système prévoit également la possibilité de recalculer les embeddings lorsque le modèle de vectorisation change ou lorsque le corpus est enrichi de façon importante. Cette opération permet de maintenir la cohérence entre les articles stockés et le modèle utilisé pour la recherche.

Cette maintenance est importante dans une architecture évolutive. Elle garantit que les documents déjà présents dans la base restent comparables aux nouveaux articles et que le moteur de recommandation conserve un comportement homogène.

## 2.6. Interprétation et évaluation du modèle

### 2.6.1. Évaluation de la recherche sémantique

L'évaluation du système repose d'abord sur la qualité de la récupération. Une bonne requête doit permettre de retrouver rapidement les articles réellement pertinents pour une question donnée. Pour cela, plusieurs critères peuvent être observés: la proximité sémantique des résultats, la diversité des sources et la cohérence des contenus renvoyés.

L'objectif n'est pas seulement de mesurer un score technique, mais de vérifier si le système répond bien au besoin de l'utilisateur. Dans un usage journalistique ou fact-checking, la pertinence des sources est aussi importante que la rapidité de récupération.

### 2.6.2. Évaluation qualitative du pipeline RAG

Le pipeline RAG est ensuite évalué sur sa capacité à produire une réponse utile à partir des documents récupérés. Cette évaluation porte notamment sur la clarté du résumé, l'alignement avec les sources, la capacité à éviter les réponses hors sujet et la cohérence du format de sortie.

Dans notre cas, la structure de réponse visée doit permettre à l'utilisateur de distinguer rapidement la vérification, l'explication et les sources. Cette organisation facilite la lecture sur mobile et réduit la charge cognitive.

## 2.7. Conclusion partielle

La méthodologie retenue dans ce travail repose sur une chaîne cohérente allant de la collecte des données à la génération de réponses. Le crawler alimente le corpus, les documents sont normalisés et vectorisés, puis indexés dans PostgreSQL avec pgvector. Cette organisation transforme la base d'articles en une ressource vivante, constamment enrichie et exploitable par le moteur RAG.

Ce chapitre montre que la qualité du système ne dépend pas uniquement du modèle génératif, mais aussi de la solidité du pipeline de données. Le chapitre suivant présentera la modélisation architecturale du système, ses composants et ses cas d'utilisation.
