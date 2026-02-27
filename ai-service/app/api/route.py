@app.post("/articles")
def create_article(article: Article):
    embedding = model.encode(article.content).tolist()

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO articles (title, content, embedding)
        VALUES (%s, %s, %s)
        """,
        (article.title, article.content, embedding)
    )

    conn.commit()
    cursor.close()

    return {"message": "Article ajouté avec succès"}