from datetime import datetime, date, timedelta

from vkbottle import BaseStateGroup
from vkbottle.bot import BotLabeler, Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.inline import notifyBeforeLessonsKeyboard, applyResetKeyboard, hideSubjectDayKeyboard, viewHiddenSubjectDayKeyboard, homeworkListKeyboard, homeworkAddKeyboard
from keyboards.reply import mainMenuKeyboard, settingsKeyboard, notifyBeforeAllLessonsKeyboard

from database.requests import get_user, get_user_homeworks, add_homework, update_user_notify_time, update_user_notify_before_min
from services.get_time import get_time_notifications_all_session, get_time_notifications_one_session
from services.fsm import set_state, clear_state, get_state_data, advance_state

user_labeler = BotLabeler()


class ScheduleNavigation(BaseStateGroup):
    navigating = "navigating"
    week_viewing = "week_viewing"


class HideSubject(BaseStateGroup):
    selecting_day = "hide_selecting_day"
    selecting_subject = "hide_selecting_subject"


class ViewHiddenSubjects(BaseStateGroup):
    selecting_day = "view_hidden_selecting_day"
    viewing_subjects = "view_hidden_viewing_subjects"


class HomeworkManagement(BaseStateGroup):
    viewing_list = "homework_viewing_list"
    adding_name = "homework_adding_name"
    adding_description = "homework_adding_description"
    adding_file = "homework_adding_file"
    adding_remind_time = "homework_adding_remind_time"


class SettingsManagement(BaseStateGroup):
    in_settings = "settings_in_settings"
    changing_notify_before = "settings_changing_notify_before"
    changing_notify_day = "settings_changing_notify_day"
    confirming_reset = "settings_confirming_reset"


@user_labeler.message(command="main")
@user_labeler.message(command="menu")
async def cmd_main(message: Message):
    await message.answer("Главное меню 🎓\n\nВыберите действие:", keyboard=mainMenuKeyboard())


@user_labeler.message(text="📅 Сегодня")
async def cmd_today(message: Message, session: AsyncSession):
    from services.get_time import get_week_type
    from services.schedule_format import DAYS_OF_WEEK, format_day_text
    from database.requests import get_schedule
    from keyboards.inline import dayNavigationKeyboard

    user = await get_user(session=session, vk_id=message.from_id)
    if not user:
        await message.answer("Сначала нужно пройти регистрацию. Напиши /start")
        return

    day_index = datetime.now().weekday()
    current_day = DAYS_OF_WEEK[day_index]
    week_type = get_week_type()

    await set_state(message.peer_id, ScheduleNavigation.navigating, day_index=day_index, show_image=False, week_type=week_type)

    schedule = await get_schedule(session=session, group_id=user.group_id, week=week_type, weekday=current_day, vk_id=user.vk_id)
    response = format_day_text(current_day, week_type, schedule, header_prefix="📅 Расписание на")

    await message.answer(response, keyboard=dayNavigationKeyboard(day_index, show_image=False, week_type=week_type))


@user_labeler.message(text="📆 Завтра")
async def cmd_tomorrow(message: Message, session: AsyncSession):
    from services.get_time import get_week_type
    from services.schedule_format import DAYS_OF_WEEK, format_day_text
    from database.requests import get_schedule
    from keyboards.inline import dayNavigationKeyboard

    user = await get_user(session=session, vk_id=message.from_id)
    if not user:
        await message.answer("Сначала нужно пройти регистрацию. Напиши /start")
        return

    tomorrow = date.today() + timedelta(days=1)
    day_index = tomorrow.weekday()
    current_day = DAYS_OF_WEEK[day_index]
    week_type = get_week_type(tomorrow)

    await set_state(message.peer_id, ScheduleNavigation.navigating, day_index=day_index, show_image=False, week_type=week_type)

    schedule = await get_schedule(session=session, group_id=user.group_id, week=week_type, weekday=current_day, vk_id=user.vk_id)
    response = format_day_text(current_day, week_type, schedule, header_prefix="📅 Расписание на")

    await message.answer(response, keyboard=dayNavigationKeyboard(day_index, show_image=False, week_type=week_type))


@user_labeler.message(text="🗓 Эта неделя")
async def cmd_this_week(message: Message):
    from keyboards.inline import weekViewKeyboard
    await message.answer("Выберите режим просмотра расписания на неделю:", keyboard=weekViewKeyboard())


@user_labeler.message(text="📋 След. неделя")
async def cmd_next_week(message: Message):
    from keyboards.inline import nextWeekViewKeyboard
    await message.answer("Выберите режим просмотра расписания на следующую неделю:", keyboard=nextWeekViewKeyboard())


@user_labeler.message(text="📝 Домашка")
async def cmd_homework(message: Message, session: AsyncSession):
    user = await get_user(session=session, vk_id=message.from_id)
    if not user:
        await message.answer("Сначала нужно пройти регистрацию. Напиши /start")
        return

    homeworks = await get_user_homeworks(session=session, vk_id=user.vk_id)

    text = "У вас пока нет домашних заданий." if not homeworks else "Ваши домашние задания:"
    await message.answer(text, keyboard=homeworkListKeyboard(homeworks))
    await set_state(message.peer_id, HomeworkManagement.viewing_list, homeworks=homeworks)


@user_labeler.message(text="⚙️ Настройки")
async def cmd_settings(message: Message, session: AsyncSession):
    user = await get_user(session=session, vk_id=message.from_id)
    if not user:
        await message.answer("Сначала нужно пройти регистрацию. Напиши /start")
        return

    await message.answer("⚙️ Настройки", keyboard=settingsKeyboard())
    await set_state(message.peer_id, SettingsManagement.in_settings)


@user_labeler.message(state=SettingsManagement.in_settings, text="🔙 Назад")
async def settings_back(message: Message):
    await message.answer("Главное меню", keyboard=mainMenuKeyboard())
    await clear_state(message.peer_id)


@user_labeler.message(state=SettingsManagement.in_settings, text="⏰ Уведомления перед парой")
async def settings_change_notify_before(message: Message):
    await message.answer(
        "Я могу присылать уведомления о предстоящей паре за несколько минут до неё. Если нужно, укажи за сколько.",
        keyboard=notifyBeforeLessonsKeyboard(),
    )
    await set_state(message.peer_id, SettingsManagement.changing_notify_before)


@user_labeler.message(state=SettingsManagement.changing_notify_before)
async def settings_notify_before_confirm(message: Message, session: AsyncSession):
    result = get_time_notifications_one_session(message.text)
    if result is None:
        await message.answer("Время написано некорректно! Напиши время в формате ЧЧ:ММ, не более 3 часов (к примеру 02:21)")
        return

    minutes = result // 60
    user = await get_user(session=session, vk_id=message.from_id)
    if user:
        await update_user_notify_before_min(session=session, vk_id=user.vk_id, notify_before_min=minutes)

    await message.answer(f"✅ Уведомления перед парой установлены за {minutes} минут", keyboard=settingsKeyboard())
    await set_state(message.peer_id, SettingsManagement.in_settings)


@user_labeler.message(state=SettingsManagement.in_settings, text="📅 Уведомления перед днём")
async def settings_change_notify_day(message: Message):
    await message.answer(
        "Я могу присылать уведомления о целом дне в указанное тобой время. Если нужно, укажи за сколько. "
        "Так же ты можешь указать своё время в формате ЧЧ:ММ",
        keyboard=notifyBeforeAllLessonsKeyboard(),
    )
    await set_state(message.peer_id, SettingsManagement.changing_notify_day)


@user_labeler.message(state=SettingsManagement.changing_notify_day)
async def settings_notify_day_confirm(message: Message, session: AsyncSession):
    result = get_time_notifications_all_session(message.text)
    if result is None and message.text != "Не присылать":
        await message.answer("Время должно быть в формате ЧЧ:ММ!\nДля продолжения введи корректное время или выбери из предложенного")
        return

    user = await get_user(session=session, vk_id=message.from_id)
    if user:
        await update_user_notify_time(session=session, vk_id=user.vk_id, notify_time=result)

    if result is not None:
        hours, minutes = result // 3600, (result % 3600) // 60
        await message.answer(f"✅ Уведомления перед днём установлены на {hours:02d}:{minutes:02d}", keyboard=settingsKeyboard())
    else:
        await message.answer("✅ Уведомления перед днём отключены", keyboard=settingsKeyboard())

    await set_state(message.peer_id, SettingsManagement.in_settings)


@user_labeler.message(state=SettingsManagement.in_settings, text="🗑 Сброс аккаунта")
async def settings_reset_account(message: Message):
    await message.answer(
        "⚠️ Вы уверены, что хотите сбросить аккаунт? Все данные, включая домашние задания, будут удалены!",
        keyboard=applyResetKeyboard(),
    )
    await set_state(message.peer_id, SettingsManagement.confirming_reset)


@user_labeler.message(text="🙈 Скрыть предметы")
async def cmd_hide_subject(message: Message):
    await message.answer("Выберите день недели, на котором хотите скрыть предмет:", keyboard=hideSubjectDayKeyboard())
    await set_state(message.peer_id, HideSubject.selecting_day)


@user_labeler.message(text="👁️ Скрытые предметы")
async def cmd_view_hidden_subjects(message: Message):
    await message.answer("Выберите день недели для просмотра скрытых предметов:", keyboard=viewHiddenSubjectDayKeyboard())
    await set_state(message.peer_id, ViewHiddenSubjects.selecting_day)


@user_labeler.message(text="ℹ️ Помощь")
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ Помощь\n\n"
        "📅 Сегодня — расписание на текущий день\n"
        "📆 Завтра — расписание на завтра\n"
        "🗓 Эта неделя — расписание на текущую неделю\n"
        "📋 След. неделя — расписание на следующую неделю\n"
        "📝 Домашка — список, добавление и удаление домашних заданий\n"
        "🙈 Скрыть предметы — скрыть предметы из расписания\n"
        "👁️ Скрытые предметы — просмотр и возврат скрытых предметов\n"
        "⚙️ Настройки — уведомления перед парой / днём и сброс аккаунта\n"
        "ℹ️ Помощь — это сообщение"
    )


# ---- Добавление домашки: пошаговый текстовый ввод ----

@user_labeler.message(state=HomeworkManagement.adding_name)
async def homework_add_name(message: Message):
    await advance_state(message.peer_id, HomeworkManagement.adding_description, homework_name=message.text)
    await message.answer("Введите описание домашки (или пропустите, отправив /skip):", keyboard=homeworkAddKeyboard())


@user_labeler.message(state=HomeworkManagement.adding_description, text="/skip")
async def homework_skip_description(message: Message):
    await advance_state(message.peer_id, HomeworkManagement.adding_file, homework_description=None)
    await message.answer("Прикрепите файл с домашкой (или пропустите, отправив /skip):", keyboard=homeworkAddKeyboard())


@user_labeler.message(state=HomeworkManagement.adding_description)
async def homework_add_description(message: Message):
    await advance_state(message.peer_id, HomeworkManagement.adding_file, homework_description=message.text)
    await message.answer("Прикрепите файл с домашкой (или пропустите, отправив /skip):", keyboard=homeworkAddKeyboard())


@user_labeler.message(state=HomeworkManagement.adding_file, text="/skip")
async def homework_skip_file(message: Message):
    await advance_state(message.peer_id, HomeworkManagement.adding_remind_time, homework_file_id=None)
    await message.answer("Укажите когда напомнить о домашке в формате ДД.ММ.ГГГГ ЧЧ:ММ (или пропустите, отправив /skip):", keyboard=homeworkAddKeyboard())


@user_labeler.message(state=HomeworkManagement.adding_file, attachment="doc")
async def homework_add_file(message: Message):
    attachment_strings = message.get_attachment_strings() or []
    file_id = attachment_strings[0] if attachment_strings else None

    await advance_state(message.peer_id, HomeworkManagement.adding_remind_time, homework_file_id=file_id)
    await message.answer("Укажите когда напомнить о домашке в формате ДД.ММ.ГГГГ ЧЧ:ММ (или пропустите, отправив /skip):", keyboard=homeworkAddKeyboard())


async def _save_homework(message: Message, session: AsyncSession, remind_time: int | None):
    data = await get_state_data(message.peer_id)

    user = await get_user(session=session, vk_id=message.from_id)
    if not user:
        await message.answer("Ошибка: пользователь не найден")
        await clear_state(message.peer_id)
        return

    try:
        await add_homework(
            session=session,
            vk_id=user.vk_id,
            name=data.get("homework_name"),
            description=data.get("homework_description"),
            file_id=data.get("homework_file_id"),
            remind_time=remind_time,
        )
        await message.answer("✅ Домашка добавлена!", keyboard=mainMenuKeyboard())
    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении домашки: {e}", keyboard=mainMenuKeyboard())

    await clear_state(message.peer_id)


@user_labeler.message(state=HomeworkManagement.adding_remind_time, text="/skip")
async def homework_skip_remind_time(message: Message, session: AsyncSession):
    await _save_homework(message, session, remind_time=None)


@user_labeler.message(state=HomeworkManagement.adding_remind_time)
async def homework_add_remind_time(message: Message, session: AsyncSession):
    try:
        remind_datetime = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        remind_timestamp = int(remind_datetime.timestamp())
    except ValueError:
        await message.answer("Неверный формат. Используйте ДД.ММ.ГГГГ ЧЧ:ММ (например: 25.12.2026 14:30)")
        return

    await _save_homework(message, session, remind_time=remind_timestamp)
