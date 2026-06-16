"""Carrega o índice curado de conceitos (concepts.json) e liga cada conceito ao
conteúdo auditado (llm_audit.content.jsonl) que orienta as respostas."""

import json
from models import AuditedChunk


def parse_concepts_json(raw: str) -> list[dict]:
    """Parse o concepts.json em uma lista de conceitos com proveniência e centralidade."""
    data = json.loads(raw)
    out: list[dict] = []
    for c in data.get("concepts", []):
        term = (c.get("term") or "").strip()
        if not term:
            continue
        out.append({
            "term": term,
            "definition": (c.get("definition") or "").strip(),
            "chunk_ids": [
                o.get("chunk_id") for o in c.get("occurrences", []) if o.get("chunk_id")
            ],
            "chapters": c.get("chapters", []),
            "centrality": float((c.get("centrality") or {}).get("score", 0.0)),
        })
    return out


def select_top_concepts(concepts: list[dict], k: int) -> list[dict]:
    """Ordena por centralidade (mais importantes primeiro) e pega os k primeiros."""
    ranked = sorted(concepts, key=lambda c: c.get("centrality", 0.0), reverse=True)
    return ranked[:k] if k and k > 0 else ranked


def filter_by_chapters(concepts: list[dict], chapters: list[str]) -> list[dict]:
    """Retorna só os conceitos que aparecem em pelo menos um dos capítulos pedidos."""
    if not chapters:
        return concepts
    wanted = {c.strip().lower() for c in chapters}
    return [
        c for c in concepts
        if any(ch.strip().lower() in wanted for ch in c.get("chapters", []))
    ]


def filter_chunks_by_chapters(chunks: list[AuditedChunk], chapters: list[str]) -> list[AuditedChunk]:
    """Filtra chunks pelo chapter_id."""
    if not chapters:
        return chunks
    wanted = {c.strip().lower() for c in chapters}
    return [c for c in chunks if (c.chapter_id or "").strip().lower() in wanted]


def chunk_text_map(chunks: list[AuditedChunk]) -> dict:
    """Mapa chunk_id -> texto, vindo do llm_audit.content.jsonl."""
    return {c.chunk_id: c.text for c in chunks if c.chunk_id and c.text}


def context_for_concept(concept: dict, text_map: dict, max_chars: int = 2200) -> str:
    """Monta o contexto que orienta a resposta: definição + trechos auditados do conceito."""
    parts: list[str] = []
    total = 0
    if concept.get("definition"):
        parts.append(concept["definition"])
        total += len(concept["definition"])
    for cid in concept.get("chunk_ids", []):
        t = text_map.get(cid)
        if not t:
            continue
        if total + len(t) > max_chars and parts:
            break
        parts.append(t)
        total += len(t)
    return "\n\n".join(parts) or concept.get("definition", "")
