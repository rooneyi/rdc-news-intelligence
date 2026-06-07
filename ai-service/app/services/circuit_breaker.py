import asyncio
import logging
import time
import os

logger = logging.getLogger(__name__)

try:
    from app.services.metrics import CIRCUIT_BREAKER_STATE as _CB_GAUGE

    def _set_cb_gauge(name: str, state: str) -> None:
        _CB_GAUGE.labels(name=name).set({"CLOSED": 0, "HALF_OPEN": 1, "OPEN": 2}.get(state, 0))
except ImportError:
    def _set_cb_gauge(name: str, state: str) -> None:  # type: ignore[misc]
        pass

_FAILURE_THRESHOLD = int(os.getenv("CIRCUIT_BREAKER_FAILURES", "3"))
_RESET_TIMEOUT = float(os.getenv("CIRCUIT_BREAKER_TIMEOUT", "30"))


class CircuitOpen(Exception):
    """Levée quand le circuit est ouvert — Ollama considéré indisponible."""
    pass


class CircuitBreaker:
    """
    Circuit breaker simple pour Ollama.
    États : CLOSED (normal) → OPEN (échecs répétés) → HALF_OPEN (test) → CLOSED
    """

    def __init__(self, name: str, failure_threshold: int = _FAILURE_THRESHOLD, reset_timeout: float = _RESET_TIMEOUT):
        self.name = name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self._failures = 0
        self._state = "CLOSED"
        self._opened_at: float | None = None
        self._lock = asyncio.Lock()

    @property
    def state(self) -> str:
        if self._state == "OPEN":
            if time.monotonic() - (self._opened_at or 0) >= self.reset_timeout:
                return "HALF_OPEN"
        return self._state

    async def check(self):
        """Lève CircuitOpen si le circuit est OPEN (fast-fail pour les générateurs)."""
        async with self._lock:
            current = self.state
            if current == "OPEN":
                logger.warning(
                    "[CircuitBreaker:%s] Fast-fail — circuit OUVERT (%ds restants)",
                    self.name,
                    max(0, int(self.reset_timeout - (time.monotonic() - (self._opened_at or 0)))),
                )
                raise CircuitOpen(f"Ollama [{self.name}] indisponible — réessaie dans quelques secondes.")
            if current == "HALF_OPEN":
                logger.info("[CircuitBreaker:%s] Circuit HALF_OPEN — tentative de rétablissement", self.name)

    async def record_success(self):
        """Enregistre un succès et referme le circuit si nécessaire."""
        async with self._lock:
            if self._state in ("OPEN", "HALF_OPEN"):
                logger.info("[CircuitBreaker:%s] Succès — circuit FERMÉ", self.name)
            self._failures = 0
            self._state = "CLOSED"
            self._opened_at = None
            _set_cb_gauge(self.name, "CLOSED")

    async def record_failure(self, exc: Exception):
        """Enregistre un échec et ouvre le circuit si le seuil est atteint."""
        async with self._lock:
            self._failures += 1
            if self._failures >= self.failure_threshold:
                self._state = "OPEN"
                self._opened_at = time.monotonic()
                _set_cb_gauge(self.name, "OPEN")
                logger.error(
                    "[CircuitBreaker:%s] Circuit OUVERT après %d échecs. Pause de %ds. Dernière erreur: %s",
                    self.name, self._failures, self.reset_timeout, exc,
                )
            else:
                logger.warning(
                    "[CircuitBreaker:%s] Échec %d/%d: %s",
                    self.name, self._failures, self.failure_threshold, exc,
                )

    async def call(self, coro):
        """
        Exécute la coroutine si le circuit est fermé.
        Lève CircuitOpen si le circuit est ouvert.
        """
        async with self._lock:
            current = self.state
            if current == "OPEN":
                logger.warning(
                    "[CircuitBreaker:%s] Circuit OUVERT — requête Ollama bloquée (%ds restants)",
                    self.name,
                    max(0, int(self.reset_timeout - (time.monotonic() - (self._opened_at or 0)))),
                )
                raise CircuitOpen(f"Ollama [{self.name}] indisponible — réessaie dans quelques secondes.")

            if current == "HALF_OPEN":
                logger.info("[CircuitBreaker:%s] Circuit HALF_OPEN — tentative de rétablissement", self.name)

        try:
            result = await coro
            async with self._lock:
                if self._state in ("OPEN", "HALF_OPEN"):
                    logger.info("[CircuitBreaker:%s] Succès — circuit FERMÉ", self.name)
                self._failures = 0
                self._state = "CLOSED"
                self._opened_at = None
                _set_cb_gauge(self.name, "CLOSED")
            return result
        except CircuitOpen:
            raise
        except Exception as exc:
            async with self._lock:
                self._failures += 1
                if self._failures >= self.failure_threshold:
                    self._state = "OPEN"
                    self._opened_at = time.monotonic()
                    _set_cb_gauge(self.name, "OPEN")
                    logger.error(
                        "[CircuitBreaker:%s] Circuit OUVERT après %d échecs. Pause de %ds. Dernière erreur: %s",
                        self.name, self._failures, self.reset_timeout, exc,
                    )
                else:
                    logger.warning(
                        "[CircuitBreaker:%s] Échec %d/%d: %s",
                        self.name, self._failures, self.failure_threshold, exc,
                    )
            raise


# Instance partagée pour Ollama — importée dans llm_service
ollama_breaker = CircuitBreaker("ollama")
