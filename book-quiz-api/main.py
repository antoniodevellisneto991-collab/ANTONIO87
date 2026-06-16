import os
from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv

from models import BookInput, QuizOutput
from llm import generate_quiz

load_dotenv()

app = FastAPI(
    title="Book Quiz API",
    description="Recebe JSON de um livro teórico e gera perguntas + respostas via GPT-4o-mini",
    version="1.0.0",
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/quiz", response_model=QuizOutput)
async def create_quiz(book: BookInput):
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY não configurada")

    if not book.chapters:
        raise HTTPException(status_code=400, detail="O livro deve ter ao menos um capítulo")

    questions = await generate_quiz(book)

    return QuizOutput(
        book_title=book.title,
        total_questions=len(questions),
        questions=questions,
    )
