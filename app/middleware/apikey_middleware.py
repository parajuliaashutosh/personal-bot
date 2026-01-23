from json import load
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os
from dotenv import load_dotenv
from app.schema.response_schema import APIResponse

load_dotenv()
API_KEY = os.getenv("X_API_KEY")
NON_BROWSER_KEY = os.getenv("NON_BROWSER_KEY")


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only protect POST requests
        if request.method == "POST":
            api_key = request.headers.get("x-api-key")
            user_agent = request.headers.get("user-agent", "")

            if not api_key or api_key != API_KEY:
                return APIResponse.error_response(
                    message="Invalid or missing chat API key",
                    data=None,
                    status_code=401
                )

            if "mozilla" not in user_agent.lower():
                api_key_2 = request.headers.get("x-non-browser-key")
                if not api_key_2 or api_key_2 != NON_BROWSER_KEY:
                    return APIResponse.error_response(
                        message="Invalid or missing non-browser API key",
                        data=None,
                        status_code=401
                    )

        return await call_next(request)
