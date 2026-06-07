"""
Métriques Prometheus personnalisées pour le service RDC News Intelligence.
Exposées via /metrics (prometheus-fastapi-instrumentator, configuré dans main.py).
"""
from prometheus_client import Counter, Histogram, Gauge

# Messages reçus et planifiés par canal
MESSAGES_TOTAL = Counter(
    "rdc_messages_total",
    "Messages reçus et planifiés pour traitement RAG",
    ["channel"],
)

# Cache RAG
CACHE_HITS = Counter(
    "rdc_response_cache_hits_total",
    "Cache RAG — résultats servis depuis Redis",
    ["channel"],
)
CACHE_MISSES = Counter(
    "rdc_response_cache_misses_total",
    "Cache RAG — requêtes sans cache (génération Ollama déclenchée)",
    ["channel"],
)

# Latence RAG de bout en bout (embedding + ChromaDB + Ollama)
RAG_LATENCY = Histogram(
    "rdc_rag_latency_seconds",
    "Latence RAG de bout en bout (embedding + retrieval + génération)",
    ["channel", "mode"],
    buckets=[1, 3, 5, 10, 20, 30, 60, 120, 300],
)

# Erreurs Ollama
OLLAMA_ERRORS = Counter(
    "rdc_ollama_errors_total",
    "Erreurs Ollama par type (connection, http_error, circuit_open)",
    ["error_type"],
)

# État du circuit breaker (0 = CLOSED, 1 = HALF_OPEN, 2 = OPEN)
CIRCUIT_BREAKER_STATE = Gauge(
    "rdc_circuit_breaker_state",
    "État courant du circuit breaker Ollama (0=CLOSED, 1=HALF_OPEN, 2=OPEN)",
    ["name"],
)
