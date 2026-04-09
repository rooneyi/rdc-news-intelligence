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

## 2. Connectivité et Distribution via API (Webhooks)

L'accessibilité technologique de l'utilisateur congolais passe davantage par les messageries instantanées que par les interfaces webs traditionnelles. 

### 2.1 Microservices de Réception (Webhooks)
Nous avons mis en place un routeur FastAPI dédié (« /webhooks ») doté de tâches d'arrière-plan (`BackgroundTasks`) pour traiter des forts flux de messages :
- **L'intégration WhatsApp (Meta Cloud API) :** Le service comprend une vérification biométrique Meta (hub verify challenge) pour sécuriser l'envoi vers un numéro d'entreprise.
- **L'intégration Telegram :** Le service accepte les structures JSON de l'API BotFather.

### 2.2 Processus de Fact-Checking Augmenté
Grâce au canal identifié, le comportement du RAG s'adapte. Au lieu de simples résumés sémantiques, le prompt côté LLM Service (`llm_service.py`) a été spécialisé (« Fact-Checker Journalist »). 
Le modèle RAG récupère l'information liée à la discussion, mais il lui est imposé une architecture de réponse militaire, évitant l'hallucination, scindée en trois blocs :
- **🚨 VÉRIFICATION :** Déclaration explicite et binaire (Vrai, Faux, ou Imprécis).
- **📝 EXPLICATION :** Contextualisation courte à l'attention d'un lecteur sur mobile.
- **🔗 SOURCES :** L'accès direct aux articles officiels qui ont participé à la prise de décision du modèle.

Cela crée une véritable valeur ajoutée métier : le bot n'est pas vu seulement comme une encyclopédie, mais comme un assistant de confiance pour mitiger l'infobésité sur les réseaux sociaux.

### 2.3 Chaîne complète « de la collecte à la recommandation »

L'intégration multicanale (web, Telegram, WhatsApp) s'appuie sur une chaîne technique continue entre la collecte des informations et la génération de recommandations utiles pour l'utilisateur final :

1. **Collecte et indexation**  
	Le crawler récupère les derniers articles, qui sont vectorisés et indexés dans la base `articles`. À ce stade, le moteur de recommandation dispose des informations les plus récentes.

2. **Réception de la demande via webhook ou polling**  
	- Sur Telegram, la demande transite soit par le webhook, soit par un mécanisme de polling intégré directement à l'application FastAPI.  
	- Sur WhatsApp, la demande est transmise par la plateforme Meta via un webhook HTTPS pointant vers le microservice.

3. **Sélection des articles pertinents**  
	La question est encodée, puis comparée à l'ensemble des embeddings stockés. Les `top_k` articles les plus proches sont sélectionnés : c'est la phase de recommandation proprement dite.

4. **Génération contrôlée de la réponse**  
	Les articles recommandés sont transmis au modèle Mistral, encapsulés dans un prompt spécialisé de fact-checking. Le LLM doit alors produire une réponse structurée (VÉRIFICATION, EXPLICATION, SOURCES) en s'appuyant uniquement sur les documents recommandés.

Cette chaîne illustre le lien direct entre le flux de collecte (crawler), la base vectorielle (pgvector) et le comportement observé par l'utilisateur final dans les applications de messagerie.
