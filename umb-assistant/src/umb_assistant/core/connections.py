import sqlite3
import chromadb
from umb_assistant.core.config import SQL_DB_PATH,CHROMA_PATH, COLLECTION_NAME

def get_connection():
    """Return a read-only connection to the SQLite database."""    
    conn = sqlite3.connect(f"file:{SQL_DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn

def get_chroma_collection():
    """Return a persistent Chroma collection for course embeddings."""
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )