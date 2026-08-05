import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

CHUNKS_PATH = Path("data/chunks.jsonl")
EMBEDDINGS_PATH = Path("data/vector_store/embeddings.npy")
METADATA_PATH = Path("data/vector_store/metadata.jsonl")

MODEL_NAME = "intfloat/multilingual-e5-large"


def load_chunks() -> list[dict]:
    chunks = []
    with CHUNKS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))
    return chunks


def build_embeddings() -> None:
    """
    Читает чанки из data/chunks.jsonl, превращает каждый в вектор
    и сохраняет:
        - embeddings.npy   — сами векторы (для FAISS на следующем этапе)
        - metadata.jsonl   — какой вектор какому чанку соответствует
                              (по индексу строки, тот же порядок)
    """
    chunks = load_chunks()
    print(f"Загружено чанков: {len(chunks)}")

    model = SentenceTransformer(MODEL_NAME)

    # У модели e5 есть требование: тексты для индексации нужно
    # префиксовать "passage: ", а поисковые запросы — "query: ".
    # Без этого префикса качество поиска заметно хуже — так модель
    # обучена различать, что индексируется, а что ищется.
    texts = [f"passage: {chunk['text']}" for chunk in chunks]

    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        normalize_embeddings=True,  # нормализация нужна для косинусной близости в FAISS
    )

    EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.save(EMBEDDINGS_PATH, embeddings)

    with METADATA_PATH.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"Сохранено: {EMBEDDINGS_PATH} (shape={embeddings.shape})")
    print(f"Метаданные: {METADATA_PATH}")


if __name__ == "__main__":
    build_embeddings()