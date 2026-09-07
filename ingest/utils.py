from bs4 import NavigableString, Tag

WANTED_FIELDS = [
    "Section", "Class Number", "Schedule/Time", "Instructor", "Location",
    "Session", "Class Dates", "Credits", "Class Notes",
    "Pre Requisites", "Course Attributes",
]

def extract_description(main_div):
    """Extract the course description text from the body-content div.
    Handles both formats: description alone, or description followed
    by other fields (Pre Requisites, etc.) in the same <p> tag."""

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
    """Extract course description and sections from the course page."""
    main_div = course_page.find('div', id='body-content')
    
    description = extract_description(main_div) 
    sections = extract_sections(main_div)
    
    return {
        "description": description,
        "sections": sections
    }


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