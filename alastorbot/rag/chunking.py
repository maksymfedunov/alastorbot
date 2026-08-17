import json
from dataclasses import dataclass
from pathlib import Path

from docx import Document

BOOKS_DIR = Path("data/books")
CHUNKS_PATH = Path("data/chunks.jsonl")

CHUNK_SIZE_WORDS = 400
CHUNK_OVERLAP_WORDS = 80


@dataclass
class Chunk:
    book: str
    chunk_index: int
    text: str


def read_paragraphs(docx_path: Path) -> list[str]:
    """Reads a .docx file and returns non-empty paragraphs as a list of strings."""
    doc = Document(docx_path)
    return [p.text.strip() for p in doc.paragraphs if p.text.strip()]


def chunk_paragraphs(paragraphs: list[str], book_name: str) -> list[Chunk]:
    """
    Groups paragraphs into chunks of roughly CHUNK_SIZE_WORDS words,
    with an overlap of CHUNK_OVERLAP_WORDS between adjacent chunks.
    """
    chunks: list[Chunk] = []
    current_words: list[str] = []
    chunk_index = 0

    for paragraph in paragraphs:
        current_words.extend(paragraph.split())

        if len(current_words) >= CHUNK_SIZE_WORDS:
            text = " ".join(current_words)
            chunks.append(Chunk(book=book_name, chunk_index=chunk_index, text=text))
            chunk_index += 1
            current_words = current_words[-CHUNK_OVERLAP_WORDS:]

    if current_words:
        text = " ".join(current_words)
        chunks.append(Chunk(book=book_name, chunk_index=chunk_index, text=text))

    return chunks


def process_all_books() -> list[Chunk]:
    """
    Walks through all .docx files in data/books/, splits each book
    into chunks, and saves them to data/chunks.jsonl — an intermediate
    file that becomes vectors in the Embeddings step.
    """
    all_chunks: list[Chunk] = []

    for docx_path in sorted(BOOKS_DIR.glob("*.docx")):
        book_name = docx_path.stem
        paragraphs = read_paragraphs(docx_path)
        book_chunks = chunk_paragraphs(paragraphs, book_name)
        all_chunks.extend(book_chunks)
        print(f"{book_name}: {len(paragraphs)} paragraphs -> {len(book_chunks)} chunks")

    with CHUNKS_PATH.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps({
                "book": chunk.book,
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
            }, ensure_ascii=False) + "\n")

    print(f"Total chunks: {len(all_chunks)} -> saved to {CHUNKS_PATH}")
    return all_chunks


if __name__ == "__main__":
    process_all_books()