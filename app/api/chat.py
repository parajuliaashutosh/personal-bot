from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from app.config import get_llm
from app.memory.vector import VectorStore

router = APIRouter()
limiter = Limiter(key_func=lambda req: req.client.host)

llm = get_llm()
memory = VectorStore()

@router.post("/chat")
# @limiter.limit("10/minute")
async def chat(request: Request, payload: dict):
    query = payload["message"]
    context = memory.search(query)

    print(context, "See waht the context is")
    # Strict instruction: answer only from personal data
    system_prompt = (
        "You are a personal assistant. "
        "Answer ONLY based on the user’s personal info below. "
        "If the answer is not in the info, reply: 'I don't know.'\n\n"
        f"User info:\n{context}"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]
    reply = await llm.chat(messages)
    return {"reply": reply}


@router.post("/chat/stream")
# @limiter.limit("5/minute")
async def chat_stream(request: Request, payload: dict):
    query = payload["message"]
    context = memory.search(query)

    messages = [
        {"role": "system", "content": "You are my personal assistant."},
        {"role": "system", "content": f"User info:\n{context}"},
        {"role": "user", "content": query},
    ]

    async def generator():
        async for token in llm.stream(messages):
            yield f"data: {token}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
