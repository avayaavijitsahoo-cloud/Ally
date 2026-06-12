from __future__ import annotations

from typing import Any

from backend.database import db, init_db


VALID_CATEGORIES = {"preferences", "projects", "skills", "history"}


def save_facts(facts: list[dict[str, Any]]) -> list[int]:
    init_db()
    saved_ids: list[int] = []
    with db() as connection:
        for fact in facts:
            content = str(fact.get("content", "")).strip()
            category = str(fact.get("category", "history")).strip().lower()
            if not content:
                continue
            if category not in VALID_CATEGORIES:
                category = "history"
            cursor = connection.execute(
                """
                INSERT INTO facts (category, content)
                VALUES (?, ?)
                ON CONFLICT(content) DO UPDATE SET
                    category = excluded.category,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
                """,
                (category, content),
            )
            saved_ids.append(int(cursor.fetchone()["id"]))
    return saved_ids


def list_facts() -> list[dict[str, Any]]:
    init_db()
    with db() as connection:
        rows = connection.execute(
            """
            SELECT id, category, content, created_at, updated_at
            FROM facts
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def delete_fact(fact_id: int) -> bool:
    init_db()
    with db() as connection:
        cursor = connection.execute("DELETE FROM facts WHERE id = ?", (fact_id,))
        return cursor.rowcount > 0


def get_profile_summary() -> str:
    facts = list_facts()
    if not facts:
        return "No saved profile facts yet."

    grouped: dict[str, list[str]] = {}
    for fact in facts:
        grouped.setdefault(fact["category"], []).append(fact["content"])

    sections = []
    for category in ("history", "preferences", "projects", "skills"):
        items = grouped.get(category, [])
        if items:
            formatted = "\n".join(f"- {item}" for item in items)
            sections.append(f"{category.title()}:\n{formatted}")
    return "\n\n".join(sections)


def get_fast_relevant_profile_summary(query: str, limit: int = 6) -> str:
    facts = list_facts()
    if not facts:
        return "No saved profile facts yet."

    tokens = {token.lower() for token in query.split() if len(token) > 2}

    def score(fact: dict[str, Any]) -> int:
        content = fact["content"].lower()
        return sum(1 for token in tokens if token in content)

    ranked = sorted(facts, key=lambda fact: (score(fact), fact["id"]), reverse=True)
    selected = [fact for fact in ranked if score(fact) > 0][:limit] or ranked[:limit]
    return "\n".join(f"- {fact['content']}" for fact in selected)
