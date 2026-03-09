import re
from datetime import datetime


def parse_ics_text(ics_text: str) -> list:
    """
    Parses raw ICS text using pure Python regex (no external ics library).
    Returns a list of dictionaries representing fixed classes.
    """
    weekdays_zh = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    classes_dict = {}

    # Split into VEVENT blocks
    events = re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", ics_text, re.DOTALL)

    for event_text in events:
        # Extract fields
        summary_match = re.search(r"SUMMARY:(.*)", event_text)
        dtstart_match = re.search(r"DTSTART(?:;[^:]*)?:(\d{8}T\d{6})", event_text)
        dtend_match = re.search(r"DTEND(?:;[^:]*)?:(\d{8}T\d{6})", event_text)
        location_match = re.search(r"LOCATION:(.*)", event_text)
        rrule_match = re.search(r"RRULE:(.*)", event_text)

        if not summary_match or not dtstart_match:
            continue

        course_name = summary_match.group(1).strip()
        dtstart_str = dtstart_match.group(1).strip()

        try:
            dt_start = datetime.strptime(dtstart_str, "%Y%m%dT%H%M%S")
        except ValueError:
            continue

        dt_end = None
        if dtend_match:
            try:
                dt_end = datetime.strptime(dtend_match.group(1).strip(), "%Y%m%dT%H%M%S")
            except ValueError:
                pass

        day_str = weekdays_zh[dt_start.weekday()]
        time_start = dt_start.strftime("%H:%M")
        time_end = dt_end.strftime("%H:%M") if dt_end else ""
        time_str = f"{time_start}-{time_end}" if time_end else time_start

        course_info = course_name
        if location_match:
            loc = location_match.group(1).strip()
            if loc:
                course_info += f" ({loc})"

        start_date_str = dt_start.strftime("%Y-%m-%d")
        end_date_str = start_date_str

        # Try to extract UNTIL from RRULE
        if rrule_match:
            rrule_text = rrule_match.group(1)
            until_match = re.search(r"UNTIL=(\d{8})", rrule_text)
            if until_match:
                until_str = until_match.group(1)
                end_date_str = f"{until_str[:4]}-{until_str[4:6]}-{until_str[6:8]}"

        unique_key = f"{day_str}_{time_str}_{course_info}"
        if unique_key not in classes_dict:
            classes_dict[unique_key] = {
                "day": day_str,
                "time": time_str,
                "course": course_info,
                "active_dates": [],
            }
        date_range = f"{start_date_str} 至 {end_date_str}"
        if date_range not in classes_dict[unique_key]["active_dates"]:
            classes_dict[unique_key]["active_dates"].append(date_range)

    fixed_classes = []
    for key, val in classes_dict.items():
        val["active_dates"] = "，".join(val["active_dates"])
        fixed_classes.append(val)

    day_order = {day: i for i, day in enumerate(weekdays_zh)}
    fixed_classes.sort(key=lambda x: (day_order.get(x["day"], 99), x["time"]))
    return fixed_classes
