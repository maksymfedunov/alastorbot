"""
AlastorBot — a Telegram bot with an AI character, Alastor Rowley.

The package is split by area of responsibility:
    bot/        — receiving and sending Telegram messages (aiogram)
    database/   — models and access to SQLite (SQLAlchemy)
    character/  — character logic and calls to the Gemini API
    rag/        — search over the book lore (chunking, embeddings, FAISS)
    memory/     — memory about individual users
"""