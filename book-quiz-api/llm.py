import os
import json
from openai import AsyncOpenAI
from models import BookInput, QA, AuditedChunk
from dna import format_chunks_for_prompt

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

PROMPT_PT = """Você é um professor especialista. Com base no conteúdo abaixo de um livro teórico,
gere exatamente {num_questions} perguntas de compreensão profunda com suas respectivas respostas.

Livro: {title}
{author_line}

Conteúdo:
{content}

Responda APENAS em JSON válido, sem markdown, no formato:
[
  {{"question": "...", "answer": "..."}},
  ...
]"""

PROMPT_EN = """You are an expert teacher. Based on the content below from a theoretical book,
generate exactly {num_questions} deep comprehension questions with their answers.

Book: {title}
{author_line}

Content:
{content}

Reply ONLY with valid JSON, no markdown, in the format:
[
  {{"question": "...", "answer": "..."}},
  ...
]"""


def _build_content(book: BookInput, max_chars: int = 12000) -> str:
    parts = []
    for ch in book.chapters:
        parts.append(f"[{ch.title}]\n{ch.content}")
    full = "\n\n".join(parts)
    return full[:max_chars]


async def generate_quiz(book: BookInput) -> list[QA]:
    template = PROMPT_PT if book.language == "pt" else PROMPT_EN
    author_line = f"Autor: {book.author}" if book.author else ""

    prompt = template.format(
        num_questions=book.num_questions,
        title=book.title,
        author_line=author_line,
        content=_build_content(book),
    )

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    return _parse_qa(response.choices[0].message.content)


def _parse_qa(raw: str) -> list[QA]:
    data = json.loads(raw)
    # the model may wrap in a key or return a list directly
    items = data if isinstance(data, list) else next(iter(data.values()))
    return [
        QA(
            question=item["question"],
            answer=item["answer"],
            source_chunks=item.get("source_chunks", []),
        )
        for item in items
    ]


DNA_PROMPT = """Você é um professor especialista preparando questões de estudo sobre uma obra teórica.
Abaixo estão trechos AUDITADOS do livro "{book_id}", cada um identificado por um chunk_id, com sua
frase-chave, conceitos e classificações (tese, definição, movimento argumentativo, etc.).

Gere exatamente {num_questions} perguntas de compreensão profunda, com respostas fundamentadas
APENAS nestes trechos. Cada pergunta deve citar os chunk_ids que a fundamentam.

Trechos:
{content}

Responda APENAS em JSON válido (sem markdown), no formato:
{{"questions": [
  {{"question": "...", "answer": "...", "source_chunks": ["{book_id}_chNN_cNNNN"]}},
  ...
]}}"""


async def generate_quiz_from_dna(
    chunks: list[AuditedChunk], book_id: str, num_questions: int = 5
) -> list[QA]:
    prompt = DNA_PROMPT.format(
        book_id=book_id,
        num_questions=num_questions,
        content=format_chunks_for_prompt(chunks),
    )

    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        response_format={"type": "json_object"},
    )

    return _parse_qa(response.choices[0].message.content)
