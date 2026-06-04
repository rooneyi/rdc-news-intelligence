# Figures du mémoire (diagrammes)

Fichiers **Mermaid** prêts à exporter en PNG pour Word / LaTeX.

## Export rapide

1. Ouvrir [mermaid.live](https://mermaid.live)
2. Coller le contenu de `01-use-cases.mmd` ou `05-erd-donnees.mmd`
3. **Actions → PNG/SVG** → enregistrer dans ce dossier :
   - `fig-02-use-cases.png` (Figure 2 — cas d'utilisation)
   - `fig-erd-donnees.png` (ERD / données)

## draw.io

Source détaillée et variantes : [`../Diagrammes_UML_Mermaid.md`](../Diagrammes_UML_Mermaid.md)

| Figure mémoire | Section Mermaid | Fichier draw.io (repo ai-service) |
|----------------|-----------------|-----------------------------------|
| Cas d'utilisation | § 1, § 1b, `01-use-cases.mmd` | `ai-service/docs/04-class-diagram.drawio` (≠) → créer `01-use-cases.drawio` |
| ERD PostgreSQL seul | § 13–14 | `ai-service/docs/diagrams/05-erd.mmd` |
| ERD complet (PG + Chroma + Redis) | § 18, `05-erd-donnees.mmd` | — |

**Important ERD :** ne pas dessiner `embedding` dans la table SQL `articles` — les vecteurs sont dans **ChromaDB** (`articles_rdc`).

## Correspondance chapitre III

| § Chapitre III | Fichier figure |
|----------------|----------------|
| 3.3 Cas d'utilisation | `01-use-cases.mmd` |
| 3.5 / 3.7.4 Base de données | `05-erd-donnees.mmd` (vue globale) ou § 13 seul pour PostgreSQL uniquement |
