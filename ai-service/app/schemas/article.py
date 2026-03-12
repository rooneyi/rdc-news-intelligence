from pydantic import BaseModel, ConfigDict


class ArticleCreate(BaseModel):
    title: str
    content: str


class ArticleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    content: str
