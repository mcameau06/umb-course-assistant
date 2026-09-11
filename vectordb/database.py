"""Read-only access to ingest/courses.db for the vector-DB embedding pipeline."""

import os
import re
import sqlite3

NAME_PATTERN = re.compile(r"^(\S+)\s+(\S+)\s+(.+)$")

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "ingest", "courses.db")


def get_connection(db_path=None):
    """Return a read-only connection to the SQLite database."""
    path = db_path or DEFAULT_DB_PATH
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    return conn


def get_courses_for_embedding(db_path=None):
    """Return one row per course with a non-empty description, joined to its major.

    Each row: {id, major, subject, course_number, title, description}.
    """
    conn = get_connection(db_path)
    try:
        cur = conn.execute(
            """
            SELECT courses.id, courses.name, majors.name AS major, courses.subject,
                   courses.course_number, courses.title, courses.description
            FROM courses
            JOIN majors ON majors.id = courses.major_id
            WHERE courses.description IS NOT NULL AND TRIM(courses.description) != ''
            """
        )
        return [_fill_missing_fields(dict(row)) for row in cur.fetchall()]
    finally:
        conn.close()


def _fill_missing_fields(course):
    """Recover subject/course_number/title from `name` when the scraper failed to parse them.

    A handful of courses (irregular numbering like "227GL", "114QR") have NULL
    subject/course_number/title even though `name` itself has the full "SUBJECT NUMBER Title" text.
    """
    if course["subject"] and course["course_number"] and course["title"]:
        return course

    match = NAME_PATTERN.match(course["name"] or "")
    if not match:
        return course

    subject, course_number, title = match.groups()
    course["subject"] = course["subject"] or subject
    course["course_number"] = course["course_number"] or course_number
    course["title"] = course["title"] or title
    return course


def course_level(course_number):
    """"ugrd" or "grd" based on the numeric prefix of course_number (>=500 = grad)."""
    match = re.match(r"\d+", course_number or "")
    if not match:
        return None
    return "grd" if int(match.group()) >= 500 else "ugrd"
