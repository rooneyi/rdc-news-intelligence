from fastapi import APIRouter, HTTPException
from app.schemas.article import ArticleCreate, ArticleOut
from app.services.article_service import create_article, search_similar
from app.services.embedding_service import generate_embedding

router = APIRouter()

@router.post("/articles", response_model=ArticleOut)
def post_article(article: ArticleCreate):
    return create_article(article.title, article.content)

@router.post("/query")
def query_articles(payload: dict):
    query = payload.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Query is required")
    query_embedding = generate_embedding(query)
    results = search_similar(query_embedding)
    return {"results": [r.dict() for r in results]}
