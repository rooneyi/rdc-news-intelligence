# Diagrammes tldraw (`.tldr`) — Chapitre 2

Documentation visuelle du **chaînage théorique et pratique** de RDC News Intelligence, calquée sur le schéma manuscrit [`../rdc news .jpeg`](../rdc%20news%20.jpeg).

**Format : tldraw uniquement** (pas draw.io). Fichiers ouvrables dans [tldraw.com](https://www.tldraw.com) ou l’extension VS Code **tldraw**.

---

## Fichiers fournis

| Fichier `.tldr` | Contenu | Section chapitre 2 suggérée |
|-----------------|---------|------------------------------|
| `00-vue-generale.tldr` | Parcours complet WhatsApp → VPS → local → réponse | 2.2 / introduction flux |
| `01-module-messagerie.tldr` | Entrée/sortie, groupe vs DM, types message | 2.3.1 |
| `02-module-serveur-ligne.tldr` | VPS, webhooks, file, relay | 2.3.2 |
| `03-module-polling-local.tldr` | Worker polling `queue/pop` | 2.3.3 |
| `04-module-topic-gate.tldr` | Filtrage thématique groupes | 2.4.1 |
| `05-module-corpus-chroma.tldr` | Crawler, Postgres, ChromaDB | 2.3 – 2.5 |
| `06-module-pipeline-rag.tldr` | Embedding, retrieval, Mistral | 2.6 |
| `07-module-restitution.tldr` | Relay et retour WhatsApp | 2.6 / fin flux |

Texte rédactionnel pour le lecteur : [`CHAPITRE_2_ENCHAINEMENT.md`](CHAPITRE_2_ENCHAINEMENT.md).

---

## Ouvrir / modifier

1. Aller sur https://www.tldraw.com → **Open file** → choisir un `.tldr`.
2. Ou VS Code : extension **tldraw** → ouvrir le fichier.
3. Pour régénérer après modification du JSON source :

```bash
cd ai-service/docs/tdraw
node scripts/gen-tldr.mjs --in diagrams/00-vue-generale.json --out 00-vue-generale.tldr
```

Les définitions modifiables sont dans `diagrams/*.json` (nœuds, groupes, flèches).

---

## Légende couleurs (vue générale)

| Couleur tldraw | Zone |
|----------------|------|
| Vert | Messagerie / utilisateur |
| Orange | Serveur en ligne (VPS) |
| Violet | Traitement local (IA) |

---

## Références code

| Module | Fichiers principaux |
|--------|---------------------|
| Webhooks / polling | `app/api/routes/webhooks.py` |
| RAG | `app/services/rag_service.py` |
| Chroma | `app/services/vector_store_service.py` |
| Topic gate | `app/services/topic_gate_service.py` |
| Crawler | `app/services/crawler/` |

Voir aussi : [`../FLUX_WHATSAPP_VERS_DRAWIO.md`](../FLUX_WHATSAPP_VERS_DRAWIO.md) (description textuelle du même flux).
