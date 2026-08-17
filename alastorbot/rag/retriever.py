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
    Builds a FAISS index on top of the already-computed embeddings.npy
    and saves it to disk. Run once after embeddings.py (and again
    whenever the lore is rebuilt).
    """
    embeddings = np.load(EMBEDDINGS_PATH).astype("float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_PATH))
    print(f"Index built: {index.ntotal} vectors -> {INDEX_PATH}")


class Retriever:
    """
    Loads the pre-built index and metadata once at startup, then
    answers search() calls without reloading — this matters so that
    every user message doesn't re-load the embeddings model and the
    index from disk.
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
        Returns the top_k most relevant chunks for the query — a list
        of dicts with book, chunk_index, and text fields.
        """
       
        query_vector = self.model.encode(
            [f"query: {query}"],
            normalize_embeddings=True,
        ).astype("float32")

        _, indices = self.index.search(query_vector, top_k)

        return [self.metadata[i] for i in indices[0]]


if __name__ == "__main__":
    build_index()