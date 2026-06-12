# AllyAI 🧠

A privacy-focused AI assistant with persistent memory, semantic retrieval, and conversation understanding.

AllyAI remembers important facts across conversations using local storage and vector embeddings, allowing the assistant to provide personalized and context-aware responses without requiring retraining.

---

## Features

### Persistent Memory

* Stores important user facts locally
* Automatically extracts relevant information from conversations
* Memory survives across sessions

### Semantic Retrieval (RAG)

* Uses ChromaDB as a vector database
* Retrieves only relevant memories instead of injecting the entire profile
* Improves response quality and scalability

### AI Chat

* Supports multiple LLM providers
* Integrated with Groq for fast inference
* Easily extendable to OpenRouter, Gemini, or other APIs

### Conversation Management

* Save conversations
* Delete conversations
* View conversation history
* Import external conversations

### Memory Vault

* View stored memories
* Delete specific memories
* Semantic search across memories

### Local-First Architecture

* SQLite for structured storage
* ChromaDB for vector search
* Sentence Transformers for embeddings

---

# Tech Stack

## Backend

* FastAPI
* Python 3.11+

## AI & Retrieval

* Groq API
* Sentence Transformers
* ChromaDB
* RAG (Retrieval-Augmented Generation)

## Database

* SQLite

## Frontend

* HTML
* CSS
* JavaScript

---

# Project Structure

```bash
AllyAI/
│
├── backend/
│   ├── main.py
│   ├── retrieval.py
│   ├── extraction.py
│   ├── profile_store.py
│   ├── prompt_builder.py
│   ├── importer.py
│   └── llm_client.py
│
├── frontend/
│   └── index.html
│
├── chroma_db/
│
├── .env
├── .env.example
├── pyproject.toml
└── README.md
```

---

# Installation

## 1. Clone Repository

```bash
git clone https://github.com/REVAPANDE/AllyAI.git

cd AllyAI
```

---

## 2. Create Virtual Environment

### Windows

```bash
python -m venv .venv

.venv\Scripts\activate
```

### Linux / Mac

```bash
python3 -m venv .venv

source .venv/bin/activate
```

---

## 3. Install Poetry

```bash
pip install poetry
```

---

## 4. Install Dependencies

```bash
poetry install
```

---

## 5. Configure Environment Variables

Create a `.env` file:

```env
GROQ_API_KEY=your_groq_api_key

GOOGLE_API_KEY=

OPENROUTER_API_KEY=

NVIDIA_API_KEY=
```

---

# Running Locally

Start the FastAPI server:

```bash
py -3.11 -m poetry run uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

or

```bash
poetry run uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

---

# Deployment

## Railway

Start Command:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

Environment Variables:

```env
GROQ_API_KEY=your_key
```

---

## Render

Build Command:

```bash
pip install poetry && poetry config virtualenvs.create false && poetry install --no-root
```

Start Command:

```bash
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
```

---

# How Memory Works

1. User sends a message.
2. AllyAI extracts potential facts.
3. Facts are stored in SQLite.
4. Facts are embedded using Sentence Transformers.
5. Embeddings are stored in ChromaDB.
6. On future messages:

   * Relevant memories are retrieved semantically.
   * Retrieved memories are injected into the system prompt.
   * The LLM generates a personalized response.

---

# Example

User:

```text
My name is Aryan.
```

Stored Memory:

```text
Name is Aryan
```

Later:

```text
Who am I?
```

Response:

```text
You're Aryan.
```

without requiring the user to repeat information.

---

# Future Improvements

* User authentication
* Multi-user memory isolation
* Long-term memory ranking
* Memory editing interface
* File uploads
* PDF knowledge ingestion
* Agent workflows
* LangGraph integration
* Cloud database support

---

# Author

**Aryan Soni**

B.Tech 

IIT Roorkee

Built as a personal AI memory assistant exploring:

* RAG
* Vector Databases
* LLM Integration
* Semantic Search
* Persistent Memory Systems

