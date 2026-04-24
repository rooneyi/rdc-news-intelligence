# Chapitre de Rédaction: Intégration Multicanale et Automatisation RAG

*Ce document servira de base de rédaction pour votre mémoire de fin d'études concernant la mise en production du modèle RDC News Intelligence.*

---

## 1. Automatisation de la Collecte et de l'Apprentissage (Continuous Learning)

### 1.1 Problématique de la fraîcheur des données
L'actualité en République Démocratique du Congo évolue à un rythme effréné. Un modèle d'intelligence artificielle figeant sa connaissance à un instant `T` (via un entraînement classique) devient rapidement obsolète face aux enjeux de désinformation au quotidien.

### 1.2 Solution : Architecture RAG avec Rafraîchissement Périodique (CRON)
Pour combler cette faille de connaissance, nous avons développé un moteur d'apprentissage continu sans ré-entraîner les pondérations profondes du LLM (ce qui limite le coût et l'ingénierie matérielle). Le système repose sur deux mécanismes chaînés via une tâche asynchrone fonctionnant toutes les deux heures (optionnelle, par défaut désactivée pour ne pas impacter la réactivité) :
1. **Écoute et Ingestion (Crawler) :** L'activation programmatique du script `app.services.crawler.scripts.sync` collecte les articles les plus récents depuis notre liste de sources fiables (ex: RadioOkapi, Actualité.cd, 7sur7.cd). Les articles sont d'abord stockés en JSONL, puis rejoués vers l'API via `replay_jsonl`.
2. **Transfer Learning via Re-Embedding :** Le composant IA s'enclenche ensuite automatiquement. Les nouveaux textes sont transformés en Vecteurs Hyper-dimensionnels (« Embeddings ») via le modèle sélectionné (ex: `paraphrase-multilingual-MiniLM-L12-v2` en production, `all-MiniLM-L6-v2` pour le dataset HF) et insérés dynamiquement dans la structure PostgreSQL enrichie de l'extension `pgvector`. L'index IVFFLAT `articles_embedding_idx` est mis à jour automatiquement. Le moteur de recommandation dispose ainsi silencieusement de compétences sur des informations apparues il y a moins de deux heures.

### 1.3 Rôle du crawler dans l'alimentation du moteur de recommandation

Le composant « crawler » constitue la porte d'entrée de l'apprentissage continu. Il interroge régulièrement un ensemble de sources journalistiques prédéfinies (configurées dans `data/crawler/sources.json` : RadioOkapi, Actualité.cd, 7sur7.cd, etc.) et extrait les nouveaux articles sous forme structurée (titre, corps du texte, URL, date de publication). Ces articles sont d'abord stockés dans des fichiers JSONL locaux (ex: `data/crawler/radiookapi.net.jsonl`), puis injectés dans l'API via des appels HTTP standard (`POST /crawler/articles/batch` ou `replay_jsonl`).

À chaque fois qu'un article transite par l'API, le service `ArticleService` déclenche la génération d'un vecteur d'embedding à l'aide d'un modèle `SentenceTransformers`. Le couple (`texte`, `embedding`) est finalement persisté dans la table `articles` de PostgreSQL, enrichie par l'extension `pgvector`. L'index IVFFLAT `articles_embedding_idx` est automatiquement mis à jour. Le crawler joue donc un double rôle : il maintient le corpus d'actualités à jour et il alimente en continu le **moteur de recommandation vectoriel** utilisé par le RAG.

**Commandes pratiques :**
```bash
# Crawler une source
python -m app.services.crawler.scripts.sync --source-id radiookapi.net --limit 20

# Crawler toutes les sources
python -m app.services.crawler.scripts.sync --source-id all --limit 20

# Rejouer un JSONL vers l'API
python -m app.services.crawler.scripts.replay_jsonl \
  --file data/crawler/radiookapi.net.jsonl \
  --endpoint http://127.0.0.1:8000 \
  --batch-size 50
```

### 1.4 Moteur de recommandation vectoriel basé sur pgvector

Le moteur de recommandation du système repose sur la **similarité entre vecteurs sémantiques** plutôt que sur de simples mots-clés ou topic modeling statique. Lorsqu'un utilisateur pose une question via Telegram, WhatsApp ou l'interface web, celle-ci est encodée dans le même espace vectoriel que les articles. La requête est ensuite comparée aux embeddings stockés dans la base à l'aide d'une **distance de type cosinus**, et les `k` articles les plus proches sont sélectionnés via un index IVFFLAT optimizer pour la performance.

**Mécanisme technique :**
- Requête utilisateur → `EmbeddingService.encode()` → vecteur 384-dim.  
- Query PostgreSQL : `SELECT ... ORDER BY embedding <=> query_vector LIMIT k`.  
- Résultat : top-K articles sémantiquement proches.

Ce mécanisme permet non seulement de retrouver des articles traitant **explicitement** du même sujet, mais aussi de recommander des contenus **implicites** ou formulés différemment. Par exemple, une question sur "la crise économique" retrouvera aussi des articles sur "la dévaluation du franc congolais", même si les mots ne sont pas identiques.

En pratique, le moteur de recommandation est donc entièrement déterminé par :
1. La **qualité du corpus** injecté par le crawler.  
2. La **qualité des embeddings** (modèle SentenceTransformers).  
3. L'**index pgvector** qui optimise la recherche.  

Tout cela **sans nécessiter de ré-entraîner** le modèle génératif Mistral lui-même. C'est l'avantage clé du RAG : adapter le système aux dernières actualités RDC en quelques heures, plutôt qu'en mois de fine-tuning.

---

## 2. Connectivité, Webhooks et Cas d'Utilisation

L'accessibilité technologique de l'utilisateur congolais passe davantage par les messageries instantanées que par les interfaces webs traditionnelles. L'architecture a été pensée autour de deux cas d'utilisation (Use Cases) principaux pour maximiser l'impact contre la désinformation.

### 2.1 Diagramme des Cas d'Utilisation : Le flux utilisateur

**Cas d'utilisation 1 : Vérification contextuelle dans les Groupes (WhatsApp / Telegram)**
L'utilisateur final se trouve dans une discussion de groupe où circulent de nombreuses informations (souvent sources d'infobésité ou de fakes news). 
- Le système n'intervient pas systématiquement pour ne pas polluer la discussion. 
- Il fonctionne sur **déclencheur (Trigger)** : lorsqu'une information douteuse est partagée, un membre du groupe mentionne le bot (ex: *@NewsBot vérifie* ou *?*). 
- L'information ciblée est transmise via notre Webhook (FastAPI) vers le composant RAG.
- Le RAG effectue une recherche vectorielle dans les articles locaux préalablement crawlés, puis le modèle d'IA génère et renvoie le fact-checking **directement dans le groupe**.

**Cas d'utilisation 2 : Interaction directe via l'Interface Web**
L'utilisateur, tel qu'un journaliste ou un étudiant, se rend sur l'application Web de RDC News Intelligence. 
- Point de besoin de déclencheur ici : la question est posée directement dans le champ de recherche.
- La requête attaque directement l'endpoint API REST standard. Le système RAG opère exactement de la même manière et fournit une réponse sourcée et détaillée sur l'interface.

### 2.2 Processus de Fact-Checking Augmenté
Grâce au canal identifié, le comportement du LLM s'adapte via le `llm_service.py`. Le modèle récupère l'information liée à la discussion de groupe ou du Web, et il lui est imposé une architecture de réponse militaire scindée en trois blocs :
- **🚨 VÉRIFICATION :** Déclaration explicite et binaire (Vrai, Faux, ou Imprécis).
- **📝 EXPLICATION :** Contextualisation courte à l'attention d'un lecteur sur mobile.
- **🔗 SOURCES :** L'accès direct aux articles officiels stockés en base.

---

## 3. Apport du Système face aux IA existantes (Perplexity, ChatGPT)

Il est légitime de se demander pourquoi déployer une architecture RAG dédiée alors que des géants comme ChatGPT (OpenAI) ou Perplexity AI existent déjà sur le marché.

### 3.1 La limitation des IA Généralistes (ChatGPT)
ChatGPT s'appuie sur une base de connaissances figée issue de l'internet mondial et a tendance à **halluciner** les faits locaux. Lorsqu'interrogé sur des mouvements politiques subtils à Kinshasa ou des incidents très récents à l'Est de la RDC, un modèle généraliste manque cruellement de données primaires spécifiques congolaises et va générer une réponse plausible mais potentiellement factuellement inexacte.

### 3.2 La limitation des Moteurs de Recherche Augmentés (Perplexity)
Perplexity AI contourne l'obsolescence en cherchant sur le web en temps réel. Cependant, il **ne filtre pas l'infobésité par la source locale**. Perplexity peut très bien utiliser comme source de vérité un blog partisan, une dépêche étrangère biaisée ou un site non reconnu par la corporation journalistique congolaise, propageant ainsi la désinformation sous une apparence de légitimité.

### 3.3 La valeur ajoutée de "RDC News Intelligence"
Notre système se distingue par sa **restriction volontaire de la connaissance (Corpus Clos)** :
1. **Hyper-Localisation et Fiabilité :** Le RAG ne s'abreuve **que** d'une base de données d'articles de presse officiels congolais (RadioOkapi, Actualité.cd, etc.) préalablement validés et moissonnés par notre propre Crawler. 
2. **Action au cœur du problème (WhatsApp) :** Contrairement à Perplexity ou ChatGPT qui demandent à l'utilisateur de quitter sa plateforme, notre système s'intègre au cœur des groupes WhatsApp/Telegram en RDC, là où la fausse information naît et se propage. 
3. **Impartialité mathématique :** Le modèle d'intelligence artificielle est "bridé" par le prompt pour ne jamais inventer de réponse. Si la base de données RDC ne contient aucune information sur la rumeur, l'IA répondra humblement "Non Vérifiable", bloquant ainsi la chaîne de propagation des fakes news.
