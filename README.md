# AlastorBot

Telegram-бот с AI-персонажем **Аластера Роули** — демона сделок и
демона перекрёстка из авторской книжной вселенной. Цель проекта —
не сложная архитектура, а убедительный, живой персонаж: пользователь
не должен ощущать, что разговаривает с ботом.

## Структура проекта
alastorbot/
├── pyproject.toml # зависимости (Poetry)
├── alembic.ini # конфиг миграций
├── .env.example # шаблон переменных окружения
├── alastorbot/
│ ├── main.py # точка входа, запуск polling
│ ├── config.py # настройки из .env (pydantic-settings)
│ ├── bot/
│ │ └── handlers.py # обработка сообщений Telegram (aiogram)
│ ├── database/
│ │ ├── models.py # SQLAlchemy-модели (User, Message, UserMemory)
│ │ ├── engine.py # подключение к SQLite
│ │ └── repositories.py # чтение/запись, дневной лимит, обрезка истории
│ ├── character/
│ │ ├── persona.py # SYSTEM_PROMPT — канон, характер, манера речи
│ │ └── ai_client.py # обращение к Gemini API + сборка контекста
│ ├── rag/
│ │ ├── chunking.py # разбиение книг на чанки
│ │ ├── embeddings.py # чанки -> векторы (multilingual-e5-large)
│ │ └── retriever.py # построение FAISS-индекса и поиск
│ └── memory/
│ └── memory_manager.py # разбор [ЗАПОМНИТЬ: ...] из ответов модели
├── alembic/versions/ # миграции БД
├── data/
│ ├── books/ # исходные .docx книги для RAG
│ ├── chunks.jsonl # чанки книг (генерируется chunking.py)
│ ├── vector_store/ # embeddings.npy, index.faiss, metadata.jsonl
  └── alastorbot.db # SQLite база (не в git)

## Установка

```bash
poetry install
cp .env.example .env
# заполните .env: BOT_TOKEN (от @BotFather) и GEMINI_API_KEY (aistudio.google.com/apikey)
```

## Подготовка лора (один раз, перед первым запуском)

Положите книги в `data/books/*.docx`, затем:

```bash
poetry run python -m alastorbot.rag.chunking
poetry run python -m alastorbot.rag.embeddings
poetry run python -m alastorbot.rag.retriever
```

## База данных

```bash
poetry run alembic upgrade head
```

## Запуск

```bash
poetry run python -m alastorbot.main
```

## Возможности

- Живой диалог в характере персонажа, без команд и меню — даже `/start`
  воспринимается как обычное сообщение
- RAG-поиск по книжному лору (FAISS + multilingual-e5-large)
- Короткая память — последние 20 сообщений диалога (старые обрезаются
  автоматически)
- Долгая память — модель сама помечает важные факты о собеседнике
  через `[ЗАПОМНИТЬ: ...]`, они сохраняются в БД и подтягиваются во
  все будущие разговоры
- Дневной лимит — 10 сообщений в сутки на пользователя
- Ретраи и fallback-ответы в характере при сбоях API
- Индикатор "печатает..." и обработка не-текстовых/слишком длинных
  сообщений

## Стек

Python 3.12+, Poetry, aiogram 3, SQLAlchemy 2 + Alembic + SQLite,
Google Gemini API, sentence-transformers, FAISS.