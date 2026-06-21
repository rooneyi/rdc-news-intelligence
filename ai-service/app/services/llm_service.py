import os
import httpx
import logging
import json
from typing import List, AsyncGenerator
from app.schemas.article import ArticleOut
from app.services.circuit_breaker import ollama_breaker, CircuitOpen

logger = logging.getLogger(__name__)


def normalize_ollama_keep_alive(raw: str | None = None) -> int | str:
    """
    Ollama accepte keep_alive comme :
    - entier (secondes, -1 = garder en mémoire, 0 = décharger)
    - chaîne durée (« 5m », « 24h »)
    La chaîne « -1 » provoque une 400 (parseur durée sans unité).
    """
    val = (raw if raw is not None else "-1").strip()
    if not val:
        return -1
    if val.lstrip("-").isdigit():
        return int(val)
    return val


class LLMService:
    """Client pour Mistral via Ollama optimisé pour la RDC."""

    def __init__(self, model: str | None = None, host: str | None = None, timeout: int | None = None):
        self.model = model or os.getenv("OLLAMA_MODEL", "mistral")
        self.host = host or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        self.timeout = timeout or int(os.getenv("OLLAMA_TIMEOUT", "300"))
        # num_ctx=2048 suffit pour le prompt (articles ~600 tokens + question + réponse).
        # 4096 double le temps de génération sur CPU sans gain de qualité pour ce cas d’usage.
        self.num_ctx = int(os.getenv("OLLAMA_NUM_CTX", "2048"))
        self.num_batch = int(os.getenv("OLLAMA_NUM_BATCH", "128"))
        self.num_thread = int(os.getenv("OLLAMA_NUM_THREAD", "4"))
        self.msg_num_predict = int(os.getenv("OLLAMA_NUM_PREDICT_MSG", "256"))
        self.web_num_predict = int(os.getenv("OLLAMA_NUM_PREDICT_WEB", "300"))
        self.rag_article_chars = int(os.getenv("OLLAMA_RAG_ARTICLE_CHARS", "300"))
        # keep_alive=-1 (entier) : modèle reste chargé — évite le cold start de 3-5 min.
        self.keep_alive = normalize_ollama_keep_alive(os.getenv("OLLAMA_KEEP_ALIVE", "-1"))
        raw_fallbacks = os.getenv("OLLAMA_FALLBACK_MODELS", "mistral:latest,mistral")
        self.fallback_models = [m.strip() for m in raw_fallbacks.split(",") if m.strip()]

    def _ollama_options(self, *, temperature: float = 0.1, extra: dict | None = None) -> dict:
        opts = {
            "temperature": temperature,
            "num_ctx": self.num_ctx,
            "num_batch": self.num_batch,
            "num_thread": self.num_thread,
        }
        if extra:
            opts.update(extra)
        return opts

    def _ollama_body(
        self,
        model: str,
        prompt: str,
        *,
        stream: bool = True,
        num_predict: int | None = None,
        temperature: float = 0.1,
    ) -> dict:
        body: dict = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "keep_alive": self.keep_alive,
            "options": self._ollama_options(temperature=temperature),
        }
        if num_predict is not None:
            body["num_predict"] = num_predict
        return body

    def _model_candidates(self) -> list[str]:
        candidates: list[str] = []
        for model_name in [self.model, *self.fallback_models]:
            if model_name and model_name not in candidates:
                candidates.append(model_name)
        return candidates

    def _build_prompt(self, query: str, articles: List[ArticleOut], channel: str = "web") -> str:
        # On réduit un peu la taille du contexte pour accélérer Mistral
        context = "\n".join([
            f"[{i+1}] {a.title}: {a.content[:self.rag_article_chars]} (Lien: {a.link})" for i, a in enumerate(articles)
        ])
        
        # Même structure verdict + explication que WhatsApp/Telegram pour éviter des réponses « web » plus vagues.
        format_instruction = f"""Réponds pour le canal « {channel} », ton clair et structuré, emojis discrets.
Couvre les faits importants jusqu’au bout (verdict + pourquoi + nuances), sans digresser hors des articles.
Format strict :
🚨 VÉRIFICATION : (VRAI, FAUX, IMPRÉCIS, ou NON VÉRIFIABLE — une phrase nette)
📝 EXPLICATION : (développement complet mais dense : qui, quoi, quand si présent dans les textes)
🔗 SOURCES : (titres + liens des articles utilisés)"""

        return f"""[INST] Tu es un expert fact-checker journaliste en RDC. Réponds UNIQUEMENT en français.
Réponds à la question ou vérifie l'information en utilisant UNIQUEMENT les articles fournis.
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
        
        # Web aligné sur la messagerie (OLLAMA_NUM_PREDICT_MSG) pour la même profondeur de réponse.
        max_tokens = (
            self.msg_num_predict if channel in {"whatsapp", "telegram", "web"} else self.web_num_predict
        )
        attempts = self._model_candidates()
        last_error = "Erreur inconnue"

        for idx, model_name in enumerate(attempts):
            try:
                await ollama_breaker.check()
                async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, read=None)) as client:
                    async with client.stream(
                        "POST",
                        url,
                        json=self._ollama_body(model_name, prompt, num_predict=max_tokens),
                    ) as response:
                        if response.status_code != 200:
                            error_body = await response.aread()
                            last_error = (
                                f"Ollama {response.status_code} sur modèle '{model_name}': "
                                f"{error_body.decode(errors='ignore')[:300]}"
                            )
                            logger.error("[LLMService] %s", last_error)
                            await ollama_breaker.record_failure(RuntimeError(last_error))
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
                                    await ollama_breaker.record_success()
                                    return
                            except json.JSONDecodeError:
                                continue
            except CircuitOpen as e:
                last_error = str(e)
                break
            except Exception as e:
                last_error = f"Ollama connection error sur '{model_name}': {e}"
                logger.error("[LLMService] %s", last_error)
                await ollama_breaker.record_failure(e)
                if idx < len(attempts) - 1:
                    continue

        yield f"❌ Erreur Ollama: {last_error}"

    async def summarize_full(
        self, query: str, articles: List[ArticleOut], channel: str = "web"
    ) -> str:
        """Réponse RAG non streamée (WhatsApp / Telegram / endpoints sync)."""
        logger.info(
            "[LLMService] Génération complète (%s articles, canal=%s) : %.80s",
            len(articles),
            channel,
            query,
        )
        parts: list[str] = []
        async for chunk in self.summarize_stream(query, articles, channel):
            parts.append(chunk)
        return "".join(parts)

    def _build_refined_prompt(self, query: str, old_query: str, old_verdict: str, articles: List[ArticleOut], channel: str = "web") -> str:
        context = "\n".join([
            f"[{i+1}] {a.title}: {a.content[:self.rag_article_chars]} (Lien: {a.link})" for i, a in enumerate(articles)
        ])
        
        format_instruction = f"""Réponds pour le canal « {channel} », ton clair et structuré, emojis discrets.
Même si une réponse a déjà été donnée, essaie d'être plus précis ou de mieux formuler la solution.
Format strict :
🚨 VÉRIFICATION : (Verdict actualisé)
📝 EXPLICATION AMÉLIORÉE : (Développement plus complet ou mieux structuré)
🔗 SOURCES : (Titres + liens)"""

        return f"""[INST] Tu es un expert fact-checker journaliste en RDC.
L'utilisateur vient de poser une question similaire à une question traitée récemment.

Question précédente : {old_query}
Réponse précédente : {old_verdict}

Nouvelle question : {query}

Articles de référence récents :
{context}

Ta tâche est de :
1. Traiter la nouvelle question comme une demande à part entière (RAG sur les articles fournis).
2. Si la question apporte un angle nouveau, l’intégrer ; sinon confirmer ou préciser le verdict.
3. Ne pas répéter mécaniquement « pas de nuance » : répondre de façon utile et concise.

{format_instruction}
[/INST]"""

    def _build_viral_refined_prompt(self, query: str, old_query: str, old_verdict: str, articles: List[ArticleOut], group_count: int, channel: str = "web") -> str:
        context = "\n".join([
            f"[{i+1}] {a.title}: {a.content[:self.rag_article_chars]} (Lien: {a.link})" for i, a in enumerate(articles)
        ])
        
        virality_note = f"⚠️ ATTENTION : Ce sujet est actuellement VIRAL et a été détecté dans {group_count} groupes différents en RDC." if group_count > 1 else ""

        return f"""[INST] Tu es un expert fact-checker journaliste en RDC.
{virality_note}
L'utilisateur pose une question sur un sujet qui circule largement.

Question actuelle : {query}
Question de référence : {old_query}
Dernière analyse : {old_verdict}

Articles de presse récents :
{context}

Ta tâche est de produire une SYNTHÈSE D'INTELLIGENCE :
1. Confirme ou affine le verdict précédent avec les nouvelles données.
2. Si le sujet est viral ({group_count} groupes), adopte un ton plus formel et pédagogique pour calmer la rumeur.
3. Produis une réponse qui clôt le débat de manière définitive.

Format strict :
🚨 VERDICT GLOBAL : (VRAI/FAUX/...)
📊 ANALYSE DE VIRALITÉ : (Explique pourquoi ce sujet circule et quelle est la vérité établie)
📝 SYNTHÈSE POUR LE GROUPE : (Résumé clair et actionnable)
🔗 SOURCES : (Liens)
[/INST]"""

    async def summarize_viral_stream(
        self,
        query: str,
        old_query: str,
        old_verdict: str,
        articles: List[ArticleOut],
        group_count: int,
        channel: str = "web"
    ) -> AsyncGenerator[str, None]:
        """Génère une réponse de synthèse pour un sujet viral transverse."""
        prompt = self._build_viral_refined_prompt(query, old_query, old_verdict, articles, group_count, channel)
        url = f"{self.host}/api/generate"
        max_tokens = (
            self.msg_num_predict if channel in {"whatsapp", "telegram", "web"} else self.web_num_predict
        )
        attempts = self._model_candidates()
        last_error = "Erreur inconnue"

        for idx, model_name in enumerate(attempts):
            try:
                await ollama_breaker.check()
                async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, read=None)) as client:
                    async with client.stream(
                        "POST", url,
                        json=self._ollama_body(model_name, prompt, num_predict=max_tokens),
                    ) as response:
                        if response.status_code != 200:
                            error_body = await response.aread()
                            last_error = (
                                f"Ollama {response.status_code} sur modèle '{model_name}': "
                                f"{error_body.decode(errors='ignore')[:300]}"
                            )
                            logger.error("[LLMService] %s", last_error)
                            await ollama_breaker.record_failure(RuntimeError(last_error))
                            continue

                        logger.info("[LLMService] Synthèse virale Ollama avec modèle '%s'", model_name)
                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                chunk = data.get("response", "")
                                if chunk:
                                    yield chunk
                                if data.get("done"):
                                    await ollama_breaker.record_success()
                                    return
                            except Exception:
                                continue
            except CircuitOpen as e:
                last_error = str(e)
                break
            except Exception as e:
                last_error = f"Ollama connection error sur '{model_name}': {e}"
                logger.error("[LLMService] %s", last_error)
                await ollama_breaker.record_failure(e)
                if idx < len(attempts) - 1:
                    continue

        yield f"❌ Erreur Ollama (viral): {last_error}"

    async def summarize_refined_stream(
        self, 
        query: str, 
        old_query: str, 
        old_verdict: str, 
        articles: List[ArticleOut], 
        channel: str = "web"
    ) -> AsyncGenerator[str, None]:
        """Génère une réponse améliorée basée sur une réponse similaire précédente."""
        logger.info(
            "[LLMService] Raffinement (%s articles, canal=%s) : %.80s",
            len(articles),
            channel,
            query,
        )
        prompt = self._build_refined_prompt(query, old_query, old_verdict, articles, channel)
        url = f"{self.host}/api/generate"
        
        max_tokens = (
            self.msg_num_predict if channel in {"whatsapp", "telegram", "web"} else self.web_num_predict
        )
        attempts = self._model_candidates()
        last_error = "Erreur inconnue"

        for idx, model_name in enumerate(attempts):
            try:
                await ollama_breaker.check()
                async with httpx.AsyncClient(timeout=httpx.Timeout(self.timeout, read=None)) as client:
                    async with client.stream(
                        "POST",
                        url,
                        json=self._ollama_body(model_name, prompt, num_predict=max_tokens, temperature=0.2),
                    ) as response:
                        if response.status_code != 200:
                            error_body = await response.aread()
                            last_error = f"Ollama {response.status_code} sur '{model_name}'"
                            await ollama_breaker.record_failure(RuntimeError(last_error))
                            continue

                        async for line in response.aiter_lines():
                            if not line:
                                continue
                            try:
                                data = json.loads(line)
                                chunk = data.get("response", "")
                                if chunk:
                                    yield chunk
                                if data.get("done"):
                                    await ollama_breaker.record_success()
                                    return
                            except Exception:
                                continue
            except CircuitOpen as e:
                last_error = str(e)
                break
            except Exception as e:
                last_error = str(e)
                logger.error("[LLMService] Raffinement erreur sur '%s': %s", model_name, e)
                await ollama_breaker.record_failure(e)
                if idx < len(attempts) - 1:
                    continue

        yield f"❌ Erreur Ollama: {last_error}"

    async def summarize_refined_full(self, query: str, old_query: str, old_verdict: str, articles: List[ArticleOut], channel: str = "web") -> str:
        response_text = ""
        async for chunk in self.summarize_refined_stream(query, old_query, old_verdict, articles, channel):
            response_text += chunk
        return response_text

    async def rerank(self, query: str, articles: List[ArticleOut]) -> List[ArticleOut]:
        """Utilise Mistral pour ré-évaluer la pertinence des articles et les re-classer."""
        if len(articles) <= 1:
            return articles

        # Préparation du prompt de re-ranking
        articles_text = "\n".join(
            "ID:"
            + str(i)
            + " | TITRE:"
            + (a.title or "")
            + " | CONTENU:"
            + (a.content or "")[:200]
            + "..."
            for i, a in enumerate(articles)
        )

        # Pas de f-string sur le tout : les accolades du JSON d'exemple et celles des titres
        # utilisateurs cassent sinon le parseur de formats Python.
        q_lit = json.dumps(query, ensure_ascii=False)
        prompt = (
            "[INST] Tu es un assistant expert en pertinence de l'information.\n"
            "Évalue la pertinence de chaque article ci-dessous par rapport à la question :\n"
            + q_lit
            + "\n\n"
            "Pour chaque article, attribue un score de 0 à 10 (10 étant extrêmement pertinent, 0 hors sujet).\n"
            "Réponds UNIQUEMENT sous forme d'un tableau JSON d'objets contenant l'ID et le SCORE.\n"
            'Exemple de réponse : [{"id": 0, "score": 8}, {"id": 1, "score": 3}]\n\n'
            "Articles à évaluer :\n"
            + articles_text
            + "\n[/INST]"
        )

        url = f"{self.host}/api/generate"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await ollama_breaker.call(
                    client.post(
                        url,
                        json=self._ollama_body(
                            self.model, prompt, stream=False,
                            num_predict=300,
                            temperature=0.0,
                        ),
                    )
                )
                if response.status_code == 200:
                    result = response.json()
                    text_response = result.get("response", "").strip()

                    # Tentative d'extraction du JSON si Mistral a rajouté du texte
                    try:
                        start_idx = text_response.find("[")
                        end_idx = text_response.rfind("]") + 1
                        if start_idx != -1 and end_idx != -1:
                            scores_data = json.loads(text_response[start_idx:end_idx])
                            score_map: dict[int, float] = {}
                            for item in scores_data:
                                if not isinstance(item, dict):
                                    continue
                                try:
                                    idx = int(item.get("id", -1))
                                    score_map[idx] = float(item.get("score", 0))
                                except (TypeError, ValueError):
                                    continue
                            for i, article in enumerate(articles):
                                # On met à jour la similarité avec le score du re-ranking (normalisé sur 1.0)
                                llm_score = score_map.get(i, 0.0) / 10.0
                                # On combine avec la similarité cosinus (moyenne pondérée par exemple)
                                article.similarity = (article.similarity or 0) * 0.3 + llm_score * 0.7

                            # Tri par nouvelle similarité
                            articles.sort(key=lambda x: x.similarity or 0, reverse=True)
                            logger.info(f"[LLMService] Re-ranking terminé pour {len(articles)} articles")
                    except Exception as e:
                        logger.warning(
                            f"[LLMService] Échec du parsing JSON re-ranking: {e}. "
                            f"Texte: {text_response[:100]}"
                        )
        except CircuitOpen:
            logger.warning("[LLMService] Re-ranking ignoré — circuit Ollama ouvert")
        except Exception as e:
            logger.error(f"[LLMService] Erreur lors du re-ranking: {e}")

        return articles

