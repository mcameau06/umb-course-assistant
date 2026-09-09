# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Stage 1 of a larger project: an AI course-advising chatbot for UMB (UMass Boston) students, ultimately delivered as a website. Its primary feature is letting a student upload their course audit and get matched to courses that still satisfy their remaining distribution/gen-ed requirements; it also supports general course questions. This repo currently implements the ingest stage — scraping the UMB course catalog (https://courses.umb.edu/course_catalog/) into a local SQLite database.

Planned downstream stages (not yet built):

2. **Vector DB** — embed course data (Gemini embeddings) and store it in Chroma, run in embedded/persistent mode alongside the backend (no separate service to host).
3. **Audit parsing** — accept an uploaded course audit and use an LLM (Gemini) to extract completed courses / remaining requirements from it.
4. **Matching/recommendation logic** — cross-reference the parsed audit against the catalog (vector DB + structured distribution-requirement data) to find courses satisfying remaining requirements, and answer general course questions.
5. **Backend API** — FastAPI, tying ingest data, the vector DB, audit parsing, and matching logic together into endpoints for the frontend.
6. **Frontend** — React app for uploading audits and viewing recommendations.

Stages 3 and 4 may end up merged into a single audit-to-recommendations pipeline depending on implementation. Note: the scraped catalog data may not include real distribution-requirement tags yet (the `Course Attributes` field seen so far only carries course-material-cost notes) — this needs verifying across more majors, and a separate UMB data source for distribution requirements may be needed before stage 4 can work.

## Setup and commands

```bash
python -m venv myenv && source myenv/bin/activate
pip install -r requirements.txt

# Run the scraper (from repo root — ingest/ is a package, run as a module)
python -m ingest.scraper --level ugrd          # undergrad only (default)
python -m ingest.scraper --level both --max-majors 1   # quick test run
```

Key `scraper.py` flags: `--level {ugrd,grd,both}`, `--max-majors N`, `--db-path`, `--progress-file`, `--sleep-offering`, `--sleep-course`, `--log-level`. `--db-path`/`--progress-file` default to `ingest/courses.db`/`ingest/scraped_majors.txt` regardless of cwd.

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

`ingest/` is a Python package (`ingest/__init__.py`); `scraper.py` and `database.py` import sibling modules via absolute package paths (`from ingest.utils import ...`), so run everything from the repo root as `python -m ingest.scraper`, and future components (vector DB, chatbot) can do `from ingest.database import ...` the same way.
