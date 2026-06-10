from __future__ import annotations

import json
import logging
import uuid
from uuid import UUID

import httpx
from asyncpg import Pool

from shared.config.settings import settings

logger = logging.getLogger(__name__)
_geo_client = httpx.AsyncClient(timeout=5.0)


def validate_session_id(session_id: str) -> bool:
    try:
        val = UUID(session_id, version=4)
        return str(val) == session_id
    except ValueError:
        return False


async def create_session(
    ip: str | None,
    user_agent: str | None,
    pool: Pool,
    ip_forwarded_for: str | None = None,
) -> UUID:
    row = await pool.fetchrow(
        "INSERT INTO sessions (ip, user_agent, ip_forwarded_for)"
        " VALUES ($1, $2, $3) RETURNING id",
        ip,
        user_agent,
        ip_forwarded_for,
    )
    return row["id"]


async def get_session(session_id: str, pool: Pool) -> dict | None:
    row = await pool.fetchrow("SELECT * FROM sessions WHERE id = $1", UUID(session_id))
    return dict(row) if row else None


async def update_last_active(session_id: str, pool: Pool) -> None:
    await pool.execute(
        "UPDATE sessions SET last_active = now() WHERE id = $1",
        UUID(session_id),
    )


async def enrich_session_geo(session_id: str, ip: str | None, pool: Pool) -> None:
    if not ip or not settings.ipinfo_api_key:
        return

    row = await pool.fetchrow(
        "SELECT geo_looked_up_at FROM sessions WHERE id = $1",
        UUID(session_id),
    )
    if row and row["geo_looked_up_at"] is not None:
        return

    try:
        resp = await _geo_client.get(
            f"https://ipinfo.io/{ip}",
            params={"token": settings.ipinfo_api_key},
        )
        resp.raise_for_status()
        data = resp.json()
        logger.info("Response from ipinfo call: %s", data)

        await pool.execute(
            "UPDATE sessions"
            " SET ip_city = $1, ip_region = $2, ip_country = $3,"
            "     ip_asn = $4, ip_timezone = $5, geo_looked_up_at = now(),"
            "     geo_raw = $6"
            " WHERE id = $7",
            data.get("city"),
            data.get("region"),
            data.get("country"),
            data.get("org"),
            data.get("timezone"),
            json.dumps(data),
            UUID(session_id),
        )
    except Exception as exc:
        logger.warning(
            "geo enrichment failed for session %s: %s", session_id, exc)
