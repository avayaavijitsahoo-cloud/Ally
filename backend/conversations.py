from __future__ import annotations

from typing import Any

from backend.database import db, init_db


def create_conversation(title: str | None = None) -> dict[str, Any]:
    init_db()
    clean_title = (title or "New conversation").strip()[:80] or "New conversation"
    with db() as connection:
        cursor = connection.execute("INSERT INTO conversations (title) VALUES (?) RETURNING *", (clean_title,))
        return dict(cursor.fetchone())


def list_conversations() -> list[dict[str, Any]]:
    init_db()
    with db() as connection:
        rows = connection.execute(
            """
            SELECT c.id, c.title, c.created_at, c.updated_at, COUNT(m.id) AS message_count
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            GROUP BY c.id
            ORDER BY c.updated_at DESC
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_conversation(conversation_id: int) -> dict[str, Any] | None:
    init_db()
    with db() as connection:
        conversation = connection.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if conversation is None:
            return None
        messages = connection.execute(
            """
            SELECT id, role, content, created_at
            FROM messages
            WHERE conversation_id = ?
            ORDER BY id ASC
            """,
            (conversation_id,),
        ).fetchall()
    result = dict(conversation)
    result["messages"] = [dict(message) for message in messages]
    return result


def add_message(conversation_id: int, role: str, content: str) -> dict[str, Any]:
    init_db()
    with db() as connection:
        cursor = connection.execute(
            """
            INSERT INTO messages (conversation_id, role, content)
            VALUES (?, ?, ?)
            RETURNING id, conversation_id, role, content, created_at
            """,
            (conversation_id, role, content),
        )
        connection.execute(
            "UPDATE conversations SET updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (conversation_id,),
        )
        return dict(cursor.fetchone())


def delete_conversation(conversation_id: int) -> bool:
    init_db()
    with db() as connection:
        cursor = connection.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        return cursor.rowcount > 0


def conversation_history(conversation_id: int) -> list[dict[str, str]]:
    conversation = get_conversation(conversation_id)
    if not conversation:
        return []
    return [
        {"role": message["role"], "content": message["content"]}
        for message in conversation["messages"]
        if message["role"] in {"user", "assistant"}
    ]
