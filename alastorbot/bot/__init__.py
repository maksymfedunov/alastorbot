"""
Telegram layer (aiogram).

This is the only place in the project that knows Telegram exists.
This module must not call the Gemini API or the database directly —
it delegates to functions from character/ and database/.
"""

from alastorbot.bot.handlers import router

__all__ = ["router"]