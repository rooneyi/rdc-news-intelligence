import os
import httpx
import logging
from typing import List
from app.schemas.article import ArticleOut

logger = logging.getLogger(__name__)


class LLMService:
    """Client simple pour un LLM exposé via Ollama (HTTP /api/generate)."""

    def __init__(self, model: str | None = None, host: str | None = None, timeout: int | None = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "mistral")
        self.host = host or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        # Timeout plus court par défaut pour éviter les blocages avant fallback
        env_timeout = os.getenv("OLLAMA_TIMEOUT")
        self.timeout = timeout or (int(env_timeout) if env_timeout else 20)

    def _build_prompt(self, query: str, articles: List[ArticleOut]) -> str:
        bullets = []
        for idx, art in enumerate(articles[:5], 1):
            bullets.append(
                f"[{idx}] Titre: {art.title}\nSource: {art.link or art.source_id or 'n/a'}\nTexte: {art.content}\n"
            )
        sources_text = "\n".join(bullets)
        prompt = f"""
Tu es un assistant chargé de fournir des réponses fiables à partir d’un système RAG basé sur des articles d’actualité.
Tu dois réduire la désinformation et la surinformation.

Règles strictes :
1. Tu dois répondre UNIQUEMENT à partir des documents fournis.
2. Tu ne dois jamais inventer d'information.
3. Si l’information n’existe pas dans le contexte → réponds : "Information non trouvée dans les sources disponibles."
4. Privilégie la cohérence, les sources multiples, les informations récentes.

Pipeline logique :
1. Analyse la question utilisateur
2. Comprends l’intention (politique, santé, sport…)
3. Lis les documents fournis (contexte RAG)
4. Identifie les informations pertinentes
5. Vérifie la cohérence entre les sources
6. Génère une réponse structurée

Vérification des faits (OBLIGATOIRE) :
* Si plusieurs sources confirment → information fiable
* Si contradiction → signale l’incertitude
* Si aucune source → information non vérifiable

Format de réponse (utilise toujours cette structure) :
📊 Résumé :
(Résumé clair et court de la situation)

📰 Vérification :
- Confirmé / Contredit / Non vérifiable
- Explication basée sur les sources

🔗 Sources :
- Source 1
- Source 2
- Source 3

📎 Articles :
1. Titre - Source
2. Titre - Source

Cas particuliers :
Si la question est fausse ou trompeuse :
⚠️ Cette information semble incorrecte ou non confirmée.
📊 Explication :
(Aucune source fiable ne confirme cette affirmation)
🔗 Sources fiables : ...

Si l’information est insuffisante :
⚠️ Information non vérifiable pour le moment.
📊 Données disponibles : ...

Bonnes pratiques :
* Toujours synthétiser (pas copier)
* Ne pas répondre trop long
* Éviter les répétitions
* Prioriser les informations importantes
* Regrouper les articles similaires (même événement)

Objectif final :
Fournir une réponse :
✔ pertinente
✔ fiable
✔ structurée
✔ basée sur les données réelles
Tout en réduisant :
❌ le bruit informationnel
❌ la désinformation
❌ la redondance

---
Affirmation ou question utilisateur : "{query}"
Voici des extraits d’articles de référence :
{sources_text}
---
Respecte strictement le format demandé ci-dessus."
        """
        return prompt

    def summarize(self, query: str, articles: List[ArticleOut]) -> str:
        if not articles:
            return "Aucun article fourni."

        prompt = self._build_prompt(query, articles)
        url = f"{self.host}/api/generate"
        try:
            logger.info("Calling LLM model=%s host=%s", self.model, self.host)
            resp = httpx.post(
                url,
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response") or data.get("text") or ""
        except Exception as exc:  # noqa: BLE001
            logger.warning("LLM call failed: %s", exc)
            raise

