"""
Telegram-слой (aiogram).

Здесь и только здесь проект знает о существовании Telegram.
Этот модуль не должен обращаться к Claude API или к базе данных
напрямую — вызывает функции из character/ и database/.
"""

from alastorbot.bot.handlers import router

__all__ = ["router"]