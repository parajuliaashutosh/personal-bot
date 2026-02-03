# FastAPI Personal Chatbot (Model-Agnostic)

## Features

- FastAPI
- uv package manager
- Local LLM via Ollama
- OpenAI-ready (plug & play)
- Streaming responses (SSE)
- Rate limiting
- RAG memory with Chroma

## Setup

```bash
curl -Ls https://astral.sh/uv/install.sh | sh
uv venv
source .venv/bin/activate
uv pip install -r pyproject.toml
```

## Run

```bash
uvicorn app.main:app --reload
```

## data to ingest

Replace your personal data (PDFs, text files, etc.) in the `data/`. Donot use json files inside data

## Ingest personal data

```bash
python -m app.memory.ingest
```

## Environment Variables

Data
