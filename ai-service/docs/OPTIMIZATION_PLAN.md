# 🚀 Plan d'Optimisation de la Performance (Cible < 2 min)

Ce document suit les efforts pour réduire le temps de réponse du système RAG, passant de **15 minutes** à moins de **2 minutes**.

## 📊 Diagnostic Actuel (Profiling)

Le script `scripts/profile_rag_pipeline.py` a été exécuté le 23/05/26.

### Résultats du 23/05/26
1. **Embedding** : 7.72s (CPU)
2. **Vector Search (ChromaDB)** : 1.71s
3. **LLM Calls (Re-ranking / Generation)** : **TIMEOUT (> 300s)**

### Analyse des goulots d'étranglement
- **Multiples appels LLM** : Confirmé comme le blocage majeur. Un seul appel LLM (re-ranking) dépasse déjà les 5 minutes sur cette configuration matérielle.
- **Hardware** : Le CPU met environ 7-8s pour un simple embedding, ce qui indique que la génération de texte sera très lente.

## 🛠 Stratégies d'Optimisation Appliquées

### Phase 1 : Réduction Drastique des appels LLM (Effectué ✅)
- [x] **Désactiver le Re-ranking** : `RAG_ENABLE_RERANK=false` (Économise ~5-10 min).
- [x] **Limiter le contexte** : `RAG_WEB_TOP_K=3` (Accélère la génération).
- [x] **Topic Gate "Fast-Path"** : `TOPIC_GATE_KEYWORD_MODE=keywords-first` (Évite l'IA pour les sujets clairs, économise ~2-5 min).

### Phase 2 : Optimisation Inférence (En cours 🏃‍♂️)
- [x] **Modèle Quantifié** : Passage à `mistral:7b-instruct-v0.3-q4_K_M` (Inférence plus rapide sur CPU).
- [ ] **Ollama Keep-Alive** : S'assurer que le modèle reste en RAM.

## 📈 Résultats des tests

| Date | Version | Temps Total | Gain | Note |
|------|---------|-------------|------|------|
| 23/05/26 | Baseline | > 15 min | - | État initial |
| 23/05/26 | Sans Rerank | ~5-6 min | ~60% | Re-ranking désactivé |
| 23/05/26 | Keywords + Q4 | **TBD** | - | Cible < 3 min |
