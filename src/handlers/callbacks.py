"""Единая точка обработки нажатий на инлайн-кнопки (VK message_event).

В отличие от aiogram, vkbottle не фильтрует raw_event по текущему состоянию
автоматически, поэтому там, где одна и та же кнопка используется в разных
сценариях (регистрация/настройки), состояние проверяется вручную внутри
хендлера.
"""

from datetime import datetime

from vkbottle import GroupEventType, PhotoMessageUploader
from vkbottle.bot import BotLabeler, MessageEvent
from sqlalchemy.ext.asyncio import AsyncSession

from database.requests import (
    get_user, delete_user, get_or_create_group, get_schedule,
    add_hidden_subject, get_hidden_subjects_by_day, remove_hidden_subject,
    update_user_notify_before_min, update_user_notify_time,
    get_user_homeworks, delete_homework,
)
from keyboards.inline import (
    generateGroupsKeyboard, notifyBeforeLessonsKeyboard, applyResetKeyboard,
    settingsInlineKeyboard, dayNavigationKeyboard, weekViewKeyboard, weekToggleKeyboard,
    nextWeekViewKeyboard, nextWeekToggleKeyboard, daySelectionKeyboard, nextDaySelectionKeyboard,
    hideSubjectDayKeyboard, viewHiddenSubjectDayKeyboard, dayNavWithSubjectsKeyboard, dayNavOnlyKeyboard,
    confirmUnhideKeyboard, hiddenSubjectsListKeyboard, homeworkListKeyboard, homeworkAddKeyboard,
    homeworkViewKeyboard, DAYS_OF_WEEK, DAYS_TITLE,
)
from keyboards.reply import mainMenuKeyboard, settingsKeyboard, notifyBeforeAllLessonsKeyboard
from services.fsm import get_state, get_state_data, set_state, advance_state, clear_state, is_state
from services.get_time import get_week_type
from services.schedule_format import format_day_text, format_week_text, schedule_to_image_items, week_label
from services.gen_schedule import generate_schedule_image, generate_week_schedule_image

from handlers.registration import Registration
from handlers.user import ScheduleNavigation, HideSubject, ViewHiddenSubjects, HomeworkManagement, SettingsManagement

callbacks_labeler = BotLabeler()


async def _delete_event_message(event: MessageEvent) -> None:
    await event.ctx_api.messages.delete(peer_id=event.peer_id, cmids=[event.conversation_message_id], delete_for_all=True)


# ---------------------------------------------------------------------------
# Регистрация
# ---------------------------------------------------------------------------

@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": lambda v: v.startswith("group_")})
async def confirmation(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    selected_group = event.payload["cmd"][len("group_"):]

    group = await get_or_create_group(session=session, name=selected_group)
    await advance_state(
        event.peer_id, Registration.waiting_time_notify,
        groupName=selected_group, groupId=group.id, vkId=event.user_id,
    )

    await event.edit_message(
        "Я могу присылать уведомления о предстоящей паре за несколько минут до неё. Если нужно, укажи за сколько.",
        keyboard=notifyBeforeLessonsKeyboard(),
    )


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "SETTUP_BACK"})
async def back_to_group_selection(event: MessageEvent):
    await event.send_empty_answer()
    await event.edit_message("Напиши свою группу!")
    await set_state(event.peer_id, Registration.waiting_for_group)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "RESET_YES"})
async def reset_yes(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    state = await get_state(event.peer_id)
    if not is_state(state, Registration.waiting_reset_confirm, SettingsManagement.confirming_reset):
        return

    if await get_user(session=session, vk_id=event.user_id) is not None:
        await delete_user(session=session, vk_id=event.user_id)

    await event.edit_message("Напиши свою группу!")
    await set_state(event.peer_id, Registration.waiting_for_group)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "RESET_NO"})
async def reset_no(event: MessageEvent):
    await event.send_empty_answer()
    state = await get_state(event.peer_id)

    if is_state(state, SettingsManagement.confirming_reset):
        await event.edit_message("⚙️ Настройки", keyboard=settingsInlineKeyboard())
        await set_state(event.peer_id, SettingsManagement.in_settings)
    elif is_state(state, Registration.waiting_reset_confirm):
        await _delete_event_message(event)
        await clear_state(event.peer_id)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "USERS_TIME_BEFORELESSONS"})
async def users_time_before_lessons(event: MessageEvent):
    await event.send_empty_answer()
    state = await get_state(event.peer_id)

    await event.send_message("Напиши время, за которое тебе надо отправлять уведомление о парах (максимум 3 часа, формат времени ЧЧ:ММ)")

    if is_state(state, Registration.waiting_time_notify):
        await advance_state(event.peer_id, Registration.waiting_write_time_notify)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": lambda v: v.startswith("BEFORELESSONS_")})
async def before_lessons_preset(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    variant = event.payload["cmd"][len("BEFORELESSONS_"):]
    value = 0 if variant == "DONT_NOTIFY" else int(variant)

    state = await get_state(event.peer_id)

    if is_state(state, Registration.waiting_time_notify):
        await advance_state(event.peer_id, Registration.waiting_all_day_notify, notifyBeforeLessons=value)
        await event.send_message(
            "Ещё я могу присылать уведомления о целом дне в указанное тобой время. Если нужно, укажи за сколько. "
            "Так же ты можешь указать своё время в формате ЧЧ:ММ",
            keyboard=notifyBeforeAllLessonsKeyboard(),
        )
    elif is_state(state, SettingsManagement.changing_notify_before):
        user = await get_user(session=session, vk_id=event.user_id)
        if user:
            await update_user_notify_before_min(session=session, vk_id=user.vk_id, notify_before_min=value)

        text = f"✅ Уведомления перед парой установлены за {value} минут" if value else "✅ Уведомления перед парой отключены"
        await event.edit_message(text, keyboard=settingsInlineKeyboard())
        await set_state(event.peer_id, SettingsManagement.in_settings)


# ---------------------------------------------------------------------------
# Настройки (инлайн-версия settingsKeyboard)
# ---------------------------------------------------------------------------

@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "settings_back"})
async def settings_inline_back(event: MessageEvent):
    await event.send_empty_answer()
    await _delete_event_message(event)
    await event.send_message("Главное меню", keyboard=mainMenuKeyboard())
    await clear_state(event.peer_id)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "settings_notify_before"})
async def settings_inline_notify_before(event: MessageEvent):
    await event.send_empty_answer()
    await event.edit_message(
        "Я могу присылать уведомления о предстоящей паре за несколько минут до неё. Если нужно, укажи за сколько.",
        keyboard=notifyBeforeLessonsKeyboard(),
    )
    await set_state(event.peer_id, SettingsManagement.changing_notify_before)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "settings_notify_day"})
async def settings_inline_notify_day(event: MessageEvent):
    await event.send_empty_answer()
    await event.edit_message("Я могу присылать уведомления о целом дне в указанное тобой время. Если нужно, укажи за сколько.")
    await event.send_message("Так же ты можешь указать своё время в формате ЧЧ:ММ", keyboard=notifyBeforeAllLessonsKeyboard())
    await set_state(event.peer_id, SettingsManagement.changing_notify_day)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "settings_reset"})
async def settings_inline_reset(event: MessageEvent):
    await event.send_empty_answer()
    await event.edit_message(
        "⚠️ Вы уверены, что хотите сбросить аккаунт? Все данные, включая домашние задания, будут удалены!",
        keyboard=applyResetKeyboard(),
    )
    await set_state(event.peer_id, SettingsManagement.confirming_reset)


# ---------------------------------------------------------------------------
# Навигация по расписанию
# ---------------------------------------------------------------------------

async def _upload_schedule_photo(event: MessageEvent, day_name: str, schedule) -> str:
    items = schedule_to_image_items(schedule)
    buffer = generate_schedule_image(day_name, items)
    uploader = PhotoMessageUploader(event.ctx_api)
    return await uploader.upload(buffer, peer_id=event.peer_id)


async def _render_day(event: MessageEvent, session: AsyncSession, day_index: int, week_type: str, show_image: bool):
    user = await get_user(session=session, vk_id=event.user_id)
    if not user:
        await event.show_snackbar("Сначала нужно пройти регистрацию")
        return

    weekday = DAYS_OF_WEEK[day_index]
    schedule = await get_schedule(session=session, group_id=user.group_id, week=week_type, weekday=weekday, vk_id=user.vk_id)
    kb = dayNavigationKeyboard(day_index, show_image=show_image, week_type=week_type)

    if show_image:
        attachment = await _upload_schedule_photo(event, weekday, schedule)
        caption = f"📅 Расписание на {weekday.capitalize()} ({week_label(week_type)})"
        await event.edit_message(caption, attachment=attachment, keyboard=kb)
    else:
        text = format_day_text(weekday, week_type, schedule)
        await event.edit_message(text, attachment="", keyboard=kb)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": lambda v: v.startswith("day_")})
async def navigate_day(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    day_index = int(event.payload["cmd"][len("day_"):])
    data = await advance_state(event.peer_id, ScheduleNavigation.navigating, day_index=day_index)
    await _render_day(event, session, day_index, data.get("week_type", "all"), data.get("show_image", False))


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "toggle_image"})
async def toggle_to_image(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    data = await advance_state(event.peer_id, ScheduleNavigation.navigating, show_image=True)
    await _render_day(event, session, data.get("day_index", 0), data.get("week_type", "all"), True)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "toggle_text"})
async def toggle_to_text(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    data = await advance_state(event.peer_id, ScheduleNavigation.navigating, show_image=False)
    await _render_day(event, session, data.get("day_index", 0), data.get("week_type", "all"), False)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "week_select_day"})
async def week_select_day(event: MessageEvent):
    await event.send_empty_answer()
    await event.edit_message("Выберите день недели:", keyboard=daySelectionKeyboard())


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": lambda v: v.startswith("select_day_")})
async def select_day(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    day_index = int(event.payload["cmd"][len("select_day_"):])
    week_type = get_week_type()
    await advance_state(event.peer_id, ScheduleNavigation.navigating, day_index=day_index, show_image=False, week_type=week_type)
    await _render_day(event, session, day_index, week_type, False)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "week_show_all"})
async def week_show_all(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    user = await get_user(session=session, vk_id=event.user_id)
    if not user:
        await event.show_snackbar("Сначала нужно пройти регистрацию")
        return

    week_type = get_week_type()
    await advance_state(event.peer_id, ScheduleNavigation.week_viewing, week_type=week_type, show_image=False, is_next_week=False)

    week_schedule = {}
    for day_name in DAYS_OF_WEEK:
        week_schedule[day_name] = await get_schedule(session=session, group_id=user.group_id, week=week_type, weekday=day_name, vk_id=user.vk_id)

    text = format_week_text(week_type, week_schedule, "эту неделю")
    await event.edit_message(text, attachment="", keyboard=weekToggleKeyboard(show_image=False))


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "next_week_select_day"})
async def next_week_select_day(event: MessageEvent):
    await event.send_empty_answer()
    await event.edit_message("Выберите день следующей недели:", keyboard=nextDaySelectionKeyboard())


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": lambda v: v.startswith("select_next_day_")})
async def select_next_day(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    day_index = int(event.payload["cmd"][len("select_next_day_"):])
    current_week_type = get_week_type()
    next_week_type = "down" if current_week_type == "up" else "up"
    await advance_state(event.peer_id, ScheduleNavigation.navigating, day_index=day_index, show_image=False, week_type=next_week_type)
    await _render_day(event, session, day_index, next_week_type, False)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "next_week_show_all"})
async def next_week_show_all(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    user = await get_user(session=session, vk_id=event.user_id)
    if not user:
        await event.show_snackbar("Сначала нужно пройти регистрацию")
        return

    current_week_type = get_week_type()
    next_week_type = "down" if current_week_type == "up" else "up"
    await advance_state(event.peer_id, ScheduleNavigation.week_viewing, week_type=next_week_type, show_image=False, is_next_week=True)

    week_schedule = {}
    for day_name in DAYS_OF_WEEK:
        week_schedule[day_name] = await get_schedule(session=session, group_id=user.group_id, week=next_week_type, weekday=day_name, vk_id=user.vk_id)

    text = format_week_text(next_week_type, week_schedule, "следующую неделю")
    await event.edit_message(text, attachment="", keyboard=nextWeekToggleKeyboard(show_image=False))


async def _render_week(event: MessageEvent, session: AsyncSession, week_type: str, header: str, show_image: bool, kb: str):
    user = await get_user(session=session, vk_id=event.user_id)
    if not user:
        await event.show_snackbar("Сначала нужно пройти регистрацию")
        return

    week_schedule = {}
    for day_name in DAYS_OF_WEEK:
        week_schedule[day_name] = await get_schedule(session=session, group_id=user.group_id, week=week_type, weekday=day_name, vk_id=user.vk_id)

    if show_image:
        buffer = generate_week_schedule_image(
            {d: schedule_to_image_items(s) for d, s in week_schedule.items() if s},
            header,
        )
        uploader = PhotoMessageUploader(event.ctx_api)
        attachment = await uploader.upload(buffer, peer_id=event.peer_id)
        await event.edit_message(f"📅 Расписание на {header}", attachment=attachment, keyboard=kb)
    else:
        text = format_week_text(week_type, week_schedule, header)
        await event.edit_message(text, attachment="", keyboard=kb)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "week_toggle_image"})
async def week_toggle_image(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    data = await advance_state(event.peer_id, ScheduleNavigation.week_viewing, show_image=True)
    header = "эту неделю"
    await _render_week(event, session, data.get("week_type", "all"), header, True, weekToggleKeyboard(show_image=True))


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "week_toggle_text"})
async def week_toggle_text(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    data = await advance_state(event.peer_id, ScheduleNavigation.week_viewing, show_image=False)
    header = "эту неделю"
    await _render_week(event, session, data.get("week_type", "all"), header, False, weekToggleKeyboard(show_image=False))


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "next_week_toggle_image"})
async def next_week_toggle_image(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    data = await advance_state(event.peer_id, ScheduleNavigation.week_viewing, show_image=True)
    header = "следующую неделю"
    await _render_week(event, session, data.get("week_type", "all"), header, True, nextWeekToggleKeyboard(show_image=True))


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "next_week_toggle_text"})
async def next_week_toggle_text(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    data = await advance_state(event.peer_id, ScheduleNavigation.week_viewing, show_image=False)
    header = "следующую неделю"
    await _render_week(event, session, data.get("week_type", "all"), header, False, nextWeekToggleKeyboard(show_image=False))


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": lambda v: v in ("week_all", "week_up", "week_down")})
async def change_week_type(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    new_week_type = event.payload["cmd"][len("week_"):]

    data = await get_state_data(event.peer_id)
    if new_week_type == data.get("week_type", "all"):
        await event.show_snackbar("Расписание уже отображается")
        return

    data = await advance_state(event.peer_id, ScheduleNavigation.navigating, week_type=new_week_type)
    await _render_day(event, session, data.get("day_index", 0), new_week_type, data.get("show_image", False))


# ---------------------------------------------------------------------------
# Скрытие предметов
# ---------------------------------------------------------------------------

@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "back_to_main_menu"})
async def back_to_main_menu(event: MessageEvent):
    await event.send_empty_answer()
    await clear_state(event.peer_id)
    await _delete_event_message(event)


async def _render_hide_subjects_for_day(event: MessageEvent, session: AsyncSession, day_index: int):
    user = await get_user(session=session, vk_id=event.user_id)
    if not user:
        await event.show_snackbar("Сначала нужно пройти регистрацию")
        return

    selected_day = DAYS_OF_WEEK[day_index]
    await advance_state(event.peer_id, HideSubject.selecting_subject, selected_day=selected_day, day_index=day_index)

    schedule = await get_schedule(session=session, group_id=user.group_id, week="all", weekday=selected_day)

    if not schedule:
        await event.edit_message(f"На {selected_day} нет пар.", keyboard=dayNavOnlyKeyboard(day_index, "back_to_hide_menu", "nav_hide_day_"))
        return

    subjects_list = sorted({lesson.subject for lesson in schedule})
    await advance_state(event.peer_id, HideSubject.selecting_subject, subjects=subjects_list)

    kb = dayNavWithSubjectsKeyboard(day_index, "hide_subj_", subjects_list, "back_to_hide_menu", "nav_hide_day_")
    await event.edit_message(f"Выберите предмет для скрытия на {selected_day}:", keyboard=kb)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": lambda v: v.startswith("hide_day_")})
async def hide_day_selected(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    day_index = int(event.payload["cmd"][len("hide_day_"):])
    await _render_hide_subjects_for_day(event, session, day_index)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": lambda v: v.startswith("nav_hide_day_")})
async def nav_hide_day(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    day_index = int(event.payload["cmd"][len("nav_hide_day_"):])
    await _render_hide_subjects_for_day(event, session, day_index)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": lambda v: v.startswith("hide_subj_")})
async def hide_subject_selected(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    user = await get_user(session=session, vk_id=event.user_id)
    if not user:
        return

    subject_idx = int(event.payload["cmd"][len("hide_subj_"):])
    data = await get_state_data(event.peer_id)
    subjects_list = data.get("subjects", [])
    selected_day = data.get("selected_day")

    if subject_idx >= len(subjects_list):
        await event.show_snackbar("Ошибка: предмет не найден")
        return

    subject = subjects_list[subject_idx]
    await add_hidden_subject(session=session, vk_id=user.vk_id, subject=subject, weekday=selected_day)

    await event.edit_message(f"✅ Предмет '{subject}' скрыт на {selected_day}.")
    await clear_state(event.peer_id)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "back_to_hide_menu"})
async def back_to_hide_menu(event: MessageEvent):
    await event.send_empty_answer()
    await set_state(event.peer_id, HideSubject.selecting_day)
    await event.edit_message("Выберите день недели, на котором хотите скрыть предмет:", keyboard=hideSubjectDayKeyboard())


# ---------------------------------------------------------------------------
# Просмотр скрытых предметов
# ---------------------------------------------------------------------------

async def _render_hidden_subjects_for_day(event: MessageEvent, session: AsyncSession, day_index: int):
    user = await get_user(session=session, vk_id=event.user_id)
    if not user:
        await event.show_snackbar("Сначала нужно пройти регистрацию")
        return

    selected_day = DAYS_OF_WEEK[day_index]
    await advance_state(event.peer_id, ViewHiddenSubjects.viewing_subjects, selected_day=selected_day, day_index=day_index)

    hidden_subjects = await get_hidden_subjects_by_day(session=session, vk_id=user.vk_id, weekday=selected_day)

    if not hidden_subjects:
        await event.edit_message(
            f"На {selected_day} нет скрытых предметов.",
            keyboard=dayNavOnlyKeyboard(day_index, "back_to_hidden_menu", "nav_hidden_day_"),
        )
        return

    await advance_state(event.peer_id, ViewHiddenSubjects.viewing_subjects, hidden_subjects=hidden_subjects)
    kb = dayNavWithSubjectsKeyboard(day_index, "view_subj_", hidden_subjects, "back_to_hidden_menu", "nav_hidden_day_")
    await event.edit_message(f"Скрытые предметы на {selected_day}:", keyboard=kb)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": lambda v: v.startswith("view_hidden_day_")})
async def view_hidden_day_selected(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    day_index = int(event.payload["cmd"][len("view_hidden_day_"):])
    await _render_hidden_subjects_for_day(event, session, day_index)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": lambda v: v.startswith("nav_hidden_day_")})
async def nav_hidden_day(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    day_index = int(event.payload["cmd"][len("nav_hidden_day_"):])
    await _render_hidden_subjects_for_day(event, session, day_index)


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "back_to_hidden_menu"})
async def back_to_hidden_menu(event: MessageEvent):
    await event.send_empty_answer()
    await set_state(event.peer_id, ViewHiddenSubjects.selecting_day)
    await event.edit_message("Выберите день недели для просмотра скрытых предметов:", keyboard=viewHiddenSubjectDayKeyboard())


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": lambda v: v.startswith("view_subj_")})
async def view_subject_selected(event: MessageEvent):
    await event.send_empty_answer()
    subject_idx = int(event.payload["cmd"][len("view_subj_"):])
    data = await get_state_data(event.peer_id)
    hidden_subjects = data.get("hidden_subjects", [])
    selected_day = data.get("selected_day")

    if subject_idx >= len(hidden_subjects):
        await event.show_snackbar("Ошибка: предмет не найден")
        return

    subject = hidden_subjects[subject_idx]
    await event.edit_message(
        f"Предмет: {subject}\nДень: {selected_day}\n\nУдалить из скрытых?",
        keyboard=confirmUnhideKeyboard(subject_idx),
    )


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": lambda v: v.startswith("remove_subj_")})
async def remove_subject(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    user = await get_user(session=session, vk_id=event.user_id)
    if not user:
        return

    subject_idx = int(event.payload["cmd"][len("remove_subj_"):])
    data = await get_state_data(event.peer_id)
    hidden_subjects = data.get("hidden_subjects", [])
    selected_day = data.get("selected_day")

    if subject_idx >= len(hidden_subjects):
        await event.show_snackbar("Ошибка: предмет не найден")
        return

    subject = hidden_subjects[subject_idx]
    await remove_hidden_subject(session=session, vk_id=user.vk_id, subject=subject, weekday=selected_day)

    updated_hidden = await get_hidden_subjects_by_day(session=session, vk_id=user.vk_id, weekday=selected_day)

    if not updated_hidden:
        await event.edit_message(f"✅ Предмет '{subject}' удалён из скрытых.\n\nНа {selected_day} больше нет скрытых предметов.")
        await clear_state(event.peer_id)
        return

    await advance_state(event.peer_id, ViewHiddenSubjects.viewing_subjects, hidden_subjects=updated_hidden)
    await event.edit_message(
        f"✅ Предмет '{subject}' удалён из скрытых.\n\nСкрытые предметы на {selected_day}:",
        keyboard=hiddenSubjectsListKeyboard(updated_hidden),
    )


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "back_to_hidden"})
async def back_to_hidden(event: MessageEvent):
    await event.send_empty_answer()
    data = await get_state_data(event.peer_id)
    hidden_subjects = data.get("hidden_subjects", [])
    day_index = data.get("day_index", 0)
    selected_day = data.get("selected_day")

    if not hidden_subjects:
        await event.edit_message(
            f"На {selected_day} нет скрытых предметов.",
            keyboard=dayNavOnlyKeyboard(day_index, "back_to_hidden_menu", "nav_hidden_day_"),
        )
        return

    kb = dayNavWithSubjectsKeyboard(day_index, "view_subj_", hidden_subjects, "back_to_hidden_menu", "nav_hidden_day_")
    await event.edit_message(f"Скрытые предметы на {selected_day}:", keyboard=kb)


# ---------------------------------------------------------------------------
# Домашние задания
# ---------------------------------------------------------------------------

@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "homework_add"})
async def homework_add_start(event: MessageEvent):
    await event.send_empty_answer()
    await set_state(event.peer_id, HomeworkManagement.adding_name)
    await event.edit_message("Введите название домашки:", attachment="", keyboard=homeworkAddKeyboard())


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": lambda v: v.startswith("homework_view_")})
async def homework_view(event: MessageEvent):
    await event.send_empty_answer()
    homework_idx = int(event.payload["cmd"][len("homework_view_"):])
    data = await get_state_data(event.peer_id)
    homeworks = data.get("homeworks", [])

    if homework_idx >= len(homeworks):
        await event.show_snackbar("Ошибка: домашка не найдена")
        return

    homework = homeworks[homework_idx]

    response = f"📝 {homework.name}\n\n"
    if homework.description:
        response += f"📄 Описание:\n{homework.description}\n\n"
    if homework.remind_time:
        remind_datetime = datetime.fromtimestamp(homework.remind_time)
        response += f"⏰ Напомнить: {remind_datetime.strftime('%d.%m.%Y %H:%M')}\n\n"
    response += "📎 Файл прикреплён" if homework.file_id else "📎 Файл не прикреплён"

    await event.edit_message(response, attachment=homework.file_id or "", keyboard=homeworkViewKeyboard(homework_idx))


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": lambda v: v.startswith("homework_delete_")})
async def homework_delete(event: MessageEvent, session: AsyncSession):
    await event.send_empty_answer()
    homework_idx = int(event.payload["cmd"][len("homework_delete_"):])
    data = await get_state_data(event.peer_id)
    homeworks = data.get("homeworks", [])

    if homework_idx >= len(homeworks):
        await event.show_snackbar("Ошибка: домашка не найдена")
        return

    homework = homeworks[homework_idx]
    await delete_homework(session=session, homework_id=homework.id)

    user = await get_user(session=session, vk_id=event.user_id)
    homeworks = await get_user_homeworks(session=session, vk_id=user.vk_id) if user else []
    await advance_state(event.peer_id, HomeworkManagement.viewing_list, homeworks=homeworks)

    text = "У вас пока нет домашних заданий." if not homeworks else "Ваши домашние задания:"
    await event.edit_message(text, attachment="", keyboard=homeworkListKeyboard(homeworks))


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "homework_back_to_list"})
async def homework_back_to_list(event: MessageEvent):
    await event.send_empty_answer()
    data = await get_state_data(event.peer_id)
    homeworks = data.get("homeworks", [])
    await set_state(event.peer_id, HomeworkManagement.viewing_list, homeworks=homeworks)

    text = "У вас пока нет домашних заданий." if not homeworks else "Ваши домашние задания:"
    await event.edit_message(text, attachment="", keyboard=homeworkListKeyboard(homeworks))


@callbacks_labeler.raw_event(GroupEventType.MESSAGE_EVENT, MessageEvent, payload_map={"cmd": "homework_cancel"})
async def homework_cancel(event: MessageEvent):
    await event.send_empty_answer()
    await clear_state(event.peer_id)
    await _delete_event_message(event)
