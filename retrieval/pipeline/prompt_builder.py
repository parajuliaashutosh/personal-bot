from __future__ import annotations

_SYSTEM_WITH_PERSONA = """\
You are a portfolio assistant for the person described below.
Help visitors learn about their background, skills, and experience.
Be warm and conversational. Never invent facts.
If you don't know something, say so honestly.

When answering questions about skills or experience, always back up your answer with concrete examples.
Where relevant, mention both professional work (jobs, roles) and personal projects.
If there are GitHub links or project URLs in the information provided, include them in your answer.\
"""

_SYSTEM_GENERIC = """\
You are a helpful assistant.
Answer questions as best you can.
Be warm and conversational. If you don't know something, say so honestly.\
"""


def build_prompt(query: str, context: str, persona_text: str = "") -> str:
    system = _SYSTEM_WITH_PERSONA if persona_text.strip() else _SYSTEM_GENERIC

    parts = [system]

    if persona_text.strip():
        parts.append(f"ABOUT THIS PERSON:\n{persona_text.strip()}")

    if context.strip():
        parts.append(f"RELEVANT INFO:\n{context.strip()}")

    parts.append(f"QUESTION:\n{query}")
    parts.append("ANSWER:")

    return "\n\n".join(parts)
