import os
from openai import AsyncOpenAI
from models import BookInput, QA

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

    raw = response.choices[0].message.content
    import json

    data = json.loads(raw)
    # the model may wrap in a key or return a list directly
    if isinstance(data, list):
        items = data
    else:
        items = next(iter(data.values()))

    return [QA(question=item["question"], answer=item["answer"]) for item in items]
