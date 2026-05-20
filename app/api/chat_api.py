from typing import Optional
from urllib import response
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config.llm_factory import get_llm
from app.memory.vector import VectorStore
from app.schema.chat_schema import ChatRequest
from app.schema.response_schema import APIResponse
from app.service.chat_service import ChatService

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


llm = get_llm()
memory = VectorStore()
chat_service = ChatService()


@router.post("/chat")
@limiter.limit("5/minute")
async def chat(request: Request, payload: ChatRequest):
    try:
        query = payload.message

        # Use the service
        context = chat_service.get_enhanced_context(query)
        system_prompt = chat_service.build_system_prompt(context, query)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query},
        ]

        reply = await llm.chat(messages)
        return APIResponse.success_response(
            message="Chat response generated successfully",
            data={"reply": reply},
            status_code=200
        )
    except ValueError as e:
        print("Value error in chat:", e)
        # Bad request - client error
        return APIResponse.error_response(
            message=f"Invalid request: {str(e)}",
            data=None,
            status_code=400
        )

    except RuntimeError as e:
        print("Runtime error in chat:", e)
        # Check if this is a PyTorch memory error
        if "out of memory" in str(e).lower() or "requires more system memory" in str(e).lower():
            return APIResponse.error_response(
                message="Server is under heavy load. Please try again in a few minutes.",
                data=None,
                status_code=503  # 503 = Service Unavailable
            )

        # Otherwise, treat as generic runtime error
        return APIResponse.error_response(
            message="Oops! Something went wrong. Please try again later.",
            data=None,
            status_code=500
        )

    except Exception as e:
        print("Error in chat:", e)
        if "requires more system memory" in str(e).lower() or "requires more system memory" in str(e).lower():
            return APIResponse.error_response(
                message="Server is under heavy load. Please try again in a few minutes.",
                data=None,
                status_code=503  # 503 = Service Unavailable
            )

        # Internal server error
        return APIResponse.error_response(
            message=f"Oops! Something went wrong. Please try again later.",
            data=None,
            status_code=500
        )


@router.post("/chat/stream")
@limiter.limit("5/minute")
async def chat_stream(request: Request, payload: ChatRequest):
    try:
        query = payload.message

        # Use the service
        response = chat_service.stream_chat(query)

        return StreamingResponse(response, media_type="text/event-stream")

    except ValueError as e:
        print("Value error in chat stream:", e)
        # Bad request - client error
        return APIResponse.error_response(
            message=f"Invalid request: {str(e)}",
            data=None,
            status_code=400
        )

    except RuntimeError as e:
        print("Runtime error in chat stream:", e)
        # Check if this is a PyTorch memory error
        if "out of memory" in str(e).lower() or "requires more system memory" in str(e).lower():
            return APIResponse.error_response(
                message="Server is under heavy load. Please try again in a few minutes.",
                data=None,
                status_code=503  # 503 = Service Unavailable
            )

        # Otherwise, treat as generic runtime error
        return APIResponse.error_response(
            message="Oops! Something went wrong. Please try again later.",
            data=None,
            status_code=500
        )

    except Exception as e:
        print("Error in chat stream:", e)
        # Internal server error
        if "requires more system memory" in str(e).lower() or "requires more system memory" in str(e).lower():
            return APIResponse.error_response(
                message="Server is under heavy load. Please try again in a few minutes.",
                data=None,
                status_code=503  # 503 = Service Unavailable
            )

        return APIResponse.error_response(
            message=f"Oops! Something went wrong. Please try again later.",
            data=None,
            status_code=500
        )
