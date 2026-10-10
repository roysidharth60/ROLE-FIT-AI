import sqlite3
from pathlib import Path

# The database file lives in backend\data\rolefit.db (ignored by Git via *.db)
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "rolefit.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft', 'published')),
    profile_json  TEXT NOT NULL,
    cv_json       TEXT NOT NULL,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    published_at  TEXT
);

CREATE TABLE IF NOT EXISTS catalog_projects (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    title                  TEXT NOT NULL,
    domain                 TEXT NOT NULL,
    description            TEXT NOT NULL,
    skills_json            TEXT NOT NULL,
    difficulty             TEXT NOT NULL
                           CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
    evidence_signals_json  TEXT NOT NULL
);
"""


def get_connection() -> sqlite3.Connection:
    """Open the database (creating the data folder if needed)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # rows behave like dictionaries
    return conn


def init_db() -> None:
    """Create the tables if they do not exist yet."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        print("Database file:", DB_PATH)
        print("Tables:", [r["name"] for r in rows])
    finally:
        conn.close()