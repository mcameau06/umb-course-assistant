"""Semantic search over the courses Chroma collection."""

from google import genai
from google.genai import types

from vectordb.client import EMBEDDING_MODEL, get_collection, resolve_api_key


def embed_query(query_text, client):
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=query_text,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY"),
    )
    return response.embeddings[0].values


def search_courses(query_text, n_results=5, where=None, chroma_path=None, api_key=None):
    """Semantically search course descriptions.

    `where` is an optional Chroma metadata filter, e.g. {"level": "ugrd"} or
    {"major": "Computer Science"}.

    Returns a list of {id, document, metadata, distance} dicts, nearest match first.
    """
    genai_client = genai.Client(api_key=resolve_api_key(api_key))
    query_embedding = embed_query(query_text, genai_client)

    collection = get_collection(chroma_path)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where,
    )

    return [
        {"id": id_, "document": document, "metadata": metadata, "distance": distance}
        for id_, document, metadata, distance in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]
