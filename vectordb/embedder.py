"""Embeds course descriptions with Gemini and upserts them into a persistent Chroma collection."""

import argparse
import logging

from google import genai
from google.genai import types

from vectordb.client import CHROMA_PATH, COLLECTION_NAME, EMBEDDING_MODEL, get_collection, resolve_api_key
from vectordb.database import DEFAULT_DB_PATH, course_level, get_courses_for_embedding

BATCH_SIZE = 100

logger = logging.getLogger(__name__)


def course_id(course):
    return f"{course['subject']} {course['course_number']}"


def embed_text(course):
    return f"{course['major']} — {course['title']}\n{course['description']}"


def embed_descriptions(texts, client):
    response = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT"),
    )
    return [embedding.values for embedding in response.embeddings]


def embed_all_courses(db_path=None, chroma_path=None, api_key=None, batch_size=BATCH_SIZE):
    """Embed every course description in the SQL DB and upsert into Chroma.

    Returns the number of courses embedded.
    """
    genai_client = genai.Client(api_key=resolve_api_key(api_key))
    collection = get_collection(chroma_path)

    courses = get_courses_for_embedding(db_path)
    logger.info("Embedding %d courses in batches of %d", len(courses), batch_size)

    for i in range(0, len(courses), batch_size):
        batch = courses[i : i + batch_size]
        texts = [embed_text(c) for c in batch]
        embeddings = embed_descriptions(texts, genai_client)
        collection.upsert(
            ids=[course_id(c) for c in batch],
            embeddings=embeddings,
            documents=texts,
            metadatas=[
                {
                    "major": c["major"],
                    "subject": c["subject"],
                    "course_number": c["course_number"],
                    "level": course_level(c["course_number"]) or "",
                }
                for c in batch
            ],
        )
        logger.info("Upserted batch %d-%d of %d", i + 1, i + len(batch), len(courses))

    return len(courses)


def main():
    parser = argparse.ArgumentParser(description="Embed course descriptions into Chroma")
    parser.add_argument("--db-path", default=DEFAULT_DB_PATH,
                         help=f"Path to the SQLite database file (default: {DEFAULT_DB_PATH})")
    parser.add_argument("--chroma-path", default=CHROMA_PATH,
                         help="Path to the persistent Chroma directory (default: vectordb/chroma_db)")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE,
                         help=f"Number of courses to embed per Gemini request (default: {BATCH_SIZE})")
    parser.add_argument("--log-level", default="INFO",
                         help="Logging level (default: INFO)")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    embedded_count = embed_all_courses(
        db_path=args.db_path, chroma_path=args.chroma_path, batch_size=args.batch_size
    )
    logger.info("Embedded %d courses into Chroma collection '%s'", embedded_count, COLLECTION_NAME)


if __name__ == "__main__":
    main()
