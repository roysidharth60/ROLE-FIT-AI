import json
from datetime import datetime, timezone

from app.db import get_connection
from app.models import JobDraft, JobRecord, JobSummary


def _summary(row) -> JobSummary:
    try:
        employer = json.loads(row["profile_json"]).get("employer_name", "") or ""
    except (ValueError, TypeError):
        employer = ""  # older rows saved before this field existed
    return JobSummary(
        id=row["id"],
        title=row["title"],
        status=row["status"],
        created_at=row["created_at"],
        published_at=row["published_at"],
        employer_name=employer,
    )


def save_job(title: str, draft: JobDraft, publish: bool) -> JobSummary:
    """Store the draft. The CV goes in cv_json, everything else in profile_json."""
    status = "published" if publish else "draft"
    published_at = datetime.now(timezone.utc).isoformat(timespec="seconds") if publish else None

    conn = get_connection()
    try:
        cur = conn.execute(
            "INSERT INTO jobs (title, status, profile_json, cv_json, published_at) VALUES (?, ?, ?, ?, ?)",
            (title, status, draft.model_dump_json(exclude={"cv"}), draft.cv.model_dump_json(), published_at),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (cur.lastrowid,)).fetchone()
        return _summary(row)
    finally:
        conn.close()


def list_jobs(status: str | None = None) -> list[JobSummary]:
    conn = get_connection()
    try:
        if status:
            rows = conn.execute("SELECT * FROM jobs WHERE status = ? ORDER BY id DESC", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
        return [_summary(r) for r in rows]
    finally:
        conn.close()


def get_job(job_id: int) -> JobRecord | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    finally:
        conn.close()
    if row is None:
        return None

    profile = json.loads(row["profile_json"])
    profile["cv"] = json.loads(row["cv_json"])
    return JobRecord(**_summary(row).model_dump(), draft=JobDraft.model_validate(profile))