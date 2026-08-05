from google import genai

from alastorbot.character.persona import SYSTEM_PROMPT
from alastorbot.config import settings


client = genai.Client(
    api_key=settings.GEMINI_API_KEY
)


async def gemini_answer(text):
    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=text
    )
    return response.text