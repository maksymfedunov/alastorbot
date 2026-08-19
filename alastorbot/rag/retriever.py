import json
from pathlib import Path

import faiss
import numpy as np
from google import genai

from alastorbot.config import settings

EMBEDDINGS_PATH = Path("data/vector_store/embeddings.npy")
METADATA_PATH = Path("data/vector_store/metadata.jsonl")
INDEX_PATH = Path("data/vector_store/index.faiss")

EMBEDDING_MODEL = "gemini-embedding-001"
OUTPUT_DIMENSIONALITY = 768


def build_index() -> None:
    """
    Builds a FAISS index on top of the already-computed embeddings.npy
    and saves it to disk. Run once after embeddings.py.
    """
    embeddings = np.load(EMBEDDINGS_PATH).astype("float32")
    

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_PATH))
    print(f"Index built: {index.ntotal} vectors -> {INDEX_PATH}")


class Retriever:
    """
    Loads the pre-built FAISS index and metadata once at startup.
    Query vectorization now happens via the Gemini Embedding API
    (a network call) instead of a local model — search() is async
    because of that.
    """

    def __init__(self) -> None:
        self.index = faiss.read_index(str(INDEX_PATH))
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> list[dict]:
        metadata = []
        with METADATA_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                metadata.append(json.loads(line))
        return metadata

    async def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Returns the top_k most relevant chunks for the query — a list
        of dicts with book, chunk_index, and text fields.
        """
        result = await self.client.aio.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=query,
            config={
                "task_type": "RETRIEVAL_QUERY",  # asymmetric to RETRIEVAL_DOCUMENT above
                "output_dimensionality": OUTPUT_DIMENSIONALITY,
            },
        )
        query_vector = np.array([result.embeddings[0].values], dtype="float32")
        faiss.normalize_L2(query_vector)

        _, indices = self.index.search(query_vector, top_k)

        return [self.metadata[i] for i in indices[0]]


if __name__ == "__main__":
    build_index()