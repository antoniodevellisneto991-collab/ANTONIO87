import os
import json
import asyncio
from openai import AsyncOpenAI
from models import BookInput, QA, AuditedChunk, Validation
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
    chunks: list[AuditedChunk], book_id: str, num_questions: int = 5, validate: bool = True
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

    qas = [
        QA(
            question=q["question"],
            answer=ans,
            concept=q.get("concept"),
            source_chunks=[q["chunk_id"]] if q.get("chunk_id") else [],
        )
        for q, ans in zip(questions, answers)
    ]

    # Fase 3 — auditar fidelidade, usando o texto do chunk de origem como base teórica.
    if validate:
        text_map = {c.chunk_id: c.text for c in chunks if c.chunk_id}
        validations = await asyncio.gather(*[
            _validate_qa(
                q.get("concept") or "",
                text_map.get(q.get("chunk_id"), ""),
                q["question"],
                ans,
            )
            for q, ans in zip(questions, answers)
        ])
        for qa, v in zip(qas, validations):
            qa.validation = v

    return qas


# --- Fase 3: validação de fidelidade do diálogo (pergunta+resposta) à teoria do conceito ---

VALIDATION_PROMPT = """Você é um auditor teórico rigoroso. Abaixo há um CONCEITO (com sua base teórica)
e um DIÁLOGO (pergunta + resposta) que deveria EXEMPLIFICAR esse conceito na prática, sem citá-lo.

Conceito: {term}
Base teórica:
{context}

Diálogo:
- Pergunta: {question}
- Resposta: {answer}

Avalie se o diálogo realmente INSTANCIA o conceito — isto é, se a dinâmica descrita na base teórica
aparece de fato na cena (e não apenas de forma superficial ou tangencial).

Responda APENAS em JSON válido (sem markdown):
{{"coincide": true ou false, "score": número de 0.0 a 1.0, "analise": "1 a 2 frases explicando"}}"""


async def _validate_qa(term: str, context: str, question: str, answer: str) -> Validation:
    prompt = VALIDATION_PROMPT.format(
        term=term, context=context or "(sem base)", question=question, answer=answer
    )
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        response_format={"type": "json_object"},
    )
    data = json.loads(response.choices[0].message.content)
    return Validation(
        coincide=bool(data.get("coincide", False)),
        score=max(0.0, min(1.0, float(data.get("score", 0.0)))),
        analise=str(data.get("analise", "")),
    )


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
    concepts: list[dict],
    text_map: dict,
    questions_per_concept: int = 2,
    validate: bool = True,
    emb_index: dict | None = None,
    emb_matrix=None,
) -> list[QA]:
    """Para cada conceito curado, gera N perguntas e responde orientado pelos trechos auditados.

    Se emb_index/emb_matrix forem fornecidos, adiciona a âncora objetiva: similaridade de
    cosseno entre o diálogo gerado e os embeddings dos chunks do conceito.
    """
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

    qas = [
        QA(
            question=q,
            answer=ans,
            concept=concept["term"],
            source_chunks=concept["chunk_ids"],
        )
        for (concept, q), ans in zip(items, answers)
    ]

    # Fase 3a — juiz LLM: audita a fidelidade de cada diálogo à teoria do conceito.
    if validate:
        validations = await asyncio.gather(*[
            _validate_qa(concept["term"], contexts[concept["term"]], q, ans)
            for (concept, q), ans in zip(items, answers)
        ])
        for qa, v in zip(qas, validations):
            qa.validation = v

    # Fase 3b — âncora objetiva: similaridade de embeddings (diálogo x conceito).
    if emb_index is not None and emb_matrix is not None:
        from embeddings import concept_vector, embed_text, cosine

        # Vetor de cada conceito = média dos vetores dos seus chunks.
        concept_vecs = {
            c["term"]: concept_vector(c["chunk_ids"], emb_index, emb_matrix)
            for c in concepts
        }
        # Vetoriza cada diálogo (pergunta + resposta) no mesmo espaço.
        dialog_vecs = await asyncio.gather(*[
            embed_text(f"{q}\n{ans}") for (concept, q), ans in zip(items, answers)
        ])
        for qa, (concept, _q), dvec in zip(qas, items, dialog_vecs):
            sim = cosine(dvec, concept_vecs.get(concept["term"]))
            if qa.validation is None:
                qa.validation = Validation(similarity=sim)
            else:
                qa.validation.similarity = sim

    return qas
