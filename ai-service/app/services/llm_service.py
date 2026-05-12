import os
import httpx
import logging
import json
from typing import List, AsyncGenerator
from app.schemas.article import ArticleOut

logger = logging.getLogger(__name__)


class LLMService:
    """Client pour Mistral via Ollama optimisé pour la RDC."""

    def __init__(self, model: str | None = None, host: str | None = None, timeout: int | None = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "mistral")
        self.host = host or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        # On met un timeout très large (5 min) pour éviter les erreurs de chargement du modèle
        self.timeout = timeout or 300
        # Paramètres mémoire/performance (garde le même modèle, réduit la RAM utilisée).
        # Contexte suffisant pour articles + prompt + réponse (sinon la sortie est tronquée).
        self.num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
        self.num_batch = int(os.getenv("OLLAMA_NUM_BATCH", "32"))
        # Plafond de tokens générés : 120 pour messagerie coupait l’explication au milieu d’une phrase.
        self.msg_num_predict = int(os.getenv("OLLAMA_NUM_PREDICT_MSG", "512"))
        self.web_num_predict = int(os.getenv("OLLAMA_NUM_PREDICT_WEB", "512"))
        # Modèles de secours (optionnels) en cas d'échec sur le modèle principal.
        raw_fallbacks = os.getenv("OLLAMA_FALLBACK_MODELS", "mistral:latest,mistral")
        self.fallback_models = [m.strip() for m in raw_fallbacks.split(",") if m.strip()]

    def _model_candidates(self) -> list[str]:
        candidates: list[str] = []
        for model_name in [self.model, *self.fallback_models]:
            if model_name and model_name not in candidates:
                candidates.append(model_name)
        return candidates

    def _build_prompt(self, query: str, articles: List[ArticleOut], channel: str = "web") -> str:
        # On réduit un peu la taille du contexte pour accélérer Mistral
        context = "\n".join([
            f"[{i+1}] {a.title}: {a.content[:300]} (Lien: {a.link})" for i, a in enumerate(articles)
        ])
        
        format_instruction = ""
        if channel in ["whatsapp", "telegram"]:
            format_instruction = f"""Réponds pour messagerie ({channel}), ton clair et structuré, emojis discrets.
Couvre les faits importants jusqu’au bout (verdict + pourquoi + nuances), sans digresser hors des articles.
Format strict :
🚨 VÉRIFICATION : (VRAI, FAUX, IMPRÉCIS, ou NON VÉRIFIABLE — une phrase nette)
📝 EXPLICATION : (développement complet mais dense : qui, quoi, quand si présent dans les textes)
🔗 SOURCES : (titres + liens des articles utilisés)"""
        else:
            format_instruction = """Format :
📊 RÉSUMÉ : (Bref et percutant)
📰 VÉRIFICATION : (Indique si l'information est confirmée, fausse ou nuancée)
🔗 SOURCES : (Titres des articles)"""

        return f"""[INST] Tu es un expert fact-checker journaliste en RDC. Réponds à la question ou vérifie l'information en utilisant UNIQUEMENT les articles fournis.
Si l'information n'est pas dans les articles, dis que tu ne peux pas vérifier. Ne crée aucune fausse information.

{format_instruction}

Information à vérifier : {query}
Articles de référence :
{context}
[/INST]"""

    async def summarize_stream(self, query: str, articles: List[ArticleOut], channel: str = "web") -> AsyncGenerator[str, None]:
        """Génération en streaming réel : les mots s'affichent dès qu'ils sortent de Mistral."""
        logger.info(f"[LLMService] Appel à Mistral/Ollama pour la question : {query}")
        if not articles:
            yield "Désolé, aucune source trouvée pour répondre à cette question."
            return

        prompt = self._build_prompt(query, articles, channel)
        url = f"{self.host}/api/generate"
        
        # On limite le nombre de tokens générés pour réduire le temps de réponse.
        # Réponse plus courte pour messageries.
        max_tokens = self.web_num_predict if channel == "web" else self.msg_num_predict
        attempts = self._model_candidates()
        last_error = "Erreur inconnue"

        for idx, model_name in enumerate(attempts):
            try:
                # Utilisation d'un client avec timeout désactivé pour la lecture du stream
                async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, read=None)) as client:
                    async with client.stream(
                        "POST",
                        url,
                        json={
                            "model": model_name,
                            "prompt": prompt,
                            "stream": True,
                            "num_predict": max_tokens,
                            "options": {
                                "temperature": 0.2,
                                "num_ctx": self.num_ctx,
                                "num_batch": self.num_batch,
                            },
                        },
                    ) as response:
                        if response.status_code != 200:
                            error_body = await response.aread()
                            last_error = (
                                f"Ollama {response.status_code} sur modèle '{model_name}': "
                                f"{error_body.decode(errors='ignore')[:300]}"
                            )
                            logger.error("[LLMService] %s", last_error)
                            continue

                        logger.info("[LLMService] Génération Ollama avec modèle '%s'", model_name)
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                chunk = data.get("response", "")
                                if chunk:
                                    yield chunk
                                if data.get("done"):
                                    return
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                last_error = f"Ollama connection error sur '{model_name}': {e}"
                logger.error("[LLMService] %s", last_error)
                # Petit backoff entre les tentatives
                if idx < len(attempts) - 1:
                    continue

        yield f"❌ Erreur Ollama: {last_error}"

    async def summarize_full(self, query: str, articles: List[ArticleOut], channel: str = "web") -> str:
        """Gère la réponse complète sans streaming (utile pour les Webhooks WhatsApp/Telegram)."""
        response_text = ""
        async for chunk in self.summarize_stream(query, articles, channel):
            response_text += chunk
        return response_text

    def summarize(self, query: str, articles: List[ArticleOut]) -> str:
        """Méthode de secours (évite le crash si appelée par erreur)"""
        return "Erreur: Utilisez la méthode asynchrone summarize_stream ou summarize_full pour Mistral."
