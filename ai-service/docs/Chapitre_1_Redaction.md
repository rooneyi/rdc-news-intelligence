# Chapitre 1 : L'intelligence artificielle au service de la gestion de l'information

## 1.1. Introduction partielle

La transformation numérique a profondément modifié la manière dont l'information est produite, diffusée et consommée. Dans un environnement où les contenus circulent à très grande vitesse, l'utilisateur n'est plus seulement confronté à une abondance de sources, mais aussi à une difficulté croissante de sélection, de vérification et de contextualisation. Cette situation est particulièrement visible dans le domaine de l'actualité, où la multiplication des sites d'information, des réseaux sociaux et des messageries instantanées rend l'accès à une information fiable plus complexe.

En République Démocratique du Congo, cette réalité est encore plus marquée par plusieurs facteurs: la diversité linguistique, la place centrale du mobile dans l'accès à Internet, la circulation rapide des rumeurs et la redondance des contenus entre médias. L'usager doit souvent consulter plusieurs sources pour comprendre un même événement, sans garantie de trouver une synthèse claire, structurée et vérifiée. Dans ce contexte, l'intelligence artificielle apparaît comme un levier pertinent pour améliorer la gestion de l'information, non pas en remplaçant le travail éditorial, mais en facilitant la recherche, le regroupement et la restitution des contenus les plus utiles.

Le présent chapitre examine d'abord les principaux défis de l'écosystème informationnel congolais. Il présente ensuite les solutions existantes, leurs apports, mais aussi leurs limites. Enfin, il introduit l'approche proposée dans ce travail, fondée sur une architecture de recherche augmentée par récupération (RAG), alimentée par un crawler, des embeddings sémantiques et un moteur de recommandation vectoriel.

## 1.2. Les défis de l'écosystème informationnel congolais

La gestion de l'information en RDC est confrontée à plusieurs difficultés structurelles. La première est la surcharge informationnelle. L'utilisateur est exposé à un volume important de contenus qui se répètent, se contredisent ou ne sont que partiellement pertinents. Cette situation crée un phénomène d'infobésité, c'est-à-dire un excès d'informations qui dépasse les capacités normales de traitement cognitif.

Un deuxième défi est le désordre de l'information. Dans l'espace numérique, la désinformation ne se limite plus à quelques cas isolés; elle s'inscrit souvent dans une circulation continue de rumeurs, d'interprétations partielles et de contenus sortis de leur contexte. Les messageries instantanées, les publications virales et les reprises non vérifiées amplifient cette dynamique. L'utilisateur peut alors avoir accès à une grande quantité de données, sans disposer d'outils efficaces pour distinguer le vrai, le faux et l'imprécis.

Le troisième défi est celui de la redondance des contenus. De nombreux articles traitent du même événement en reprenant des formulations proches, parfois avec des différences superficielles dans le titre ou l'angle éditorial. Cette répétition réduit la valeur ajoutée de la recherche manuelle et oblige l'utilisateur à lire plusieurs documents pour obtenir une compréhension globale.

Enfin, le contexte congolais pose un défi multilingue important. Même si le français reste une langue dominante dans la presse en ligne, les langues nationales jouent un rôle majeur dans la diffusion de l'information. Un système de gestion de l'information efficace doit donc tenir compte de cette diversité linguistique afin de rester pertinent pour un large public.

## 1.3. Les solutions actuelles au désordre informationnel

Plusieurs approches existent déjà pour répondre au désordre informationnel. Les premières sont les solutions de fact-checking manuel. Elles consistent à vérifier une information à partir de sources fiables, à recouper les faits et à publier une correction ou une mise en contexte. Ces initiatives jouent un rôle essentiel, en particulier dans les périodes de crise, car elles contribuent à limiter la propagation de fausses nouvelles.

D'autres solutions reposent sur les systèmes de recommandation et les moteurs de recherche. Ils permettent d'aider l'utilisateur à trouver des contenus similaires ou complémentaires à une requête donnée. Dans les environnements d'actualité, ces outils réduisent partiellement le temps de recherche et facilitent l'accès à des articles pertinents. Toutefois, ils restent souvent centrés sur des correspondances lexicales ou sur des classements génériques qui ne prennent pas toujours en compte le sens réel des contenus.

Les approches de traitement automatique du langage naturel ont également permis des progrès notables. Les modèles de classification, de résumé automatique, d'analyse de similarité et de détection de sujets donnent la possibilité de structurer de grands ensembles d'articles et de mieux organiser l'accès à l'information. Dans le cas des contenus africains et congolais, ces méthodes sont particulièrement intéressantes lorsqu'elles peuvent fonctionner dans plusieurs langues et s'adapter à des corpus locaux.

## 1.4. Les limites des solutions actuelles

Malgré leurs apports, les solutions existantes présentent encore plusieurs limites. Le fact-checking manuel reste coûteux en temps et dépend fortement de l'intervention humaine. Il ne peut pas absorber en continu le volume croissant de contenus publiés chaque jour. De plus, ses résultats sont souvent dispersés sur plusieurs plateformes, ce qui complique leur réutilisation par l'utilisateur final.

Les moteurs de recherche classiques et les systèmes de recommandation basés uniquement sur des critères lexicaux montrent également leurs limites. Une requête formulée avec des mots différents de ceux du document cible peut renvoyer des résultats peu pertinents, même si le sujet est proche. Ce décalage entre les mots et le sens est particulièrement problématique dans les environnements multilingues et dans les contextes où les utilisateurs n'expriment pas leurs besoins de manière standardisée.

Les approches fondées sur le seul regroupement thématique permettent, elles aussi, d'identifier des ensembles d'articles proches, mais elles ne suffisent pas toujours à produire une réponse directement exploitable. Elles classent, organisent ou regroupent, mais elles ne fournissent pas nécessairement une synthèse contextualisée. Dans un usage orienté vers le public ou vers le journalisme mobile, cette limite réduit l'efficacité opérationnelle du système.

C'est précisément pour combler cet écart entre la recherche d'information et la restitution utile que notre travail adopte une architecture RAG, capable d'associer récupération pertinente et génération de réponse.

## 1.5. Solution proposée basée sur l'intelligence artificielle

La solution proposée dans ce travail, RDC News Intelligence, s'inscrit dans une logique de recherche augmentée par récupération. L'objectif n'est pas seulement de trouver des articles similaires, mais de construire un système capable d'alimenter une réponse fiable à partir d'un corpus d'actualité continuellement mis à jour.

Le premier pilier de cette solution est le crawler. Il collecte régulièrement des articles issus de sources d'information congolaises et alimente le corpus de travail. Cette étape est essentielle, car un moteur de recommandation n'a de valeur que s'il repose sur des données fraîches, diversifiées et structurées.

Le deuxième pilier est la vectorisation sémantique. Chaque article collecté est transformé en embedding, c'est-à-dire en représentation numérique qui conserve l'information de sens. Grâce à cette représentation, le système peut comparer des textes de manière sémantique et non seulement par mots-clés. Cette approche améliore considérablement la pertinence des résultats.

Le troisième pilier est l'indexation vectorielle dans PostgreSQL avec pgvector. Les embeddings sont stockés dans la base de données et interrogés à l'aide d'opérations de similarité. Lorsqu'un utilisateur soumet une requête, celle-ci est convertie en vecteur puis comparée aux articles déjà indexés. Les contenus les plus proches servent alors de contexte à la génération de réponse.

Le quatrième pilier est la génération locale par un modèle de langage. Dans notre cas, le système s'appuie sur un modèle exécuté localement via Ollama. Le modèle ne travaille pas de manière isolée: il reçoit les passages récupérés par la recherche sémantique et produit une réponse structurée, contextualisée et plus fiable que celle d'un générateur non alimenté par des sources.

Enfin, l'accès au système est pensé pour être simple et mobile. L'intégration avec Telegram et WhatsApp permet aux utilisateurs d'interagir avec le moteur d'information depuis des canaux déjà familiers. Un traitement OCR local complète l'ensemble pour permettre l'analyse d'images contenant du texte, ce qui renforce l'utilité du système dans des situations de fact-checking ou de consultation rapide.

Ainsi, l'IA n'est pas utilisée ici comme un effet de mode, mais comme une réponse méthodologique au problème réel de surinformation. Elle permet de collecter, structurer, comparer et restituer l'information de manière plus efficace, tout en tenant compte du contexte congolais.

## 1.6. Conclusion partielle

Ce chapitre a montré que la gestion de l'information en RDC est confrontée à des contraintes fortes liées à la surcharge informationnelle, à la désinformation, à la redondance des contenus et à la diversité linguistique. Les solutions classiques apportent des réponses utiles, mais elles restent incomplètes lorsqu'il s'agit de produire une synthèse fiable, rapide et contextualisée.

L'approche proposée dans ce travail repose donc sur une architecture RAG alimentée par un crawler, des embeddings sémantiques et une base vectorielle. Cette combinaison permet de transformer un corpus d'actualité en base de connaissance vivante, exploitable depuis Telegram, WhatsApp ou d'autres interfaces mobiles. Le chapitre suivant détaillera la méthodologie de collecte, de préparation et d'indexation des données qui rendent cette architecture possible.
