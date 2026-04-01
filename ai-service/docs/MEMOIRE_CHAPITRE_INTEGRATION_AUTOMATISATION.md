# Chapitre de Rédaction: Intégration Multicanale et Automatisation RAG

*Ce document servira de base de rédaction pour votre mémoire de fin d'études concernant la mise en production du modèle RDC News Intelligence.*

---

## 1. Automatisation de la Collecte et de l'Apprentissage (Continuous Learning)

### 1.1 Problématique de la fraîcheur des données
L'actualité en République Démocratique du Congo évolue à un rythme effréné. Un modèle d'intelligence artificielle figeant sa connaissance à un instant `T` (via un entraînement classique) devient rapidement obsolète face aux enjeux de désinformation au quotidien.

### 1.2 Solution : Architecture RAG avec Rafraîchissement Périodique (CRON)
Pour combler cette faille de connaissance, nous avons développé un moteur d'apprentissage continu sans ré-entraîner les pondérations profondes du LLM (ce qui limite le coût et l'ingénierie matérielle). Le système repose sur deux mécanismes chaînés via une tâche asynchrone fonctionnant toutes les deux heures :
1. **Écoute et Ingestion (Crawler) :** L'activation programmatique du script `SyncCrawler` limité à la capture des 30 publications les plus récentes depuis notre liste de sources fiables (ex: RadioOkapi).
2. **Transfer Learning via Re-Embedding :** Le composant IA s'enclenche ensuite automatiquement. Les nouveaux textes sont transformés en Vecteurs Hyper-dimensionnels (« Embeddings ») via le modèle sélectionné (ex: `all-MiniLM-L6-v2`) et insérés dynamiquement dans la structure PostgreSQL enrichie de l'extension `pgvector`. Le modèle génératif dispose ainsi silencieusement de compétences sur des informations apparues il y a moins de deux heures.

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
