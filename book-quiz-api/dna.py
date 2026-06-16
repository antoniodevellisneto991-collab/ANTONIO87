"""Carrega e formata artefatos do pipeline DNA do Livro (llm_audit.content.jsonl)."""

import json
from models import AuditedChunk


def parse_audit_jsonl(raw: str) -> list[AuditedChunk]:
    """Parse o conteúdo de um llm_audit.content.jsonl em chunks auditados."""
    chunks: list[AuditedChunk] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        chunks.append(
            AuditedChunk(
                chunk_id=obj.get("chunk_id", ""),
                chapter_id=obj.get("chapter_id"),
                decision=obj.get("decision"),
                classifications=obj.get("classifications", []),
                key_sentence=obj.get("key_sentence"),
                text=obj.get("text", ""),
                concepts=obj.get("concepts", []),
            )
        )
    return chunks


def book_id_from(chunks: list[AuditedChunk]) -> str:
    """Deriva o book_id a partir do prefixo dos chunk_ids (ex: goffman1_dna_ch01_c0001)."""
    for c in chunks:
        if "_ch" in c.chunk_id:
            return c.chunk_id.split("_ch")[0]
    return "livro"


def included(chunks: list[AuditedChunk]) -> list[AuditedChunk]:
    """Mantém só os trechos auditados como 'include'."""
    inc = [c for c in chunks if (c.decision or "include") == "include"]
    return inc or chunks


def iter_concept_axes(chunks: list[AuditedChunk]) -> list[dict]:
    """Percorre o livro na ordem e extrai os conceitos-eixo com proveniência.

    Cada eixo é um conceito de Goffman (term + definition) ligado ao chunk de origem.
    Chunks sem conceito explícito entram com a frase-chave como eixo de fallback.
    """
    axes: list[dict] = []
    for c in chunks:
        used = False
        for cp in c.concepts:
            term = (cp.get("term") or "").strip()
            if not term:
                continue
            axes.append({
                "concept": term,
                "definition": (cp.get("definition") or "").strip(),
                "key_sentence": c.key_sentence or "",
                "chapter_id": c.chapter_id,
                "chunk_id": c.chunk_id,
            })
            used = True
        if not used and c.key_sentence:
            axes.append({
                "concept": c.key_sentence.strip(),
                "definition": "",
                "key_sentence": c.key_sentence or "",
                "chapter_id": c.chapter_id,
                "chunk_id": c.chunk_id,
            })
    return axes


def select_axes(axes: list[dict], n: int) -> list[dict]:
    """Seleciona n eixos distribuídos uniformemente ao longo do livro (cobertura)."""
    if not axes or n <= 0:
        return []
    if len(axes) <= n:
        return axes
    step = len(axes) / n
    return [axes[int(i * step)] for i in range(n)]


def group_axes_by_chapter(axes: list[dict]) -> list[tuple]:
    """Agrupa os eixos por capítulo preservando a ordem do livro."""
    groups: list[tuple] = []
    for a in axes:
        if not groups or groups[-1][0] != a["chapter_id"]:
            groups.append((a["chapter_id"], []))
        groups[-1][1].append(a)
    return groups


def format_chunks_for_prompt(chunks: list[AuditedChunk], max_chars: int = 14000) -> str:
    """Formata os chunks num bloco textual com proveniência para o prompt do LLM."""
    parts: list[str] = []
    total = 0
    for c in chunks:
        concepts = "; ".join(
            f"{cp.get('term')}: {cp.get('definition')}" for cp in c.concepts if cp.get("term")
        )
        block = (
            f"[{c.chunk_id}] (cap {c.chapter_id}; {', '.join(c.classifications)})\n"
            f"Frase-chave: {c.key_sentence or '-'}\n"
            f"Conceitos: {concepts or '-'}\n"
            f"Trecho: {c.text}"
        )
        if total + len(block) > max_chars and parts:
            break
        parts.append(block)
        total += len(block)
    return "\n\n".join(parts)
