"""
AHTN vector search — query the AHTN database for HS code classification.

Requires running: python -m scripts.pillar2.build_ahtn_vector_db first.
"""

import json
import os
from pathlib import Path

import numpy as np
from openai import OpenAI

from app.pillar2.query_expansion import expand_query

# Use text-embedding-3-large for higher Sim (requires rebuild with same model)
EMBEDDING_MODEL = os.getenv("AHTN_EMBEDDING_MODEL", "text-embedding-3-small")

# Pillar2 data lives in backend/data/pillar2/
_BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = _BACKEND_DIR / "data" / "pillar2"
EMBEDDINGS_PATH = DATA_DIR / "ahtn_embeddings.npy"
METADATA_PATH = DATA_DIR / "ahtn_metadata.json"


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two vectors."""
    a_norm = np.linalg.norm(a)
    b_norm = np.linalg.norm(b)
    if a_norm == 0 or b_norm == 0:
        return 0.0
    return float(np.dot(a, b) / (a_norm * b_norm))


def search_ahtn(
    query: str,
    top_k: int = 5,
    openai_api_key: str | None = None,
    expand: bool = True,
) -> list[dict]:
    """
    Search AHTN database for product descriptions matching the query.

    Args:
        query: Product description (e.g. "leather handbag" or "chocolate biscuits")
        top_k: Number of results to return
        openai_api_key: OpenAI API key (or set OPENAI_API_KEY env var)

    Returns:
        List of dicts with ahtn_code, description, heading, rate, similarity
    """
    api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY required for embedding the query")

    if not EMBEDDINGS_PATH.exists() or not METADATA_PATH.exists():
        raise FileNotFoundError(
            "AHTN vector DB not found. Run: python -m scripts.pillar2.build_ahtn_vector_db"
        )

    # Expand query with synonyms to improve similarity
    search_text = expand_query(query) if expand else query

    embeddings = np.load(EMBEDDINGS_PATH)
    with open(METADATA_PATH, encoding="utf-8") as f:
        metadata = json.load(f)

    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=search_text,
    )
    query_embedding = np.array(response.data[0].embedding, dtype=np.float32)

    similarities = np.array([
        _cosine_similarity(query_embedding, embeddings[i])
        for i in range(len(metadata))
    ])
    top_indices = np.argsort(similarities)[::-1][:top_k]

    results = []
    for idx in top_indices:
        r = metadata[idx].copy()
        r["similarity"] = float(similarities[idx])
        results.append(r)
    return results
