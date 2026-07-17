from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def notifyBeforeAllLessonsKeyboard() -> ReplyKeyboardMarkup:
    notifyKeyboard = ReplyKeyboardBuilder()

    notifyKeyboard.button(text="20:00", icon_custom_emoji_id="5974076810386738645")
    notifyKeyboard.button(text="21:00", icon_custom_emoji_id="5974076810386738645")
    notifyKeyboard.button(text="22:00", icon_custom_emoji_id="5974076810386738645")
    notifyKeyboard.button(text="23:00", icon_custom_emoji_id="5974076810386738645")
    notifyKeyboard.button(text="Не присылать", style="danger", icon_custom_emoji_id="5974565736578813237")

    notifyKeyboard.adjust(2)
    return notifyKeyboard.as_markup(resize_keyboard=True, is_persistent=False)

def mainMenuKeyboard() -> ReplyKeyboardMarkup:
    mainMenu = ReplyKeyboardBuilder()
    mainMenu.button(text="📅 Сегодня")
    mainMenu.button(text="📆 Завтра")
    mainMenu.button(text="🗓 Эта неделя")
    mainMenu.button(text="📋 След. неделя")
    mainMenu.button(text="📝 Домашка")
    mainMenu.button(text="🙈 Скрыть предметы")
    mainMenu.button(text="👁️ Скрытые предметы")
    mainMenu.button(text="⚙️ Настройки")
    mainMenu.button(text="ℹ️ Помощь")
    
    mainMenu.adjust(2, 2, 2, 2)
    return mainMenu.as_markup(resize_keyboard=True, is_persistent=False)