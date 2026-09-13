from google import genai
from dotenv import load_dotenv
import os
import sqlite3
import chromadb

load_dotenv()



UNDERGRADUATE_URL = "https://courses.umb.edu/course_catalog/listing/ugrd"
GRADUATE_URL = "https://courses.umb.edu/course_catalog/listing/grd"


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SQL_DB_PATH = os.path.join(ROOT_DIR, "data", "courses.db")
CHROMA_PATH = os.path.join(ROOT_DIR, "data", "chroma_db")
CHECKPOINT_PATH = os.path.join(ROOT_DIR, "pipeline", "scraping", "scraped_majors.txt")
COLLECTION_NAME = "courses"
EMBEDDING_MODEL = "gemini-embedding-001"

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set.")

client = genai.Client(api_key=GEMINI_API_KEY)


def get_connection():
    """Return a read-only connection to the SQLite database."""
    conn = sqlite3.connect(f"file:{SQL_DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn

def get_chroma_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection(
        COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

