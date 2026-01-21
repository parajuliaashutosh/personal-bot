from typing import Optional
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from app.config import get_llm
from app.memory.vector import VectorStore

router = APIRouter()
limiter = Limiter(key_func=lambda req: req.client.host)


llm = get_llm()
memory = VectorStore()


def classify_query_intent(query: str) -> str:
    """Determine what the user is asking about"""
    query_lower = query.lower()

    # Professional experience keywords
    if any(word in query_lower for word in [
        "work", "job", "professional", "company", "employer",
        "experience", "career", "position", "role", "working"
    ]):
        return "professional_experience"

    # Personal projects keywords
    elif any(word in query_lower for word in [
        "project", "built", "created", "developed", "github",
        "personal project", "side project"
    ]):
        return "personal_projects"

    # Education keywords
    elif any(word in query_lower for word in [
        "education", "school", "college", "degree", "university",
        "gpa", "graduated", "study", "studied"
    ]):
        return "education"

    # Skills/technical keywords
    elif any(word in query_lower for word in [
        "skill", "technology", "tech stack", "programming",
        "language", "framework", "know", "familiar"
    ]):
        return "skills"

    return "general"


def get_enhanced_context(query: str, memory: VectorStore, k: int = 5) -> str:
    """Get context with intent-based filtering"""
    intent = classify_query_intent(query)

    print(f"🎯 Detected intent: {intent}")

    # Try filtered search first
    if intent != "general":
        context = memory.search(
            query,
            k=k,
            filter_metadata={"type": intent}
        )

        # If filtered search returns nothing, fall back to general search
        if not context or len(context.strip()) < 50:
            print(f"⚠️  Filtered search empty, falling back to general search")
            context = memory.search(query, k=k)
    else:
        context = memory.search(query, k=k)

    return context


def build_system_prompt(context: str, query: str) -> str:
    """Build a better system prompt based on query type"""
    intent = classify_query_intent(query)

    base_prompt = (
        "You are Aashutosh's personal assistant AI. "
        "Your job is to represent Aashutosh professionally and accurately.\n\n"
    )

    # Intent-specific instructions
    if intent == "professional_experience":
        specific_instruction = (
            "The user is asking about Aashutosh's professional work experience. "
            "Focus on his roles at companies (HamroPatro Inc., Information Care Pvt. Ltd.), "
            "his responsibilities, achievements, and technologies used in professional settings. "
            "Do NOT mention personal/side projects unless specifically asked.\n\n"
        )
    elif intent == "personal_projects":
        specific_instruction = (
            "The user is asking about Aashutosh's personal projects. "
            "Focus on side projects like FastAPI Chatbot, Charitable, Discuss Forum, etc. "
            "Include GitHub links and technologies used.\n\n"
        )
    elif intent == "education":
        specific_instruction = (
            "The user is asking about Aashutosh's educational background. "
            "Provide details about his schools, college, degrees, and grades.\n\n"
        )
    else:
        specific_instruction = ""

    return (
        f"{base_prompt}"
        f"{specific_instruction}"
        f"**Available Information:**\n{context}\n\n"
        f"**Important Rules:**\n"
        f"1. Answer ONLY based on the information provided above\n"
        f"2. If the answer is not in the information, say: 'I don't have that information'\n"
        f"3. Be concise and natural - avoid bullet points unless asked\n"
        f"4. Speak in first person as if you ARE Aashutosh (use 'I' not 'he')\n"
        f"5. Be professional but conversational\n"
    )


@router.post("/chat")
# @limiter.limit("10/minute")
async def chat(request: Request, payload: dict):
    query = payload["message"]

    # Get enhanced context with intent detection
    context = get_enhanced_context(query, memory, k=5)

    print("=" * 60)
    print(f"📝 Query: {query}")
    print(f"🔍 Context retrieved:\n{context[:200]}...")  # Print first 200 chars
    print("=" * 60)

    # Build better system prompt
    system_prompt = build_system_prompt(context, query)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query},
    ]

    reply = await llm.chat(messages)

    return {
        "reply": reply,
        "debug": {  # Optional: remove in production
            "intent": classify_query_intent(query),
            "context_length": len(context)
        }
    }


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
