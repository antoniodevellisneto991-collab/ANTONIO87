"""Persistência dos quizzes gerados — um artefato JSON por quiz (preserva, não sobrescreve)."""

import os
import json
import uuid
from pathlib import Path
from datetime import datetime, timezone

from models import QuizOutput

RESULTS_DIR = Path(os.getenv("RESULTS_DIR", Path(__file__).parent / "results"))


def _slug(text: str) -> str:
    keep = "".join(c if c.isalnum() or c in "-_" else "_" for c in text)
    return keep.strip("_") or "quiz"


def save_quiz(quiz: QuizOutput, source: str, model: str = "gpt-4o-mini") -> dict:
    """Salva o quiz como JSON e devolve metadados (quiz_id, path, created_at_utc)."""
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    created = datetime.now(timezone.utc)
    quiz_id = f"{_slug(quiz.book_title)}__{created.strftime('%Y%m%dT%H%M%S')}__{uuid.uuid4().hex[:6]}"
    path = RESULTS_DIR / f"{quiz_id}.json"

    payload = {
        "quiz_id": quiz_id,
        "book_title": quiz.book_title,
        "source": source,  # "dna" ou "manual"
        "model": model,
        "created_at_utc": created.isoformat(),
        "total_questions": quiz.total_questions,
        "questions": [q.model_dump() for q in quiz.questions],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"quiz_id": quiz_id, "path": str(path), "created_at_utc": created.isoformat()}


def list_quizzes() -> list[dict]:
    """Lista resumos dos quizzes salvos, mais recentes primeiro."""
    if not RESULTS_DIR.exists():
        return []
    items = []
    for p in RESULTS_DIR.glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
            items.append({
                "quiz_id": d.get("quiz_id"),
                "book_title": d.get("book_title"),
                "source": d.get("source"),
                "total_questions": d.get("total_questions"),
                "created_at_utc": d.get("created_at_utc"),
            })
        except Exception:
            continue
    return sorted(items, key=lambda x: x.get("created_at_utc") or "", reverse=True)


def load_quiz(quiz_id: str) -> dict | None:
    """Carrega o quiz completo pelo id, ou None se não existir."""
    path = RESULTS_DIR / f"{_slug(quiz_id)}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
