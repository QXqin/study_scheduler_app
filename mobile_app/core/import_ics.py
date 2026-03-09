import yaml
from datetime import datetime
try:
    from ics import Calendar
except ImportError:
    pass

def parse_ics_text(ics_text: str) -> list:
    """Parses raw ICS strings and returns a list of dictionary classes"""
    cal = Calendar(ics_text)
    fixed_classes = []
    classes_dict = {}
    weekdays_zh = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

    for event in cal.events:
        local_begin = event.begin.to('Asia/Shanghai')
        local_end = event.end.to('Asia/Shanghai')
        day_str = weekdays_zh[local_begin.weekday()]
        time_str = f"{local_begin.format('HH:mm')}-{local_end.format('HH:mm')}"
        course_info = event.name
        if event.location:
             course_info += f" ({event.location})"
        start_date_str = local_begin.format('YYYY-MM-DD')
        end_date_str = start_date_str
        if hasattr(event, 'extra') or hasattr(event, '_unused'):
            raw_lines = str(event).split('\n')
            for line in raw_lines:
                if line.startswith('RRULE:'):
                    if 'UNTIL=' in line:
                        until_part = line.split('UNTIL=')[1].split(';')[0]
                        end_date_str = f"{until_part[:4]}-{until_part[4:6]}-{until_part[6:8]}"
                    break
        unique_key = f"{day_str}_{time_str}_{course_info}"
        if unique_key not in classes_dict:
            classes_dict[unique_key] = {"day": day_str, "time": time_str, "course": course_info, "active_dates": []}
        date_range = f"{start_date_str} 至 {end_date_str}"
        if date_range not in classes_dict[unique_key]["active_dates"]:
            classes_dict[unique_key]["active_dates"].append(date_range)
            
    for key, val in classes_dict.items():
        val["active_dates"] = "，".join(val["active_dates"])
        fixed_classes.append(val)
        
    day_order = {day: i for i, day in enumerate(weekdays_zh)}
    fixed_classes.sort(key=lambda x: (day_order[x['day']], x['time']))
    return fixed_classes
