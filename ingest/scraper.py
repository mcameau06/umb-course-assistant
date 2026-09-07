from bs4 import BeautifulSoup
import requests
import time
import argparse
from utils import extract_course_info, print_course_record
from database import save_records_to_sqlite

UNDERGRADUATE_URL = "https://courses.umb.edu/course_catalog/listing/ugrd" 
GRADUATE_URL = "https://courses.umb.edu/course_catalog/listing/grd"  

HEADERS = {'User-Agent': 'UMB-CoursePlanner (student course-planning project)'}

def request_page(url, headers=HEADERS):
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Raise an error for bad responses
        return BeautifulSoup(response.content, 'lxml')
    except requests.RequestException as e:
        print(f"Error occurred while fetching the main page: {e}")
        return None

def get_course_data(link, sleep_secs=2):
    """Fetch a course page and extract its description + section info.
    Returns None if there's no link to fetch."""
    if link is None:
        return None

    time.sleep(sleep_secs)
    course_page = request_page(link)

    if not course_page:
        return None

    return extract_course_info(course_page)


def scrape_all_majors(school_url, headers=HEADERS):
    """
    Extracts all majors from the given school page and returns a dictionary
    """
    school_page = request_page(school_url, headers=headers)

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


def scrape_course_offerings(majors, headers=HEADERS, max_majors=None, sleep_secs=3):
    """
    Extracts course offerings for each major and returns a nested dictionary
    """
    count = 0
    course_offerings = {}

    for major in majors:
        major_name = major["name"]
        major_url = major["url"]

        if max_majors is not None and count >= max_majors:
            break

        time.sleep(sleep_secs)

        print(f"Major: {major_name}, URL: {major_url}")
        major_page = request_page(major_url, headers=headers)

        if not major_page:
            print(f"Skipping {major_name} due to failed page request.")
            continue

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

            print(f"Course Name: {course_name}")
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
                print(f"No offerings found for {course_name}.")
                courses_dict[course_name] = {"TBA": None}
                continue
        
            else:
                for offering_link in offering_links:
                    link = offering_link["href"]
                    season = offering_link.get_text()
                    offering_dict[season] = link

                courses_dict[course_name] = offering_dict

        course_offerings[major_name] = courses_dict
        count += 1

    return course_offerings

def scrape_course_sections(course_offerings, max_majors=None, sleep_secs=2):
    """Walk the nested majors -> courses -> offerings structure,
    fetching and printing course data. Returns a flat list of records."""
    all_records = []
    major_count = 0

    for major_name, courses in course_offerings.items():
        if max_majors is not None and major_count >= max_majors:
            break

        print(f"Major: {major_name}")
        for course_name, offerings in courses.items():
            print(f"  Course: {course_name}")
            for season, link in offerings.items():

                if link is None:
                    print(f"    Offering: {season}, No link available.")
                    all_records.append({
                        "major": major_name,
                        "course": course_name,
                        "season": season,
                        "link": None,
                        "course_info": None,
                    })
                    continue
                
                course_info = get_course_data(link, sleep_secs=sleep_secs)
                print_course_record(major_name, course_name, season, link, course_info)

                all_records.append({
                    "major": major_name,
                    "course": course_name,
                    "season": season,
                    "link": link,
                    "course_info": course_info,
                })

        major_count += 1
        print(f"  Majors processed: {major_count}")

    return all_records

def main():
    parser = argparse.ArgumentParser(description="Scrape the UMB course catalog into SQLite.")
    parser.add_argument("--level", choices=["ugrd", "grd", "both"], default="ugrd",
                         help="Which catalog to scrape (default: ugrd)")
    parser.add_argument("--max-majors", type=int, default=None,
                         help="Limit the number of majors scraped per catalog (default: all)")
    parser.add_argument("--db-path", default="courses.db",
                         help="Path to the SQLite database file (default: courses.db)")
    parser.add_argument("--sleep-offering", type=float, default=3.0,
                         help="Seconds to sleep between major-page requests (default: 3)")
    parser.add_argument("--sleep-course", type=float, default=2.0,
                         help="Seconds to sleep between course-page requests (default: 2)")
    args = parser.parse_args()

    urls = []
    if args.level in ("ugrd", "both"):
        urls.append(UNDERGRADUATE_URL)
    if args.level in ("grd", "both"):
        urls.append(GRADUATE_URL)

    all_course_records = []
    for url in urls:
        majors = scrape_all_majors(url)
        course_offerings = scrape_course_offerings(
            majors, max_majors=args.max_majors, sleep_secs=args.sleep_offering
        )
        all_course_records += scrape_course_sections(
            course_offerings, max_majors=args.max_majors, sleep_secs=args.sleep_course
        )

    save_records_to_sqlite(all_course_records, db_path=args.db_path)

if __name__ == "__main__":
    main()