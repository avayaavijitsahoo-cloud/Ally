from __future__ import annotations

import json
from typing import Any

from backend.conversations import add_message, create_conversation


def import_conversation(payload: dict[str, Any]) -> dict[str, Any]:
    title = payload.get("title") or "Imported conversation"
    messages = payload.get("messages", [])
    if isinstance(messages, str):
        messages = json.loads(messages)
    if not isinstance(messages, list):
        raise ValueError("messages must be a list")

    conversation = create_conversation(title)
    imported = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = message.get("role")
        content = str(message.get("content", "")).strip()
        if role in {"user", "assistant", "system"} and content:
            imported.append(add_message(conversation["id"], role, content))

    conversation["messages"] = imported
    return conversation
