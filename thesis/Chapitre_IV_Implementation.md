# CHAPITRE IV : RÉALISATION, IMPLÉMENTATION ET DISCUSSION

### 4.1. Introduction partielle
Après avoir défini la méthodologie et modélisé l'architecture du système, ce dernier chapitre est consacré à la réalisation technique et au déploiement de la solution **RDC News Intelligence**. Nous y détaillons l'environnement de développement, les étapes de configuration du serveur VPS, ainsi qu'une discussion sur les résultats obtenus et l'efficacité du système de "bulles" pour la réduction de la surinformation.

### 4.2. Environnement de Développement et Stack Technique
Le choix des technologies a été guidé par la nécessité de performance, de flexibilité et de souveraineté des données (exécution locale de l'IA).

- **Langage de programmation** : Python 3.12, pour sa richesse en bibliothèques de traitement du langage naturel (NLP) et d'IA.
- **Framework Web** : FastAPI, choisi pour sa gestion asynchrone native, essentielle pour traiter les Webhooks WhatsApp/Telegram en temps réel.
- **Base de données Vectorielle** : ChromaDB, utilisée pour stocker les embeddings et effectuer des recherches de similarité ultra-rapides.
- **Moteur d'IA Local** : Ollama, permettant d'exécuter le modèle **Mistral-7B** sans dépendance aux APIs payantes ou externes, garantissant la confidentialité des échanges.
- **Gestion de la Mémoire** : Redis, pour le stockage temporaire des contextes de discussion et la gestion des clusters (bulles).

### 4.3. Déploiement sur Serveur Privé Virtuel (VPS)
Conformément aux exigences de production, le système a été déployé sur un VPS Linux (Ubuntu Server). 

#### 4.3.1. Configuration de l'infrastructure
Le déploiement a nécessité la configuration d'un environnement virtualisé (`venv`) pour isoler les dépendances. Nous avons utilisé **PM2** (Process Manager) pour garantir que l'API FastAPI et le moteur Ollama restent actifs 24h/24, même après un redémarrage du serveur.

#### 4.3.2. Exposition des Webhooks
Pour permettre à WhatsApp (via Meta ou Whapi) et Telegram d'envoyer des messages à notre serveur, nous avons configuré un tunnel sécurisé et un certificat SSL. L'Orchestrateur reçoit les requêtes `POST` sur des routes protégées, garantissant que seuls les services autorisés peuvent interagir avec l'IA.

### 4.4. Implémentation du Système de Bulles (Innovation)
L'une des contributions majeures de ce travail est l'implémentation du système de **Cross-Group Intelligence**. 
- **Clustering Transversal** : Lorsqu'un message arrive, le système ne vérifie pas seulement s'il existe dans le groupe actuel, mais s'il circule globalement dans d'autres groupes suivis par le bot.
- **Messages Pivots** : Pour éviter l'infobésité, le bot utilise les fonctionnalités de "Réponse" (Quote) de WhatsApp/Telegram pour lier sa nouvelle réponse au message racine du sujet, créant un fil d'actualité structuré au sein même du chat.

### 4.5. Présentation et Discussion des Résultats

#### 4.5.1. Analyse du Corpus
Le testbed a été alimenté par un crawler ayant traité plus de **13 000 articles** d'actualité. 
- **Langues** : Français (94%), Anglais (5%), Swahili (1,3%). La prédominance du français s'explique par la disponibilité des sources numériques en RDC.
- **Sources** : Radio Okapi, 7sur7.cd, Actualite.cd, etc.

#### 4.5.2. Efficacité contre la surinformation
L'introduction du système de bulles a permis de réduire drastiquement le nombre de messages générés par le bot. Dans un scénario de test avec 10 questions similaires posées en 15 minutes, le système n'a produit qu'une seule synthèse détaillée et 9 réponses courtes de type "pivot", réduisant l'occupation visuelle du chat de près de **80%**.

#### 4.5.3. Limites et Perspectives
Bien que performant, le système rencontre des défis liés aux nuances dialectales du Swahili et aux images de très basse qualité pour l'OCR. Les perspectives incluent l'intégration de modèles multilingues plus robustes et l'extension du crawling à des sources locales plus diversifiées en province.

### 4.6. Conclusion partielle
Ce chapitre a démontré la faisabilité technique du framework proposé. Le passage d'une architecture théorique à un système déployé sur VPS prouve que des solutions d'IA souveraines peuvent répondre efficacement aux défis de la désinformation en RDC tout en gérant intelligemment le volume d'information produit.
