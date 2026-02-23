# RDC RAG News Platform

An intelligent news aggregation and semantic recommendation platform designed to reduce information overload and mitigate misinformation in the Democratic Republic of Congo (RDC).

---

## Tech Stack

### Backend
- Symfony 7+
- Doctrine ORM
- PostgreSQL + pgvector

### Frontend
- Next.js 15
- React
- TailwindCSS

### AI Service
- Python
- HuggingFace Transformers
- Sentence Embeddings (1024-dim)
- Retrieval-Augmented Generation (RAG)

---

##  System Architecture

The platform is composed of three main layers:

1. Symfony API (Core Business Logic)
2. Next.js Frontend (User Interface)
3. Python AI Microservice (Semantic Processing)

---

##  Processing Pipeline

### Article Ingestion

1. Article stored via Symfony
2. Symfony triggers AI service
3. Article is chunked (500 chars)
4. Embeddings generated
5. Similarity computed
6. Story updated or created

---

### User Query

1. User submits search query
2. Symfony forwards query to AI service
3. AI generates embedding
4. Vector similarity search (pgvector)
5. Results grouped by story
6. RAG summary generated
7. Structured response returned to frontend

---

##  Repository Structure

- backend/ → Symfony API
- frontend/ → Next.js application
- ai-service/ → Python semantic engine

---

##  Development Setup

### 