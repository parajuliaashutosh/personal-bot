from json import load
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import os
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("X_API_KEY")

class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only protect POST requests
        if request.method == "POST":
            api_key = request.headers.get("x-api-key")
            if not api_key or api_key != API_KEY:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid or missing API key"}
                )

        return await call_next(request)
