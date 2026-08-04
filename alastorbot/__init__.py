"""
AlastorBot — Telegram-бот с AI-персонажем Аластера Роули.

Пакет разбит по зонам ответственности:
    bot/        — приём и отправка сообщений в Telegram (aiogram)
    database/   — модели и доступ к SQLite (SQLAlchemy)
    character/  — логика персонажа и обращение к Claude API
    rag/        — поиск по книгам (chunking, эмбеддинги, FAISS)
    memory/     — память о конкретных пользователях
"""