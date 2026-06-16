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


class QA(BaseModel):
    question: str
    answer: str


class QuizOutput(BaseModel):
    book_title: str
    total_questions: int
    questions: list[QA]
