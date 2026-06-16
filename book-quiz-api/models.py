from pydantic import BaseModel, Field
from typing import Optional


class Chapter(BaseModel):
    title: str
    content: str


class BookInput(BaseModel):
    title: str
    author: Optional[str] = None
    chapters: list[Chapter]
    num_questions: int = Field(default=5, ge=1, le=20)
    language: str = Field(default="pt", description="Idioma das perguntas: 'pt' ou 'en'")


class Validation(BaseModel):
    coincide: bool = Field(description="O diálogo realmente instancia o conceito?")
    score: float = Field(ge=0.0, le=1.0, description="Quão fiel o diálogo é à teoria (0 a 1)")
    analise: str = Field(description="Justificativa curta da avaliação")


class QA(BaseModel):
    question: str
    answer: str
    concept: Optional[str] = Field(
        default=None,
        description="Conceito de Goffman que é o eixo (oculto) da pergunta",
    )
    source_chunks: list[str] = Field(
        default_factory=list,
        description="chunk_ids do DNA que fundamentam a pergunta (rastreabilidade)",
    )
    validation: Optional[Validation] = Field(
        default=None,
        description="Auditoria de fidelidade do diálogo à teoria do conceito",
    )


class QuizOutput(BaseModel):
    book_title: str
    total_questions: int
    questions: list[QA]
    quiz_id: Optional[str] = Field(default=None, description="Id do quiz salvo em disco")


class AuditedChunk(BaseModel):
    """Subconjunto dos campos de um registro de llm_audit.content.jsonl."""

    chunk_id: str
    chapter_id: Optional[str] = None
    decision: Optional[str] = None
    classifications: list[str] = Field(default_factory=list)
    key_sentence: Optional[str] = None
    text: str = ""
    concepts: list[dict] = Field(default_factory=list)
