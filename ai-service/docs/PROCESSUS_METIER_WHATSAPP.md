# Document de Synthèse : Processus Métier & Intégration WhatsApp
**Projet : RDC News Intelligence**

Ce document explique de manière simple et claire le fonctionnement global du système d'intelligence artificielle, la gestion des données, et le plan pour l'intégration future avec WhatsApp.

---

## 1. Comprendre le Processus Métier Actuel

Le but de RDC News Intelligence est de lutter contre la désinformation (l'infobésité) en analysant et comprenant le contenu de l'actualité congolaise. Le processus se divise en trois grandes étapes :

### A. La Base de Connaissances (Crawler & Base de données)
1. **Collecte :** Nous récupérons des articles d'actualités (ex. depuis le corpus `drc-news-corpus` ou via nos propres crawlers) axés sur la République Démocratique du Congo.
2. **Transformation Mathématique (Embeddings) :** Chaque texte est converti en "vecteurs" (une suite de nombres) grâce au modèle d'IA **all-MiniLM-L6-v2**. Ce modèle capture *le sens* profond du texte, et non pas juste les mots-clés.
3. **Stockage Intelligent :** Ces vecteurs sont sauvegardés dans notre base de données **PostgreSQL** équipée de **pgvector**. Cela permet de ranger les notions par "proximité de sens" (Search Similarity).

### B. Le Moteur de Recherche Sémantique
Lorsqu'un utilisateur pose une question (ex: "Mesures sanitaires à Kinshasa") :
1. Sa question est elle aussi transformée en vecteur.
2. Le système cherche dans la base de données les articles qui s'en rapprochent le plus sémantiquement.
3. Il trouve des résultats pertinents, même si les mots utilisés dans la question ne sont pas exactement les mêmes que ceux de l'article.

### C. Le Chatbot RAG (Génération Augmentée par Récupération)
1. Plutôt que de laisser l'IA répondre au hasard à partir de ce qu'elle connaît d'internet, nous lui fournissons **seulement nos articles vérifiés**.
2. L'IA lit ces articles pertinents récupérés dans la base PostgreSQL et génère une **synthèse courte, fiable et accompagnée des liens sources**.

---

## 2. Le "Transfer Learning" appliqué à notre contexte

Vous avez mentionné le "Transfer Learning". Dans ce système, l'approche principale est la suivante :
- **Utilisation d'un modèle pré-entraîné** : Le modèle d'embedding (`all-MiniLM-L6-v2`) fait déjà un "Transfer Learning" puisqu'il transfère sa connaissance globale des langues pour notre cas spécifique.
- **RAG vs Fine-tuning** : Au lieu de réentraîner complètement un modèle de génération de texte sur vos données (ce qui est lourd et coûteux), l'architecture utilise le paradigme **RAG** (Génération par récupération). L'information de votre base constitue le "nouveau savoir" que le LLM utilise.
- *Option Future (vrai Transfer Learning / Fine-Tuning)* : Si plus tard l'IA doit parler un dialecte très spécifique ou classifier précisément des tendances purement congolaises (sentiment politique, sarcasme local), le code d'entraînement récupérera effectivement les données nettoyées depuis PostgreSQL pour ajuster les poids d'un réseau de neurones spécifique (comme MobileNet pour l'image ou un petit modèle NLP).

---

## 3. Planification Stratégique : L'Intégration WhatsApp

L'objectif est d'étendre la puissance de l'IA directement dans les poches des Congolais via WhatsApp (Groupes ou Conversations privées).

### Le Workflow WhatsApp
1. **Écoute passive (Capture) :**
   - Le service (connecté via la **WhatsApp Cloud API** officielle ou Twilio) écoute un numéro dédié.
   - Les messages de la conversation, ou du groupe où le bot est présent, arrivent sur nos serveurs.
   
2. **Déclenchement ciblé (Anti-Spam) :** 
   - *Critique :* Pour éviter que le bot de l'IA ne génère une réponse longue pour chaque message anodin d'un groupe, il réagira **uniquement à certains mots-clés** ou déclencheurs (ex: "*@NewsBot vérifie :*", "*#FakeNews*").
   
3. **Traitement IA via notre Microservice :**
   - La question capturée sur WhatsApp est envoyée à notre **Microservice IA**.
   - Ce microservice effectue la fameuse recherche vectorielle (RAG) dans PostgreSQL.
   
4. **Réponse Synthétisée :**
   - Le modèle LLM lit les sources internes et rédige une synthèse courte et directe (adaptée pour mobile).
   - Le bot répond directement dans la discussion WhatsApp sous cette forme : 
     > *"D'après nos sources vérifiées : [Synthèse courte de 2 lignes]. Plus d'infos ici : [Lien 1]"*

### Prérequis Techniques pour l'Intégration
1. **Enregistrement Meta / WhatsApp :** Créer un compte "Meta for Developers" pour obtenir un token (WhatsApp Business API).
2. **Webhook (`/backend`) :** Un endpoint API (ex: `POST /api/webhooks/whatsapp`) prêt à recevoir les messages entrants (texte, statut).
3. **Traitement asynchrone :** Mettre le traitement du LLM dans une queue (ex: Celery ou Redis) pour répondre à WhatsApp rapidement (< 3 secondes pour accuser réception) et envoyer la réponse IA quelques secondes plus tard.
