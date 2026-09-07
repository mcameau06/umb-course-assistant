# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Stage 1 of a larger project: an AI course-advising chatbot for UMB (UMass Boston) students. This repo currently implements the ingest stage — scraping the UMB course catalog (https://courses.umb.edu/course_catalog/) into a local SQLite database.

Planned downstream stages (not yet built): loading catalog data (courses, descriptions, prerequisites) into a vector database, and a chatbot that takes a student's course audit as input, figures out which courses they still need, and answers questions/gives recommendations based on retrieved catalog data.

## Setup and commands

```bash
python -m venv myenv && source myenv/bin/activate
pip install -r requirements.txt

# Run the scraper (from ingest/)
cd ingest
python scraper.py --level ugrd          # undergrad only (default)
python scraper.py --level both --max-majors 1   # quick test run
```

Key `scraper.py` flags: `--level {ugrd,grd,both}`, `--max-majors N`, `--db-path`, `--progress-file`, `--sleep-offering`, `--sleep-course`, `--log-level`.

There is no test suite, linter, or build step configured in this repo yet.

`scraper.ipynb` is a notebook used for interactive/exploratory development of the same scraping logic in `scraper.py` / `utils.py`.

## Architecture

Everything below describes `ingest/`, which today is the entire repo — but it is only the scraping/ingest component of the larger chatbot project described above. The vector DB and chatbot layers will be added to this same repo as new top-level components alongside `ingest/`, not in `ingest/` itself.

The scraping pipeline has three stages, chained in `scraper.py:main()`:

1. **`scrape_all_majors`** — fetch a catalog listing page (ugrd or grd) and extract the list of majors (name + URL).
2. **`scrape_major_courses`** — for one major, fetch its page and build `{course_name: {season: link}}` (a course may have no link, e.g. "TBA").
3. **`scrape_course_sections`** — walk that structure, fetching each course-offering page via `get_course_data` → `extract_course_info` (in `utils.py`), which parses out the course description and a per-section table (`WANTED_FIELDS`: Section, Class Number, Schedule/Time, Instructor, Location, Session, Class Dates, Credits, Class Notes, Pre Requisites, Course Attributes).

Records flow into `database.py:save_records_to_sqlite`, which upserts across four related tables: `majors` → `courses` → `offerings` → `sections`, plus a `prerequisites` table populated by regex-extracting course codes (`extract_prereq_course_codes`) out of each section's free-text "Pre Requisites" field.

**Resumability**: scraping the full catalog is slow (rate-limited via `sleep_secs` between requests) and can be interrupted. `scraped_majors.txt` (the `--progress-file`) records completed major URLs via `load_completed_majors`/`mark_major_completed`, so a re-run skips majors already scraped. `save_records_to_sqlite` is called once per major with a shared `conn`, committing incrementally so partial progress isn't lost. Within a run, `course_page_cache` (in `scrape_course_sections`) avoids re-fetching a course page when the same link appears under multiple season offerings.

**HTML parsing is brittle by nature**: `scrape_major_courses` and `utils.extract_description`/`extract_sections` depend on specific CSS classes and DOM structure on courses.umb.edu (e.g. `showHideList`, `class-info-rows`, `body-content`). If scraping starts returning empty results, the site's markup has likely changed — check these selectors first.

`database.py` and `utils.py` are imported by bare module name (`from utils import ...`), so `scraper.py` must be run with `ingest/` as the working directory / on the path (as the `cd ingest` in the run command above does).
