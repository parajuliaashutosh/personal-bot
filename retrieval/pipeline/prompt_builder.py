from __future__ import annotations

import logging
import sys
from pathlib import Path

from shared.config.settings import settings

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT_FILE = "system_persona.md"


def _load_system_prompt() -> str:
    """Read the system persona prompt from disk. Missing or empty file is fatal."""
    path = Path(settings.prompts_dir) / _SYSTEM_PROMPT_FILE

    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        logger.critical("System prompt file %s could not be read: %s", path, exc)
        sys.exit(1)

    if not text:
        logger.critical("System prompt file %s is empty", path)
        sys.exit(1)

    return text


_SYSTEM = _load_system_prompt()

_STATE_FIRST = (
    "FIRST MESSAGE — this is the opening turn. Introduce yourself in one short line, "
    "then answer."
)
_STATE_FOLLOW_UP = (
    "FOLLOW-UP — you have already introduced yourself earlier in this conversation. "
    "Do NOT greet, do NOT state your name or job title again. Answer directly."
)


def build_prompt(query: str, context: str, is_first_turn: bool = True) -> str:
    parts = [_SYSTEM]

    if context.strip():
        parts.append(f"RELEVANT INFO:\n{context.strip()}")

    parts.append(
        "CONVERSATION STATE:\n" + (_STATE_FIRST if is_first_turn else _STATE_FOLLOW_UP)
    )
    parts.append(f"QUESTION:\n{query}")
    parts.append("ANSWER:")

    return "\n\n".join(parts)
