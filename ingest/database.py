import sqlite3

def save_records_to_sqlite(all_records, db_path="courses.db"):
    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA foreign_keys = ON")

        cur.executescript("""
            CREATE TABLE IF NOT EXISTS majors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                url TEXT
            );
            CREATE TABLE IF NOT EXISTS courses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                major_id INTEGER NOT NULL,
                name TEXT NOT NULL,
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
                UNIQUE (offering_id, class_number)
            );
        """)

        with conn:
            for record in all_records:
                major_name = record["major"]
                major_url = record.get("major_url")
                course_name = record["course"]
                season = record["season"]
                link = record["link"]
                course_info = record.get("course_info") or {}
                description = course_info.get("description")
                sections = course_info.get("sections") or []

                # major (get-or-create)
                cur.execute("INSERT OR IGNORE INTO majors (name, url) VALUES (?, ?)", (major_name, major_url))
                if major_url:
                    cur.execute(
                        "UPDATE majors SET url = ? WHERE name = ? AND url IS NULL",
                        (major_url, major_name)
                    )
                cur.execute("SELECT id FROM majors WHERE name = ?", (major_name,))
                major_id = cur.fetchone()[0]

                # course (get-or-create; update description if we now have one)
                cur.execute(
                    "INSERT OR IGNORE INTO courses (major_id, name, description) VALUES (?, ?, ?)",
                    (major_id, course_name, description)
                )
                if description:
                    cur.execute(
                        "UPDATE courses SET description = ? WHERE major_id = ? AND name = ? AND description IS NULL",
                        (description, major_id, course_name)
                    )
                cur.execute("SELECT id FROM courses WHERE major_id = ? AND name = ?", (major_id, course_name))
                course_id = cur.fetchone()[0]

                # offering (get-or-create; fill in a link that was previously missing)
                cur.execute(
                    """INSERT INTO offerings (course_id, season, link) VALUES (?, ?, ?)
                       ON CONFLICT (course_id, season) DO UPDATE SET link = excluded.link
                       WHERE offerings.link IS NULL AND excluded.link IS NOT NULL""",
                    (course_id, season, link)
                )
                cur.execute("SELECT id FROM offerings WHERE course_id = ? AND season = ?", (course_id, season))
                offering_id = cur.fetchone()[0]

                # sections (deduped on offering_id + class_number)
                for sec in sections:
                    cur.execute(
                        """INSERT OR IGNORE INTO sections
                           (offering_id, section, class_number, schedule_time, instructor,
                            location, session, class_dates, credits, class_notes,
                            pre_requisites, course_attributes)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (offering_id, sec.get("Section"), sec.get("Class Number"),
                         sec.get("Schedule/Time"), sec.get("Instructor"), sec.get("Location"),
                         sec.get("Session"), sec.get("Class Dates"), sec.get("Credits"),
                         sec.get("Class Notes"), sec.get("Pre Requisites"), sec.get("Course Attributes"))
                    )
    finally:
        conn.close()
