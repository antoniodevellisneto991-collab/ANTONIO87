import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from dotenv import load_dotenv

from models import BookInput, QuizOutput
from llm import generate_quiz, generate_quiz_from_dna
from dna import parse_audit_jsonl, included, book_id_from

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
    if not book.chapters:
        raise HTTPException(status_code=400, detail="O livro deve ter ao menos um capítulo")

    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY não configurada")

    questions = await generate_quiz(book)

    return QuizOutput(
        book_title=book.title,
        total_questions=len(questions),
        questions=questions,
    )


@app.post("/quiz/dna", response_model=QuizOutput)
async def create_quiz_from_dna(
    file: UploadFile = File(..., description="Arquivo llm_audit.content.jsonl do DNA do Livro"),
    num_questions: int = Query(default=5, ge=1, le=20),
):
    """Gera perguntas+respostas a partir de um llm_audit.content.jsonl, com rastreabilidade por chunk_id."""
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY não configurada")

    raw = (await file.read()).decode("utf-8", errors="replace")
    try:
        chunks = included(parse_audit_jsonl(raw))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Arquivo JSONL inválido: {e}")

    if not chunks:
        raise HTTPException(status_code=400, detail="Nenhum trecho auditado encontrado no arquivo")

    book_id = book_id_from(chunks)
    questions = await generate_quiz_from_dna(chunks, book_id, num_questions)

    return QuizOutput(
        book_title=book_id,
        total_questions=len(questions),
        questions=questions,
    )
