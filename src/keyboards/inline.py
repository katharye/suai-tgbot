from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def generateGroupsKeyboard(groups: list[str]) -> InlineKeyboardMarkup:
    groupsKeyboard = InlineKeyboardBuilder()

    for group in groups:
        groupsKeyboard.button(text=group, callback_data=f"group_{group}")
    groupsKeyboard.button(
        text="Назад", 
        callback_data="SETTUP_BACK", 
        style="danger",
        icon_custom_emoji_id="5854967531793550989")

    buttons_count = len(groups)
    rowsOfFour = buttons_count // 4
    remainder = buttons_count % 4
    adjust_shema = [4] * rowsOfFour
    adjust_shema.append(remainder)

    groupsKeyboard.adjust(*adjust_shema)
    return groupsKeyboard.as_markup()

def applyResetKeyboard() -> InlineKeyboardMarkup:
    resetKeyboard = InlineKeyboardBuilder()
    resetKeyboard.button(text="Да", callback_data="RESET_YES", 
                         style="success", icon_custom_emoji_id="5373084673767407538")
    resetKeyboard.button(text="Нет", callback_data="RESET_NO", 
                         style="danger", icon_custom_emoji_id="5375142362534148649")
    return resetKeyboard.as_markup()

def notifyBeforeLessonsKeyboard() -> InlineKeyboardMarkup:
    notifyKeyboard = InlineKeyboardBuilder()

    for notifyTime in range(5, 31, 5):
        notifyKeyboard.button(text=f"{notifyTime} минут", 
                              callback_data=f"BEFORELESSONS_{notifyTime}", 
                              icon_custom_emoji_id="5974076810386738645"
        )
    notifyKeyboard.button(text="Своё значение", 
                          callback_data="USERS_TIME_BEFORELESSONS", 
                          icon_custom_emoji_id="5371053145646441722",
                          style="primary"
    )

    notifyKeyboard.button(text="Не присылать", 
                          callback_data="BEFORELESSONS_DONT_NOTIFY", 
                          icon_custom_emoji_id="5974565736578813237",
                          style="danger"
    )

    adjust_shema = [2] * 3 + [1] * 2
    notifyKeyboard.adjust(*adjust_shema)
    return notifyKeyboard.as_markup()


def dayNavigationKeyboard(current_day_index: int, show_image: bool = False, week_type: str = "all") -> InlineKeyboardMarkup:
    """Клавиатура для навигации по дням недели."""
    navKeyboard = InlineKeyboardBuilder()
    
    # Кнопка переключения текст/картинка
    if show_image:
        navKeyboard.button(text="📝 Текст", callback_data="toggle_text")
    else:
        navKeyboard.button(text="🖼️ Картинка", callback_data="toggle_image")
    
    # Кнопки переключения типа недели
    week_buttons = []
    if week_type == "all":
        week_buttons.append(("Все недели", "week_all"))
        week_buttons.append(("Нечётная", "week_up"))
        week_buttons.append(("Чётная", "week_down"))
    elif week_type == "up":
        week_buttons.append(("Все недели", "week_all"))
        week_buttons.append(("🔵 Нечётная", "week_up"))
        week_buttons.append(("Чётная", "week_down"))
    elif week_type == "down":
        week_buttons.append(("Все недели", "week_all"))
        week_buttons.append(("Нечётная", "week_up"))
        week_buttons.append(("🟢 Чётная", "week_down"))
    
    for text, callback in week_buttons:
        navKeyboard.button(text=text, callback_data=callback)
    
    # Кнопка предыдущего дня
    prev_day = (current_day_index - 1) % 7
    navKeyboard.button(text="◀️", callback_data=f"day_{prev_day}")
    
    # Кнопка следующего дня
    next_day = (current_day_index + 1) % 7
    navKeyboard.button(text="▶️", callback_data=f"day_{next_day}")
    
    navKeyboard.adjust(1, 3, 2)
    return navKeyboard.as_markup()


def weekViewKeyboard(show_image: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для выбора режима просмотра недели."""
    weekKeyboard = InlineKeyboardBuilder()
    
    weekKeyboard.button(text="📅 Выбрать день", callback_data="week_select_day")
    weekKeyboard.button(text="🗓 Вся неделя", callback_data="week_show_all")
    
    weekKeyboard.adjust(2)
    return weekKeyboard.as_markup()


def weekToggleKeyboard(show_image: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для переключения текст/картинка при просмотре недели."""
    weekKeyboard = InlineKeyboardBuilder()
    
    if show_image:
        weekKeyboard.button(text="📝 Текст", callback_data="week_toggle_text")
    else:
        weekKeyboard.button(text="🖼️ Картинка", callback_data="week_toggle_image")
    
    weekKeyboard.adjust(1)
    return weekKeyboard.as_markup()


def nextWeekViewKeyboard(show_image: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для выбора режима просмотра следующей недели."""
    weekKeyboard = InlineKeyboardBuilder()
    
    weekKeyboard.button(text="📅 Выбрать день", callback_data="next_week_select_day")
    weekKeyboard.button(text="🗓 Вся неделя", callback_data="next_week_show_all")
    
    weekKeyboard.adjust(2)
    return weekKeyboard.as_markup()


def nextWeekToggleKeyboard(show_image: bool = False) -> InlineKeyboardMarkup:
    """Клавиатура для переключения текст/картинка при просмотре следующей недели."""
    weekKeyboard = InlineKeyboardBuilder()
    
    if show_image:
        weekKeyboard.button(text="📝 Текст", callback_data="next_week_toggle_text")
    else:
        weekKeyboard.button(text="🖼️ Картинка", callback_data="next_week_toggle_image")
    
    weekKeyboard.adjust(1)
    return weekKeyboard.as_markup()


def daySelectionKeyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора конкретного дня недели."""
    dayKeyboard = InlineKeyboardBuilder()
    
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    for i, day in enumerate(days):
        dayKeyboard.button(text=day, callback_data=f"select_day_{i}")
    
    dayKeyboard.adjust(2, 2, 2, 1)
    return dayKeyboard.as_markup()


def nextDaySelectionKeyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора конкретного дня следующей недели."""
    dayKeyboard = InlineKeyboardBuilder()
    
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    for i, day in enumerate(days):
        dayKeyboard.button(text=day, callback_data=f"select_next_day_{i}")
    
    dayKeyboard.adjust(2, 2, 2, 1)
    return dayKeyboard.as_markup()


def hideSubjectDayKeyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора дня недели для скрытия предмета."""
    dayKeyboard = InlineKeyboardBuilder()
    
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    for i, day in enumerate(days):
        dayKeyboard.button(text=day, callback_data=f"hide_day_{i}")
    
    dayKeyboard.adjust(2, 2, 2, 1)
    return dayKeyboard.as_markup()


def viewHiddenSubjectDayKeyboard() -> InlineKeyboardMarkup:
    """Клавиатура для выбора дня недели для просмотра скрытых предметов."""
    dayKeyboard = InlineKeyboardBuilder()
    
    days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
    for i, day in enumerate(days):
        dayKeyboard.button(text=day, callback_data=f"view_hidden_day_{i}")
    
    dayKeyboard.adjust(2, 2, 2, 1)
    return dayKeyboard.as_markup()