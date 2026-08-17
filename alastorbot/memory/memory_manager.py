import re

from sqlalchemy.ext.asyncio import AsyncSession

from alastorbot.database.repositories import save_memory_fact

MEMORY_PATTERN = re.compile(r"\[ЗАПОМНИТЬ:\s*(.+?)\]", re.DOTALL)


def extract_and_strip_memories(raw_reply: str) -> tuple[str, list[str]]:
    """
    Finds [ЗАПОМНИТЬ: fact] markers in the model's reply, strips them
    out of the text the user will see, and returns the extracted
    facts as a separate list.
    """
    facts = [match.strip() for match in MEMORY_PATTERN.findall(raw_reply)]
    clean_reply = MEMORY_PATTERN.sub("", raw_reply).strip()
    return clean_reply, facts


async def save_new_memories(session: AsyncSession, user_id: int, facts: list[str]) -> None:
    for fact in facts:
        await save_memory_fact(session, user_id, fact)