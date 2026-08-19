import json
import time
from pathlib import Path

import numpy as np
from google import genai
from google.genai import errors

from alastorbot.config import settings


CHUNKS_PATH = Path("data/chunks.jsonl")
EMBEDDINGS_PATH = Path("data/vector_store/embeddings.npy")
METADATA_PATH = Path("data/vector_store/metadata.jsonl")
CHECKPOINT_PATH = Path("data/vector_store/embeddings_checkpoint.npy")

EMBEDDING_MODEL = "gemini-embedding-001"
OUTPUT_DIMENSIONALITY = 768

BATCH_SIZE = 10

# Pause between successful API requests.
# We deliberately keep this fairly large because Gemini
# may return 429 RESOURCE_EXHAUSTED after several requests.
REQUEST_DELAY = 10

# Maximum number of retries for one batch.
MAX_RETRIES = 8

# Initial retry delay after 429.
INITIAL_RETRY_DELAY = 10


def load_chunks() -> list[dict]:
    chunks = []

    with CHUNKS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            chunks.append(json.loads(line))

    return chunks


def save_checkpoint(vectors: list[list[float]]) -> None:
    """
    Save embeddings generated so far.

    This allows the script to continue from the last successful
    batch instead of starting from zero after an error.
    """
    if not vectors:
        return

    array = np.array(vectors, dtype="float32")

    CHECKPOINT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    np.save(CHECKPOINT_PATH, array)

    print(
        f"  checkpoint saved: "
        f"{len(vectors)} vectors"
    )


def load_checkpoint(
    total_chunks: int,
) -> list[list[float]]:
    """
    Load previously generated embeddings if a checkpoint exists.
    """
    if not CHECKPOINT_PATH.exists():
        return []

    checkpoint = np.load(CHECKPOINT_PATH)

    if checkpoint.ndim != 2:
        print("  Invalid checkpoint. Starting from zero.")
        return []

    if checkpoint.shape[1] != OUTPUT_DIMENSIONALITY:
        print(
            "  Checkpoint has wrong dimensionality: "
            f"{checkpoint.shape[1]} "
            f"(expected {OUTPUT_DIMENSIONALITY})."
        )
        return []

    if len(checkpoint) > total_chunks:
        print(
            "  Checkpoint contains more vectors "
            "than there are chunks. Starting from zero."
        )
        return []

    print(
        f"  Loaded checkpoint: "
        f"{len(checkpoint)}/{total_chunks} vectors"
    )

    return checkpoint.tolist()


def embed_batch(
    client: genai.Client,
    texts: list[str],
) -> list[list[float]]:
    """
    Generate embeddings for one batch.

    Handles temporary 429 RESOURCE_EXHAUSTED errors
    with exponential backoff.
    """

    retry_delay = INITIAL_RETRY_DELAY

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            result = client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=texts,
                config={
                    "task_type": "RETRIEVAL_DOCUMENT",
                    "output_dimensionality": OUTPUT_DIMENSIONALITY,
                },
            )

            return [
                embedding.values
                for embedding in result.embeddings
            ]

        except errors.ClientError as exc:
            if exc.code != 429:
                raise

            print(
                f"  429 RESOURCE_EXHAUSTED "
                f"(attempt {attempt}/{MAX_RETRIES})"
            )

            if attempt == MAX_RETRIES:
                raise

            print(
                f"  Waiting {retry_delay}s before retry..."
            )

            time.sleep(retry_delay)

            retry_delay *= 2

    raise RuntimeError(
        "Failed to generate embeddings."
    )


def normalize_embeddings(
    embeddings: np.ndarray,
) -> np.ndarray:
    """
    Normalize vectors for cosine similarity.

    After normalization, cosine similarity can be calculated
    using FAISS inner product.
    """

    norms = np.linalg.norm(
        embeddings,
        axis=1,
        keepdims=True,
    )

    # Protect against division by zero.
    norms = np.maximum(norms, 1e-12)

    return embeddings / norms


def save_final_embeddings(
    chunks: list[dict],
    vectors: list[list[float]],
) -> None:
    """
    Normalize and save final embeddings and metadata.
    """

    embeddings = np.array(
        vectors,
        dtype="float32",
    )

    if embeddings.shape != (
        len(chunks),
        OUTPUT_DIMENSIONALITY,
    ):
        raise ValueError(
            "Embedding shape mismatch: "
            f"{embeddings.shape}. "
            f"Expected "
            f"({len(chunks)}, "
            f"{OUTPUT_DIMENSIONALITY})."
        )

    embeddings = normalize_embeddings(
        embeddings
    )

    EMBEDDINGS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    np.save(
        EMBEDDINGS_PATH,
        embeddings,
    )

    with METADATA_PATH.open(
        "w",
        encoding="utf-8",
    ) as f:
        for chunk in chunks:
            f.write(
                json.dumps(
                    chunk,
                    ensure_ascii=False,
                )
                + "\n"
            )

    print()
    print(
        f"Saved: {EMBEDDINGS_PATH} "
        f"(shape={embeddings.shape})"
    )

    print(
        f"Metadata: {METADATA_PATH}"
    )


def build_embeddings() -> None:
    chunks = load_chunks()

    print(
        f"Loaded chunks: {len(chunks)}"
    )

    client = genai.Client(
        api_key=settings.GEMINI_API_KEY
    )

    vectors = load_checkpoint(
        total_chunks=len(chunks)
    )

    start_index = len(vectors)

    if start_index == len(chunks):
        print(
            "All embeddings already exist "
            "in checkpoint."
        )

        save_final_embeddings(
            chunks,
            vectors,
        )

        CHECKPOINT_PATH.unlink(
            missing_ok=True
        )

        return

    if start_index > 0:
        print(
            f"Resuming from chunk "
            f"{start_index}/{len(chunks)}"
        )

    for start in range(
        start_index,
        len(chunks),
        BATCH_SIZE,
    ):
        batch = chunks[
            start:start + BATCH_SIZE
        ]

        texts = [
            chunk["text"]
            for chunk in batch
        ]

        print(
            f"  embedding "
            f"{start + 1}-"
            f"{min(start + BATCH_SIZE, len(chunks))}"
            f"/{len(chunks)}..."
        )

        batch_vectors = embed_batch(
            client,
            texts,
        )

        if len(batch_vectors) != len(batch):
            raise RuntimeError(
                "Gemini returned an unexpected "
                "number of embeddings: "
                f"{len(batch_vectors)} "
                f"for {len(batch)} texts."
            )

        vectors.extend(
            batch_vectors
        )

        processed = len(vectors)

        print(
            f"  embedded "
            f"{processed}/{len(chunks)}"
        )

        # Save progress after EVERY successful batch.
        save_checkpoint(vectors)

        # Wait between successful requests.
        if processed < len(chunks):
            print(
                f"  waiting {REQUEST_DELAY}s..."
            )
            time.sleep(REQUEST_DELAY)

    save_final_embeddings(
        chunks,
        vectors,
    )

    # Checkpoint is no longer needed.
    CHECKPOINT_PATH.unlink(
        missing_ok=True
    )

    print()
    print("Embedding generation complete.")


if __name__ == "__main__":
    build_embeddings()