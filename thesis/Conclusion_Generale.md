# CONCLUSION GÉNÉRALE

## C.1 Rappel du contexte et de la problématique

Ce mémoire s'est inscrit dans un contexte où l'accès à l'information n'est plus le principal obstacle pour les publics congolais, mais où la **qualité**, la **fiabilité** et la **lisibilité** des contenus le deviennent. La généralisation du smartphone, l'usage massif de WhatsApp et de Telegram, ainsi que la multiplication des médias en ligne ont transformé le mobile en canal central de consultation et de partage de l'actualité [7], [27]. Cette dynamique s'accompagne toutefois d'une exposition croissante à des messages incomplets, redondants ou trompeurs, dans des espaces de discussion souvent privés et difficiles à observer depuis l'extérieur [8], [29].

Deux phénomènes, étroitement liés, structurent cette crise : la **désinformation** et l'**infobésité** [3], [4], [32]. La première concerne la diffusion de contenus faux ou orientés ; la seconde renvoie à la surcharge cognitive provoquée par un volume d'informations que l'utilisateur ne peut plus traiter correctement. Or, les outils de correction automatique peuvent, s'ils sont mal conçus, aggraver cette seconde difficulté en multipliant les longues réponses dans un même fil de discussion [12], [30].

La question centrale posée en introduction visait donc à dépasser une logique purement binaire « vrai / faux ». Il s'agissait de concevoir une architecture de chatbot intelligent, fondée sur la **génération augmentée par récupération (RAG)**, capable de transformer un corpus d'articles d'actualité en réponses structurées, traçables et adaptées aux contraintes des messageries, afin de **réduire la surinformation** en République démocratique du Congo [13].

## C.2 Rappel des hypothèses et de la démarche retenue

L'hypothèse directrice affirmait qu'un système combinant recherche sémantique, regroupement de contenus proches et génération conditionnée pourrait contribuer significativement à cette réduction de la surinformation. Concrètement, le dispositif devait :

- analyser la requête ou le message utilisateur ;
- interroger un corpus local d'articles congolais ;
- regrouper les contenus ou messages similaires ;
- produire une réponse synthétique, courte et appuyée sur des sources [13], [14].

La démarche retenue a été **orientée données** : constitution progressive d'un corpus via un crawler ciblé, structuration en base relationnelle, indexation vectorielle, puis chaîne RAG connectée à des interfaces conversationnelles WhatsApp (Whapi) et Telegram. Un filtrage thématique, une mémoire sémantique et un mécanisme anti-répétition ont été ajoutés pour limiter les traitements inutiles et éviter que la correction elle-même ne surcharge la conversation.

Le mémoire a été organisé en quatre chapitres, complétés par la présente conclusion :

1. **Chapitre I** : contexte, état de l'art et positionnement de la recherche ;
2. **Chapitre II** : méthodologie (collecte, préparation, vectorisation, RAG, anti-redondance) ;
3. **Chapitre III** : modélisation UML et architecture du système ;
4. **Chapitre IV** : implémentation, déploiement et discussion des résultats.

## C.3 Synthèse du travail réalisé

### C.3.1 Cadre conceptuel (Chapitre I)

Le premier chapitre a montré que la crise informationnelle contemporaine ne se réduit pas à la seule détection du faux. Dans les messageries chiffrées, la confiance relationnelle, la viralité cachée et la fragmentation en groupes imposent de repenser les outils de vérification [29], [31]. L'état de l'art confirme l'intérêt des approches automatisées — classifieurs, fact-bots, outils de surveillance — mais souligne leurs limites lorsqu'elles négligent l'infobésité ou les spécificités locales [28]. Le paradigme RAG [13], [14], complété par l'OCR pour les contenus visuels [33] et par la similarité sémantique pour la déduplication conversationnelle, constitue la base théorique retenue.

### C.3.2 Méthodologie (Chapitre II)

Le second chapitre a détaillé le pipeline opérationnel : collecte documentaire, ingestion, génération d'embeddings, stockage dual (PostgreSQL + ChromaDB), retrieval Top-k, génération via modèle local (Ollama/Mistral), puis restitution structurée (verdict, explication, sources). La méthodologie intègre explicitement une **mémoire conversationnelle** : comparaison vectorielle entre le message entrant et les échanges récents, regroupement en clusters sémantiques, réutilisation de verdicts ou envoi de rappels courts lorsque l'information a déjà été traitée. Cette logique répond directement à la lacune identifiée : corriger sans alourdir.

### C.3.3 Modélisation (Chapitre III)

Le troisième chapitre a traduit ces choix en vues UML (cas d'utilisation, classes, séquences, déploiement), en mettant en évidence les interactions entre l'orchestrateur (webhooks, files Redis), le moteur de traitement (topic gate, RAG, mémoire), le crawler et les bases de données [18], [20]. Cette modélisation a servi de guide pour l'implémentation et la maintenance du système.

### C.3.4 Réalisation et déploiement (Chapitre IV)

Le quatrième chapitre a présenté la concrétisation sur un serveur VPS : stack FastAPI, PostgreSQL, ChromaDB, Redis, Ollama, PM2 et Nginx [21]–[26]. Les modules critiques — crawler, ingestion, retrieval, webhooks Whapi/Telegram, OCR Tesseract, topic gate, mémoire locale et globale — ont été décrits dans leur version opérationnelle. Le déploiement sur un corpus de **plus de 13 000 articles**, majoritairement en français, avec une couverture progressive de l'anglais et du swahili, confirme la faisabilité d'un dispositif local, maîtrisé et adapté au contexte congolais.

## C.4 Réponse à la question de recherche

La question posée en introduction trouve une réponse affirmative, **dans le cadre delimité** de cette étude (RDC, médias numériques, déploiement messagerie, corpus local).

Il est possible de concevoir une architecture conversationnelle RAG qui :

1. **structure** l'information en s'appuyant sur des articles d'actualité congolais indexés sémantiquement ;
2. **restitue** des réponses courtes, avec verdict explicite et sources citées ;
3. **limite** la redondance grâce à la mémoire sémantique et à la réutilisation de réponses pivots ;
4. **élargit** le périmètre d'entrée via l'OCR pour les messages visuels ;
5. **s'adapte** aux contraintes techniques des messageries (webhooks, files d'attente, latence variable).

Le système ne prétend pas trancher définitivement toute controverse factuelle ni remplacer une vérification journalistique humaine. En revanche, il offre un **appui conversationnel** permettant à l'utilisateur d'obtenir rapidement une synthèse sourcée, ou d'être informé qu'un contenu proche a déjà été analysé — ce qui réduit le bruit dans le fil de discussion.

L'hypothèse RAG est ainsi **partiellement confirmée** : l'ancrage documentaire améliore la traçabilité des réponses [13], [14], et le couplage avec l'anti-répétition contribue à la sobriété informationnelle recherchée. La confirmation reste toutefois **conditionnelle** à la couverture du corpus, à la qualité des sources indexées et à la clarté du message utilisateur.

## C.5 Principaux apports et résultats

Les apports de cette recherche peuvent être regroupés en six axes, en cohérence avec les contributions annoncées en introduction :

1. **Collecte et mise à jour de sources fiables**  
   Un crawler configurable alimente en continu la base documentaire à partir de médias congolais sélectionnés (RSS, sitemaps, pages ciblées), avec métadonnées structurées et embeddings associés.

2. **Vérification conversationnelle multi-canal**  
   Le système traite les messages reçus via WhatsApp (Whapi) et Telegram, en contexte privé ou en groupe, avec orchestration asynchrone et gestion de charge.

3. **Filtrage thématique et pertinence**  
   Un module de topic gate limite les traitements aux domaines pertinents (santé, sécurité, politique, etc.), réduisant les réponses hors sujet.

4. **Synthèses RAG avec références**  
   Les réponses sont générées à partir de documents récupérés dans le corpus, avec restitution structurée et citation des sources mobilisées.

5. **Réduction de la redondance informationnelle**  
   La mémoire sémantique détecte les messages proches déjà traités ; le système réutilise alors un verdict existant ou envoie un rappel court, au lieu de relancer systématiquement un pipeline complet. Une mémoire globale permet aussi de signaler des sujets déjà abordés dans d'autres conversations.

6. **Adaptabilité contextuelle**  
   L'architecture accepte l'ajout de nouvelles sources et progresse vers une meilleure couverture multilingue (français dominant, anglais et swahili en extension).

Sur le plan des résultats observés en conditions de déploiement, les logs et tests conversationnels confirment le bon enchaînement réception → filtrage → retrieval → génération → restitution. Les scénarios de requêtes répétées montrent une **diminution nette du volume de messages longs**, grâce à la stratégie « une réponse détaillée, puis des rappels courts ». Lorsque le corpus couvre bien le sujet, les réponses perçues sont plus fiables et mieux contextualisées ; lorsque la couverture est insuffisante, le système adopte une posture prudente (« non vérifiable » ou « imprécis »), limitant les affirmations non fondées.

Enfin, l'exécution locale du modèle via Ollama [24] participe à une **maîtrise relative des données** et à une indépendance vis-à-vis d'API cloud tierces — un point important pour un déploiement durable en contexte de recherche appliquée.

## C.6 Limites de l'étude

Malgré ces résultats encourageants, plusieurs limites doivent être reconnues avec lucidité.

**Limites techniques.** Le système repose sur un serveur unique (VPS) dont les ressources CPU et RAM conditionnent fortement les temps de réponse, surtout lors des synchronisations massives ou des appels LLM concurrents. La qualité de l'OCR dépend de la netteté des images reçues ; les captures floues ou fortement compressées restent difficiles à traiter. La couverture en swahili, bien qu'en progression, demeure insuffisante pour certains sujets locaux [28].

**Limites méthodologiques.** L'évaluation s'appuie surtout sur des observations de production, des tests conversationnels et des indicateurs opérationnels (latence, stabilité, comportement anti-répétition). Une campagne d'évaluation utilisateur à grande échelle, avec métriques comparatives et protocole expérimental strict, n'a pas encore été menée. Les résultats restent donc solides pour un **pilote opérationnel**, mais leur généralisation exige des validations ultérieures.

**Limites de périmètre.** Comme indiqué en introduction, les aspects juridiques, économiques et institutionnels de la régulation des médias sont hors scope. Le système ne constitue pas une agence de fact-checking au sens professionnel : il assiste l'utilisateur au moment où celui-ci soumet un contenu, sans prétendre à une modération globale des plateformes.

**Limites liées au corpus.** La qualité des réponses dépend directement de la fraîcheur, de la diversité et de la fiabilité des sources indexées. Un événement très récent ou peu couvert par la presse en ligne restera difficile à vérifier automatiquement.

## C.7 Perspectives de recherche et d'évolution

Les travaux futurs pourraient s'orienter vers les pistes suivantes, déjà esquissées au chapitre IV :

1. **Enrichissement linguistique**  
   Renforcer le corpus swahili et, plus largement, les langues nationales sous-représentées dans les ressources NLP, afin d'élargir l'accessibilité du dispositif [28].

2. **Amélioration de l'OCR et du traitement visuel**  
   Affiner la reconnaissance de texte sur captures dégradées et étendre progressivement le traitement d'autres formats multimodaux, dans la limite des ressources disponibles.

3. **Évaluation utilisateur structurée**  
   Organiser des tests avec des groupes réels, mesurer la satisfaction, la compréhension des réponses et la réduction perçue de la surcharge, au-delà des seuls indicateurs techniques.

4. **Métriques de sobriété cognitive**  
   Formaliser des indicateurs quantifiant la « charge cognitive évitée » grâce à l'anti-répétition (nombre de messages longs non envoyés, taux de réutilisation de verdicts, etc.).

5. **Scalabilité et résilience**  
   Séparer progressivement les services lourds (indexation, LLM) sur des nœuds dédiés, renforcer l'observabilité (tableaux de bord, alertes) et stabiliser l'exploitation en charge élevée.

6. **Interconnexion avec des API externes**  
   Prévoir des connecteurs vers des bases de fact-checking reconnues, pour compléter le corpus local lorsque les sources nationales sont insuffisantes.

7. **Gouvernance éditoriale des sources**  
   Mettre en place une procédure de validation, de retrait et de pondération des sources, afin de consolider la confiance à long terme dans le système.

Ces perspectives visent à faire évoluer le prototype actuel vers une plateforme plus robuste, mieux évaluée et plus représentative de la diversité linguistique et médiatique congolaise.

## C.8 Mot de clôture

En définitive, ce mémoire a montré qu'il est possible de concevoir et de déployer un dispositif de vérification conversationnelle adapté aux réalités de la RDC : un environnement mobile, des messageries privées, un besoin de sources locales et une double contrainte — lutter contre la désinformation **sans** alourdir davantage la conversation.

L'originalité du travail ne réside pas dans l'invention d'un algorithme isolé, mais dans l'**assemblage cohérent** de briques connues — crawler, index vectoriel, RAG, OCR, mémoire sémantique, webhooks — guidé par un principe simple : **informer avec sobriété**. Dans un contexte où la correction automatique peut elle-même devenir bruit, cette orientation mérite d'être approfondie et évaluée plus largement.

Si la route vers une information plus fiable en RDC reste longue, ce projet apporte une brique concrète : un assistant accessible sur les canaux que les citoyens utilisent déjà, capable de transformer un flot d'articles dispersés en réponses structurées, sourcées et moins redondantes. C'est là, nous l'espérons, une contribution utile — scientifique, technique et sociétale — à la clarté informationnelle à l'ère du numérique.

---

## Références

Les références bibliographiques citées dans cette conclusion sont centralisées dans `thesis/References.md`, avec une numérotation IEEE unique et continue pour l'ensemble du mémoire (numéros [1] à [36]).
