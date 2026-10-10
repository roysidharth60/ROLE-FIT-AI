import json
import re

from app.db import get_connection
from app.models import CatalogProject

_WORD = re.compile(r"[a-z0-9+#.]+")
_FILLER = {
    "the", "and", "for", "with", "our", "you", "are", "will", "your",
    "this", "that", "from", "have", "has", "can", "not", "all", "any",
}


def _tokens(text: str) -> set[str]:
    """Lowercase words from text, without filler words."""
    words = {w.strip(".") for w in _WORD.findall(text.lower())}
    return {w for w in words if len(w) > 1 and w not in _FILLER}


def _to_project(row, score: int = 0) -> CatalogProject:
    return CatalogProject(
        id=row["id"],
        title=row["title"],
        domain=row["domain"],
        description=row["description"],
        skills=json.loads(row["skills_json"]),
        difficulty=row["difficulty"],
        evidence_signals=json.loads(row["evidence_signals_json"]),
        score=score,
    )


def list_projects() -> list[CatalogProject]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM catalog_projects ORDER BY id").fetchall()
        return [_to_project(r) for r in rows]
    finally:
        conn.close()


def search_projects(query: str, limit: int = 3) -> list[CatalogProject]:
    """Rank projects by keyword overlap. Skill matches count 3, other text counts 1."""
    query_words = _tokens(query)
    if not query_words:
        return []

    hits: list[CatalogProject] = []
    for project in list_projects():
        skill_words = _tokens(" ".join(project.skills))
        text_words = _tokens(f"{project.title} {project.domain} {project.description}")
        score = 3 * len(query_words & skill_words) + len(query_words & (text_words - skill_words))
        if score > 0:
            hits.append(project.model_copy(update={"score": score}))

    hits.sort(key=lambda p: (-p.score, p.id))
    return hits[:limit]