"""
Book lore search (RAG).

Contains:
    chunking.py    — splitting the .docx books into chunks
    embeddings.py  — turning chunks into vectors (sentence-transformers)
    retriever.py   — searching relevant chunks via a FAISS index

This module is only responsible for finding matching pieces of text
from the books. It does not decide how they're used in a reply —
that's character/'s job.
"""