from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def notifyBeforeAllLessonsKeyboard() -> ReplyKeyboardMarkup:
    notifyKeyboard = ReplyKeyboardBuilder()

    notifyKeyboard.button(text="20:00")
    notifyKeyboard.button(text="21:00")
    notifyKeyboard.button(text="22:00")
    notifyKeyboard.button(text="23:00")
    notifyKeyboard.button(text="Не присылать")

    notifyKeyboard.adjust(2)
    return notifyKeyboard.as_markup(resize_keyboard=True, is_persistent=False)


# КАЛЕНДАРЬ 52516137687517977722