"""Âncora objetiva: reutiliza os embeddings dos chunks (text-embedding-3-small)
para medir a similaridade entre o diálogo gerado e a base teórica do conceito."""

import io
import os
import json
import numpy as np
from openai import AsyncOpenAI

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Deve ser o MESMO modelo usado no embed.py do pipeline (ver embedding_index.json).
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")


def load_embedding_index(raw: str) -> dict:
    """Mapeia chunk_id -> row, a partir do embedding_index.json."""
    data = json.loads(raw)
    return {
        it["chunk_id"]: it["row"]
        for it in data.get("items", [])
        if "chunk_id" in it and "row" in it
    }


def load_embedding_matrix(npy_bytes: bytes) -> np.ndarray:
    """Carrega a matriz de vetores do embeddings.npy (linhas = chunks)."""
    return np.load(io.BytesIO(npy_bytes))


def concept_vector(chunk_ids: list[str], index: dict, matrix: np.ndarray):
    """Vetor do conceito = média dos vetores dos chunks onde ele ocorre."""
    rows = [index[c] for c in chunk_ids if c in index]
    if not rows:
        return None
    return matrix[rows].mean(axis=0)


async def embed_text(text: str) -> np.ndarray:
    """Vetoriza um texto novo (a resposta/diálogo) no mesmo espaço dos chunks."""
    resp = await client.embeddings.create(model=EMBED_MODEL, input=text[:8000])
    return np.array(resp.data[0].embedding, dtype=float)


def cosine(a, b) -> float:
    if a is None or b is None:
        return 0.0
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a, b) / (na * nb))
