from pydantic import BaseModel

class ArticleCreate(BaseModel):
    title: str
    content: str

class ArticleOut(BaseModel):
    id: int
    title: str
    content: str
