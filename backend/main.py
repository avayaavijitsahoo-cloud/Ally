from __future__ import annotations

from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.conversations import (
    add_message,
    conversation_history,
    create_conversation,
    delete_conversation,
    get_conversation,
    list_conversations,
)
from backend.database import init_db
from backend.extraction import extract_and_save
from backend.importer import import_conversation
from backend.llm_client import get_chat_client
from backend.profile_store import delete_fact, list_facts, save_facts
from backend.prompt_builder import build_conversation_messages, build_system_prompt
from backend.retrieval import delete_fact_from_vector_store, search_memories, upsert_facts_to_vector_store


load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(title="AllyAI", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    conversation_id: int | None = None
    provider: str = "groq"
    model: str | None = None


class ConversationCreate(BaseModel):
    title: str | None = None


class ManualFact(BaseModel):
    category: str = "history"
    content: str = Field(..., min_length=1)


class ImportRequest(BaseModel):
    title: str | None = None
    messages: list[dict[str, Any]]


class FrontendChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    model_key: str | None = None


class ImportUrlRequest(BaseModel):
    url: str = Field(..., min_length=1)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/", response_model=None)
def home() -> FileResponse | dict[str, str]:
    index = FRONTEND_DIR / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"name": "AllyAI", "status": "running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _prepare_chat(request: ChatRequest) -> tuple[int, list[dict[str, str]], list[dict[str, str]]]:
    conversation = (
        get_conversation(request.conversation_id)
        if request.conversation_id is not None
        else create_conversation(request.message[:60])
    )
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation_id = int(conversation["id"])
    history = conversation_history(conversation_id)
    system_prompt = build_system_prompt(request.message)
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(build_conversation_messages(history, request.message))
    return conversation_id, history, messages


@app.post("/api/chat")
def chat(request: ChatRequest, background_tasks: BackgroundTasks) -> dict[str, Any]:
    conversation_id, history, messages = _prepare_chat(request)

    try:
        client = get_chat_client(request.provider)
        assistant_reply = client.complete(messages, request.model)
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    user_message = add_message(conversation_id, "user", request.message)
    assistant_message = add_message(conversation_id, "assistant", assistant_reply)
    background_tasks.add_task(
        extract_and_save,
        [*history, {"role": "user", "content": request.message}, {"role": "assistant", "content": assistant_reply}],
        client,
    )

    return {
        "conversation_id": conversation_id,
        "reply": assistant_reply,
        "messages": [user_message, assistant_message],
    }


@app.post("/api/conversations")
def create_conversation_endpoint(request: ConversationCreate) -> dict[str, Any]:
    return create_conversation(request.title)


@app.get("/api/conversations")
def conversations_endpoint() -> list[dict[str, Any]]:
    return list_conversations()


@app.get("/api/conversations/{conversation_id}")
def conversation_endpoint(conversation_id: int) -> dict[str, Any]:
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.delete("/api/conversations/{conversation_id}")
def delete_conversation_endpoint(conversation_id: int) -> dict[str, bool]:
    return {"deleted": delete_conversation(conversation_id)}


@app.post("/api/import")
def import_endpoint(request: ImportRequest) -> dict[str, Any]:
    return import_conversation(request.model_dump())


@app.get("/api/memories")
def memories_endpoint() -> list[dict[str, Any]]:
    return list_facts()


@app.post("/api/memories")
def add_memory_endpoint(fact: ManualFact) -> dict[str, Any]:
    ids = save_facts([fact.model_dump()])
    saved = [memory for memory in list_facts() if memory["id"] in ids]
    try:
        upsert_facts_to_vector_store(saved)
    except Exception:
        pass
    return saved[0] if saved else {}


@app.delete("/api/memories/{fact_id}")
def delete_memory_endpoint(fact_id: int) -> dict[str, bool]:
    deleted = delete_fact(fact_id)
    if deleted:
        delete_fact_from_vector_store(fact_id)
    return {"deleted": deleted}


@app.get("/api/memories/search")
def search_memories_endpoint(q: str, limit: int = 5) -> list[dict[str, Any]]:
    return search_memories(q, limit)


@app.get("/models")
def models_endpoint() -> dict[str, list[dict[str, str]]]:
    return {
        "models": [
            {"key": "llama-3.1-8b", "name": "Groq Llama 3.1 8B Instant"},
            {"key": "llama-3.3-70b", "name": "Groq Llama 3.3 70B Quality"},
            {"key": "mixtral-8x7b", "name": "Groq Mixtral 8x7B"},
        ]
    }


def _groq_model_name(model_key: str | None) -> str | None:
    models = {
        "llama-3.3-70b": "llama-3.3-70b-versatile",
        "llama-3.1-8b": "llama-3.1-8b-instant",
        "mixtral-8x7b": "mixtral-8x7b-32768",
    }
    return models.get(model_key or "")


@app.post("/chat")
def frontend_chat(request: FrontendChatRequest, background_tasks: BackgroundTasks) -> StreamingResponse:
    payload = ChatRequest(message=request.message, model=_groq_model_name(request.model_key))
    conversation_id, history, messages = _prepare_chat(payload)
    try:
        client = get_chat_client()
    except Exception as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    def token_stream():
        chunks: list[str] = []
        try:
            for chunk in client.stream(messages, payload.model):
                chunks.append(chunk)
                yield chunk
        finally:
            assistant_reply = "".join(chunks).strip()
            if assistant_reply:
                add_message(conversation_id, "user", request.message)
                add_message(conversation_id, "assistant", assistant_reply)
                background_tasks.add_task(
                    extract_and_save,
                    [
                        *history,
                        {"role": "user", "content": request.message},
                        {"role": "assistant", "content": assistant_reply},
                    ],
                    client,
                )

    return StreamingResponse(token_stream(), media_type="text/plain")


@app.delete("/conversation")
def clear_frontend_conversation() -> dict[str, bool]:
    return {"cleared": True}


@app.get("/conversations")
def frontend_conversations() -> dict[str, list[dict[str, Any]]]:
    return {"conversations": list_conversations()}


@app.get("/conversations/{conversation_id}")
def frontend_conversation(conversation_id: int) -> dict[str, Any]:
    return conversation_endpoint(conversation_id)


@app.delete("/conversations/{conversation_id}")
def frontend_delete_conversation(conversation_id: int) -> dict[str, bool]:
    return delete_conversation_endpoint(conversation_id)


@app.get("/profile")
def profile_endpoint() -> dict[str, str]:
    from backend.profile_store import get_profile_summary

    return {"profile": get_profile_summary()}


@app.get("/profile/full")
def full_profile_endpoint() -> dict[str, dict[str, list[dict[str, Any]]]]:
    grouped: dict[str, list[dict[str, Any]]] = {
        "preferences": [],
        "projects": [],
        "skills": [],
        "history": [],
    }
    for fact in list_facts():
        grouped.setdefault(fact["category"], []).append(fact)
    return {"profile": grouped}


@app.post("/profile/fact")
def add_profile_fact_endpoint(fact: ManualFact) -> dict[str, Any]:
    return add_memory_endpoint(fact)


@app.delete("/profile/fact/{fact_id}")
def delete_profile_fact_endpoint(fact_id: int) -> dict[str, bool]:
    return delete_memory_endpoint(fact_id)


@app.get("/profile/export")
def export_profile_endpoint() -> dict[str, Any]:
    return {"facts": list_facts()}


@app.post("/profile/import")
def import_profile_endpoint(payload: dict[str, Any]) -> dict[str, str]:
    facts = payload.get("facts", [])
    if not isinstance(facts, list):
        raise HTTPException(status_code=400, detail="facts must be a list")
    ids = save_facts(facts)
    saved = [memory for memory in list_facts() if memory["id"] in ids]
    try:
        upsert_facts_to_vector_store(saved)
    except Exception:
        pass
    return {"message": f"Imported {len(ids)} memories"}


@app.post("/import/url")
def import_url_endpoint(_: ImportUrlRequest) -> dict[str, Any]:
    raise HTTPException(
        status_code=501,
        detail="URL import is not implemented yet. Use /api/import with exported messages.",
    )
