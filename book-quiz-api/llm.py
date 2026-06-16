import os
import json
import asyncio
from openai import AsyncOpenAI
from models import BookInput, QA, AuditedChunk
from dna import (
    format_chunks_for_prompt,
    iter_concept_axes,
    select_axes,
    group_axes_by_chapter,
)

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


# --- Fluxo DNA: o conceito é o EIXO; a pergunta aplica o conceito numa interação real ---

GEN_PROMPT = """Você vai elaborar perguntas para INICIAR diálogos reais entre duas pessoas comuns.

Cada item abaixo traz um conceito (o EIXO OCULTO da pergunta) com sua definição. Para CADA item,
crie UMA pergunta que:
- seja uma situação concreta e cotidiana de interação entre pessoas — algo que alguém realmente
  diria ou perguntaria a outra pessoa numa conversa;
- use o conceito apenas como lente por trás da cena, SEM JAMAIS citá-lo, sem citar Goffman, sem
  soar teórica ou acadêmica. A pergunta NÃO é sobre o conceito, é uma situação onde ele aparece na prática;
- soe como fala espontânea de quem puxa conversa ou traz um caso real do dia a dia.

Itens:
{listing}

Responda APENAS em JSON válido (sem markdown), no formato:
{{"questions": [
  {{"chunk_id": "...", "concept": "...", "question": "..."}}
]}}"""

ANSWER_PROMPT = """Duas pessoas estão conversando numa situação cotidiana. A primeira disse:

"{question}"

Responda como a segunda pessoa responderia numa conversa real: de forma concreta, natural e prática,
contando como você agiria, o que perceberia ou faria nessa situação. NÃO seja acadêmico, NÃO cite
teorias, autores nem termos técnicos. Apenas a fala da segunda pessoa, em 2 a 4 frases."""


def _format_axes(axes: list[dict]) -> str:
    lines = []
    for a in axes:
        base = a["definition"] or a["key_sentence"] or "(sem definição)"
        lines.append(f'- chunk_id={a["chunk_id"]} | conceito="{a["concept"]}" | base: {base}')
    return "\n".join(lines)


async def _generate_questions(axes: list[dict]) -> list[dict]:
    """Fase 1: a partir de um lote de conceitos-eixo, gera uma pergunta situacional para cada."""
    prompt = GEN_PROMPT.format(listing=_format_axes(axes))
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content)
    items = data if isinstance(data, list) else next(iter(data.values()))
    return [i for i in items if i.get("question")]


async def _answer_question(question: str) -> str:
    """Fase 2: executa a pergunta no LLM e captura a resposta (a 'outra pessoa' do diálogo)."""
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": ANSWER_PROMPT.format(question=question)}],
        temperature=0.8,
    )
    return (response.choices[0].message.content or "").strip()


async def generate_quiz_from_dna(
    chunks: list[AuditedChunk], book_id: str, num_questions: int = 5
) -> list[QA]:
    # Percorre o livro e seleciona conceitos-eixo distribuídos por todos os capítulos.
    axes = select_axes(iter_concept_axes(chunks), num_questions)
    if not axes:
        return []

    # Fase 1 — gerar as perguntas, percorrendo o livro capítulo a capítulo.
    groups = group_axes_by_chapter(axes)
    generated = await asyncio.gather(*[_generate_questions(g[1]) for g in groups])
    questions = [q for batch in generated for q in batch]

    # Fase 2 — executar cada pergunta no LLM (em paralelo) e coletar as respostas.
    answers = await asyncio.gather(*[_answer_question(q["question"]) for q in questions])

    return [
        QA(
            question=q["question"],
            answer=ans,
            concept=q.get("concept"),
            source_chunks=[q["chunk_id"]] if q.get("chunk_id") else [],
        )
        for q, ans in zip(questions, answers)
    ]


# --- Fluxo por conceito curado: N perguntas por conceito; respostas orientadas pelo conteúdo ---

GEN_CONCEPT_PROMPT = """Você vai criar {n} pergunta(s) DIFERENTE(S) para iniciar diálogos reais entre
duas pessoas comuns.

O EIXO OCULTO de todas elas é este conceito (use-o apenas como lente por trás da cena):
Conceito: {term}
Definição: {definition}

Regras para cada pergunta:
- ser uma situação concreta e cotidiana de interação entre pessoas — algo que alguém realmente diria
  ou perguntaria numa conversa;
- NUNCA citar o conceito, nem Goffman, nem soar teórica/acadêmica. A pergunta NÃO é sobre o conceito,
  é uma cena onde ele aparece na prática;
- as {n} situações devem ser bem diferentes entre si.

Responda APENAS em JSON válido (sem markdown):
{{"questions": ["...", "..."]}}"""

ANSWER_GROUNDED_PROMPT = """Duas pessoas estão conversando numa situação cotidiana. A primeira disse:

"{question}"

Para responder de forma fiel, considere COMO o material abaixo descreve esse tipo de situação
(use como orientação, mas SEM citá-lo):
{context}

Responda como a segunda pessoa responderia numa conversa real: concreta, natural e prática, coerente
com a dinâmica descrita acima, mas SEM citar teorias, autores ou termos técnicos. 2 a 4 frases."""


async def _generate_questions_for_concept(term: str, definition: str, n: int) -> list[str]:
    prompt = GEN_CONCEPT_PROMPT.format(n=n, term=term, definition=definition or "(sem definição)")
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content)
    items = data if isinstance(data, list) else next(iter(data.values()))
    return [q for q in items if isinstance(q, str) and q.strip()]


async def _answer_grounded(question: str, context: str) -> str:
    prompt = ANSWER_GROUNDED_PROMPT.format(question=question, context=context or "(sem contexto)")
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )
    return (response.choices[0].message.content or "").strip()


async def generate_quiz_from_concepts(
    concepts: list[dict], text_map: dict, questions_per_concept: int = 2
) -> list[QA]:
    """Para cada conceito curado, gera N perguntas e responde orientado pelos trechos auditados."""
    from concepts import context_for_concept

    # Fase 1 — gerar N perguntas por conceito (em paralelo).
    gen = await asyncio.gather(*[
        _generate_questions_for_concept(c["term"], c["definition"], questions_per_concept)
        for c in concepts
    ])

    # Achata mantendo o vínculo pergunta -> conceito e pré-calcula o contexto de cada conceito.
    items: list[tuple] = []
    contexts: dict = {}
    for concept, qs in zip(concepts, gen):
        contexts[concept["term"]] = context_for_concept(concept, text_map)
        for q in qs:
            items.append((concept, q))

    if not items:
        return []

    # Fase 2 — responder cada pergunta orientada pelo conteúdo auditado do conceito.
    answers = await asyncio.gather(*[
        _answer_grounded(q, contexts[concept["term"]]) for concept, q in items
    ])

    return [
        QA(
            question=q,
            answer=ans,
            concept=concept["term"],
            source_chunks=concept["chunk_ids"],
        )
        for (concept, q), ans in zip(items, answers)
    ]
