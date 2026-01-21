from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from app.config import get_llm
from app.memory.vector import VectorStore
from app.service.chat_service import ChatService

router = APIRouter()
limiter = Limiter(key_func=lambda req: req.client.host)


llm = get_llm()
memory = VectorStore()
chat_service = ChatService()

@router.post("/chat")
async def chat(payload: dict):
    query = payload["message"]
    
    # Use the service
    context = chat_service.get_enhanced_context(query)
    system_prompt = chat_service.build_system_prompt(context, query)
    
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
