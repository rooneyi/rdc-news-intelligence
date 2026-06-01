# INTRODUCTION GENERALE

## 0.1 Generalites

L'ecosysteme informationnel contemporain est marque par une production continue de contenus numeriques, facilitee par la generalisation de l'Internet mobile, des reseaux sociaux et des services de messagerie instantanee. Cette evolution, tout en democratisant l'acces a l'information, accentue la vulnerabilite des publics a la circulation rapide de contenus incomplets, trompeurs ou hors contexte. Plusieurs travaux ont montre que la dynamique de diffusion privilegie souvent la viralite plutot que la veracite, ce qui cree un terrain favorable a la desinformation et a la polarisation [2], [8].

En Republique Democratique du Congo (RDC), cette dynamique est particulierement marquee. La diffusion du smartphone et l'usage massif des services de communication numerique (WhatsApp, Facebook, sites d'information en ligne) ont fait du mobile un canal central d'acces aux actualites [27]. Dans un environnement fortement mobile, les utilisateurs consultent et partagent des informations de maniere fragmentee, souvent au sein de groupes prives ou communautaires.

Cependant, cette accessibilite accrue s'accompagne d'un effet secondaire majeur: la multiplication des contenus informationnels, non structures, redondants et de qualite variable. Les plateformes numeriques, optimisees pour l'engagement, mettent en avant des contenus qui suscitent reactions et partages, au detriment de la fiabilite [2]. Cette logique augmente la probabilite d'exposition a des messages sensationnalistes ou trompeurs, en particulier lors d'evenements sensibles (sante publique, securite, tensions politiques).

Dans ce contexte, les utilisateurs sont confrontes a un phenomene de surinformation, souvent designe sous le terme d'**infobesite**. Il se caracterise par une exposition excessive a un volume d'informations difficile a traiter, comprenant des contenus contradictoires, incomplets ou dupliques [3], [4]. Cette surcharge reduit la capacite a analyser, comparer et interpreter correctement les informations disponibles, et encourage des heuristiques rapides fondees sur la repetition ou l'emotion [5], [6].

Par ailleurs, un autre defi important concerne le traitement automatique des langues. La majorite des technologies NLP est historiquement developpee et evaluee sur des langues a fortes ressources (anglais, francais), ce qui limite leur efficacite dans des contextes multilingues comme celui de la RDC, ou plusieurs langues nationales coexistent et ou les corpus numeriques disponibles sont parfois faibles [28]. Cette situation renforce les inegalites d'acces a l'information et reduit la pertinence des systemes automatises dans les environnements locaux.

Ainsi, la combinaison de la surinformation, de la desinformation et des limites technologiques rend necessaire le developpement de solutions intelligentes capables de structurer, filtrer et restituer l'information de maniere pertinente, avec des garanties minimales de tracabilite.

## 0.2 Problematique

Dans le contexte congolais, le probleme fondamental ne reside plus dans la rarete de l'information, mais dans sa profusion desorganisee. Les utilisateurs sont exposes a une grande quantite de contenus sans disposer d'outils efficaces pour en evaluer rapidement la fiabilite ou la pertinence.

La detection automatique de la desinformation constitue un defi majeur. Elle suppose l'existence de sources de reference fiables et disponibles en temps reel, condition rarement satisfaite lors d'evenements recents ou de situations de crise [8]. De plus, les canaux prives (messageries chiffrees) reduisent la visibilite globale des flux, ce qui complique les methodes classiques de monitorage.

Face a cette difficulte, une alternative consiste a repenser le probleme en se concentrant non seulement sur la detection du faux, mais sur la reduction de la surinformation par structuration. L'objectif devient de regrouper les contenus disponibles afin de faciliter leur comprehension, en diminuant les redondances et en rendant explicites les divergences.

L'approche de **Story Identification** s'inscrit dans cette logique: elle vise a regrouper des articles traitant d'un meme evenement, meme s'ils proviennent de sources differentes. Cette methode permet a l'utilisateur de comparer les angles de traitement, d'identifier les informations communes et de reperer les divergences eventuelles. Elle contribue ainsi a reduire le bruit informationnel et a ameliorer la lisibilite des contenus.

Le defi consiste donc a concevoir un systeme capable de:

- regrouper automatiquement les informations similaires;
- detecter les redondances;
- restituer une information synthetique et comprehensible.

Dans ce cadre, la question centrale de cette recherche est la suivante:

**Comment concevoir une architecture de chatbot intelligent, capable de traiter des requetes simples et d'exploiter une approche de Generation Augmentee par Recuperation (RAG), afin de transformer un ensemble d'articles d'actualite en une reponse structuree permettant de reduire la surinformation en RDC?** [13]

## 0.3 Hypotheses

Nous posons l'hypothese qu'un systeme fonde sur une architecture **Retrieval-Augmented Generation (RAG)** peut contribuer significativement a la reduction de la surinformation. Ce systeme repose sur plusieurs mecanismes complementaires:

- analyse de la requete utilisateur;
- recherche semantique dans un corpus d'actualites;
- regroupement des contenus similaires (Story Identification);
- generation d'une reponse synthetique.

Concretement, le chatbot recoit une question en langage naturel, interroge un corpus constitue de donnees issues de medias congolais (par exemple Radio Okapi, Actualite.cd, 7sur7.cd), puis selectionne les informations les plus pertinentes via retrieval vectoriel [13], [14]. Ces informations sont ensuite utilisees pour produire une reponse structuree, permettant a l'utilisateur de comprendre rapidement un evenement sans consulter plusieurs sources.

Ainsi, l'integration de la recherche semantique et de la generation conditionnee permet de transformer une recherche brute en une recommandation intelligente et contextualisee.

## 0.4 Contributions principales de la recherche

En coherence avec l'article ITNCC2026, la presente recherche revendique les contributions suivantes:

1. **Identification rapide de sources fiables**  
   Le systeme met en oeuvre un crawler cible qui alimente en continu une base documentaire locale exploitable en verification.

2. **Verification conversationnelle multi-canal**  
   L'architecture permet le traitement de messages reçus via WhatsApp/Whapi et Telegram, en contexte prive ou en groupe.

3. **Classification thematique et priorisation**  
   Le moteur applique un filtrage thematique et une logique de pertinence pour limiter les traitements inutiles.

4. **Generation de syntheses avec references (RAG)**  
   Les reponses sont generees a partir de sources recuperees dans le corpus, avec restitution structuree (verdict, explication, references).

5. **Reduction de la redondance informationnelle**  
   Un mecanisme de similarite semantique permet d'identifier les messages deja traites et de reutiliser des reponses pivots courtes, afin de limiter l'infobesite.

6. **Adaptabilite contextuelle (sources/langues)**  
   Le framework est conçu pour integrer de nouvelles sources et mieux couvrir la diversite linguistique (francais, anglais, swahili).

## 0.5 Choix et interet du sujet

Le choix de ce sujet presente un interet scientifique, technologique et societal.

- **Interet scientifique**: le travail s'inscrit dans la recherche d'information, les systemes de recommandation et le NLP, avec un accent sur les LLM et les architectures RAG [13]. Il contribue a l'adaptation de ces approches a des environnements multilingues et moins couverts.

- **Interet technologique**: la solution integre des composantes modernes et complementaires:
  - collecte automatique (crawler);
  - vectorisation semantique (embeddings);
  - base de donnees vectorielle;
  - generation de texte par modele local;
  - interface conversationnelle sur messageries.

- **Interet societal**: en facilitant l'acces a une information structuree, le systeme contribue a ameliorer la qualite de l'information disponible pour les citoyens. Le choix d'un deploiement via WhatsApp/Telegram se justifie par leur adoption et leur accessibilite (usage mobile, cout de donnees reduit, interface familiere) [7].

## 0.6 Methodologies et techniques

La presente etude adopte une demarche orientee donnees (data-driven). Elle consiste a collecter, organiser et analyser des informations issues de sources d'actualites en ligne afin de produire des resultats pertinents pour l'utilisateur.

Le coeur technique repose sur une architecture RAG, combinant retrieval d'information et generation de reponses [13]. La methodologie est articulee autour des etapes suivantes:

1. constitution d'un corpus d'actualites;
2. structuration et stockage des metadonnees (SQL);
3. vectorisation et indexation (base vectorielle);
4. recherche des documents pertinents (Top-k);
5. generation d'une reponse synthetique structuree.

Le developpement suit une approche iterative: les performances et la qualite des resultats sont ameliores progressivement au fil des tests, en ajustant les seuils de similarite, les parametres de retrieval et les contraintes de formatage des reponses.

## 0.7 Etat de l'art (synthese)

### 0.7.1 Architectures RAG pour la verification d'information

L'etat de l'art montre que les architectures RAG ameliorent la fiabilite des reponses en imposant un ancrage documentaire explicite [13], [14]. Cette logique correspond directement au fonctionnement de notre projet, qui combine retrieval semantique sur base vectorielle et generation contextuelle.

### 0.7.2 Retrieval vectoriel et indexation semantique

La recherche vectorielle permet de retrouver des contenus proches semantiquement, meme lorsque la formulation de la requete differencie des articles sources [16]. Ce principe est implemente dans notre systeme via ChromaDB et embeddings, et sert de base au regroupement de contenus similaires.

### 0.7.3 Chatbots, OCR et acces conversationnel

Les chatbots constituent une interface efficace pour rendre la verification accessible sur mobile [12]. Dans notre implementation, cette interface est completee par un module OCR afin de traiter aussi les rumeurs diffusees sous forme d'images, puis de les reinjecter dans le pipeline RAG.

## 0.8 Delimitation du travail

Afin de garantir une pertinence locale, cette etude se concentre exclusivement sur la RDC. Elle porte sur la collecte, la recherche et la recommandation de contenus informationnels produits par les medias numeriques, principalement sous forme textuelle, avec une ouverture au traitement d'images via OCR.

Sur le plan technique, l'etude se limite a la conception et l'implementation d'un systeme de regroupement et de restitution de contenus, deploye via API et chatbots (WhatsApp/Telegram). Les aspects juridiques, economiques et organisationnels de la regulation des medias, ainsi que la verification manuelle exhaustive des faits, sont hors perimetre.

## 0.9 Subdivision du travail

Outre l'introduction et la conclusion generales, le memoire est structure en quatre chapitres:

1. **Chapitre I**: contexte, enjeux (surinformation/desinformation) et apports de l'IA.
2. **Chapitre II**: methodologie (collecte, preparation, vectorisation, indexation, RAG).
3. **Chapitre III**: modelisation UML et architecture du systeme.
4. **Chapitre IV**: implementation technique, deploiement et discussion des resultats.

---

## References

Les references bibliographiques sont centralisees dans `thesis/References.md` avec une numerotation IEEE unique et continue pour l'ensemble du memoire.
