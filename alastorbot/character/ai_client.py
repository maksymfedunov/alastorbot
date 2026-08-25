import asyncio
import logging

from google import genai

from alastorbot.character.persona import SYSTEM_PROMPT
from alastorbot.config import settings
from alastorbot.database.models import Message, UserMemory
from alastorbot.rag.retriever import Retriever

client = genai.Client(api_key=settings.GEMINI_API_KEY)
retriever = Retriever()
logger = logging.getLogger(__name__)

MAX_RETRIES = 2
RETRY_DELAY_SECONDS = 1.5


async def build_lore_context(user_message: str) -> str:
    chunks = await retriever.search(user_message, top_k=4)
    lore_parts = [f"[{chunk['book']}]\n{chunk['text']}" for chunk in chunks]
    return "\n\n---\n\n".join(lore_parts)


def build_memory_context(user_facts: list[UserMemory]) -> str:
    if not user_facts:
        return "Ты пока ничего не запомнил об этом собеседнике — это ваш первый значимый разговор."
    facts_text = "\n".join(f"- {fact.fact}" for fact in user_facts)
    return f"То, что ты помнишь об этом собеседнике:\n{facts_text}"


def build_history_contents(history: list[Message]) -> list[dict]:
    role_map = {"user": "user", "assistant": "model"}
    return [
        {"role": role_map[m.role], "parts": [{"text": m.content}]}
        for m in history
    ]


class QuotaExceededError(Exception):
    """Raised specifically when Gemini's request quota is exhausted —
    as opposed to other transient errors, this won't resolve with a
    few retries; the message needs to wait for the quota to reset."""


async def gemini_answer(
    user_message: str,
    history: list[Message],
    user_facts: list[UserMemory],
) -> str:
    lore_context = await build_lore_context(user_message)
    memory_context = build_memory_context(user_facts)

    full_system_prompt = f"""{SYSTEM_PROMPT}

# Фрагменты из твоей истории (используй как память о своём прошлом,
# не пересказывай дословно, а отвечай так, будто это твои воспоминания)

{lore_context}

# Память об этом собеседнике

{memory_context}
"""

    contents = build_history_contents(history) + [
        {"role": "user", "parts": [{"text": user_message}]}
    ]

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            response = await client.aio.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config={"system_instruction": full_system_prompt},
            )
            return response.text
        except Exception as e:
            last_error = e
            # Quota errors won't fix themselves by retrying a few
            # seconds later — fail fast instead of wasting retries.
            if "RESOURCE_EXHAUSTED" in str(e):
                raise QuotaExceededError(str(e)) from e
            logger.warning(f"Gemini call attempt {attempt} failed: {e}")
            if attempt <= MAX_RETRIES:
                await asyncio.sleep(RETRY_DELAY_SECONDS * attempt)

    raise last_error
