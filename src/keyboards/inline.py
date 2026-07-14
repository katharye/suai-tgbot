from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, \
    InlineKeyboardButton, InlineKeyboardMarkup
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


# КАЛЕНДАРЬ 52516137687517977722