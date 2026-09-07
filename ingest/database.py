import sqlite3

from ingest.utils import parse_course_title, extract_prereq_course_codes

SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS majors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        url TEXT
    );
    CREATE TABLE IF NOT EXISTS courses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        major_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        subject TEXT,
        course_number TEXT,
        title TEXT,
        description TEXT,
        FOREIGN KEY (major_id) REFERENCES majors(id),
        UNIQUE (major_id, name)
    );
    CREATE TABLE IF NOT EXISTS offerings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        season TEXT NOT NULL,
        link TEXT,
        FOREIGN KEY (course_id) REFERENCES courses(id),
        UNIQUE (course_id, season)
    );
    CREATE TABLE IF NOT EXISTS sections (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offering_id INTEGER NOT NULL,
        section TEXT, class_number TEXT, schedule_time TEXT,
        instructor TEXT, location TEXT, session TEXT,
        class_dates TEXT, credits TEXT, class_notes TEXT,
        pre_requisites TEXT, course_attributes TEXT,
        FOREIGN KEY (offering_id) REFERENCES offerings(id),
        UNIQUE (offering_id, section, class_number)
    );
    CREATE TABLE IF NOT EXISTS prerequisites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_id INTEGER NOT NULL,
        prereq_course_code TEXT NOT NULL,
        requirement_type TEXT,
        raw_text TEXT,
        FOREIGN KEY (course_id) REFERENCES courses(id),
        UNIQUE (course_id, prereq_course_code, raw_text)
    );
"""


def init_db(db_path="courses.db"):
    """Open a connection and ensure the schema exists.

    Hold onto the returned connection and pass it to save_records_to_sqlite
    across multiple calls (e.g. once per major) to commit incrementally, so
    progress isn't lost if a scrape is interrupted.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        An open sqlite3.Connection with the schema created.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def save_records_to_sqlite(records, conn=None, db_path="courses.db"):
    """Insert a batch of records into the database.

    Args:
        records: List of record dicts, each with major, major_url, course,
            season, link, and course_info (a {"description", "sections"} dict).
        conn: An open sqlite3.Connection (from init_db) to commit incrementally
            across multiple calls. If omitted, a connection is opened for this
            call alone and closed before returning (single-shot usage).
        db_path: Path to the SQLite database file, used only when `conn` is omitted.

    Returns:
        None.
    """
    close_when_done = conn is None
    if conn is None:
        conn = init_db(db_path)

    try:
        cur = conn.cursor()

        with conn:
            for record in records:
                major_name = record["major"]
                major_url = record.get("major_url")
                course_name = record["course"]
                season = record["season"]
                link = record["link"]
                course_info = record.get("course_info") or {}
                description = course_info.get("description")
                sections = course_info.get("sections") or []

                # insertion into majors/subjects table 
                cur.execute("INSERT OR IGNORE INTO majors (name, url) VALUES (?, ?)", (major_name, major_url))
                if major_url:
                    cur.execute(
                        "UPDATE majors SET url = ? WHERE name = ? AND url IS NULL",
                        (major_url, major_name)
                    )
                cur.execute("SELECT id FROM majors WHERE name = ?", (major_name,))
                major_id = cur.fetchone()[0]

                # insertion into courses table
                parsed_title = parse_course_title(course_name)
                subject, course_number, title = parsed_title if parsed_title else (None, None, None)

                cur.execute(
                    """INSERT OR IGNORE INTO courses
                       (major_id, name, subject, course_number, title, description)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (major_id, course_name, subject, course_number, title, description)
                )
                if description:
                    cur.execute(
                        "UPDATE courses SET description = ? WHERE major_id = ? AND name = ? AND description IS NULL",
                        (description, major_id, course_name)
                    )
                cur.execute("SELECT id FROM courses WHERE major_id = ? AND name = ?", (major_id, course_name))
                course_id = cur.fetchone()[0]

                # insertion into offerings table (ex: fall, spring, summer, or TBA/not offered)
                cur.execute(
                    """INSERT INTO offerings (course_id, season, link) VALUES (?, ?, ?)
                       ON CONFLICT (course_id, season) DO UPDATE SET link = excluded.link
                       WHERE offerings.link IS NULL AND excluded.link IS NOT NULL""",
                    (course_id, season, link)
                )
                cur.execute("SELECT id FROM offerings WHERE course_id = ? AND season = ?", (course_id, season))
                offering_id = cur.fetchone()[0]

                # insertion into course sections table
                seen_prereq_texts = set()
                for sec in sections:
                    class_number = sec.get("Class Number")
                    section_label = sec.get("Section")

                    cur.execute(
                        """INSERT OR IGNORE INTO sections
                           (offering_id, section, class_number, schedule_time, instructor,
                            location, session, class_dates, credits, class_notes,
                            pre_requisites, course_attributes)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (offering_id, section_label, class_number,
                         sec.get("Schedule/Time"), sec.get("Instructor"), sec.get("Location"),
                         sec.get("Session"), sec.get("Class Dates"), sec.get("Credits"),
                         sec.get("Class Notes"), sec.get("Pre Requisites"), sec.get("Course Attributes"))
                    )

                    # insertion into prerequisites table
                    prereq_text = sec.get("Pre Requisites")
                    if prereq_text and prereq_text not in seen_prereq_texts:
                        seen_prereq_texts.add(prereq_text)
                        for prereq_code in extract_prereq_course_codes(prereq_text):
                            cur.execute(
                                """INSERT OR IGNORE INTO prerequisites
                                   (course_id, prereq_course_code, requirement_type, raw_text)
                                   VALUES (?, ?, ?, ?)""",
                                (course_id, prereq_code, None, prereq_text)
                            )
    finally:
        if close_when_done:
            conn.close()
