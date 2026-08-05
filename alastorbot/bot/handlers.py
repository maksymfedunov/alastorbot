from aiogram import Router
from aiogram.types import Message

from alastorbot.character.ai_client import gemini_answer

router = Router()


@router.message()
async def echo(message: Message):
    response = await gemini_answer(message.text)
    await message.answer(response)