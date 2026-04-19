# Guide de Modélisation UML : RDC News Intelligence

Ce document récapitule chaque diagramme du système, son utilité et son emplacement recommandé dans votre travail de rédaction ou votre soutenance.

---

### 1. Diagramme des Cas d'Utilisation
**Emplacement recommandé** : Chapitre 3 (Conception)
**Usage** : Montrer **ce que fait** le système du point de vue de l'utilisateur.
- **Acteurs** : Utilisateurs Web, Utilisateurs Messagerie, Administrateur.
- **Fonctions clés** : Pose de questions, déclenchement du bot, Fact-Checking RAG, Crawling automatique.
- **Fichier** : `01-use-cases.drawio`

---

### 2. Séquence de Déploiement et Démarrage
**Emplacement recommandé** : Chapitre 3 ou 4
**Usage** : Expliquer l'**initialisation** technique du projet.
- **Processus** : Lancement de FastAPI, initialisation de pgvector, exposition des Webhooks (WA/TG), lancement du planificateur CRON.
- **Fichier** : `02-deployment-sequence.drawio`

---

### 3. Séquence du Crawler (Alimentation)
**Emplacement recommandé** : Chapitre 3 (paragraphe sur l'ingestion)
**Usage** : Détailler la **collecte des données** en arrière-plan.
- **Étapes** : Requête Web -> HTML brut -> Nettoyage -> Vectorisation (NLP) -> Stockage VectorDB.
- **Fichier** : `Diagramme_Sequence_Crawler.drawio`

---

### 4. Séquence d'Interception et Classification
**Emplacement recommandé** : Chapitre 4 (Flux d'exécution)
**Usage** : Expliquer comment le bot **décide d'intervenir** ou non.
- **Points clés** : Analyse OCR pour les images, classifieur thématique (Politique/Santé), filtrage des messages de groupe.
- **Fichier** : `Diagramme_Sequence_Interception.drawio`

---

### 5. Séquence de Vérification et RAG
**Emplacement recommandé** : Chapitre 3 (Cœur de l'architecture)
**Usage** : Montrer comment l'IA **prouve les faits**.
- **Processus** : Recherche de similarité -> Extraction du contexte -> Génération Mistral-7B -> Réponse sourcée ou avertissement.
- **Fichier** : `Diagramme_Sequence_Verification.drawio` / `03-rag-sequence.drawio`

---

### 6. Diagramme de Séquence Générale
**Emplacement recommandé** : Chapitre 4 (Synthèse des flux) ou Introduction technique.
**Usage** : Offrir une **vue d'ensemble fluide** du parcours d'un message.
- **Fichier** : `Diagramme_Sequence_Generale.drawio`

---

### 7. Diagramme de Classes
**Emplacement recommandé** : Chapitre 3
**Usage** : Décrire la **structure logicielle** (Services et Modèles).
- **Entités** : ArticleService, RAGService, LLMService (Ollama), OCRService.
- **Fichier** : `04-class-diagram.drawio`

---

### 8. Schéma de la Base de Données (ERD)
**Emplacement recommandé** : Chapitre 3
**Usage** : Présenter la **structure de stockage**.
- **Tables** : `ARTICLES` (avec colonne `embedding`), `TRAINING_RUNS` (historique).
- **Fichier** : `05-erd.drawio`
