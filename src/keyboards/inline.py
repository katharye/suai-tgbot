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