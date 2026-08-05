import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

EMBEDDINGS_PATH = Path("data/vector_store/embeddings.npy")
METADATA_PATH = Path("data/vector_store/metadata.jsonl")
INDEX_PATH = Path("data/vector_store/index.faiss")

MODEL_NAME = "intfloat/multilingual-e5-large"


def build_index() -> None:
    """
    Строит FAISS-индекс поверх уже готовых embeddings.npy
    и сохраняет его на диск. Запускается один раз после
    embeddings.py (и заново — при пересборе лора).
    """
    embeddings = np.load(EMBEDDINGS_PATH).astype("float32")

    # IndexFlatIP — точный поиск по скалярному произведению.
    # Векторы уже нормализованы (normalize_embeddings=True на
    # этапе Embeddings), поэтому скалярное произведение эквивалентно
    # косинусной близости. "Flat" означает точный перебор без
    # аппроксимации — для 1223 векторов это доли миллисекунды,
    # приближённые индексы (IVF, HNSW) имели бы смысл на десятках
    # тысяч+ векторов, но не здесь.
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_PATH))
    print(f"Индекс построен: {index.ntotal} векторов -> {INDEX_PATH}")


class Retriever:
    """
    Загружает готовый индекс и метаданные один раз при старте бота,
    дальше отвечает на запросы `search()` без повторной загрузки —
    это важно, чтобы каждое сообщение пользователя не тянуло
    заново модель эмбеддингов и индекс с диска.
    """

    def __init__(self) -> None:
        self.index = faiss.read_index(str(INDEX_PATH))
        self.model = SentenceTransformer(MODEL_NAME)
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> list[dict]:
        metadata = []
        with METADATA_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                metadata.append(json.loads(line))
        return metadata

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Возвращает top_k наиболее релевантных чанков для запроса —
        список словарей с полями book, chunk_index, text.
        """
        # Префикс "query: " — обязателен для e5, симметричен
        # префиксу "passage: " на этапе индексации.
        query_vector = self.model.encode(
            [f"query: {query}"],
            normalize_embeddings=True,
        ).astype("float32")

        _, indices = self.index.search(query_vector, top_k)

        return [self.metadata[i] for i in indices[0]]


if __name__ == "__main__":
    build_index()