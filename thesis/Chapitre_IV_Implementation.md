# CHAPITRE IV : REALISATION, IMPLEMENTATION ET DISCUSSION

## 4.1 Introduction du chapitre

Ce chapitre presente la concretisation de l'architecture decrite precedemment. L'objectif est de montrer comment les choix methodologiques (RAG, memoire semantique, anti-redondance, orchestration asynchrone) ont ete traduits en composants executables dans un environnement VPS reel. Nous detaillons:

1. l'environnement technique de developpement et de production;
2. les etapes d'implementation des modules critiques;
3. la procedure de deploiement et d'exploitation;
4. les resultats observes et leur interpretation;
5. les limites techniques et les perspectives d'amelioration.

Le chapitre adopte une logique de "preuve par l'execution": chaque choix est discute en fonction de son impact concret sur la fiabilite, la latence et la qualite de reponse.

## 4.2 Environnement de realisation

### 4.2.1 Stack logicielle retenue

La solution RDC News Intelligence repose sur une pile coherent avec les contraintes d'un systeme conversationnel orienté IA:

- **Python 3.x** comme langage principal pour l'ecosysteme NLP/LLM.
- **FastAPI** pour l'exposition des endpoints webhook et des APIs internes [21].
- **PostgreSQL** pour les donnees transactionnelles (articles, metadonnees).
- **ChromaDB** pour l'indexation vectorielle et le retrieval semantique [22].
- **Redis** pour files temporaires, etats courts et desacouplage des flux [23].
- **Ollama** comme runtime local de modele (Mistral 7B quantize) [24].
- **PM2** pour la supervision des processus applicatifs [25].
- **Nginx** pour la terminaison HTTPS et le reverse proxy [26].

Cette combinaison a ete choisie pour privilegier la maitrise locale des donnees, la reduction des couts API externes et la robustesse operationnelle.

### 4.2.2 Environnement d'execution

Le deploiement cible est un VPS Linux unique. Ce choix simplifie l'exploitation en phase de recherche appliquee et permet de:

- limiter la complexite d'orchestration multi-noeuds;
- observer facilement les goulots d'etranglement;
- iterer rapidement sur les reglages (batch, timeout, mode cron).

Les services sont configures en local (`127.0.0.1`) pour les flux internes sensibles (DB, Redis, Ollama, queue pop/relay).

## 4.3 Implementation des modules fonctionnels

### 4.3.1 Module de collecte documentaire (Crawler)

Le crawler execute des synchronisations par source ou en mode global (`--source-id all`). Il lit un catalogue de sources configurees (RSS/HTML), extrait le contenu et poste les articles vers l'API d'ingestion. Les choix d'implementation incluent:

- limitation `--limit` pour controler la charge;
- support multilingue via `sourceLang` (fr, en, sw);
- deduplication par hash/lien;
- journalisation des erreurs source par source.

Le pipeline de collecte n'est pas strictement couple au moteur LLM: il peut fonctionner independamment puis alimenter la couche vectorielle.

### 4.3.2 Module d'ingestion et persistence

L'endpoint d'ingestion (`/crawler/articles`) applique les etapes suivantes:

1. validation payload;
2. normalisation minimale des champs;
3. insertion SQL avec contraintes d'unicite;
4. generation d'embedding;
5. upsert dans l'index vectoriel.

Ce schema garantit qu'un article valide est rapidement exploitable par le retrieval.

### 4.3.3 Module de retrieval et generation

Le service RAG articule:

- recherche Top-k dans Chroma;
- filtrage de pertinence (seuil de similarite);
- composition d'un prompt structure;
- generation de reponse par Ollama;
- restitution avec sources.

Le format de sortie a ete standardise pour les canaux conversationnels:

- verdict explicite;
- explication compacte;
- section sources.

### 4.3.4 Module memoire et anti-redondance

La memoire conversationnelle compare chaque nouvelle requete aux requetes recentes d'un meme espace de discussion. Si la similarite est elevee:

- reutilisation d'un verdict precedent;
- message court de rappel;
- evite regeneration longue.

Ce mecanisme constitue le coeur de la strategie anti-surinformation.

### 4.3.5 Module OCR

Les images et captures d'ecran sont traitees par OCR local. Le texte extrait est fusionne avec la legende eventuelle puis injecte dans le meme pipeline que les messages texte.

Ce module augmente significativement la couverture de cas reels, car de nombreuses rumeurs circulent sous forme visuelle.

## 4.4 Implementation des canaux de messagerie

### 4.4.1 WhatsApp / Whapi

Le canal Whapi utilise un webhook public (`/webhooks/whapi`) avec deux modes:

- **mode direct**: traitement immediat sur le VPS;
- **mode proxy+queue**: mise en file pour un worker distant.

Dans l'architecture finale tout-en-un VPS, le mode direct a ete privilegie pour reduire la complexite operationnelle.

### 4.4.2 Telegram

Le canal Telegram est supporte via polling (`getUpdates`) ou webhook selon la configuration. En contexte VPS, le polling simplifie les tests car il ne depend pas d'une configuration HTTPS entrante specifique cote Telegram.

### 4.4.3 Robustesse des integrations

Les integrations utilisent:

- tokens de verification;
- timeouts explicites;
- gestion d'erreurs transport;
- logs de traces par endpoint.

Ces garde-fous limitent les pertes de messages en cas de fluctuation reseau.

## 4.5 Deploiement VPS et exploitation

### 4.5.1 Etapes de deploiement

La sequence de deploiement appliquee est:

1. preparation du serveur (dependances systeme);
2. installation de PostgreSQL, Redis, Ollama;
3. restauration des donnees SQL;
4. synchronisation/rebuild de Chroma;
5. configuration `.env`;
6. demarrage FastAPI via PM2;
7. exposition HTTPS via Nginx;
8. validation webhooks et tests fonctionnels.

### 4.5.2 Supervision et logs

Trois niveaux de logs sont utilises:

- logs PM2 (`pm2-ai-out.log`, `pm2-ai-error.log`);
- logs applicatifs (`.logs/fastapi.log`);
- logs Ollama (`journalctl -u ollama`).

Cette triangulation facilite le diagnostic des erreurs de type:

- modele absent;
- conflit de port 8000;
- echec webhook;
- timeout vers services internes.

### 4.5.3 Problemes rencontres et resolutions

Parmi les incidents marquants:

1. **Conflits de processus sur le port 8000**  
   Resolution: nettoyage des instances orphelines, relance unique sous PM2.

2. **Incoherence de variables d'environnement**  
   Resolution: unification des variables et redemarrage controle.

3. **Transfert de donnees instable (scp/rsync)**  
   Resolution: reindexation directe sur VPS et scripts de reprise.

4. **Extensions DB manquantes en restauration**  
   Resolution: installation/activation des extensions requises avant restore.

Ces incidents ont servi de base pour consolider le runbook operationnel.

## 4.6 Resultats obtenus

### 4.6.1 Etat du corpus et indexation

Le corpus exploitable depasse 13 000 articles. La synchronisation SQL -> Chroma a permis d'atteindre une couverture vectorielle quasi complete, condition necessaire pour la qualite du retrieval.

La distribution linguistique observee est globalement:

- francais majoritaire;
- anglais en progression;
- swahili encore sous-represente mais en hausse via nouvelles sources.

### 4.6.2 Comportement du pipeline en production

Les logs de production confirment la chaine suivante:

- reception webhook;
- filtrage thematique;
- retrieval;
- appel LLM;
- restitution avec sources.

Le systeme reste fonctionnel en temps reel sous charge moderee, avec des latences variables selon la taille du contexte et la disponibilite memoire.

### 4.6.3 Efficacite anti-surinformation

Les tests conversationnels sur requetes redondantes montrent une reduction nette du volume de messages longs grace a la reutilisation des verdicts pivots. Dans les scenarios de repetition, la strategie "1 reponse detaillee + rappels courts" diminue la saturation visuelle tout en maintenant la continuite informative.

### 4.6.4 Qualite percue des reponses

La qualite percue est meilleure lorsque:

- les sources locales sont nombreuses et recentes;
- le sujet est bien couvert dans le corpus;
- le message utilisateur est explicite.

Les cas non couverts sont retournes en mode prudent ("non verifiable" ou "imprecis"), ce qui limite les hallucinations assertives.

## 4.7 Discussion critique

### 4.7.1 Forces de la solution

Les forces observees incluent:

- architecture pragmatique et deployable;
- souverainete relative des donnees (LLM local);
- compatibilite multi-canaux;
- reduction de redondance conversationnelle;
- bonne observabilite operationnelle.

### 4.7.2 Limites techniques

Malgre les resultats positifs, plusieurs limites persistent:

1. forte dependance aux ressources CPU/RAM du VPS;
2. sensibilite a la qualite OCR des images degradees;
3. couverture swahili encore insuffisante pour certains sujets;
4. maintenance plus delicate quand plusieurs modes transport sont actives simultanement.

### 4.7.3 Validite externe

Les resultats sont solides pour un cadre pilote operationnel, mais leur generalisation a grande echelle requerra:

- des evaluations comparatives multi-regions;
- des tests de charge prolonges;
- une gouvernance editoriale renforcee des sources.

## 4.8 Perspectives d'amelioration

Les pistes de suite prioritaires sont:

1. enrichissement cible du corpus swahili;
2. politiques de resume adaptatif selon contexte utilisateur;
3. metriques explicites de "charge cognitive evitee";
4. separation progressive des services lourds (LLM/indexation) sur noeuds dedies;
5. tableau de bord d'observabilite unifie (alertes, latence, erreurs webhook, etat index).

Ces evolutions visent a transformer le pilote en plateforme resilient a charge plus elevee.

## 4.9 Conclusion partielle

Ce chapitre a montre que la solution proposee n'est pas seulement conceptualisable, mais effectivement implementable et exploitable sur infrastructure VPS. L'architecture RAG locale, combinee aux mecanismes de memoire semantique et de gestion de flux, permet de traiter des cas reels de verification conversationnelle en limitant la surinformation produite par le systeme lui-meme.

La trajectoire globale du memoire est ainsi complete:

- chapitre I: problematisation et etat de l'art;
- chapitre II: methodologie;
- chapitre III: modelisation;
- chapitre IV: realisation et discussion.

Cette progression confirme la faisabilite d'une IA de verification contextuelle orientee sobriete informationnelle, adaptee aux contraintes du contexte congolais.

---

## References

Les references bibliographiques de ce chapitre sont centralisees dans `thesis/References.md` avec une numerotation IEEE unique et continue pour l'ensemble du memoire.
