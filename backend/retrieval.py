from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from backend.profile_store import list_facts


BASE_DIR = Path(__file__).resolve().parents[1]
CHROMA_PATH = Path(os.getenv("CHROMA_PATH", BASE_DIR / "chroma_db"))
COLLECTION_NAME = "allyai_profile"
_collection: Any | None = None
_embedder: Any | None = None
_synced_fact_ids: set[int] = set()


def _get_embedder() -> Any:
    global _embedder
    if _embedder is None:
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
        _embedder = SentenceTransformer(model_name)
    return _embedder


def _get_collection() -> Any:
    global _collection
    if _collection is None:
        import chromadb

        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        _collection = client.get_or_create_collection(name=COLLECTION_NAME)
    return _collection


def _embed(texts: list[str]) -> list[list[float]]:
    embeddings = _get_embedder().encode(texts, normalize_embeddings=True)
    return [embedding.tolist() for embedding in embeddings]


def upsert_facts_to_vector_store(facts: list[dict[str, Any]]) -> None:
    if not facts:
        return

    collection = _get_collection()
    documents = [fact["content"] for fact in facts]
    ids = [str(fact["id"]) for fact in facts]
    metadatas = [{"category": fact["category"]} for fact in facts]
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=_embed(documents),
    )


def delete_fact_from_vector_store(fact_id: int) -> None:
    try:
        _get_collection().delete(ids=[str(fact_id)])
    except Exception:
        return


def sync_vector_store() -> None:
    global _synced_fact_ids
    facts = list_facts()
    unsynced = [fact for fact in facts if int(fact["id"]) not in _synced_fact_ids]
    upsert_facts_to_vector_store(unsynced)
    _synced_fact_ids.update(int(fact["id"]) for fact in facts)


def search_memories(query: str, limit: int = 5) -> list[dict[str, Any]]:
    facts = list_facts()
    if not facts:
        return []

    try:
        results = _get_collection().query(
            query_embeddings=_embed([query]),
            n_results=min(limit, len(facts)),
        )
        documents = results.get("documents", [[]])[0]
        ids = results.get("ids", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        return [
            {
                "id": int(ids[index]),
                "content": documents[index],
                "category": metadatas[index].get("category", "history"),
                "distance": distances[index] if index < len(distances) else None,
            }
            for index in range(len(documents))
        ]
    except Exception:
        lowered = query.lower()
        matched = [
            fact
            for fact in facts
            if any(token in fact["content"].lower() for token in lowered.split())
        ]
        return matched[:limit] or facts[:limit]


def get_relevant_profile_summary(query: str, limit: int = 5) -> str:
    memories = search_memories(query, limit)
    if not memories:
        return "No saved profile facts matched this message."
    return "\n".join(f"- {memory['content']}" for memory in memories)
