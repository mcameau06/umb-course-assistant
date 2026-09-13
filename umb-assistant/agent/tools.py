import sqlite3
from typing import Optional

from pipeline.vectordb.utils import DEFAULT_DB_PATH
from services.query import search_courses



def get_course_prerequisites(subject: str, course_number: str) -> dict:
  """Fetch verified prerequisites and corequisites for a specific course code (e.g. 'CS', '240').

  Use this whenever a student asks about requirements, eligibility, or
  prerequisites for a specific course.
  """
  conn = sqlite3.connect(f"file:{DEFAULT_DB_PATH}?mode=ro", uri=True)
  conn.row_factory = sqlite3.Row
  try:
    cur = conn.execute(
        """
            SELECT c.subject, c.course_number, c.title,
                   GROUP_CONCAT(DISTINCT p.prereq_course_code) AS prereq_codes,
                   GROUP_CONCAT(DISTINCT p.raw_text) AS raw_requirements
            FROM courses c
            LEFT JOIN prerequisites p ON c.id = p.course_id
            WHERE UPPER(c.subject) = UPPER(?) AND UPPER(c.course_number) = UPPER(?)
            GROUP BY c.id
        """,
        (subject.strip(), course_number.strip()),
    )
    row = cur.fetchone()
    if not row:
      return {"error": f"No course found for {subject} {course_number}"}
    return dict(row)
  finally:
    conn.close()


def get_course_schedule(
    subject: str, course_number: str, season: Optional[str] = None
) -> list[dict]:
  """Fetch class sections, times, professors, locations, and credits for a specific course.

  Optional season filters like 'Fall 2026' or 'Summer 2026'.
  """
  conn = sqlite3.connect(f"file:{DEFAULT_DB_PATH}?mode=ro", uri=True)
  conn.row_factory = sqlite3.Row
  try:
    query = """
            SELECT o.season, s.section, s.instructor, s.schedule_time, s.location, s.credits, s.class_notes
            FROM courses c
            JOIN offerings o ON c.id = o.course_id
            JOIN sections s ON o.id = s.offering_id
            WHERE UPPER(c.subject) = UPPER(?) AND UPPER(c.course_number) = UPPER(?)
        """
    params = [subject.strip(), course_number.strip()]
    if season:
      query += " AND o.season LIKE ?"
      params.append(f"%{season.strip()}%")

    cur = conn.execute(query, params)
    rows = cur.fetchall()
    return (
        [dict(r) for r in rows]
        if rows
        else [{"message": "No active sections found."}]
    )
  finally:
    conn.close()



def search_course_catalog(client,query: str) -> list[dict]:
  """Perform semantic search over catalog descriptions when the student is exploring topics,
    fields of study, careers, or electives without naming a specific course

    args:
        query: The query strings.
    returns:
        A list of course dictionaries with keys: {id, major, subject, course_number, title, description}.
  """
  return search_courses(client,query, n_results=2)