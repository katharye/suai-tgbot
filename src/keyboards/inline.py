from vkbottle import Callback, Keyboard, KeyboardButtonColor

DAYS_OF_WEEK = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
DAYS_TITLE = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


def generateGroupsKeyboard(groups: list[str]) -> str:
    kb = Keyboard(inline=True)

    for i, group in enumerate(groups):
        if i and i % 4 == 0:
            kb.row()
        kb.add(Callback(group, payload={"cmd": f"group_{group}"}))

    kb.row()
    kb.add(Callback("Назад", payload={"cmd": "SETTUP_BACK"}), color=KeyboardButtonColor.NEGATIVE)

    return kb.get_json()


def applyResetKeyboard() -> str:
    kb = Keyboard(inline=True)
    kb.add(Callback("Да", payload={"cmd": "RESET_YES"}), color=KeyboardButtonColor.POSITIVE)
    kb.add(Callback("Нет", payload={"cmd": "RESET_NO"}), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


def notifyBeforeLessonsKeyboard() -> str:
    kb = Keyboard(inline=True)

    times = list(range(5, 31, 5))
    for i, notify_time in enumerate(times):
        if i and i % 2 == 0:
            kb.row()
        kb.add(Callback(f"{notify_time} минут", payload={"cmd": f"BEFORELESSONS_{notify_time}"}))

    kb.row()
    kb.add(
        Callback("Своё значение", payload={"cmd": "USERS_TIME_BEFORELESSONS"}),
        color=KeyboardButtonColor.PRIMARY,
    )
    kb.row()
    kb.add(
        Callback("Не присылать", payload={"cmd": "BEFORELESSONS_DONT_NOTIFY"}),
        color=KeyboardButtonColor.NEGATIVE,
    )

    return kb.get_json()


def dayNavigationKeyboard(current_day_index: int, show_image: bool = False, week_type: str = "all") -> str:
    """Клавиатура для навигации по дням недели."""
    kb = Keyboard(inline=True)

    if show_image:
        kb.add(Callback("📝 Текст", payload={"cmd": "toggle_text"}))
    else:
        kb.add(Callback("🖼️ Картинка", payload={"cmd": "toggle_image"}))

    kb.row()

    if week_type == "all":
        kb.add(Callback("Все недели", payload={"cmd": "week_all"}))
        kb.add(Callback("Нечётная", payload={"cmd": "week_up"}))
        kb.add(Callback("Чётная", payload={"cmd": "week_down"}))
    elif week_type == "up":
        kb.add(Callback("Все недели", payload={"cmd": "week_all"}))
        kb.add(Callback("🔵 Нечётная", payload={"cmd": "week_up"}))
        kb.add(Callback("Чётная", payload={"cmd": "week_down"}))
    elif week_type == "down":
        kb.add(Callback("Все недели", payload={"cmd": "week_all"}))
        kb.add(Callback("Нечётная", payload={"cmd": "week_up"}))
        kb.add(Callback("🟢 Чётная", payload={"cmd": "week_down"}))

    kb.row()
    prev_day = (current_day_index - 1) % 7
    next_day = (current_day_index + 1) % 7
    kb.add(Callback("◀️", payload={"cmd": f"day_{prev_day}"}))
    kb.add(Callback("▶️", payload={"cmd": f"day_{next_day}"}))

    return kb.get_json()


def weekViewKeyboard() -> str:
    """Клавиатура для выбора режима просмотра недели."""
    kb = Keyboard(inline=True)
    kb.add(Callback("📅 Выбрать день", payload={"cmd": "week_select_day"}))
    kb.add(Callback("🗓 Вся неделя", payload={"cmd": "week_show_all"}))
    return kb.get_json()


def weekToggleKeyboard(show_image: bool = False) -> str:
    """Клавиатура для переключения текст/картинка при просмотре недели."""
    kb = Keyboard(inline=True)
    if show_image:
        kb.add(Callback("📝 Текст", payload={"cmd": "week_toggle_text"}))
    else:
        kb.add(Callback("🖼️ Картинка", payload={"cmd": "week_toggle_image"}))
    return kb.get_json()


def nextWeekViewKeyboard() -> str:
    """Клавиатура для выбора режима просмотра следующей недели."""
    kb = Keyboard(inline=True)
    kb.add(Callback("📅 Выбрать день", payload={"cmd": "next_week_select_day"}))
    kb.add(Callback("🗓 Вся неделя", payload={"cmd": "next_week_show_all"}))
    return kb.get_json()


def nextWeekToggleKeyboard(show_image: bool = False) -> str:
    """Клавиатура для переключения текст/картинка при просмотре следующей недели."""
    kb = Keyboard(inline=True)
    if show_image:
        kb.add(Callback("📝 Текст", payload={"cmd": "next_week_toggle_text"}))
    else:
        kb.add(Callback("🖼️ Картинка", payload={"cmd": "next_week_toggle_image"}))
    return kb.get_json()


def daySelectionKeyboard() -> str:
    """Клавиатура для выбора конкретного дня недели."""
    kb = Keyboard(inline=True)
    for i, day in enumerate(DAYS_TITLE):
        if i and i % 2 == 0:
            kb.row()
        kb.add(Callback(day, payload={"cmd": f"select_day_{i}"}))
    return kb.get_json()


def nextDaySelectionKeyboard() -> str:
    """Клавиатура для выбора конкретного дня следующей недели."""
    kb = Keyboard(inline=True)
    for i, day in enumerate(DAYS_TITLE):
        if i and i % 2 == 0:
            kb.row()
        kb.add(Callback(day, payload={"cmd": f"select_next_day_{i}"}))
    return kb.get_json()


def hideSubjectDayKeyboard() -> str:
    """Клавиатура для выбора дня недели для скрытия предмета."""
    kb = Keyboard(inline=True)
    for i, day in enumerate(DAYS_TITLE):
        if i and i % 2 == 0:
            kb.row()
        kb.add(Callback(day, payload={"cmd": f"hide_day_{i}"}))
    kb.row()
    kb.add(Callback("🔙 Назад", payload={"cmd": "back_to_main_menu"}))
    return kb.get_json()


def viewHiddenSubjectDayKeyboard() -> str:
    """Клавиатура для выбора дня недели для просмотра скрытых предметов."""
    kb = Keyboard(inline=True)
    for i, day in enumerate(DAYS_TITLE):
        if i and i % 2 == 0:
            kb.row()
        kb.add(Callback(day, payload={"cmd": f"view_hidden_day_{i}"}))
    kb.row()
    kb.add(Callback("🔙 Назад", payload={"cmd": "back_to_main_menu"}))
    return kb.get_json()


def dayNavWithSubjectsKeyboard(day_index: int, subject_prefix: str, subjects: list[str], back_cmd: str, nav_cmd_prefix: str) -> str:
    """Общая клавиатура: список предметов (по индексу) + навигация по дням + кнопка в меню."""
    kb = Keyboard(inline=True)

    for idx, _subject in enumerate(subjects):
        kb.row()
        kb.add(Callback(_subject, payload={"cmd": f"{subject_prefix}{idx}"}))

    kb.row()
    prev_day_index = (day_index - 1) % 7
    next_day_index = (day_index + 1) % 7
    kb.add(Callback(f"◀ {DAYS_TITLE[prev_day_index]}", payload={"cmd": f"{nav_cmd_prefix}{prev_day_index}"}))
    kb.add(Callback(f"{DAYS_TITLE[next_day_index]} ▶", payload={"cmd": f"{nav_cmd_prefix}{next_day_index}"}))
    kb.row()
    kb.add(Callback("🔙 В меню", payload={"cmd": back_cmd}))

    return kb.get_json()


def dayNavOnlyKeyboard(day_index: int, back_cmd: str, nav_cmd_prefix: str) -> str:
    """Клавиатура навигации по дням без предметов (когда список пуст)."""
    kb = Keyboard(inline=True)
    prev_day_index = (day_index - 1) % 7
    next_day_index = (day_index + 1) % 7
    kb.add(Callback(f"◀ {DAYS_TITLE[prev_day_index]}", payload={"cmd": f"{nav_cmd_prefix}{prev_day_index}"}))
    kb.add(Callback(f"{DAYS_TITLE[next_day_index]} ▶", payload={"cmd": f"{nav_cmd_prefix}{next_day_index}"}))
    kb.row()
    kb.add(Callback("🔙 В меню", payload={"cmd": back_cmd}))
    return kb.get_json()


def confirmUnhideKeyboard(subject_idx: int) -> str:
    kb = Keyboard(inline=True)
    kb.add(Callback("❌ Удалить из скрытых", payload={"cmd": f"remove_subj_{subject_idx}"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Callback("🔙 Назад", payload={"cmd": "back_to_hidden"}))
    return kb.get_json()


def hiddenSubjectsListKeyboard(subjects: list[str]) -> str:
    kb = Keyboard(inline=True)
    for idx, subject in enumerate(subjects):
        kb.row()
        kb.add(Callback(subject, payload={"cmd": f"view_subj_{idx}"}))
    return kb.get_json()


def homeworkListKeyboard(homeworks: list) -> str:
    """Клавиатура для списка домашних заданий."""
    kb = Keyboard(inline=True)

    for idx, homework in enumerate(homeworks):
        kb.row()
        kb.add(Callback(homework.name, payload={"cmd": f"homework_view_{idx}"}))

    kb.row()
    kb.add(Callback("➕ Добавить домашку", payload={"cmd": "homework_add"}), color=KeyboardButtonColor.POSITIVE)
    kb.row()
    kb.add(Callback("🔙 Назад", payload={"cmd": "back_to_main_menu"}))

    return kb.get_json()


def homeworkAddKeyboard() -> str:
    """Клавиатура для добавления домашки."""
    kb = Keyboard(inline=True)
    kb.add(Callback("🔙 Отмена", payload={"cmd": "homework_cancel"}), color=KeyboardButtonColor.NEGATIVE)
    return kb.get_json()


def homeworkViewKeyboard(homework_idx: int) -> str:
    """Клавиатура для просмотра конкретной домашки."""
    kb = Keyboard(inline=True)
    kb.add(Callback("🗑 Удалить", payload={"cmd": f"homework_delete_{homework_idx}"}), color=KeyboardButtonColor.NEGATIVE)
    kb.row()
    kb.add(Callback("🔙 Назад", payload={"cmd": "homework_back_to_list"}))
    return kb.get_json()


def settingsInlineKeyboard() -> str:
    """Инлайн клавиатура для настроек (для message_event хендлеров)."""
    kb = Keyboard(inline=True)
    kb.add(Callback("⏰ Уведомления перед парой", payload={"cmd": "settings_notify_before"}))
    kb.add(Callback("📅 Уведомления перед днём", payload={"cmd": "settings_notify_day"}))
    kb.row()
    kb.add(Callback("🗑 Сброс аккаунта", payload={"cmd": "settings_reset"}), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Callback("🔙 Назад", payload={"cmd": "settings_back"}))
    return kb.get_json()
