from bs4 import BeautifulSoup
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import time
import argparse
import logging
import os
from ingest.utils import extract_course_info
from ingest.database import init_db, save_records_to_sqlite

UNDERGRADUATE_URL = "https://courses.umb.edu/course_catalog/listing/ugrd"
GRADUATE_URL = "https://courses.umb.edu/course_catalog/listing/grd"

INGEST_DIR = os.path.dirname(os.path.abspath(__file__))

HEADERS = {'User-Agent': 'UMB-CoursePlanner (student course-planning project)'}

logger = logging.getLogger(__name__)


def build_session(headers=HEADERS, retries=3, backoff_factor=1.0):
    """Build a requests.Session that automatically retries server errors
    and connection failures with exponential backoff.

    Args:
        headers: Request headers to attach to every call made with this session.
        retries: Max number of retry attempts for a failed request.
        backoff_factor: Multiplier controlling the delay between retries.

    Returns:
        A requests.Session configured with a retrying HTTPAdapter.
    """
    session = requests.Session()
    session.headers.update(headers)

    retry = Retry(
        total=retries,
        connect=retries,
        read=retries,
        status=retries,
        backoff_factor=backoff_factor,
        status_forcelist=(500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


def request_page(url, session):
    """Fetch a URL and parse it into a BeautifulSoup document.

    Args:
        url: The page URL to fetch.
        session: The requests.Session to make the request with.

    Returns:
        A BeautifulSoup document, or None if the request failed.
    """
    try:
        response = session.get(url)
        response.raise_for_status()  
        return BeautifulSoup(response.content, 'lxml')
    except requests.RequestException as e:
        logger.error(f"Error occurred while fetching {url}: {e}")
        return None


def get_course_data(link, session, sleep_secs=2):
    """Fetch a course page and extract its description and section info.

    Args:
        link: URL of the course page, or None if no page is available.
        session: The requests.Session to make the request with.
        sleep_secs: Seconds to sleep before the request, to rate-limit the site.

    Returns:
        A dict with "description" and "sections" keys, or None if `link`
        is None or the page could not be fetched.
    """
    if link is None:
        return None

    time.sleep(sleep_secs)
    course_page = request_page(link, session)

    if not course_page:
        return None

    return extract_course_info(course_page)


def scrape_all_majors(school_url, session):
    """Extract all majors listed on a school's catalog page.

    Args:
        school_url: URL of the school's catalog listing page.
        session: The requests.Session to make the request with.

    Returns:
        A list of {"name": str, "url": str} dicts, one per major. Empty
        if the page couldn't be fetched or has no majors list.
    """
    school_page = request_page(school_url, session)

    if school_page is None:
        return []

    majors = []

    content = school_page.find("div", class_="unit-70 content")
    if content is None:
        return []

    for major in content.find_all("li"):
        link = major.find("a")

        if link is None:
            continue

        majors.append({
            "name": " ".join(link.get_text(" ", strip=True).split()),
            "url": link["href"],
        })

    return majors


def scrape_major_courses(major, session, sleep_secs=3):
    """Fetch a single major's page and collect its courses and offerings.

    Args:
        major: A {"name": str, "url": str} dict identifying the major.
        session: The requests.Session to make the request with.
        sleep_secs: Seconds to sleep before the request, to rate-limit the site.

    Returns:
        A dict mapping course name to a dict of {season: link}, e.g.
        {"AF 210 Financial Accounting": {"Fall 2026": link, ...}}. Empty
        if the major's page couldn't be fetched.
    """
    major_name = major["name"]
    major_url = major["url"]

    time.sleep(sleep_secs)

    logger.info(f"Major: {major_name}, URL: {major_url}")
    major_page = request_page(major_url, session)

    if not major_page:
        logger.warning(f"Skipping {major_name} due to failed page request.")
        return {}

    courses_list = major_page.find_all(
        "ul",
        class_="showHideList"
    )[0].find_all("li", recursive=False)

    courses_dict = {}
    for course in courses_list:
        course_name = (
            course.find("h4")
            .get_text()
            .split("+")[0]
            .replace("\xa0\xa0", " ")
            .strip()
        )

        logger.debug(f"Course Name: {course_name}")
        offering_list = course.find(
            "ul",
            class_="course-info-listing-padding-bottom"
        )

        if offering_list is None:
            courses_dict[course_name] = {"TBA": None}
            continue

        offering_links = offering_list.find_all("a")
        offering_dict = {}

        if not offering_links:
            logger.debug(f"No offerings found for {course_name}.")
            courses_dict[course_name] = {"TBA": None}
            continue

        else:
            for offering_link in offering_links:
                link = offering_link["href"]
                season = offering_link.get_text()
                offering_dict[season] = link

            courses_dict[course_name] = offering_dict

    return courses_dict


def scrape_course_sections(major_name, courses, session, sleep_secs=2, course_page_cache=None):
    """Walk one major's courses -> offerings structure, fetching course data.

    Args:
        major_name: Name of the major these courses belong to.
        courses: Dict of {course_name: {season: link}}, as returned by scrape_major_courses.
        session: The requests.Session to make requests with.
        sleep_secs: Seconds to sleep before each course-page request.
        course_page_cache: Dict mapping a course link to its already-extracted
            course_info. If a course has multiple offerings pointing at the
            identical link (e.g. cross-listed seasons), it's only downloaded
            and parsed once. Mutated in place; pass the same dict across
            calls to share the cache across majors.

    Returns:
        A flat list of record dicts (major, course, season, link, course_info)
        for this major.
    """
    if course_page_cache is None:
        course_page_cache = {}

    records = []

    logger.info(f"Major: {major_name}")
    for course_name, offerings in courses.items():
        logger.debug(f"  Course: {course_name}")
        for season, link in offerings.items():

            if link is None:
                logger.debug(f"    Offering: {season}, No link available.")
                records.append({
                    "major": major_name,
                    "course": course_name,
                    "season": season,
                    "link": None,
                    "course_info": None,
                })
                continue

            if link in course_page_cache:
                logger.debug(f"    Offering: {season}, Link: {link} (cached)")
                course_info = course_page_cache[link]
            else:
                course_info = get_course_data(link, session, sleep_secs=sleep_secs)
                course_page_cache[link] = course_info
                logger.debug(f"    Offering: {season}, Link: {link}")

            records.append({
                "major": major_name,
                "course": course_name,
                "season": season,
                "link": link,
                "course_info": course_info,
            })

    return records


def load_completed_majors(progress_path):
    """Read the set of major URLs already scraped from a progress file.

    Args:
        progress_path: Path to a text file with one completed major URL
            per line. Need not exist yet.

    Returns:
        A set of major URLs that have already been scraped.
    """
    try:
        with open(progress_path) as f:
            return {line.strip() for line in f if line.strip()}
    except FileNotFoundError:
        return set()


def mark_major_completed(progress_path, major_url):
    """Append a major URL to the progress file, marking it as done.

    Args:
        progress_path: Path to the progress file.
        major_url: URL of the major that finished scraping successfully.
    """
    with open(progress_path, "a") as f:
        f.write(f"{major_url}\n")


def main():
    parser = argparse.ArgumentParser(description="Scrape the UMB course catalog into SQLite.")
    parser.add_argument("--level", choices=["ugrd", "grd", "both"], default="ugrd",
                         help="Which catalog to scrape (default: ugrd)")
    parser.add_argument("--max-majors", type=int, default=None,
                         help="Limit the number of majors scraped per catalog (default: all)")
    parser.add_argument("--db-path", default=os.path.join(INGEST_DIR, "courses.db"),
                         help="Path to the SQLite database file (default: ingest/courses.db)")
    parser.add_argument("--progress-file", default=os.path.join(INGEST_DIR, "scraped_majors.txt"),
                         help="Text file tracking completed major URLs, for resuming (default: ingest/scraped_majors.txt)")
    parser.add_argument("--sleep-offering", type=float, default=3.0,
                         help="Seconds to sleep between major-page requests (default: 3)")
    parser.add_argument("--sleep-course", type=float, default=2.0,
                         help="Seconds to sleep between course-page requests (default: 2)")
    parser.add_argument("--log-level", default="INFO",
                         help="Logging level (default: INFO)")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    urls = []
    if args.level in ("ugrd", "both"):
        urls.append(UNDERGRADUATE_URL)
    if args.level in ("grd", "both"):
        urls.append(GRADUATE_URL)

    session = build_session()
    conn = init_db(args.db_path)
    course_page_cache = {}
    completed_majors = load_completed_majors(args.progress_file)

    try:
        for url in urls:
            majors = scrape_all_majors(url, session)
            majors = [m for m in majors if m["url"] not in completed_majors]

            for count, major in enumerate(majors):
                if args.max_majors is not None and count >= args.max_majors:
                    break

                courses = scrape_major_courses(major, session, sleep_secs=args.sleep_offering)
                records = scrape_course_sections(
                    major["name"], courses, session,
                    sleep_secs=args.sleep_course, course_page_cache=course_page_cache
                )

                save_records_to_sqlite(records, conn=conn)
                mark_major_completed(args.progress_file, major["url"])
                logger.info(f"Saved {len(records)} records for {major['name']}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
