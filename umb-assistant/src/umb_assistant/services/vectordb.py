"""Semantic search over the courses Chroma collection."""

from google.genai import types

from umb_assistant.core.config import client as CLIENT, EMBEDDING_MODEL
from umb_assistant.core.connections import get_chroma_collection

def embed_query(query_text) -> list[float]:
    """Embed a query string for semantic search."""
    response = CLIENT.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query_text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )

    return response.embeddings[0].values


def search_courses(query_text, n_results=5, where=None, chroma_path=None) -> list[dict]:
    """Semantically search course descriptions.

    `where` is an optional Chroma metadata filter, e.g. {"level": "ugrd"} or
    {"major": "Computer Science"}.

    Returns a list of {id, document, metadata, distance} dicts, nearest match first.
    """
    query_embedding = embed_query(query_text)

    collection = get_chroma_collection()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
    )

    if not results["ids"] or not results["ids"][0]:
        return []

    return [
        {"id": id_, "document": document, "metadata": metadata, "distance": distance}
        for id_, document, metadata, distance in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]
