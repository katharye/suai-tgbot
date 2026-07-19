from database.models import Schedule

DAYS_OF_WEEK = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
DAYS_TITLE = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


def week_indicator(week_type: str) -> str:
    return "🔴" if week_type == "up" else "🔵" if week_type == "down" else "⚪"


def week_label(week_type: str) -> str:
    return "нечётной" if week_type == "up" else "чётной" if week_type == "down" else "всех недель"


def _format_time(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"


def format_day_text(weekday: str, week_type: str, schedule: list[Schedule], header_prefix: str = "📅 Расписание на") -> str:
    indicator = week_indicator(week_type)

    if not schedule:
        return f"{indicator} На {weekday} пар нет 🎉"

    label = week_label(week_type)
    response = f"{indicator} {header_prefix} {weekday} ({label} неделя):\n\n"

    for lesson in sorted(schedule, key=lambda x: x.class_num):
        time_str = _format_time(lesson.start_time)
        lesson_indicator = "🟥" if lesson.week == "up" else "🟦" if lesson.week == "down" else "⬜"
        lesson_type_display = f" [{lesson.lesson_type}]" if lesson.lesson_type else ""

        response += f"{lesson_indicator} {lesson.class_num}. {lesson.subject}{lesson_type_display}\n"
        response += f"   🕐 {time_str}\n"
        response += f"   👨‍🏫 {lesson.teacher}\n"
        response += f"   🏢 {lesson.room}\n\n"

    return response


def format_week_text(week_type: str, week_schedule: dict[str, list[Schedule]], header: str) -> str:
    indicator = week_indicator(week_type)
    response = f"{indicator} 📅 Расписание на {header}:\n\n"

    for day_name in DAYS_OF_WEEK:
        schedule = week_schedule.get(day_name)
        if not schedule:
            continue

        response += f"📆 {day_name.capitalize()}:\n"
        for lesson in sorted(schedule, key=lambda x: x.class_num):
            time_str = _format_time(lesson.start_time)
            lesson_indicator = "🟥" if lesson.week == "up" else "🟦" if lesson.week == "down" else "⬜"
            lesson_type_display = f" [{lesson.lesson_type}]" if lesson.lesson_type else ""
            response += f"  {lesson_indicator} {lesson.class_num}. {lesson.subject}{lesson_type_display} ({time_str})\n"
        response += "\n"

    return response


def schedule_to_image_items(schedule: list[Schedule]) -> list[dict]:
    items = []
    for lesson in sorted(schedule, key=lambda x: x.class_num):
        items.append({
            "time": _format_time(lesson.start_time),
            "subject": lesson.subject,
            "room": lesson.room,
            "teacher": lesson.teacher,
            "lesson_type": lesson.lesson_type,
        })
    return items
