"""
Character logic — Alastor Rowley's "brain".

Contains:
    persona.py    — the system prompt, character canon, speech style
    ai_client.py  — calls to the LLM (currently Gemini)

This is the most important part of the project — the rest of the
modules exist to serve it. Data from rag/ (book lore) and memory/
(user memory) flows here before a reply is generated.
"""