import os

from ingest.scraper import UNDERGRADUATE_URL, build_session, scrape_all_majors
from ingest.scraper import INGEST_DIR


def main():
    session = build_session()
    total = len(scrape_all_majors(UNDERGRADUATE_URL, session))

    progress_file = os.path.join(INGEST_DIR, "scraped_majors.txt")
    if os.path.exists(progress_file):
        with open(progress_file) as f:
            done = sum(1 for line in f if line.strip())
    else:
        done = 0

    summary = f"Progress: {done}/{total} majors scraped"
    print(summary)

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        with open(step_summary, "a") as f:
            f.write(summary + "\n")


if __name__ == "__main__":
    main()
