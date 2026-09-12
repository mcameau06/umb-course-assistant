"""Shared Chroma/Gemini setup used by both the embedding pipeline and query side."""

import os

import chromadb
from dotenv import load_dotenv

VECTORDB_DIR = os.path.dirname(__file__)
CHROMA_PATH = os.path.join(VECTORDB_DIR, "chroma_db")
COLLECTION_NAME = "courses"
EMBEDDING_MODEL = "gemini-embedding-001"

load_dotenv(os.path.join(VECTORDB_DIR, ".env"))


def get_collection(chroma_path=None):
    client = chromadb.PersistentClient(path=chroma_path or CHROMA_PATH)
    return client.get_or_create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )



def resolve_api_key(api_key=None):
    resolved = api_key or os.environ.get("GEMINI_API_KEY")
    if not resolved:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to vectordb/.env or export it in your shell "
            "before running this command."
        )
    return resolved
