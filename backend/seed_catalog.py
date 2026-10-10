import json

from app.db import get_connection, init_db
from app.seed_data import CATALOG_PROJECTS


def seed() -> None:
    init_db()
    conn = get_connection()
    try:
        count = conn.execute("SELECT COUNT(*) FROM catalog_projects").fetchone()[0]
        if count > 0:
            print(f"Catalogue already has {count} projects. Nothing added.")
            return

        for p in CATALOG_PROJECTS:
            conn.execute(
                """
                INSERT INTO catalog_projects
                    (title, domain, description, skills_json, difficulty, evidence_signals_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    p["title"],
                    p["domain"],
                    p["description"],
                    json.dumps(p["skills"]),
                    p["difficulty"],
                    json.dumps(p["evidence_signals"]),
                ),
            )
        conn.commit()
        print(f"Added {len(CATALOG_PROJECTS)} projects.")
    finally:
        conn.close()


if __name__ == "__main__":
    seed()
    conn = get_connection()
    try:
        for row in conn.execute("SELECT id, title, difficulty FROM catalog_projects ORDER BY id"):
            print(row["id"], "|", row["difficulty"], "|", row["title"])
    finally:
        conn.close()