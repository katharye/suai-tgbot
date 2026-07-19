from vkbottle import Keyboard, KeyboardButtonColor, Text


def notifyBeforeAllLessonsKeyboard() -> str:
    kb = Keyboard(one_time=False, inline=False)

    kb.add(Text("20:00"), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("21:00"), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("22:00"), color=KeyboardButtonColor.SECONDARY)
    kb.add(Text("23:00"), color=KeyboardButtonColor.SECONDARY)
    kb.row()
    kb.add(Text("Не присылать"), color=KeyboardButtonColor.NEGATIVE)

    return kb.get_json()


def mainMenuKeyboard() -> str:
    kb = Keyboard(one_time=False, inline=False)

    kb.add(Text("📅 Сегодня"))
    kb.add(Text("📆 Завтра"))
    kb.row()
    kb.add(Text("🗓 Эта неделя"))
    kb.add(Text("📋 След. неделя"))
    kb.row()
    kb.add(Text("📝 Домашка"))
    kb.add(Text("🙈 Скрыть предметы"))
    kb.row()
    kb.add(Text("👁️ Скрытые предметы"))
    kb.add(Text("⚙️ Настройки"))
    kb.row()
    kb.add(Text("ℹ️ Помощь"))

    return kb.get_json()


def settingsKeyboard() -> str:
    kb = Keyboard(one_time=False, inline=False)

    kb.add(Text("⏰ Уведомления перед парой"))
    kb.add(Text("📅 Уведомления перед днём"))
    kb.row()
    kb.add(Text("🗑 Сброс аккаунта"), color=KeyboardButtonColor.NEGATIVE)
    kb.add(Text("🔙 Назад"))

    return kb.get_json()
