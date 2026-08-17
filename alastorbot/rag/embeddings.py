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
    Reads chunks from data/chunks.jsonl, turns each into a vector,
    and saves:
        - embeddings.npy   — the vectors themselves (for FAISS)
        - metadata.jsonl   — which vector maps to which chunk
                              (by line index, same order)
    """
    chunks = load_chunks()
    print(f"Loaded chunks: {len(chunks)}")

    model = SentenceTransformer(MODEL_NAME)

    # The e5 model requires indexed texts to be prefixed with
    # "passage: " and search queries with "query: ". Skipping this
    # prefix noticeably hurts search quality — it's how the model
    # was trained to tell indexed content apart from queries.
    texts = [f"passage: {chunk['text']}" for chunk in chunks]

    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        normalize_embeddings=True,  # required for cosine similarity in FAISS
    )

    EMBEDDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.save(EMBEDDINGS_PATH, embeddings)

    with METADATA_PATH.open("w", encoding="utf-8") as f:
        for chunk in chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print(f"Saved: {EMBEDDINGS_PATH} (shape={embeddings.shape})")
    print(f"Metadata: {METADATA_PATH}")


if __name__ == "__main__":
    build_embeddings()