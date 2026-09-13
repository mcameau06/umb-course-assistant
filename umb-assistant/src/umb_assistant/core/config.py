from google import genai
from dotenv import load_dotenv
import os

load_dotenv()

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
SQL_DB_PATH = os.path.join(ROOT_DIR, "data", "courses.db")
CHROMA_PATH = os.path.join(ROOT_DIR, "data", "chroma_db")
COLLECTION_NAME = "courses"
EMBEDDING_MODEL = "gemini-embedding-001"


GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Add it to the .env file at the project root "
        "or export it in your shell before running this app."
    )

client = genai.Client(api_key=GEMINI_API_KEY)
