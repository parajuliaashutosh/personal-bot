from fastapi import FastAPI, Request
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from fastapi.openapi.utils import get_openapi

from app.api.chat_api import router as chat_router
from app.middleware.apikey_middleware import APIKeyMiddleware
from app.schema.response_schema import APIResponse

limiter = Limiter(key_func=get_remote_address)
load_dotenv()

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

app = FastAPI(
    title="Aashutosh Personal's Personal Bot API",
    description="API with X-API-Key authentication",
    version="1.0.0",
    # Add OpenAPI security scheme for X-API-Key header
    openapi_tags=[],
    swagger_ui_parameters={
        "persistAuthorization": True,
        "syntaxHighlight": False
    }
)

app.state.limiter = limiter

# Custom OpenAPI schema to add X-API-Key header


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema["components"]["securitySchemes"] = {
        "APIKeyHeader": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    openapi_schema["security"] = [{"APIKeyHeader": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi
app.add_middleware(APIKeyMiddleware)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return APIResponse.error_response(
        message="Rate limit exceeded. Please slow down and try again later.",
        data={"retry_after": str(exc.detail)},
        status_code=429
    )

origins = os.getenv("ALLOWED_ORIGINS", "").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
