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

    def _build_prompt(self, query: str, articles: List[ArticleOut]) -> str:
        context = "\n".join([f"[{i+1}] {a.title}: {a.content[:500]}" for i, a in enumerate(articles)])
        return f"""[INST] Tu es un expert en actualité de la RDC. Réponds à la question en utilisant UNIQUEMENT les articles fournis.
Si tu ne sais pas, dis-le. Ne crée pas de fausses informations.

Format :
📊 RÉSUMÉ : (Bref et percutant)
📰 VÉRIFICATION : (Analyse de fiabilité)
🔗 SOURCES : (Titres des articles)

Question : {query}
Articles :
{context}
[/INST]"""

    async def summarize_stream(self, query: str, articles: List[ArticleOut]) -> AsyncGenerator[str, None]:
        """Génération en streaming réel : les mots s'affichent dès qu'ils sortent de Mistral."""
        logger.info(f"[LLMService] Appel à Mistral/Ollama pour la question : {query}")
        if not articles:
            yield "Désolé, aucune source trouvée pour répondre à cette question."
            return

        prompt = self._build_prompt(query, articles)
        url = f"{self.host}/api/generate"
        
        try:
            # Utilisation d'un client avec timeout désactivé pour la lecture du stream
            async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, read=None)) as client:
                async with client.stream(
                    "POST", 
                    url, 
                    json={"model": self.model, "prompt": prompt, "stream": True},
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

    def summarize(self, query: str, articles: List[ArticleOut]) -> str:
        """Méthode de secours (évite le crash si appelée par erreur)"""
        return "Erreur: Utilisez la méthode asynchrone summarize_stream pour Mistral."
