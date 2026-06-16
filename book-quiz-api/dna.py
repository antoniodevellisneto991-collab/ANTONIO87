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
