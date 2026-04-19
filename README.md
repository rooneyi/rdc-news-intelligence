# RDC News Intelligence

Une plateforme intelligente d'agrégation d'actualités et de recommandation sémantique conçue pour réduire la surcharge d'information et lutter contre la désinformation en République Démocratique du Congo (RDC).

---

## Technologies utilisées

### Backend & API
- **FastAPI (Python)** : Moteur principal de traitement IA et Webhooks.
- **PostgreSQL + pgvector** : Base de données relationnelle et vectorielle.
- **Mistral-7B (Ollama)** : Modèle de langage local pour le RAG.

### Frontend
- **Next.js 15 & React** : Interface utilisateur moderne.
- **TailwindCSS** : Design premium et réactif (bleu nuit, bleu clair, blanc).

---

## Architecture du Système

Le système est piloté par des événements et des messages :
1. **Collecte (Crawler)** : Récupère les articles des sources officielles (ex: Radio Okapi).
2. **Indexation** : Vectorise le texte (Embeddings) et le stocke dans pgvector.
3. **Moteur RAG** : Utilise Mistral-7B pour répondre aux questions en croisant les faits du corpus.
4. **Interfaces** : Web, WhatsApp et Telegram (via Webhooks).

---

## Structure du Projet

- `ai-service/` : Moteur sémantique Python, traitement IA et orchestrateur RAG.
- `frontend/` : Application Web Next.js.
- `docs/` : Documentation technique et modélisations UML (Draw.io).

---

## Guide de Démarrage Rapide

### Lancement global (Dev)
Depuis la racine du projet, exécutez :

```bash
bash scripts/dev-all.sh
```

Ce script démarre :
- **Frontend** : [http://localhost:3000](http://localhost:3000)
- **Service IA (FastAPI)** : [http://localhost:8000](http://localhost:8000)

### Configuration
Les variables d'environnement (Tokens Telegram/WhatsApp, URL DB) doivent être configurées dans `ai-service/.env`.

---

## Impact et Apport
Contrairement aux IA généralistes (ChatGPT/Perplexity), ce système est **bridé sur un corpus local validé**, évitant les hallucinations sur l'actualité congolaise et offrant un outil de Fact-Checking précis en temps réel dans les groupes de messagerie.