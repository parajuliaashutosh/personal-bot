from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentStatus(str, Enum):
    pending = "pending"
    processing = "processing"
    ready = "ready"
    rejected = "rejected"


# ── Ingestion ─────────────────────────────────────────────────────────────────

class IngestRequest(BaseModel):
    file_path: str


class DocumentOut(BaseModel):
    id: uuid.UUID
    sha256: str
    filename: str
    file_path: str
    status: DocumentStatus
    rejection_reason: str | None = None
    page_count: int | None = None
    processed_at: datetime | None = None


class ChunkMetadata(BaseModel):
    section_path: list[str] = Field(default_factory=list)
    page_start: int | None = None
    page_end: int | None = None
    token_count: int | None = None
    keywords: list[str] = Field(default_factory=list)
    language: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


# ── Session / Memory ──────────────────────────────────────────────────────────

class SessionCreate(BaseModel):
    user_agent: str | None = None
    ip: str | None = None


class SessionOut(BaseModel):
    id: uuid.UUID
    created_at: datetime


class MessageCreate(BaseModel):
    session_id: uuid.UUID
    role: str  # "user" | "assistant"
    content: str
    retrieved_chunk_ids: list[uuid.UUID] = Field(default_factory=list)
    rerank_scores: dict[str, Any] | None = None


# ── Retrieval ─────────────────────────────────────────────────────────────────

class QueryRequest(BaseModel):
    session_id: uuid.UUID
    query: str
    document_id: uuid.UUID | None = None


class QueryResponse(BaseModel):
    answer: str
    session_id: uuid.UUID
    retrieved_chunk_ids: list[uuid.UUID] = Field(default_factory=list)
    low_confidence: bool = False
