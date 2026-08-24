# Personal Bot

A RAG-powered personal portfolio chatbot. Drop in your CV/bio as a Markdown or PDF file,
edit one prompt file, and it answers questions as you — in first person.

## Prerequisites

- Python 3.11+
- PostgreSQL with the `pgvector` extension
- [uv](https://github.com/astral-sh/uv) (recommended) or pip
- A Gemini API key **or** a local [Ollama](https://ollama.com) instance

## Setup

### 1. Clone and install dependencies

```bash
git clone <your-fork-url>
cd personal-bot
uv sync          # or: pip install -e .
```

### 2. Set up PostgreSQL

Create a database and enable pgvector:

```sql
CREATE DATABASE personal_chatbot;
\c personal_chatbot
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in at minimum:

| Variable | Description |
|---|---|
| `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_NAME` | Postgres connection details |
| `GEMINI_API_KEY` | Gemini API key (skip if using Ollama) |
| `API_KEY` | Key clients send on `/chat/*` routes |
| `ADMIN_KEY` | Key for `/ingest/*` routes |

Set `LLM_PROVIDER=ollama` and configure `OLLAMA_*` vars if you prefer a local model.

### 4. Add your data

Put your CV or bio in the `data/` directory as a `.md` or `.pdf` file. The filename does not matter.

```bash
cp ~/my-cv.md data/
```

### 5. Make it *you* — edit the system prompt

**This is the one file you must edit.** `prompts/system_persona.md` is the bot's identity:
who it is, how it greets, when it deflects, plus few-shot examples showing the shape of a
good answer.

```bash
$EDITOR prompts/system_persona.md
```

Replace the `## Who I am` block (name, role, background, stack, contact) and rewrite the
answers under `## Examples` so they use *your* facts. The rule sections — identity,
greeting, scope, tooling, style — work unchanged; leave them alone unless you want
different behaviour.

Notes:

- The prompt is read once at startup. **Restart the server after editing it.**
- The file is required: if it's missing or empty the app logs the error and exits rather
  than serving a broken persona.
- Point `PROMPTS_DIR` at another directory if you keep prompts elsewhere.
- Detailed facts (dates, project links, numbers) don't belong here — they come from your
  documents in `data/` via retrieval. Keep this file to a short identity card plus rules.

### 6. Run the server

```bash
uv run uvicorn app.main:app --reload
# or without uv:
uvicorn app.main:app --reload
```

Migrations run automatically on startup. The API will be at `http://localhost:8000`.

### 7. Ingest your data

Once the server is running, trigger ingestion (requires `ADMIN_KEY`):

```bash
# Process and embed your documents
curl -X POST http://localhost:8000/ingest/reprocess \
  -H "X-API-Key: <your_admin_key>"
```

Every chat answer is grounded in the chunks retrieved from these documents.

## API

| Route | Auth | Description |
|---|---|---|
| `POST /ingest/reprocess` | `ADMIN_KEY` | Purge and re-ingest all files in `data/` |
| `POST /chat/stream` | `API_KEY` | Stream a chat response (SSE) |
| `GET /health` | none | Health check |
| `GET /docs` | none | Interactive API docs (Swagger) |

## Using Ollama instead of Gemini

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_EMBED_MODEL=nomic-embed-text
```

Pull the models before starting:

```bash
ollama pull llama3.2
ollama pull nomic-embed-text
```
