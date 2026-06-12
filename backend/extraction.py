from __future__ import annotations

import json
import re
from typing import Any

from backend.profile_store import list_facts, save_facts
from backend.retrieval import upsert_facts_to_vector_store


EXTRACTION_PROMPT = """Extract only explicit facts the user stated about themselves.

Rules:
- Do not infer or guess
- Ignore facts about the assistant or general topics
- Use one of these categories: preferences, projects, skills, history
- Return only JSON in this shape: {"facts":[{"category":"history","content":"Name is Reva"}]}
- If there are no explicit user facts, return {"facts":[]}

Conversation:
{conversation}"""


def format_conversation(messages: list[dict[str, str]]) -> str:
    return "\n".join(f"{message['role'].capitalize()}: {message['content']}" for message in messages)


def _extract_json(raw_output: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", raw_output, re.DOTALL)
    if not match:
        return {"facts": []}
    return json.loads(match.group(0))


def extract_facts(messages: list[dict[str, str]], client: Any) -> list[dict[str, str]]:
    prompt = EXTRACTION_PROMPT.replace("{conversation}", format_conversation(messages))
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        max_tokens=800,
    )
    parsed = _extract_json((response.choices[0].message.content or "").strip())
    facts = parsed.get("facts", [])
    if not isinstance(facts, list):
        return []
    return [
        {"category": str(fact.get("category", "history")), "content": str(fact.get("content", "")).strip()}
        for fact in facts
        if isinstance(fact, dict) and str(fact.get("content", "")).strip()
    ]


def extract_and_save(messages: list[dict[str, str]], raw_client: Any) -> list[int]:
    try:
        client = raw_client.client if hasattr(raw_client, "client") else raw_client
        facts = extract_facts(messages, client)
        saved_ids = save_facts(facts)
        saved_facts = [fact for fact in list_facts() if fact["id"] in saved_ids]
        upsert_facts_to_vector_store(saved_facts)
        return saved_ids
    except Exception:
        return []
