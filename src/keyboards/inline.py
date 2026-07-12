from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton, \
    InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def generateGroupsKeyboard(groups: list[str]) -> InlineKeyboardMarkup:
    groupsKeyboard = InlineKeyboardBuilder()

    for group in groups:
        groupsKeyboard.button(text=group, callback_data=f"group_{group}")
    groupsKeyboard.adjust(4)

    return groupsKeyboard.as_markup()
