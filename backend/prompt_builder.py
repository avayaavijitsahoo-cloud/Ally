from __future__ import annotations

import os

from backend.profile_store import get_fast_relevant_profile_summary, get_profile_summary


BASE_IDENTITY = """You are AllyAI, a privacy-focused personal AI assistant with persistent memory about the user.
Use saved memories naturally when they are relevant. Do not announce that you are using memory.

Your personality:
- Warm but direct
- Technically precise when depth helps
- Adaptive to the user's expertise and communication style
- Proactive when saved context is useful"""

PROFILE_INSTRUCTIONS = """Memory rules:
- Use profile facts only when they are relevant
- Never infer unstated details
- Trust the user's current message if it conflicts with saved memory
- Never say phrases like "according to your profile"
- If there is no useful memory, respond normally"""


def build_system_prompt(query: str = "") -> str:
    if query:
        if os.getenv("CHAT_MEMORY_MODE", "fast").lower() == "semantic":
            try:
                from backend.retrieval import get_relevant_profile_summary

                profile_context = get_relevant_profile_summary(query)
            except Exception:
                profile_context = get_fast_relevant_profile_summary(query)
        else:
            profile_context = get_fast_relevant_profile_summary(query)
    else:
        profile_context = get_profile_summary()

    return f"""{BASE_IDENTITY}

{PROFILE_INSTRUCTIONS}

Known user facts:
{profile_context}""".strip()


def build_conversation_messages(history: list[dict[str, str]], new_message: str) -> list[dict[str, str]]:
    return [*history, {"role": "user", "content": new_message}]
