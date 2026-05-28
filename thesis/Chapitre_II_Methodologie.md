# CHAPITRE II : METHODOLOGIE DU FRAMEWORK DE LUTTE CONTRE LA SURINFORMATION

## 2.1 Introduction du chapitre

Le chapitre precedent a etabli le cadre theorique: desinformation, infobesite, fatigue cognitive et limites des approches de fact-checking traditionnelles. Le present chapitre decrit la methode adoptee pour transformer ce cadre conceptuel en systeme operationnel deployable en contexte reel de messagerie. Notre objectif methodologique est double:

1. garantir une reponse factuelle ancree sur des sources verifiables;
2. limiter la redondance conversationnelle afin de ne pas aggraver la surcharge informationnelle.

Le dispositif retenu s'appuie sur une architecture par composants, combinant collecte documentaire locale, indexation vectorielle, retrieval semantique et generation assistee par contexte (RAG) [13], [14]. A cette base, nous ajoutons une couche de memoire conversationnelle destinee a detecter les messages semantiquement similaires et a reutiliser des reponses pivots quand cela est possible.

La methodologie exposee ci-dessous est orientee "recherche appliquee": elle privilegie des choix reproductibles, observables en production, et compatibles avec des contraintes de latence, de ressources materielle et de confidentialite des canaux chiffrees.

## 2.2 Paradigme methodological et design de recherche

### 2.2.1 Nature de la recherche

Notre travail releve d'une recherche de type conception-implementation-evaluation (design science), ou la contribution principale est un artefact socio-technique operationnel. L'artefact n'est pas un modele theorique abstrait isole, mais un systeme integre:

- collecte de nouvelles;
- traitement NLP/OCR;
- retrieval et generation;
- interaction conversationnelle sur messagerie.

Cette orientation est pertinente pour des problemes "wicked" tels que la desinformation en canaux prives, ou la valeur scientifique se mesure autant par la performance technique que par l'adaptation au contexte d'usage.

### 2.2.2 Hypotheses operationnelles

La methodologie repose sur les hypotheses suivantes:

- **H1**: une reponse ancree sur des sources locales explicites reduit le risque d'hallucination des LLM [13], [14];
- **H2**: une memoire semantique courte permet de detecter les redondances et de reduire le bruit conversationnel;
- **H3**: un pipeline asynchrone avec file d'attente absorbe mieux les pics de viralite qu'un traitement synchrone pur;
- **H4**: la qualite percue depend autant du format de restitution (lisibilite) que de l'exactitude factuelle.

### 2.2.3 Perimetre et unites d'analyse

L'unite d'analyse principale est le message utilisateur (texte ou image OCR) recu dans un canal conversationnel. L'unite secondaire est le cluster semantique de messages proches. Les resultats observes sont:

- la capacite du systeme a produire un verdict argumente avec sources;
- la reduction de reponses redondantes pour des requetes similaires;
- la stabilite du service sous charge (webhooks, files, workers).

## 2.3 Architecture globale de la solution

### 2.3.1 Vue d'ensemble

L'architecture fonctionnelle est composee de quatre sous-systemes interdependants:

1. **Collecte documentaire (Crawler)**;
2. **Orchestration des flux (Webhooks, Queue, Workers)**;
3. **Moteur d'analyse et de generation (Engine RAG)**;
4. **Canaux d'interaction (WhatsApp/Whapi, Telegram, Web API)**.

Cette decomposition permet de separer les responsabilites, d'ameliorer la maintenabilite et de faciliter l'observabilite des pannes.

### 2.3.2 Principe de fonctionnement

Le fonctionnement nominal suit la chaine:

**Message entrant -> Topic gate -> Memoire semantique -> Retrieval -> Generation -> Reponse structuree**

Si le message est detecte comme tres proche d'un cluster deja traite, le systeme privilegie une reponse courte basee sur le verdict deja etabli. Sinon, il declenche une passe RAG complete.

### 2.3.3 Justification des choix

Le choix RAG est motive par la necessite de citer des sources concretes [13], [14]. Le choix "memoire + clustering" est motive par la contrainte cognitive identifiee au chapitre I. Le choix "queue + worker" est motive par les pics d'entree observes dans les groupes de discussion.

## 2.4 Pipeline de traitement d'un message

### 2.4.1 Etape 1: Reception et normalisation

Les messages entrants sont recus via webhook (Whapi, WhatsApp Meta, Telegram) ou endpoints applicatifs. Une normalisation initiale harmonise le format:

- identifiant de conversation (`chat_id`);
- type de contenu (texte, image, document image);
- horodatage;
- auteur;
- contenu textuel brut (ou texte OCR).

Cette normalisation permet d'appliquer la meme logique metier quel que soit le canal.

### 2.4.2 Etape 2: Filtrage thematique (topic gate)

Un filtre thematique determine si le message releve effectivement du perimetre "verification d'actualite". Cette etape reduit les appels LLM inutiles et limite la charge systeme.

### 2.4.3 Etape 3: Detection de redondance semantique

Le contenu est converti en embedding et compare a la memoire conversationnelle recente du meme chat. Si la similarite depasse un seuil defini, le message est rattache a un cluster existant. Dans ce cas, la methode applique une strategie de reutilisation:

- renvoi du verdict precedent;
- eventuellement resume contextuel court;
- absence de regeneration longue.

Cette etape concretise la logique anti-infobesite de la recherche.

### 2.4.4 Etape 4: Retrieval documentaire

Si le message est nouveau (ou insuffisamment proche d'un cluster connu), le systeme interroge l'index vectoriel pour recuperer les documents les plus pertinents (Top-k). Le retrieval repose sur la similarite semantique entre embedding requete et embeddings documents [16].

### 2.4.5 Etape 5: Generation assistee (RAG)

Le LLM genere une reponse conditionnee par les sources recuperees. Le format de sortie impose:

- verdict explicite (VRAI, FAUX, IMPRECIS, NON VERIFIABLE);
- explication concise et contextuelle;
- sources citees avec liens.

Ce format normalise ameliore la lisibilite et la verificabilite des reponses.

### 2.4.6 Etape 6: Restitution et journalisation

La reponse est envoyee au canal d'origine et journalisee avec metadonnees de trace:

- latence de traitement;
- documents utilises;
- type de decision (reponse nouvelle vs reutilisation cluster).

Ces traces soutiennent l'analyse des performances et le debugging.

## 2.5 Description detaillee des composants

### 2.5.1 Crawler et gouvernance des sources

Le crawler collecte des contenus depuis un catalogue de sources configurees (RSS et HTML). La strategie de collecte applique:

- contraintes de pagination;
- limitation de volume par source;
- extraction du corps de texte, metadonnees et liens;
- controle de duplication.

Une attention particuliere est accordee au multilinguisme (francais, anglais, swahili), afin d'ameliorer la couverture documentaire du contexte congolais.

### 2.5.2 Stockage relationnel (PostgreSQL)

PostgreSQL conserve les metadonnees canoniques des articles:

- titre, contenu, source, hash, date, categorie, image;
- contraintes d'unicite (hash, lien) pour limiter les doublons.

La base relationnelle constitue la couche de verite transactionnelle.

### 2.5.3 Stockage semantique (ChromaDB)

ChromaDB conserve les representations vectorielles pour la recherche semantique rapide [16]. Le couplage PostgreSQL + Chroma permet de separer:

- integrite transactionnelle (SQL);
- proximite semantique (vectorielle).

### 2.5.4 Orchestrateur de flux (Webhook + Queue)

L'orchestrateur gere l'entree/sortie des canaux de messagerie. En mode charge elevee, la file Redis absorbe les pics et desacouple reception et traitement, limitant les pertes et timeout.

### 2.5.5 Moteur RAG

Le moteur combine:

- generation d'embeddings;
- retrieval Top-k;
- synthese LLM avec contraintes de format;
- module de memoire conversationnelle.

L'objectif est d'optimiser le triptyque precision, latence, sobriete.

### 2.5.6 OCR pour contenus visuels

Le module OCR extrait du texte depuis des captures d'ecran ou affiches virales. Cette etape est critique, car une part notable de la desinformation circule sous forme d'image.

## 2.6 Strategie de parametrage et seuils

### 2.6.1 Seuil de similarite

Le seuil de similarite controle le rattachement a un cluster existant. Un seuil trop bas fusionne des sujets differents; un seuil trop haut empeche la reutilisation utile. Le parametrage retenu est ajuste empiriquement selon:

- cohérence semantique des clusters obtenus;
- taux de reutilisation de reponses pertinentes;
- reduction effective de la redondance.

### 2.6.2 Parametres retrieval et generation

Les parametres `top_k`, contexte LLM, longueur maximale de sortie et timeout influencent directement le compromis entre qualite et cout de calcul. La methodologie retient des valeurs pragmatiques compatibles avec un VPS CPU limite.

### 2.6.3 Parametres d'exploitation

Le mode cron, les intervalles de polling et les tailles de batch de re-indexation sont definis pour assurer la continuite de service sans saturer les ressources memoire.

## 2.7 Protocoles operationnels de deploiement

### 2.7.1 Environnement cible

Le deploiement cible un VPS unique integrant:

- API FastAPI;
- PostgreSQL;
- Redis;
- Ollama;
- Nginx reverse proxy;
- PM2 comme superviseur de processus.

Ce choix privilegie la simplicite operationnelle pour une phase de recherche appliquee.

### 2.7.2 Robustesse et reprise

La methode de deploiement inclut:

- supervision de processus;
- relance automatique;
- journalisation centralisee;
- strategie de reprise pour les taches longues (screen/tmux pour synchronisations).

### 2.7.3 Securite et confidentialite

Le dispositif applique:

- tokens de webhook/relay;
- endpoints internes en `127.0.0.1` pour les flux inter-services sensibles;
- separation des secrets environnement.

Le systeme ne casse pas le chiffrement des messageries; il traite uniquement les messages explicitement recus via les integrations autorisees.

## 2.8 Indicateurs et methode d'evaluation

### 2.8.1 Indicateurs techniques

Les indicateurs retenus sont:

- disponibilite de l'API (health checks);
- taux de succes des webhooks;
- latence moyenne de reponse;
- couverture d'indexation (articles SQL vs vecteurs Chroma).

### 2.8.2 Indicateurs informationnels

Nous suivons:

- qualite du verdict (coherence avec sources);
- taux de messages non verifiables;
- diversite linguistique des sources mobilisees.

### 2.8.3 Indicateurs anti-infobesite

Les indicateurs specifique a l'hypothese centrale incluent:

- taux de reutilisation de verdicts pour messages redondants;
- reduction du volume textuel envoye pour sujets repetitifs;
- maintien de la qualite informative apres compression.

## 2.9 Limites methodologiques

Comme toute architecture appliquee, notre methode presente des limites:

- dependance a la qualite des sources collectees;
- sensibilite des performances au dimensionnement materiel du VPS;
- difficulte d'obtenir des verites terrain absolues pour tous les sujets d'actualite;
- variabilite des API tierces (messageries, fournisseurs LLM).

Ces limites n'invalident pas l'approche, mais cadrent son domaine de validite et orientent les perspectives d'amelioration.

## 2.10 Conclusion partielle

Ce chapitre a formalise la methodologie du framework propose. Nous avons decrit un pipeline complet, depuis la collecte documentaire jusqu'a la restitution conversationnelle, en passant par la memoire semantique et la generation RAG. La specificite de l'approche est d'integrer explicitement la dimension anti-infobesite au coeur du processus de fact-checking.

L'apport methodologique majeur est donc l'articulation entre exactitude factuelle et sobriete informationnelle. Le chapitre suivant presentera la modelisation UML de cette architecture (cas d'utilisation, classes, sequences) afin de traduire ces principes en artefacts de conception formels.

---

## References

Les references bibliographiques de ce chapitre sont centralisees dans `thesis/References.md` avec une numerotation IEEE unique et continue pour l'ensemble du memoire.
