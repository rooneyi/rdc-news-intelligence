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

    def _build_prompt(self, query: str, articles: List[ArticleOut], channel: str = "web") -> str:
        # On réduit un peu la taille du contexte pour accélérer Mistral
        context = "\n".join([
            f"[{i+1}] {a.title}: {a.content[:300]} (Lien: {a.link})" for i, a in enumerate(articles)
        ])
        
        format_instruction = ""
        if channel in ["whatsapp", "telegram"]:
            format_instruction = f"""Réponds au format COURT adapté pour messagerie ({channel}). Utilise des emojis.
Limite ta réponse à quelques phrases maximum.
Format strict :
🚨 VÉRIFICATION : (Commence par dire clairement si c'est VRAI, FAUX, IMPRÉCIS, ou NON VÉRIFIABLE)
📝 EXPLICATION : (Explication très courte et claire sur les faits)
🔗 SOURCES : (Donne les titres et les liens des sources fiables)"""
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
        
        try:
            # On limite le nombre de tokens générés pour réduire le temps de réponse.
            # Réponse plus courte pour messageries.
            max_tokens = 256 if channel == "web" else 160
            # Utilisation d'un client avec timeout désactivé pour la lecture du stream
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, read=None)) as client:
                async with client.stream(
                    "POST",
                    url,
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": True,
                        "num_predict": max_tokens,
                    },
                ) as response:
                    if response.status_code != 200:
                        yield f"Erreur Ollama ({response.status_code})"
                        return

                    async for line in response.aiter_lines():
                        if not line: continue
                        try:
                            data = json.loads(line)
                            chunk = data.get("response", "")
                            if chunk:
                                yield chunk
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error(f"Ollama connection error: {e}")
            yield f"\n[Erreur de connexion avec Mistral : {str(e)}]"

    async def summarize_full(self, query: str, articles: List[ArticleOut], channel: str = "web") -> str:
        """Gère la réponse complète sans streaming (utile pour les Webhooks WhatsApp/Telegram)."""
        response_text = ""
        async for chunk in self.summarize_stream(query, articles, channel):
            response_text += chunk
        return response_text

    def summarize(self, query: str, articles: List[ArticleOut]) -> str:
        """Méthode de secours (évite le crash si appelée par erreur)"""
        return "Erreur: Utilisez la méthode asynchrone summarize_stream ou summarize_full pour Mistral."
