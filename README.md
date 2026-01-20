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

## Ingest personal data
```bash
python app/memory/ingest.py
```

## Environment Variables
Data