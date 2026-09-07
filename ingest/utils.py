import re
from datetime import datetime

from bs4 import NavigableString, Tag

WANTED_FIELDS = [
    "Section", "Class Number", "Schedule/Time", "Instructor", "Location",
    "Session", "Class Dates", "Credits", "Class Notes",
    "Pre Requisites", "Course Attributes",
]

def extract_description(main_div):
    """Extract the course description text from the body-content div.

    Handles both formats: description alone, or description followed by
    other fields (Pre Requisites, etc.) in the same <p> tag.

    Args:
        main_div: BeautifulSoup Tag for the course page's body-content div.

    Returns:
        The description text, or None if no "Description" label is found.
    """

    desc_label = None
    for strong in main_div.find_all("strong"):
        if strong.get_text(strip=True).lower().startswith("description"):
            desc_label = strong
            break

    if not desc_label:
        return None

    parts = []
    node = desc_label.next_sibling
    while node is not None:
        if isinstance(node, Tag):
            if node.name != "br":
                break  # any tag other than <br> ends the description
                       # (next <strong> field, or an unclosed <p> spilling into <table>, etc.)
        elif isinstance(node, NavigableString):
            parts.append(str(node))
        node = node.next_sibling

    return "".join(parts).strip()



def extract_sections(main_div):
    """Extract each section's field values from the course page's table.

    Args:
        main_div: BeautifulSoup Tag for the course page's body-content div.

    Returns:
        A list of dicts, one per section, each containing every key in
        WANTED_FIELDS (empty string for any field not present).
    """
    table = main_div.find("table")
    if table is None:
        return []

    sections = []
    info_rows = table.find_all("tr", class_="class-info-rows")

    for info_row in info_rows:
        section = {}

        for td in info_row.find_all("td"):
            label = td.get("data-label")
            if label:
                section[label] = td.get_text(strip=True, separator=" ")

        extra_row = info_row.find_next_sibling("tr", class_="extra-info")
        if extra_row:
            for header_span in extra_row.select("span.class-div-header"):
                label = header_span.get_text(strip=True).rstrip(":")
                info_span = header_span.find_next_sibling("span", class_="class-div-info")
                section[label] = info_span.get_text(strip=True) if info_span else ""

        clean_section = {field: section.get(field, "") for field in WANTED_FIELDS}
        sections.append(clean_section)

    return sections

def extract_course_info(course_page):
    """Extract course description and sections from the course page.

    Args:
        course_page: BeautifulSoup document for a single course page.

    Returns:
        A dict with "description" (str or None) and "sections" (list of dicts).
    """
    main_div = course_page.find('div', id='body-content')
    
    description = extract_description(main_div) 
    sections = extract_sections(main_div)
    
    return {
        "description": description,
        "sections": sections
    }


COURSE_TITLE_RE = re.compile(r'^([A-Z]+)\s+(\d+[A-Z]?)\s+(.+)$')
PREREQ_COURSE_CODE_RE = re.compile(r'\b[A-Z]{2,6}\s+\d{3}[A-Z]?\b')
CREDIT_RANGE_RE = re.compile(r'^(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)$')
CREDIT_SINGLE_RE = re.compile(r'^(\d+(?:\.\d+)?)$')
DATE_RANGE_RE = re.compile(r'^\s*(\d{2}/\d{2}/\d{4})\s*-\s*(\d{2}/\d{2}/\d{4})\s*$')


def parse_course_title(text):
    """Parse a combined course name into its subject, number, and title.

    Args:
        text: A combined course name, e.g. "AF 210 Financial Accounting" or
            "AFRSTY 115G Black Consciousness".

    Returns:
        A (subject, course_number, title) tuple, or None if `text` doesn't
        match the expected pattern.
    """
    if not text:
        return None
    match = COURSE_TITLE_RE.match(text.strip())
    if not match:
        return None
    subject, course_number, title = match.groups()
    return subject, course_number, title.strip()


def extract_prereq_course_codes(text):
    """Pull course codes out of a free-text prerequisite statement.

    Args:
        text: A prerequisite statement, e.g. "Pre-req = AF 210 and a
            minimum of 15 credits".

    Returns:
        A list of course code strings (e.g. ["AF 210"]), possibly empty.
    """
    if not text:
        return []
    return PREREQ_COURSE_CODE_RE.findall(text)


def parse_credits(text):
    """Parse a credit string into a (min, max) range.

    Args:
        text: A credit string, either a range like "3/3" or "1/6", or a
            single value like "3".

    Returns:
        A (min, max) float tuple, or None if `text` can't be parsed.
    """
    if not text:
        return None
    text = text.strip()

    match = CREDIT_RANGE_RE.match(text)
    if match:
        return float(match.group(1)), float(match.group(2))

    match = CREDIT_SINGLE_RE.match(text)
    if match:
        value = float(match.group(1))
        return value, value

    return None


def parse_date_range(text):
    """Parse a date span into its start and end dates.

    Args:
        text: A date span, e.g. "09/08/2026 - 12/11/2026".

    Returns:
        A (start_date, end_date) tuple of ISO date strings, or (None, None)
        if `text` can't be parsed.
    """
    if not text:
        return None, None

    match = DATE_RANGE_RE.match(text)
    if not match:
        return None, None

    start = datetime.strptime(match.group(1), "%m/%d/%Y").date().isoformat()
    end = datetime.strptime(match.group(2), "%m/%d/%Y").date().isoformat()
    return start, end


def print_course_record(major_name, course_name, season, link, course_info):
    """print one course offering's extracted data."""
    print(f"    Offering: {season}, Link: {link}")
    if course_info is None:
        print("      No link available for this offering.")
        return

    print(f"      Description: {course_info.get('description', '')}")
    for section in course_info.get('sections', []):
        print(f"      Section: {section.get('Section', '')}")
        print(f"      Class Number: {section.get('Class Number', '')}")
        print(f"      Schedule/Time: {section.get('Schedule/Time', '')}")
        print(f"      Instructor: {section.get('Instructor', '')}")
        print(f"      Location: {section.get('Location', '')}")
        print(f"      Session: {section.get('Session', '')}")
        print(f"      Class Dates: {section.get('Class Dates', '')}")
        print(f"      Credits: {section.get('Credits', '')}")
        print(f"      Class Notes: {section.get('Class Notes', '')}")
        print(f"      Pre Requisites: {section.get('Pre Requisites', '')}")
        print(f"      Course Attributes: {section.get('Course Attributes', '')}")