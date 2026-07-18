from datetime import date, datetime


def get_time_notifications_one_session(strr: str) -> int | None:
    """Парсит интервал ЧЧ:ММ перед парой → секунды. Максимум 3 часа."""
    try:
        parsed = datetime.strptime(strr.strip(), "%H:%M")
        seconds = parsed.hour * 3600 + parsed.minute * 60
        if seconds > 10800:
            return None
        return seconds
    except Exception:
        return None


def get_time_notifications_all_session(strr: str) -> int | None:
    """Парсит время суток ЧЧ:ММ → секунды от начала дня."""
    try:
        parsed = datetime.strptime(strr.strip(), "%H:%M")
        return parsed.hour * 3600 + parsed.minute * 60
    except Exception:
        return None


def get_week_type(current_date: date | None = None) -> str:
    """Тип недели: 'up' (нечётная) или 'down' (чётная). 1 сентября — начало нечётной."""
    if current_date is None:
        current_date = date.today()

    start_date = date(current_date.year, 9, 1)
    if current_date < start_date:
        start_date = date(current_date.year - 1, 9, 1)

    week_number = (current_date - start_date).days // 7
    return "up" if week_number % 2 == 0 else "down"
