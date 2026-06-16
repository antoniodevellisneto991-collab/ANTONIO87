import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from dotenv import load_dotenv

from models import BookInput, QuizOutput
from llm import generate_quiz, generate_quiz_from_dna, generate_quiz_from_concepts
from dna import parse_audit_jsonl, included, book_id_from
from concepts import (
    parse_concepts_json, select_top_concepts, chunk_text_map,
    filter_by_chapters, filter_chunks_by_chapters,
)
from storage import save_quiz, list_quizzes, load_quiz

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

    quiz = QuizOutput(
        book_title=book.title,
        total_questions=len(questions),
        questions=questions,
    )
    quiz.quiz_id = save_quiz(quiz, source="manual")["quiz_id"]
    return quiz


@app.post("/quiz/dna", response_model=QuizOutput)
async def create_quiz_from_dna(
    file: UploadFile = File(..., description="Arquivo llm_audit.content.jsonl do DNA do Livro"),
    num_questions: int = Query(default=5, ge=1, le=50),
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

    quiz = QuizOutput(
        book_title=book_id,
        total_questions=len(questions),
        questions=questions,
    )
    quiz.quiz_id = save_quiz(quiz, source="dna")["quiz_id"]
    return quiz


@app.post("/quiz/concepts", response_model=QuizOutput)
async def create_quiz_from_concepts(
    concepts_file: UploadFile = File(..., description="concepts.json (índice curado de conceitos)"),
    audit_file: UploadFile = File(..., description="llm_audit.content.jsonl (orienta as respostas)"),
    questions_per_concept: int = Query(default=2, ge=1, le=10),
    max_concepts: int = Query(default=8, ge=1, le=200, description="Conceitos mais centrais a usar"),
    chapters: list[str] = Query(default=[], description="Filtrar por capítulo(s): ch01, ch02, ..."),
):
    """Gera N perguntas POR conceito curado; as respostas são orientadas pelos trechos auditados."""
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY não configurada")

    try:
        all_concepts = parse_concepts_json((await concepts_file.read()).decode("utf-8", errors="replace"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"concepts.json inválido: {e}")
    if not all_concepts:
        raise HTTPException(status_code=400, detail="Nenhum conceito encontrado no concepts.json")

    try:
        chunks = parse_audit_jsonl((await audit_file.read()).decode("utf-8", errors="replace"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"llm_audit.content.jsonl inválido: {e}")

    filtered_concepts = filter_by_chapters(all_concepts, chapters) if chapters else all_concepts
    if not filtered_concepts:
        raise HTTPException(status_code=404, detail=f"Nenhum conceito encontrado nos capítulos: {chapters}")

    filtered_chunks = filter_chunks_by_chapters(chunks, chapters) if chapters else chunks

    concepts = select_top_concepts(filtered_concepts, max_concepts)
    text_map = chunk_text_map(filtered_chunks)
    book_id = book_id_from(chunks)

    questions = await generate_quiz_from_concepts(concepts, text_map, questions_per_concept)

    quiz = QuizOutput(
        book_title=book_id,
        total_questions=len(questions),
        questions=questions,
    )
    quiz.quiz_id = save_quiz(quiz, source="concepts")["quiz_id"]
    return quiz


@app.get("/quizzes")
async def get_quizzes():
    """Lista os quizzes já salvos (resumo)."""
    return list_quizzes()


@app.get("/quizzes/{quiz_id}")
async def get_quiz(quiz_id: str):
    """Retorna um quiz salvo completo pelo id."""
    quiz = load_quiz(quiz_id)
    if quiz is None:
        raise HTTPException(status_code=404, detail="Quiz não encontrado")
    return quiz
