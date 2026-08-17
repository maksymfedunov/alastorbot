"""
Database layer (SQLAlchemy 2 + SQLite).

Contains:
    models.py       — table definitions (users, message history, etc.)
    engine.py        — database connection and session creation
    repositories.py  — read/write functions that hide SQL details
                        from the rest of the code

This module must not know anything about Telegram or Gemini — it
only stores and returns data.
"""