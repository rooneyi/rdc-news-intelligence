# main.py

from fastapi import FastAPI
from pydantic import BaseModel
from app.services.embedding_service import EmbeddingService
from app.services.retrieval_service import RetrievalService

app = FastAPI(title="RDC RAG AI Service")

embedding_service = EmbeddingService()
retrieval_service = RetrievalService()

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    results: list

@app.post("/query", response_model=QueryResponse)
def query_endpoint(request: QueryRequest):
    
    # Générer embedding
    embedding = embedding_service.generate(request.query)

    # Recherche vectorielle
    results = retrieval_service.search(embedding)

    return {"results": results}