from aiogram import Router, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.inline import generateGroupsKeyboard, dayNavigationKeyboard, weekViewKeyboard, daySelectionKeyboard, nextWeekViewKeyboard, nextDaySelectionKeyboard, weekToggleKeyboard, nextWeekToggleKeyboard, hideSubjectDayKeyboard, viewHiddenSubjectDayKeyboard, homeworkListKeyboard, homeworkAddKeyboard, homeworkViewKeyboard, notifyBeforeLessonsKeyboard, applyResetKeyboard, settingsInlineKeyboard
from keyboards.reply import mainMenuKeyboard, settingsKeyboard, notifyBeforeAllLessonsKeyboard
from database.requests import get_user, get_schedule, add_hidden_subject, get_hidden_subjects_by_day, remove_hidden_subject, add_homework, get_user_homeworks, delete_homework, update_user_notify_time, update_user_notify_before_min, delete_user
from services.gen_schedule import generate_schedule_image, generate_week_schedule_image
from services.get_time import get_time_notifications_all_session, get_time_notifications_one_session, get_week_type
from datetime import datetime, date, timedelta

user_router = Router()


def format_time(seconds: int | None) -> str:
    """Форматирует секунды в формат ЧЧ:ММ."""
    if seconds is None:
        return "Не указано"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"

class ScheduleNavigation(StatesGroup):
    navigating = State()
    week_viewing = State()


class HideSubject(StatesGroup):
    selecting_day = State()
    selecting_subject = State()


class ViewHiddenSubjects(StatesGroup):
    selecting_day = State()
    viewing_subjects = State()


class HomeworkManagement(StatesGroup):
    viewing_list = State()
    adding_name = State()
    adding_description = State()
    adding_file = State()
    adding_remind_time = State()


class SettingsManagement(StatesGroup):
    in_settings = State()
    changing_notify_before = State()
    changing_notify_day = State()
    confirming_reset = State()

# Хранилище для сообщений с расписанием (для редактирования)
schedule_messages = {}

@user_router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Добро пожаловать в бота ГУАП! 🎓\n\n"
        "Выберите действие:",
        reply_markup=mainMenuKeyboard()
    )

@user_router.message(Command("main"))
async def cmd_main(message: Message):
    await message.answer(
        "Главное меню 🎓\n\n"
        "Выберите действие:",
        reply_markup=mainMenuKeyboard()
    )


@user_router.message(Command("menu"))
async def cmd_menu(message: Message):
    await message.answer(
        "Главное меню 🎓\n\n"
        "Выберите действие:",
        reply_markup=mainMenuKeyboard()
    )

@user_router.message(F.text == "📅 Сегодня")
async def cmd_today(message: Message, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=message.from_user.id)
    
    if not user:
        await message.answer("Сначала нужно пройти регистрацию. Напиши /start")
        return
    
    # Определяем текущий день недели и тип недели
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    current_day_index = datetime.now().weekday()
    current_day = days_of_week[current_day_index]
    current_week_type = get_week_type()
    
    # Сохраняем индекс текущего дня, режим отображения и тип недели в состоянии
    await state.update_data(day_index=current_day_index, show_image=False, week_type=current_week_type)
    await state.set_state(ScheduleNavigation.navigating)
    
    # Получаем расписание на сегодня для текущей недели
    schedule = await get_schedule(
        session=session,
        group_id=user.group_id,
        week=current_week_type,
        weekday=current_day,
        tg_id=user.tg_id
    )
    
    if not schedule:
        week_indicator = "🔴" if current_week_type == "up" else "🔵" if current_week_type == "down" else "⚪"
        response = f"{week_indicator} На сегодня ({current_day}) пар нет 🎉"
    else:
        # Форматируем расписание в текст
        week_indicator = "🔴" if current_week_type == "up" else "🔵" if current_week_type == "down" else "⚪"
        week_text = "нечётной" if current_week_type == "up" else "чётной"
        response = f"{week_indicator} 📅 Расписание на {current_day} ({week_text} неделя):\n\n"
        schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
        
        for lesson in schedule_sorted:
            hours = lesson.start_time // 3600
            minutes = (lesson.start_time % 3600) // 60
            time_str = f"{hours:02d}:{minutes:02d}"
            
            # Индикатор типа недели для конкретной пары
            lesson_indicator = "🟥" if lesson.week == "up" else "🟦" if lesson.week == "down" else "⬜"
            
            # Тип занятия
            lesson_type_display = f" [{lesson.lesson_type}]" if lesson.lesson_type else ""
            
            response += f"{lesson_indicator} {lesson.class_num}. {lesson.subject}{lesson_type_display}\n"
            response += f"   🕐 {time_str}\n"
            response += f"   👨‍🏫 {lesson.teacher}\n"
            response += f"   🏢 {lesson.room}\n\n"
    
    # Отправляем текст с клавиатурой навигации
    msg = await message.answer(response, reply_markup=dayNavigationKeyboard(current_day_index, show_image=False, week_type=current_week_type))
    
    # Сохраняем сообщение для редактирования
    schedule_messages[message.from_user.id] = msg.message_id

@user_router.message(F.text == "📆 Завтра")
async def cmd_tomorrow(message: Message, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=message.from_user.id)
    
    if not user:
        await message.answer("Сначала нужно пройти регистрацию. Напиши /start")
        return
    
    # Определяем завтрашний день недели и тип недели
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    tomorrow = date.today() + timedelta(days=1)
    tomorrow_day_index = tomorrow.weekday()
    tomorrow_day = days_of_week[tomorrow_day_index]
    tomorrow_week_type = get_week_type(tomorrow)
    
    # Сохраняем индекс завтрашнего дня, режим отображения и тип недели в состоянии
    await state.update_data(day_index=tomorrow_day_index, show_image=False, week_type=tomorrow_week_type)
    await state.set_state(ScheduleNavigation.navigating)
    
    # Получаем расписание на завтра для соответствующей недели
    schedule = await get_schedule(
        session=session,
        group_id=user.group_id,
        week=tomorrow_week_type,
        weekday=tomorrow_day,
        tg_id=user.tg_id
    )
    
    if not schedule:
        week_indicator = "🔴" if tomorrow_week_type == "up" else "🔵" if tomorrow_week_type == "down" else "⚪"
        response = f"{week_indicator} На завтра ({tomorrow_day}) пар нет 🎉"
    else:
        # Форматируем расписание в текст
        week_indicator = "🔴" if tomorrow_week_type == "up" else "🔵" if tomorrow_week_type == "down" else "⚪"
        week_text = "нечётной" if tomorrow_week_type == "up" else "чётной"
        response = f"{week_indicator} 📅 Расписание на {tomorrow_day} ({week_text} неделя):\n\n"
        schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
        
        for lesson in schedule_sorted:
            hours = lesson.start_time // 3600
            minutes = (lesson.start_time % 3600) // 60
            time_str = f"{hours:02d}:{minutes:02d}"
            
            # Тип занятия
            lesson_type_display = f" [{lesson.lesson_type}]" if lesson.lesson_type else ""
            
            response += f"🔹 {lesson.class_num}. {lesson.subject}{lesson_type_display}\n"
            response += f"   🕐 {time_str}\n"
            response += f"   👨‍🏫 {lesson.teacher}\n"
            response += f"   🏢 {lesson.room}\n\n"
    
    # Отправляем текст с клавиатурой навигации
    msg = await message.answer(response, reply_markup=dayNavigationKeyboard(tomorrow_day_index, show_image=False, week_type=tomorrow_week_type))
    
    # Сохраняем сообщение для редактирования
    schedule_messages[message.from_user.id] = msg.message_id

@user_router.message(F.text == "🗓 Эта неделя")
async def cmd_this_week(message: Message):
    await message.answer("Выберите режим просмотра расписания на неделю:", reply_markup=weekViewKeyboard())

@user_router.message(F.text == "📋 След. неделя")
async def cmd_next_week(message: Message):
    await message.answer("Выберите режим просмотра расписания на следующую неделю:", reply_markup=nextWeekViewKeyboard())


@user_router.message(F.text == "📝 Домашка")
async def cmd_homework(message: Message, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=message.from_user.id)
    
    if not user:
        await message.answer("Сначала нужно пройти регистрацию. Напиши /start")
        return
    
    # Получаем домашние задания пользователя из базы данных
    homeworks = await get_user_homeworks(session=session, tg_id=user.tg_id)
    
    if not homeworks:
        await message.answer("У вас пока нет домашних заданий.", reply_markup=homeworkListKeyboard(homeworks))
    else:
        await message.answer("Ваши домашние задания:", reply_markup=homeworkListKeyboard(homeworks))
    
    await state.set_state(HomeworkManagement.viewing_list)
    await state.update_data(homeworks=homeworks)

@user_router.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: Message, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=message.from_user.id)
    
    if not user:
        await message.answer("Сначала нужно пройти регистрацию. Напиши /start")
        return
    
    await message.answer("⚙️ Настройки", reply_markup=settingsKeyboard())
    await state.set_state(SettingsManagement.in_settings)


@user_router.message(SettingsManagement.in_settings, F.text == "🔙 Назад")
async def settings_back(message: Message, state: FSMContext):
    await message.answer("Главное меню", reply_markup=mainMenuKeyboard())
    await state.clear()


@user_router.message(SettingsManagement.in_settings, F.text == "⏰ Уведомления перед парой")
async def settings_change_notify_before(message: Message, state: FSMContext):
    await message.answer("Я могу присылать уведомления о предстоящей паре за несколько минут до неё. Если нужно, укажи за сколько.", reply_markup=notifyBeforeLessonsKeyboard())
    await state.set_state(SettingsManagement.changing_notify_before)


@user_router.callback_query(SettingsManagement.changing_notify_before, F.data.startswith("USERS_TIME_BEFORELESSONS"))
async def settings_write_users_time(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Напиши время, за которое тебе надо отправлять уведомление о парах (максимум 3 часа, формат времени ЧЧ:ММ)")
    await state.set_state(SettingsManagement.changing_notify_before)


@user_router.message(SettingsManagement.changing_notify_before)
async def settings_notify_before_confirm(message: Message, state: FSMContext, session: AsyncSession):
    result = get_time_notifications_one_session(message.text)
    if result is None:
        await message.answer("Время написано некорректно! Напиши время в формате ЧЧ:ММ, не более 3 часов (к примеру 02:21)")
    else:
        # get_time_notifications_one_session возвращает секунды → сохраняем минуты
        minutes = result // 60
        user = await get_user(session=session, tg_id=message.from_user.id)
        if user:
            await update_user_notify_before_min(
                session=session,
                tg_id=user.tg_id,
                notify_before_min=minutes
            )
        
        await message.answer(f"✅ Уведомления перед парой установлены за {minutes} минут", reply_markup=settingsKeyboard())
        await state.set_state(SettingsManagement.in_settings)


@user_router.callback_query(SettingsManagement.changing_notify_before, F.data.startswith("BEFORELESSONS_"))
async def settings_notify_before_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    selected_variant = callback.data.replace("BEFORELESSONS_", "", 1)
    
    if selected_variant == "DONT_NOTIFY":
        result = 0
    else:
        result = int(selected_variant)
    
    user = await get_user(session=session, tg_id=callback.from_user.id)
    if user:
        await update_user_notify_before_min(
            session=session,
            tg_id=user.tg_id,
            notify_before_min=result
        )
    
    if result:
        await callback.message.edit_text(f"✅ Уведомления перед парой установлены за {result} минут", reply_markup=settingsInlineKeyboard())
    else:
        await callback.message.edit_text("✅ Уведомления перед парой отключены", reply_markup=settingsInlineKeyboard())
    
    await state.set_state(SettingsManagement.in_settings)


@user_router.message(SettingsManagement.in_settings, F.text == "📅 Уведомления перед днём")
async def settings_change_notify_day(message: Message, state: FSMContext):
    await message.answer("Я могу присылать уведомления о целом дне в указанное тобой время. Если нужно, укажи за сколько. Так же ты можешь указать своё время в формате <b>ЧЧ:ММ</b>", parse_mode="HTML", reply_markup=notifyBeforeAllLessonsKeyboard())
    await state.set_state(SettingsManagement.changing_notify_day)


@user_router.message(SettingsManagement.changing_notify_day)
async def settings_notify_day_confirm(message: Message, state: FSMContext, session: AsyncSession):
    result = get_time_notifications_all_session(message.text)
    if result is None and message.text != "Не присылать":
        await message.answer(text="<b>Время должно быть в формате ЧЧ:ММ!</b> \nДля продолжения введи корректное время или выбери из предложенного", parse_mode="HTML")
    else:
        user = await get_user(session=session, tg_id=message.from_user.id)
        if user:
            await update_user_notify_time(
                session=session,
                tg_id=user.tg_id,
                notify_time=result
            )
        
        if result is not None:
            await message.answer(f"✅ Уведомления перед днём установлены на {format_time(result)}", reply_markup=settingsKeyboard())
        else:
            await message.answer("✅ Уведомления перед днём отключены", reply_markup=settingsKeyboard())
        
        await state.set_state(SettingsManagement.in_settings)


@user_router.message(SettingsManagement.in_settings, F.text == "🗑 Сброс аккаунта")
async def settings_reset_account(message: Message, state: FSMContext):
    await message.answer("⚠️ Вы уверены, что хотите сбросить аккаунт? <b>Все данные, включая домашние задания, будут удалены!</b>", parse_mode="HTML", reply_markup=applyResetKeyboard())
    await state.set_state(SettingsManagement.confirming_reset)


@user_router.callback_query(SettingsManagement.confirming_reset, F.data == "RESET_YES")
async def settings_confirm_reset(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    await delete_user(session=session, tg_id=callback.from_user.id)
    await callback.message.edit_text(f"Привет, {callback.from_user.full_name}, напиши свою группу!")
    await state.clear()
    # Переключаемся на регистрацию
    from handlers.registration import Registration
    await state.set_state(Registration.waitingForGroup)


@user_router.callback_query(SettingsManagement.confirming_reset, F.data == "RESET_NO")
async def settings_cancel_reset(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("⚙️ Настройки", reply_markup=settingsInlineKeyboard())
    await state.set_state(SettingsManagement.in_settings)


@user_router.callback_query(SettingsManagement.in_settings, F.data == "settings_back")
async def settings_inline_back(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await callback.message.answer("Главное меню", reply_markup=mainMenuKeyboard())
    await state.clear()


@user_router.callback_query(SettingsManagement.in_settings, F.data == "settings_notify_before")
async def settings_inline_notify_before(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("Я могу присылать уведомления о предстоящей паре за несколько минут до неё. Если нужно, укажи за сколько.", reply_markup=notifyBeforeLessonsKeyboard())
    await state.set_state(SettingsManagement.changing_notify_before)


@user_router.callback_query(SettingsManagement.in_settings, F.data == "settings_notify_day")
async def settings_inline_notify_day(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("Я могу присылать уведомления о целом дне в указанное тобой время. Если нужно, укажи за сколько. Так же ты можешь указать своё время в формате <b>ЧЧ:ММ</b>", parse_mode="HTML", reply_markup=notifyBeforeAllLessonsKeyboard())
    await state.set_state(SettingsManagement.changing_notify_day)


@user_router.callback_query(SettingsManagement.in_settings, F.data == "settings_reset")
async def settings_inline_reset(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text("⚠️ Вы уверены, что хотите сбросить аккаунт? <b>Все данные, включая домашние задания, будут удалены!</b>", parse_mode="HTML", reply_markup=applyResetKeyboard())
    await state.set_state(SettingsManagement.confirming_reset)


@user_router.message(F.text == "🙈 Скрыть предметы")
async def cmd_hide_subject(message: Message, state: FSMContext):
    await message.answer("Выберите день недели, на котором хотите скрыть предмет:", reply_markup=hideSubjectDayKeyboard())
    await state.set_state(HideSubject.selecting_day)


@user_router.message(F.text == "👁️ Скрытые предметы")
async def cmd_view_hidden_subjects(message: Message, state: FSMContext):
    await message.answer("Выберите день недели для просмотра скрытых предметов:", reply_markup=viewHiddenSubjectDayKeyboard())
    await state.set_state(ViewHiddenSubjects.selecting_day)


@user_router.callback_query(HideSubject.selecting_day, F.data == "back_to_main_menu")
async def back_to_main_menu_from_hide(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer()


@user_router.callback_query(ViewHiddenSubjects.selecting_day, F.data == "back_to_main_menu")
async def back_to_main_menu_from_view(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer()


@user_router.callback_query(HideSubject.selecting_day, F.data.startswith("hide_day_"))
async def hide_day_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    # Получаем индекс дня из callback_data
    day_index = int(callback.data.replace("hide_day_", "", 1))
    
    # Сохраняем выбранный день
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    selected_day = days_of_week[day_index]
    await state.update_data(selected_day=selected_day, day_index=day_index)
    await state.set_state(HideSubject.selecting_subject)
    
    # Получаем расписание на выбранный день
    schedule = await get_schedule(
        session=session,
        group_id=user.group_id,
        week="all",
        weekday=selected_day
    )
    
    if not schedule:
        # Создаём клавиатуру навигации по дням
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        nav_keyboard = InlineKeyboardBuilder()
        
        # Кнопки навигации
        prev_day_index = (day_index - 1) % 7
        next_day_index = (day_index + 1) % 7
        nav_keyboard.button(text=f"◀ {days_of_week[prev_day_index].capitalize()}", callback_data=f"nav_hide_day_{prev_day_index}")
        nav_keyboard.button(text=f"{days_of_week[next_day_index].capitalize()} ▶", callback_data=f"nav_hide_day_{next_day_index}")
        nav_keyboard.button(text="🔙 В меню", callback_data="back_to_hide_menu")
        nav_keyboard.adjust(2, 1)
        
        await callback.message.edit_text(f"На {selected_day} нет пар.", reply_markup=nav_keyboard.as_markup())
        await callback.answer()
        return
    
    # Создаём клавиатуру с предметами и навигацией
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    subject_keyboard = InlineKeyboardBuilder()
    
    # Получаем уникальные предметы и сохраняем их в состоянии
    subjects = set()
    for lesson in schedule:
        subjects.add(lesson.subject)
    
    subjects_list = sorted(subjects)
    await state.update_data(subjects=subjects_list)
    
    # Используем индексы вместо полных названий для callback data
    for idx, subject in enumerate(subjects_list):
        subject_keyboard.button(text=subject, callback_data=f"hide_subj_{idx}")
    
    # Кнопки навигации
    prev_day_index = (day_index - 1) % 7
    next_day_index = (day_index + 1) % 7
    subject_keyboard.button(text=f"◀ {days_of_week[prev_day_index].capitalize()}", callback_data=f"nav_hide_day_{prev_day_index}")
    subject_keyboard.button(text=f"{days_of_week[next_day_index].capitalize()} ▶", callback_data=f"nav_hide_day_{next_day_index}")
    subject_keyboard.button(text="🔙 В меню", callback_data="back_to_hide_menu")
    subject_keyboard.adjust(1, 2, 1)
    
    await callback.message.edit_text(f"Выберите предмет для скрытия на {selected_day}:", reply_markup=subject_keyboard.as_markup())
    await callback.answer()


@user_router.callback_query(HideSubject.selecting_subject, F.data.startswith("hide_subj_"))
async def hide_subject_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    # Получаем индекс предмета из callback_data
    subject_idx = int(callback.data.replace("hide_subj_", "", 1))
    
    # Получаем список предметов и выбранный день из состояния
    data = await state.get_data()
    subjects_list = data.get("subjects", [])
    selected_day = data.get("selected_day")
    
    # Проверяем, что индекс валидный
    if subject_idx >= len(subjects_list):
        await callback.answer("Ошибка: предмет не найден")
        return
    
    subject = subjects_list[subject_idx]
    
    # Добавляем предмет в список скрытых
    await add_hidden_subject(session=session, tg_id=user.tg_id, subject=subject, weekday=selected_day)
    
    await callback.message.edit_text(f"✅ Предмет '{subject}' скрыт на {selected_day}.")
    await state.clear()
    await callback.answer()


@user_router.callback_query(HideSubject.selecting_subject, F.data == "back_to_hide_menu")
async def back_to_hide_menu_callback(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Выберите день недели, на котором хотите скрыть предмет:", reply_markup=hideSubjectDayKeyboard())
    await state.set_state(HideSubject.selecting_day)
    await callback.answer()


@user_router.callback_query(HideSubject.selecting_subject, F.data.startswith("nav_hide_day_"))
async def nav_hide_day_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    # Получаем индекс дня из callback_data
    day_index = int(callback.data.replace("nav_hide_day_", "", 1))
    
    # Сохраняем выбранный день
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    selected_day = days_of_week[day_index]
    await state.update_data(selected_day=selected_day, day_index=day_index)
    
    # Получаем расписание на выбранный день
    schedule = await get_schedule(
        session=session,
        group_id=user.group_id,
        week="all",
        weekday=selected_day
    )
    
    if not schedule:
        # Создаём клавиатуру навигации по дням
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        nav_keyboard = InlineKeyboardBuilder()
        
        # Кнопки навигации
        prev_day_index = (day_index - 1) % 7
        next_day_index = (day_index + 1) % 7
        nav_keyboard.button(text=f"◀ {days_of_week[prev_day_index].capitalize()}", callback_data=f"nav_hide_day_{prev_day_index}")
        nav_keyboard.button(text=f"{days_of_week[next_day_index].capitalize()} ▶", callback_data=f"nav_hide_day_{next_day_index}")
        nav_keyboard.button(text="🔙 В меню", callback_data="back_to_hide_menu")
        nav_keyboard.adjust(2, 1)
        
        await callback.message.edit_text(f"На {selected_day} нет пар.", reply_markup=nav_keyboard.as_markup())
        await callback.answer()
        return
    
    # Создаём клавиатуру с предметами и навигацией
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    subject_keyboard = InlineKeyboardBuilder()
    
    # Получаем уникальные предметы и сохраняем их в состоянии
    subjects = set()
    for lesson in schedule:
        subjects.add(lesson.subject)
    
    subjects_list = sorted(subjects)
    await state.update_data(subjects=subjects_list)
    
    # Используем индексы вместо полных названий для callback data
    for idx, subject in enumerate(subjects_list):
        subject_keyboard.button(text=subject, callback_data=f"hide_subj_{idx}")
    
    # Кнопки навигации
    prev_day_index = (day_index - 1) % 7
    next_day_index = (day_index + 1) % 7
    subject_keyboard.button(text=f"◀ {days_of_week[prev_day_index].capitalize()}", callback_data=f"nav_hide_day_{prev_day_index}")
    subject_keyboard.button(text=f"{days_of_week[next_day_index].capitalize()} ▶", callback_data=f"nav_hide_day_{next_day_index}")
    subject_keyboard.button(text="🔙 В меню", callback_data="back_to_hide_menu")
    subject_keyboard.adjust(1, 2, 1)
    
    await callback.message.edit_text(f"Выберите предмет для скрытия на {selected_day}:", reply_markup=subject_keyboard.as_markup())
    await callback.answer()


@user_router.callback_query(ViewHiddenSubjects.selecting_day, F.data.startswith("view_hidden_day_"))
async def view_hidden_day_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    # Получаем индекс дня из callback_data
    day_index = int(callback.data.replace("view_hidden_day_", "", 1))
    
    # Сохраняем выбранный день
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    selected_day = days_of_week[day_index]
    await state.update_data(selected_day=selected_day, day_index=day_index)
    await state.set_state(ViewHiddenSubjects.viewing_subjects)
    
    # Получаем скрытые предметы для этого дня
    hidden_subjects = await get_hidden_subjects_by_day(session=session, tg_id=user.tg_id, weekday=selected_day)
    
    if not hidden_subjects:
        # Создаём клавиатуру навигации по дням
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        nav_keyboard = InlineKeyboardBuilder()
        
        # Кнопки навигации
        prev_day_index = (day_index - 1) % 7
        next_day_index = (day_index + 1) % 7
        nav_keyboard.button(text=f"◀ {days_of_week[prev_day_index].capitalize()}", callback_data=f"view_hidden_day_{prev_day_index}")
        nav_keyboard.button(text=f"{days_of_week[next_day_index].capitalize()} ▶", callback_data=f"view_hidden_day_{next_day_index}")
        nav_keyboard.button(text="🔙 В меню", callback_data="back_to_hidden_menu")
        nav_keyboard.adjust(2, 1)
        
        await callback.message.edit_text(f"На {selected_day} нет скрытых предметов.", reply_markup=nav_keyboard.as_markup())
        await callback.answer()
        return
    
    # Создаём клавиатуру с предметами и навигацией
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    subject_keyboard = InlineKeyboardBuilder()
    
    # Сохраняем список предметов в состоянии
    await state.update_data(hidden_subjects=hidden_subjects)
    
    # Используем индексы для callback data
    for idx, subject in enumerate(hidden_subjects):
        subject_keyboard.button(text=subject, callback_data=f"view_subj_{idx}")
    
    # Кнопки навигации
    prev_day_index = (day_index - 1) % 7
    next_day_index = (day_index + 1) % 7
    subject_keyboard.button(text=f"◀ {days_of_week[prev_day_index].capitalize()}", callback_data=f"view_hidden_day_{prev_day_index}")
    subject_keyboard.button(text=f"{days_of_week[next_day_index].capitalize()} ▶", callback_data=f"view_hidden_day_{next_day_index}")
    subject_keyboard.button(text="🔙 В меню", callback_data="back_to_hidden_menu")
    subject_keyboard.adjust(1, 2, 1)
    
    await callback.message.edit_text(f"Скрытые предметы на {selected_day}:", reply_markup=subject_keyboard.as_markup())
    await callback.answer()


@user_router.callback_query(ViewHiddenSubjects.viewing_subjects, F.data.startswith("view_subj_"))
async def view_subject_selected(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    # Получаем индекс предмета из callback_data
    subject_idx = int(callback.data.replace("view_subj_", "", 1))
    
    # Получаем список скрытых предметов и выбранный день из состояния
    data = await state.get_data()
    hidden_subjects = data.get("hidden_subjects", [])
    selected_day = data.get("selected_day")
    
    # Проверяем, что индекс валидный
    if subject_idx >= len(hidden_subjects):
        await callback.answer("Ошибка: предмет не найден")
        return
    
    subject = hidden_subjects[subject_idx]
    
    # Сохраняем выбранный предмет для удаления
    await state.update_data(selected_subject=subject)
    
    # Создаём клавиатуру подтверждения
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    confirm_keyboard = InlineKeyboardBuilder()
    confirm_keyboard.button(text="❌ Удалить из скрытых", callback_data=f"remove_subj_{subject_idx}")
    confirm_keyboard.button(text="🔙 Назад", callback_data="back_to_hidden")
    confirm_keyboard.adjust(1)
    
    await callback.message.edit_text(f"Предмет: {subject}\nДень: {selected_day}\n\nУдалить из скрытых?", reply_markup=confirm_keyboard.as_markup())
    await callback.answer()


@user_router.callback_query(ViewHiddenSubjects.viewing_subjects, F.data.startswith("remove_subj_"))
async def remove_subject_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    # Получаем индекс предмета из callback_data
    subject_idx = int(callback.data.replace("remove_subj_", "", 1))
    
    # Получаем данные из состояния
    data = await state.get_data()
    hidden_subjects = data.get("hidden_subjects", [])
    selected_day = data.get("selected_day")
    
    # Проверяем, что индекс валидный
    if subject_idx >= len(hidden_subjects):
        await callback.answer("Ошибка: предмет не найден")
        return
    
    subject = hidden_subjects[subject_idx]
    
    # Удаляем предмет из скрытых
    await remove_hidden_subject(session=session, tg_id=user.tg_id, subject=subject, weekday=selected_day)
    
    # Получаем обновлённый список скрытых предметов
    updated_hidden = await get_hidden_subjects_by_day(session=session, tg_id=user.tg_id, weekday=selected_day)
    
    if not updated_hidden:
        await callback.message.edit_text(f"✅ Предмет '{subject}' удалён из скрытых.\n\nНа {selected_day} больше нет скрытых предметов.")
        await state.clear()
        await callback.answer()
        return
    
    # Обновляем состояние и показываем обновлённый список
    await state.update_data(hidden_subjects=updated_hidden)
    
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    subject_keyboard = InlineKeyboardBuilder()
    
    for idx, subj in enumerate(updated_hidden):
        subject_keyboard.button(text=subj, callback_data=f"view_subj_{idx}")
    
    subject_keyboard.adjust(1)
    
    await callback.message.edit_text(f"✅ Предмет '{subject}' удалён из скрытых.\n\nСкрытые предметы на {selected_day}:", reply_markup=subject_keyboard.as_markup())
    await callback.answer()


@user_router.callback_query(ViewHiddenSubjects.viewing_subjects, F.data == "back_to_hidden")
async def back_to_hidden_callback(callback: CallbackQuery, state: FSMContext):
    # Получаем данные из состояния
    data = await state.get_data()
    hidden_subjects = data.get("hidden_subjects", [])
    selected_day = data.get("selected_day")
    day_index = data.get("day_index", 0)
    
    if not hidden_subjects:
        # Создаём клавиатуру навигации по дням
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        nav_keyboard = InlineKeyboardBuilder()
        
        days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
        prev_day_index = (day_index - 1) % 7
        next_day_index = (day_index + 1) % 7
        nav_keyboard.button(text=f"◀ {days_of_week[prev_day_index].capitalize()}", callback_data=f"nav_hidden_day_{prev_day_index}")
        nav_keyboard.button(text=f"{days_of_week[next_day_index].capitalize()} ▶", callback_data=f"nav_hidden_day_{next_day_index}")
        nav_keyboard.button(text="🔙 В меню", callback_data="back_to_hidden_menu")
        nav_keyboard.adjust(2, 1)
        
        await callback.message.edit_text(f"На {selected_day} нет скрытых предметов.", reply_markup=nav_keyboard.as_markup())
        await callback.answer()
        return
    
    # Создаём клавиатуру с предметами и навигацией
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    subject_keyboard = InlineKeyboardBuilder()
    
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    
    for idx, subject in enumerate(hidden_subjects):
        subject_keyboard.button(text=subject, callback_data=f"view_subj_{idx}")
    
    # Кнопки навигации
    prev_day_index = (day_index - 1) % 7
    next_day_index = (day_index + 1) % 7
    subject_keyboard.button(text=f"◀ {days_of_week[prev_day_index].capitalize()}", callback_data=f"nav_hidden_day_{prev_day_index}")
    subject_keyboard.button(text=f"{days_of_week[next_day_index].capitalize()} ▶", callback_data=f"nav_hidden_day_{next_day_index}")
    subject_keyboard.button(text="🔙 В меню", callback_data="back_to_hidden_menu")
    subject_keyboard.adjust(1, 2, 1)
    
    await callback.message.edit_text(f"Скрытые предметы на {selected_day}:", reply_markup=subject_keyboard.as_markup())
    await callback.answer()


@user_router.callback_query(ViewHiddenSubjects.viewing_subjects, F.data.startswith("nav_hidden_day_"))
async def nav_hidden_day_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    # Получаем индекс дня из callback_data
    day_index = int(callback.data.replace("nav_hidden_day_", "", 1))
    
    # Сохраняем выбранный день
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    selected_day = days_of_week[day_index]
    await state.update_data(selected_day=selected_day, day_index=day_index)
    
    # Получаем скрытые предметы для этого дня
    hidden_subjects = await get_hidden_subjects_by_day(session=session, tg_id=user.tg_id, weekday=selected_day)
    
    if not hidden_subjects:
        # Создаём клавиатуру навигации по дням
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        nav_keyboard = InlineKeyboardBuilder()
        
        # Кнопки навигации
        prev_day_index = (day_index - 1) % 7
        next_day_index = (day_index + 1) % 7
        nav_keyboard.button(text=f"◀ {days_of_week[prev_day_index].capitalize()}", callback_data=f"nav_hidden_day_{prev_day_index}")
        nav_keyboard.button(text=f"{days_of_week[next_day_index].capitalize()} ▶", callback_data=f"nav_hidden_day_{next_day_index}")
        nav_keyboard.button(text="🔙 В меню", callback_data="back_to_hidden_menu")
        nav_keyboard.adjust(2, 1)
        
        await callback.message.edit_text(f"На {selected_day} нет скрытых предметов.", reply_markup=nav_keyboard.as_markup())
        await callback.answer()
        return
    
    # Создаём клавиатуру с предметами и навигацией
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    subject_keyboard = InlineKeyboardBuilder()
    
    # Сохраняем список предметов в состоянии
    await state.update_data(hidden_subjects=hidden_subjects)
    
    # Используем индексы для callback data
    for idx, subject in enumerate(hidden_subjects):
        subject_keyboard.button(text=subject, callback_data=f"view_subj_{idx}")
    
    # Кнопки навигации
    prev_day_index = (day_index - 1) % 7
    next_day_index = (day_index + 1) % 7
    subject_keyboard.button(text=f"◀ {days_of_week[prev_day_index].capitalize()}", callback_data=f"nav_hidden_day_{prev_day_index}")
    subject_keyboard.button(text=f"{days_of_week[next_day_index].capitalize()} ▶", callback_data=f"nav_hidden_day_{next_day_index}")
    subject_keyboard.button(text="🔙 В меню", callback_data="back_to_hidden_menu")
    subject_keyboard.adjust(1, 2, 1)
    
    await callback.message.edit_text(f"Скрытые предметы на {selected_day}:", reply_markup=subject_keyboard.as_markup())
    await callback.answer()


@user_router.callback_query(HomeworkManagement.viewing_list, F.data == "homework_add")
async def homework_add_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Введите название домашки:", reply_markup=homeworkAddKeyboard())
    await state.set_state(HomeworkManagement.adding_name)
    await callback.answer()


@user_router.message(HomeworkManagement.adding_name)
async def homework_add_name(message: Message, state: FSMContext):
    await state.update_data(homework_name=message.text)
    await message.answer("Введите описание домашки (или пропустите, отправив /skip):", reply_markup=homeworkAddKeyboard())
    await state.set_state(HomeworkManagement.adding_description)


@user_router.message(HomeworkManagement.adding_description, F.text == "/skip")
async def homework_skip_description(message: Message, state: FSMContext):
    await state.update_data(homework_description=None)
    await message.answer("Прикрепите файл с домашкой (или пропустите, отправив /skip):", reply_markup=homeworkAddKeyboard())
    await state.set_state(HomeworkManagement.adding_file)


@user_router.message(HomeworkManagement.adding_description)
async def homework_add_description(message: Message, state: FSMContext):
    await state.update_data(homework_description=message.text)
    await message.answer("Прикрепите файл с домашкой (или пропустите, отправив /skip):", reply_markup=homeworkAddKeyboard())
    await state.set_state(HomeworkManagement.adding_file)


@user_router.message(HomeworkManagement.adding_file, F.text == "/skip")
async def homework_skip_file(message: Message, state: FSMContext):
    await state.update_data(homework_file_id=None)
    await message.answer("Укажите когда напомнить о домашке в формате ДД.ММ.ГГГГ ЧЧ:ММ (или пропустите, отправив /skip):", reply_markup=homeworkAddKeyboard())
    await state.set_state(HomeworkManagement.adding_remind_time)


@user_router.message(HomeworkManagement.adding_file, F.document)
async def homework_add_file(message: Message, state: FSMContext):
    await state.update_data(homework_file_id=message.document.file_id)
    await message.answer("Укажите когда напомнить о домашке в формате ДД.ММ.ГГГГ ЧЧ:ММ (или пропустите, отправив /skip):", reply_markup=homeworkAddKeyboard())
    await state.set_state(HomeworkManagement.adding_remind_time)


@user_router.message(HomeworkManagement.adding_remind_time, F.text == "/skip")
async def homework_skip_remind_time(message: Message, state: FSMContext, session: AsyncSession):
    await state.update_data(homework_remind_time=None)
    data = await state.get_data()
    
    user = await get_user(session=session, tg_id=message.from_user.id)
    if not user:
        await message.answer("Ошибка: пользователь не найден")
        await state.clear()
        return
    
    try:
        await add_homework(
            session=session,
            tg_id=user.tg_id,
            name=data.get("homework_name"),
            description=data.get("homework_description"),
            file_id=data.get("homework_file_id"),
            remind_time=None
        )
        await message.answer("✅ Домашка добавлена!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении домашки: {e}")
    
    await state.clear()


@user_router.message(HomeworkManagement.adding_remind_time)
async def homework_add_remind_time(message: Message, state: FSMContext, session: AsyncSession):
    try:
        remind_datetime = datetime.strptime(message.text, "%d.%m.%Y %H:%M")
        remind_timestamp = int(remind_datetime.timestamp())
    except ValueError:
        await message.answer("Неверный формат. Используйте ДД.ММ.ГГГГ ЧЧ:ММ (например: 25.12.2026 14:30)")
        return
    
    await state.update_data(homework_remind_time=remind_timestamp)
    data = await state.get_data()
    
    user = await get_user(session=session, tg_id=message.from_user.id)
    if not user:
        await message.answer("Ошибка: пользователь не найден")
        await state.clear()
        return
    
    try:
        await add_homework(
            session=session,
            tg_id=user.tg_id,
            name=data.get("homework_name"),
            description=data.get("homework_description"),
            file_id=data.get("homework_file_id"),
            remind_time=remind_timestamp
        )
        await message.answer("✅ Домашка добавлена!")
    except Exception as e:
        await message.answer(f"❌ Ошибка при добавлении домашки: {e}")
    
    await state.clear()


@user_router.callback_query(HomeworkManagement.viewing_list, F.data.startswith("homework_view_"))
async def homework_view(callback: CallbackQuery, state: FSMContext):
    homework_idx = int(callback.data.replace("homework_view_", "", 1))
    data = await state.get_data()
    homeworks = data.get("homeworks", [])
    
    if homework_idx >= len(homeworks):
        await callback.answer("Ошибка: домашка не найдена")
        return
    
    homework = homeworks[homework_idx]
    
    # Формируем сообщение с информацией о домашке
    response = f"📝 {homework.name}\n\n"
    
    if homework.description:
        response += f"📄 Описание:\n{homework.description}\n\n"
    
    if homework.remind_time:
        remind_datetime = datetime.fromtimestamp(homework.remind_time)
        response += f"⏰ Напомнить: {remind_datetime.strftime('%d.%m.%Y %H:%M')}\n\n"
    
    if homework.file_id:
        response += "📎 Файл прикреплён"
        # Отправляем файл
        await callback.message.answer_document(homework.file_id, caption=response, reply_markup=homeworkViewKeyboard(homework_idx))
        await callback.message.delete()
    else:
        response += "📎 Файл не прикреплён"
        await callback.message.edit_text(response, reply_markup=homeworkViewKeyboard(homework_idx))
    
    await callback.answer()


@user_router.callback_query(F.data.startswith("homework_delete_"))
async def homework_delete(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    homework_idx = int(callback.data.replace("homework_delete_", "", 1))
    data = await state.get_data()
    homeworks = data.get("homeworks", [])
    
    if homework_idx >= len(homeworks):
        await callback.answer("Ошибка: домашка не найдена")
        return
    
    homework = homeworks[homework_idx]
    await delete_homework(session=session, homework_id=homework.id)
    
    # Обновляем список
    user = await get_user(session=session, tg_id=callback.from_user.id)
    if user:
        homeworks = await get_user_homeworks(session=session, tg_id=user.tg_id)
        await state.update_data(homeworks=homeworks)
    
    # Удаляем сообщение (оно может быть с файлом) и отправляем новое
    await callback.message.delete()
    
    if not homeworks:
        msg = await callback.message.answer("У вас пока нет домашних заданий.", reply_markup=homeworkListKeyboard(homeworks))
    else:
        msg = await callback.message.answer("Ваши домашние задания:", reply_markup=homeworkListKeyboard(homeworks))
    
    await callback.answer("✅ Домашка удалена")


@user_router.callback_query(F.data == "homework_back_to_list")
async def homework_back_to_list(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    homeworks = data.get("homeworks", [])
    
    # Удаляем сообщение (оно может быть с файлом) и отправляем новое
    await callback.message.delete()
    
    if not homeworks:
        msg = await callback.message.answer("У вас пока нет домашних заданий.", reply_markup=homeworkListKeyboard(homeworks))
    else:
        msg = await callback.message.answer("Ваши домашние задания:", reply_markup=homeworkListKeyboard(homeworks))
    
    await state.set_state(HomeworkManagement.viewing_list)
    await callback.answer()


@user_router.callback_query(F.data == "homework_cancel")
async def homework_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer()


@user_router.callback_query(HomeworkManagement.viewing_list, F.data == "back_to_main_menu")
async def homework_back_to_main_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer()

@user_router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ *Помощь*\n\n"
        "📅 *Сегодня* — расписание на текущий день\n"
        "📆 *Завтра* — расписание на завтра\n"
        "🗓 *Эта неделя* — расписание на текущую неделю\n"
        "📋 *След. неделя* — расписание на следующую неделю\n"
        "📝 *Домашка* — список, добавление и удаление домашних заданий\n"
        "🙈 *Скрыть предметы* — скрыть предметы из расписания\n"
        "👁️ *Скрытые предметы* — просмотр и возврат скрытых предметов\n"
        "⚙️ *Настройки* — уведомления перед парой / днём и сброс аккаунта\n"
        "ℹ️ *Помощь* — это сообщение",
        parse_mode="Markdown"
    )


@user_router.callback_query(ScheduleNavigation.navigating, F.data.startswith("day_"))
async def navigate_day(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    # Получаем индекс дня из callback_data
    day_index = int(callback.data.replace("day_", "", 1))
    
    # Обновляем состояние
    await state.update_data(day_index=day_index)
    data = await state.get_data()
    show_image = data.get("show_image", False)
    week_type = data.get("week_type", "all")
    
    # Определяем день недели
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    current_day = days_of_week[day_index]
    
    # Получаем расписание на выбранный день с учётом типа недели
    schedule = await get_schedule(
        session=session,
        group_id=user.group_id,
        week=week_type,
        weekday=current_day,
        tg_id=user.tg_id
    )
    
    if show_image:
        # Режим картинки
        schedule_list = []
        if schedule:
            schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
            for lesson in schedule_sorted:
                hours = lesson.start_time // 3600
                minutes = (lesson.start_time % 3600) // 60
                time_str = f"{hours:02d}:{minutes:02d}"
                
                schedule_list.append({
                    "time": time_str,
                    "subject": lesson.subject,
                    "room": lesson.room,
                    "teacher": lesson.teacher,
                    "lesson_type": lesson.lesson_type
                })
        
        # Генерируем картинку
        week_text = "нечётной" if week_type == "up" else "чётной" if week_type == "down" else "всех недель"
        image_buffer = generate_schedule_image(current_day, schedule_list)
        photo_file = BufferedInputFile(image_buffer.getvalue(), filename="schedule.png")
        media_photo = InputMediaPhoto(media=photo_file, caption=f"📅 Расписание на {current_day.capitalize()} ({week_text})")
        
        # Редактируем сообщение с новой картинкой
        await callback.message.edit_media(
            media=media_photo,
            reply_markup=dayNavigationKeyboard(day_index, show_image=True, week_type=week_type)
        )
    else:
        # Режим текста
        if not schedule:
            week_indicator = "🔴" if week_type == "up" else "🔵" if week_type == "down" else "⚪"
            response = f"{week_indicator} На {current_day} пар нет 🎉"
        else:
            week_indicator = "🔴" if week_type == "up" else "🔵" if week_type == "down" else "⚪"
            week_text = "нечётной" if week_type == "up" else "чётной" if week_type == "down" else "всех недель"
            response = f"{week_indicator} 📅 Расписание на {current_day} ({week_text} неделя):\n\n"
            schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
            
            for lesson in schedule_sorted:
                hours = lesson.start_time // 3600
                minutes = (lesson.start_time % 3600) // 60
                time_str = f"{hours:02d}:{minutes:02d}"
                
                # Индикатор типа недели для конкретной пары
                lesson_indicator = "🟥" if lesson.week == "up" else "🟦" if lesson.week == "down" else "⬜"
                
                # Тип занятия
                lesson_type_display = f" [{lesson.lesson_type}]" if lesson.lesson_type else ""
                
                response += f"{lesson_indicator} {lesson.class_num}. {lesson.subject}{lesson_type_display}\n"
                response += f"   🕐 {time_str}\n"
                response += f"   👨‍🏫 {lesson.teacher}\n"
                response += f"   🏢 {lesson.room}\n\n"
        
        # Редактируем текст сообщения
        await callback.message.edit_text(
            response,
            reply_markup=dayNavigationKeyboard(day_index, show_image=False, week_type=week_type)
        )
    
    await callback.answer()


@user_router.callback_query(ScheduleNavigation.navigating, F.data == "toggle_image")
async def toggle_to_image(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    # Обновляем состояние
    await state.update_data(show_image=True)
    data = await state.get_data()
    day_index = data.get("day_index", 0)
    week_type = data.get("week_type", "all")
    
    # Определяем день недели
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    current_day = days_of_week[day_index]
    
    # Получаем расписание на выбранный день
    schedule = await get_schedule(
        session=session,
        group_id=user.group_id,
        week=week_type,
        weekday=current_day,
        tg_id=user.tg_id
    )
    
    # Подготавливаем данные для генерации картинки
    schedule_list = []
    if schedule:
        schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
        for lesson in schedule_sorted:
            hours = lesson.start_time // 3600
            minutes = (lesson.start_time % 3600) // 60
            time_str = f"{hours:02d}:{minutes:02d}"
            
            schedule_list.append({
                "time": time_str,
                "subject": lesson.subject,
                "room": lesson.room,
                "teacher": lesson.teacher,
                "lesson_type": lesson.lesson_type
            })
    
    # Генерируем картинку
    week_text = "нечётной" if week_type == "up" else "чётной" if week_type == "down" else "всех недель"
    image_buffer = generate_schedule_image(current_day, schedule_list)
    photo_file = BufferedInputFile(image_buffer.getvalue(), filename="schedule.png")
    media_photo = InputMediaPhoto(media=photo_file, caption=f"📅 Расписание на {current_day.capitalize()} ({week_text})")
    
    # Редактируем сообщение на картинку
    await callback.message.edit_media(
        media=media_photo,
        reply_markup=dayNavigationKeyboard(day_index, show_image=True, week_type=week_type)
    )
    await callback.answer()


@user_router.callback_query(ScheduleNavigation.navigating, F.data == "toggle_text")
async def toggle_to_text(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    # Обновляем состояние
    await state.update_data(show_image=False)
    data = await state.get_data()
    day_index = data.get("day_index", 0)
    week_type = data.get("week_type", "all")
    
    # Определяем день недели
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    current_day = days_of_week[day_index]
    
    # Получаем расписание на выбранный день
    schedule = await get_schedule(
        session=session,
        group_id=user.group_id,
        week=week_type,
        weekday=current_day,
        tg_id=user.tg_id
    )
    
    # Форматируем расписание в текст
    if not schedule:
        week_indicator = "🔴" if week_type == "up" else "🔵" if week_type == "down" else "⚪"
        response = f"{week_indicator} На {current_day} пар нет 🎉"
    else:
        week_indicator = "🔴" if week_type == "up" else "🔵" if week_type == "down" else "⚪"
        week_text = "нечётной" if week_type == "up" else "чётной" if week_type == "down" else "всех недель"
        response = f"{week_indicator} 📅 Расписание на {current_day} ({week_text} неделя):\n\n"
        schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
        
        for lesson in schedule_sorted:
            hours = lesson.start_time // 3600
            minutes = (lesson.start_time % 3600) // 60
            time_str = f"{hours:02d}:{minutes:02d}"
            
            # Индикатор типа недели для конкретной пары
            lesson_indicator = "🟥" if lesson.week == "up" else "🟦" if lesson.week == "down" else "⬜"
            
            # Тип занятия
            lesson_type_display = f" [{lesson.lesson_type}]" if lesson.lesson_type else ""
            
            response += f"{lesson_indicator} {lesson.class_num}. {lesson.subject}{lesson_type_display}\n"
            response += f"   🕐 {time_str}\n"
            response += f"   👨‍🏫 {lesson.teacher}\n"
            response += f"   🏢 {lesson.room}\n\n"
    
    # Удаляем сообщение с картинкой и отправляем новое текстовое
    await callback.message.delete()
    await callback.message.answer(
        response,
        reply_markup=dayNavigationKeyboard(day_index, show_image=False, week_type=week_type)
    )
    await callback.answer()


@user_router.callback_query(F.data == "week_select_day")
async def week_select_day(callback: CallbackQuery):
    await callback.message.edit_text("Выберите день недели:", reply_markup=daySelectionKeyboard())
    await callback.answer()


@user_router.callback_query(F.data.startswith("select_day_"))
async def select_day(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    # Получаем индекс дня из callback_data
    day_index = int(callback.data.replace("select_day_", "", 1))
    
    # Определяем тип текущей недели
    current_week_type = get_week_type()
    
    # Сохраняем состояние
    await state.update_data(day_index=day_index, show_image=False, week_type=current_week_type)
    await state.set_state(ScheduleNavigation.navigating)
    
    # Определяем день недели
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    current_day = days_of_week[day_index]
    
    # Получаем расписание на выбранный день
    schedule = await get_schedule(
        session=session,
        group_id=user.group_id,
        week=current_week_type,
        weekday=current_day,
        tg_id=user.tg_id
    )
    
    if not schedule:
        week_indicator = "🔴" if current_week_type == "up" else "🔵" if current_week_type == "down" else "⚪"
        response = f"{week_indicator} На {current_day} пар нет 🎉"
    else:
        week_indicator = "🔴" if current_week_type == "up" else "🔵" if current_week_type == "down" else "⚪"
        week_text = "нечётной" if current_week_type == "up" else "чётной"
        response = f"{week_indicator} 📅 Расписание на {current_day} ({week_text} неделя):\n\n"
        schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
        
        for lesson in schedule_sorted:
            hours = lesson.start_time // 3600
            minutes = (lesson.start_time % 3600) // 60
            time_str = f"{hours:02d}:{minutes:02d}"
            
            # Индикатор типа недели для конкретной пары
            lesson_indicator = "🟥" if lesson.week == "up" else "🟦" if lesson.week == "down" else "⬜"
            
            # Тип занятия
            lesson_type_display = f" [{lesson.lesson_type}]" if lesson.lesson_type else ""
            
            response += f"{lesson_indicator} {lesson.class_num}. {lesson.subject}{lesson_type_display}\n"
            response += f"   🕐 {time_str}\n"
            response += f"   👨‍🏫 {lesson.teacher}\n"
            response += f"   🏢 {lesson.room}\n\n"
    
    # Редактируем сообщение с расписание и клавиатурой навигации
    await callback.message.edit_text(response, reply_markup=dayNavigationKeyboard(day_index, show_image=False, week_type=current_week_type))
    await callback.answer()


@user_router.callback_query(F.data == "week_show_all")
async def week_show_all(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    # Определяем тип текущей недели
    current_week_type = get_week_type()
    
    # Сохраняем состояние для режима просмотра недели
    await state.update_data(week_type=current_week_type, show_image=False, is_next_week=False)
    await state.set_state(ScheduleNavigation.week_viewing)
    
    # Определяем текст недели и индикатор
    week_indicator = "🔴" if current_week_type == "up" else "🔵" if current_week_type == "down" else "⚪"
    week_text = "нечётной" if current_week_type == "up" else "чётной"
    response = f"{week_indicator} 📅 Расписание на эту неделю ({week_text}):\n\n"
    
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    
    # Получаем расписание на каждый день недели
    for day_index, day_name in enumerate(days_of_week):
        schedule = await get_schedule(
            session=session,
            group_id=user.group_id,
            week=current_week_type,
            weekday=day_name,
            tg_id=user.tg_id
        )
        
        if schedule:
            response += f"📆 {day_name.capitalize()}:\n"
            schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
            
            for lesson in schedule_sorted:
                hours = lesson.start_time // 3600
                minutes = (lesson.start_time % 3600) // 60
                time_str = f"{hours:02d}:{minutes:02d}"
                
                # Индикатор типа недели для конкретной пары
                lesson_indicator = "🟥" if lesson.week == "up" else "🟦" if lesson.week == "down" else "⬜"
                
                # Тип занятия
                lesson_type_display = f" [{lesson.lesson_type}]" if lesson.lesson_type else ""
                
                response += f"  {lesson_indicator} {lesson.class_num}. {lesson.subject}{lesson_type_display} ({time_str})\n"
            response += "\n"
    
    # Редактируем сообщение на текст с кнопкой переключения
    await callback.message.edit_text(response, reply_markup=weekToggleKeyboard(show_image=False))
    await callback.answer()


@user_router.callback_query(F.data == "next_week_select_day")
async def next_week_select_day(callback: CallbackQuery):
    await callback.message.edit_text("Выберите день следующей недели:", reply_markup=nextDaySelectionKeyboard())
    await callback.answer()


@user_router.callback_query(F.data.startswith("select_next_day_"))
async def select_next_day(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    # Получаем индекс дня из callback_data
    day_index = int(callback.data.replace("select_next_day_", "", 1))
    
    # Определяем тип следующей недели (противоположный текущей)
    current_week_type = get_week_type()
    next_week_type = "down" if current_week_type == "up" else "up"
    
    # Сохраняем состояние
    await state.update_data(day_index=day_index, show_image=False, week_type=next_week_type)
    await state.set_state(ScheduleNavigation.navigating)
    
    # Определяем день недели
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    current_day = days_of_week[day_index]
    
    # Получаем расписание на выбранный день следующей недели
    schedule = await get_schedule(
        session=session,
        group_id=user.group_id,
        week=next_week_type,
        weekday=current_day,
        tg_id=user.tg_id
    )
    
    if not schedule:
        week_indicator = "🔴" if next_week_type == "up" else "🔵" if next_week_type == "down" else "⚪"
        response = f"{week_indicator} На {current_day} следующей недели пар нет 🎉"
    else:
        week_indicator = "🔴" if next_week_type == "up" else "🔵" if next_week_type == "down" else "⚪"
        week_text = "нечётной" if next_week_type == "up" else "чётной"
        response = f"{week_indicator} 📅 Расписание на {current_day} следующей недели ({week_text}):\n\n"
        schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
        
        for lesson in schedule_sorted:
            hours = lesson.start_time // 3600
            minutes = (lesson.start_time % 3600) // 60
            time_str = f"{hours:02d}:{minutes:02d}"
            
            # Индикатор типа недели для конкретной пары
            lesson_indicator = "🟥" if lesson.week == "up" else "🟦" if lesson.week == "down" else "⬜"
            
            # Тип занятия
            lesson_type_display = f" [{lesson.lesson_type}]" if lesson.lesson_type else ""
            
            response += f"{lesson_indicator} {lesson.class_num}. {lesson.subject}{lesson_type_display}\n"
            response += f"   🕐 {time_str}\n"
            response += f"   👨‍🏫 {lesson.teacher}\n"
            response += f"   🏢 {lesson.room}\n\n"
    
    # Редактируем сообщение с расписание и клавиатурой навигации
    await callback.message.edit_text(response, reply_markup=dayNavigationKeyboard(day_index, show_image=False, week_type=next_week_type))
    await callback.answer()


@user_router.callback_query(F.data == "next_week_show_all")
async def next_week_show_all(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    # Определяем тип следующей недели (противоположный текущей)
    current_week_type = get_week_type()
    next_week_type = "down" if current_week_type == "up" else "up"
    
    # Сохраняем состояние для режима просмотра недели
    await state.update_data(week_type=next_week_type, show_image=False, is_next_week=True)
    await state.set_state(ScheduleNavigation.week_viewing)
    
    # Определяем текст недели и индикатор
    week_indicator = "🔴" if next_week_type == "up" else "🔵" if next_week_type == "down" else "⚪"
    week_text = "нечётной" if next_week_type == "up" else "чётной"
    response = f"{week_indicator} 📅 Расписание на следующую неделю ({week_text}):\n\n"
    
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    
    # Получаем расписание на каждый день следующей недели
    for day_index, day_name in enumerate(days_of_week):
        schedule = await get_schedule(
            session=session,
            group_id=user.group_id,
            week=next_week_type,
            weekday=day_name,
            tg_id=user.tg_id
        )
        
        if schedule:
            response += f"📆 {day_name.capitalize()}:\n"
            schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
            
            for lesson in schedule_sorted:
                hours = lesson.start_time // 3600
                minutes = (lesson.start_time % 3600) // 60
                time_str = f"{hours:02d}:{minutes:02d}"
                
                # Индикатор типа недели для конкретной пары
                lesson_indicator = "🟥" if lesson.week == "up" else "🟦" if lesson.week == "down" else "⬜"
                
                # Тип занятия
                lesson_type_display = f" [{lesson.lesson_type}]" if lesson.lesson_type else ""
                
                response += f"  {lesson_indicator} {lesson.class_num}. {lesson.subject}{lesson_type_display} ({time_str})\n"
            response += "\n"
    
    # Редактируем сообщение на текст с кнопкой переключения
    await callback.message.edit_text(response, reply_markup=nextWeekToggleKeyboard(show_image=False))
    await callback.answer()


@user_router.callback_query(ScheduleNavigation.week_viewing, F.data == "week_toggle_image")
async def week_toggle_image(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    data = await state.get_data()
    week_type = data.get("week_type", "all")
    is_next_week = data.get("is_next_week", False)
    
    # Обновляем состояние
    await state.update_data(show_image=True)
    
    # Определяем текст недели
    if is_next_week:
        week_text = "следующую неделю (нечётная)" if week_type == "up" else "следующую неделю (чётная)"
    else:
        week_text = "эту неделю (нечётная)" if week_type == "up" else "эту неделю (чётную)"
    
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    week_schedule = {}
    
    # Получаем расписание на каждый день недели
    for day_index, day_name in enumerate(days_of_week):
        schedule = await get_schedule(
            session=session,
            group_id=user.group_id,
            week=week_type,
            weekday=day_name,
            tg_id=user.tg_id
        )
        
        if schedule:
            schedule_list = []
            schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
            
            for lesson in schedule_sorted:
                hours = lesson.start_time // 3600
                minutes = (lesson.start_time % 3600) // 60
                time_str = f"{hours:02d}:{minutes:02d}"
                
                schedule_list.append({
                    "time": time_str,
                    "subject": lesson.subject,
                    "room": lesson.room,
                    "teacher": lesson.teacher,
                    "lesson_type": lesson.lesson_type
                })
            
            week_schedule[day_name] = schedule_list
    
    # Генерируем картинку
    image_buffer = generate_week_schedule_image(week_schedule, week_text)
    photo_file = BufferedInputFile(image_buffer.getvalue(), filename="week_schedule.png")
    
    # Редактируем сообщение на картинку с кнопкой переключения
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo_file, caption=f"📅 Расписание на {week_text}"),
        reply_markup=weekToggleKeyboard(show_image=True)
    )
    await callback.answer()


@user_router.callback_query(ScheduleNavigation.week_viewing, F.data == "week_toggle_text")
async def week_toggle_text(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    data = await state.get_data()
    week_type = data.get("week_type", "all")
    is_next_week = data.get("is_next_week", False)
    
    # Обновляем состояние
    await state.update_data(show_image=False)
    
    # Определяем текст недели и индикатор
    week_indicator = "🔴" if week_type == "up" else "🔵" if week_type == "down" else "⚪"
    if is_next_week:
        week_text = "нечётной" if week_type == "up" else "чётной"
        response = f"{week_indicator} 📅 Расписание на следующую неделю ({week_text}):\n\n"
    else:
        week_text = "нечётной" if week_type == "up" else "чётной"
        response = f"{week_indicator} 📅 Расписание на эту неделю ({week_text}):\n\n"
    
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    
    # Получаем расписание на каждый день недели
    for day_index, day_name in enumerate(days_of_week):
        schedule = await get_schedule(
            session=session,
            group_id=user.group_id,
            week=week_type,
            weekday=day_name,
            tg_id=user.tg_id
        )
        
        if schedule:
            response += f"📆 {day_name.capitalize()}:\n"
            schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
            
            for lesson in schedule_sorted:
                hours = lesson.start_time // 3600
                minutes = (lesson.start_time % 3600) // 60
                time_str = f"{hours:02d}:{minutes:02d}"
                
                # Индикатор типа недели для конкретной пары
                lesson_indicator = "🟥" if lesson.week == "up" else "🟦" if lesson.week == "down" else "⬜"
                
                # Тип занятия
                lesson_type_display = f" [{lesson.lesson_type}]" if lesson.lesson_type else ""
                
                response += f"  {lesson_indicator} {lesson.class_num}. {lesson.subject}{lesson_type_display} ({time_str})\n"
            response += "\n"
    
    # Удаляем сообщение с картинкой и отправляем новое текстовое
    await callback.message.delete()
    await callback.message.answer(response, reply_markup=weekToggleKeyboard(show_image=False))
    await callback.answer()


@user_router.callback_query(F.data == "next_week_toggle_image")
async def next_week_toggle_image(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    data = await state.get_data()
    week_type = data.get("week_type", "all")
    is_next_week = data.get("is_next_week", False)
    
    # Обновляем состояние
    await state.update_data(show_image=True)
    
    # Определяем текст недели
    if is_next_week:
        week_text = "следующую неделю (нечётная)" if week_type == "up" else "следующую неделю (чётная)"
    else:
        week_text = "эту неделю (нечётная)" if week_type == "up" else "эту неделю (чётную)"
    
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    week_schedule = {}
    
    # Получаем расписание на каждый день недели
    for day_index, day_name in enumerate(days_of_week):
        schedule = await get_schedule(
            session=session,
            group_id=user.group_id,
            week=week_type,
            weekday=day_name,
            tg_id=user.tg_id
        )
        
        if schedule:
            schedule_list = []
            schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
            
            for lesson in schedule_sorted:
                hours = lesson.start_time // 3600
                minutes = (lesson.start_time % 3600) // 60
                time_str = f"{hours:02d}:{minutes:02d}"
                
                schedule_list.append({
                    "time": time_str,
                    "subject": lesson.subject,
                    "room": lesson.room,
                    "teacher": lesson.teacher,
                    "lesson_type": lesson.lesson_type
                })
            
            week_schedule[day_name] = schedule_list
    
    # Генерируем картинку
    image_buffer = generate_week_schedule_image(week_schedule, week_text)
    photo_file = BufferedInputFile(image_buffer.getvalue(), filename="week_schedule.png")
    
    # Редактируем сообщение на картинку с кнопкой переключения
    await callback.message.edit_media(
        media=InputMediaPhoto(media=photo_file, caption=f"📅 Расписание на {week_text}"),
        reply_markup=nextWeekToggleKeyboard(show_image=True)
    )
    await callback.answer()


@user_router.callback_query(F.data == "next_week_toggle_text")
async def next_week_toggle_text(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    data = await state.get_data()
    week_type = data.get("week_type", "all")
    is_next_week = data.get("is_next_week", False)
    
    # Обновляем состояние
    await state.update_data(show_image=False)
    
    # Определяем текст недели и индикатор
    week_indicator = "🔴" if week_type == "up" else "🔵" if week_type == "down" else "⚪"
    if is_next_week:
        week_text = "нечётной" if week_type == "up" else "чётной"
        response = f"{week_indicator} 📅 Расписание на следующую неделю ({week_text}):\n\n"
    else:
        week_text = "нечётной" if week_type == "up" else "чётной"
        response = f"{week_indicator} 📅 Расписание на эту неделю ({week_text}):\n\n"
    
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    
    # Получаем расписание на каждый день недели
    for day_index, day_name in enumerate(days_of_week):
        schedule = await get_schedule(
            session=session,
            group_id=user.group_id,
            week=week_type,
            weekday=day_name,
            tg_id=user.tg_id
        )
        
        if schedule:
            response += f"📆 {day_name.capitalize()}:\n"
            schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
            
            for lesson in schedule_sorted:
                hours = lesson.start_time // 3600
                minutes = (lesson.start_time % 3600) // 60
                time_str = f"{hours:02d}:{minutes:02d}"
                
                # Индикатор типа недели для конкретной пары
                lesson_indicator = "🟥" if lesson.week == "up" else "🟦" if lesson.week == "down" else "⬜"
                
                # Тип занятия
                lesson_type_display = f" [{lesson.lesson_type}]" if lesson.lesson_type else ""
                
                response += f"  {lesson_indicator} {lesson.class_num}. {lesson.subject}{lesson_type_display} ({time_str})\n"
            response += "\n"
    
    # Удаляем сообщение с картинкой и отправляем новое текстовое
    await callback.message.delete()
    await callback.message.answer(response, reply_markup=nextWeekToggleKeyboard(show_image=False))
    await callback.answer()


@user_router.callback_query(ScheduleNavigation.navigating, F.data.startswith("week_"))
async def change_week_type(callback: CallbackQuery, session: AsyncSession, state: FSMContext):
    user = await get_user(session=session, tg_id=callback.from_user.id)
    
    if not user:
        await callback.answer("Сначала нужно пройти регистрацию")
        return
    
    # Получаем новый тип недели из callback_data
    new_week_type = callback.data.replace("week_", "", 1)
    
    # Получаем текущий тип недели из состояния
    data = await state.get_data()
    current_week_type = data.get("week_type", "all")
    
    # Если тип недели не изменился, просто отвечаем
    if new_week_type == current_week_type:
        await callback.answer("Расписание уже отображается")
        return
    
    # Обновляем состояние
    await state.update_data(week_type=new_week_type)
    data = await state.get_data()
    day_index = data.get("day_index", 0)
    show_image = data.get("show_image", False)
    
    # Определяем день недели
    days_of_week = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    current_day = days_of_week[day_index]
    
    # Получаем расписание с новым типом недели
    schedule = await get_schedule(
        session=session,
        group_id=user.group_id,
        week=new_week_type,
        weekday=current_day,
        tg_id=user.tg_id
    )
    
    if show_image:
        # Режим картинки
        schedule_list = []
        if schedule:
            schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
            for lesson in schedule_sorted:
                hours = lesson.start_time // 3600
                minutes = (lesson.start_time % 3600) // 60
                time_str = f"{hours:02d}:{minutes:02d}"
                
                schedule_list.append({
                    "time": time_str,
                    "subject": lesson.subject,
                    "room": lesson.room,
                    "teacher": lesson.teacher,
                    "lesson_type": lesson.lesson_type
                })
        
        # Генерируем картинку
        week_text = "нечётной" if new_week_type == "up" else "чётной" if new_week_type == "down" else "всех недель"
        image_buffer = generate_schedule_image(current_day, schedule_list)
        photo_file = BufferedInputFile(image_buffer.getvalue(), filename="schedule.png")
        media_photo = InputMediaPhoto(media=photo_file, caption=f"📅 Расписание на {current_day.capitalize()} ({week_text})")
        
        # Редактируем сообщение с новой картинкой
        try:
            await callback.message.edit_media(
                media=media_photo,
                reply_markup=dayNavigationKeyboard(day_index, show_image=True, week_type=new_week_type)
            )
        except:
            # Если расписание не изменилось, просто обновляем клавиатуру
            await callback.message.edit_reply_markup(
                reply_markup=dayNavigationKeyboard(day_index, show_image=True, week_type=new_week_type)
            )
        await callback.answer()
    else:
        # Режим текста
        if not schedule:
            week_indicator = "🔴" if new_week_type == "up" else "🔵" if new_week_type == "down" else "⚪"
            response = f"{week_indicator} На {current_day} пар нет 🎉"
        else:
            week_indicator = "🔴" if new_week_type == "up" else "🔵" if new_week_type == "down" else "⚪"
            week_text = "нечётной" if new_week_type == "up" else "чётной" if new_week_type == "down" else "всех недель"
            response = f"{week_indicator} 📅 Расписание на {current_day} ({week_text} неделя):\n\n"
            schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
            
            for lesson in schedule_sorted:
                hours = lesson.start_time // 3600
                minutes = (lesson.start_time % 3600) // 60
                time_str = f"{hours:02d}:{minutes:02d}"
                
                # Индикатор типа недели для конкретной пары
                lesson_indicator = "🟥" if lesson.week == "up" else "🟦" if lesson.week == "down" else "⬜"
                
                # Тип занятия
                lesson_type_display = f" [{lesson.lesson_type}]" if lesson.lesson_type else ""
                
                response += f"{lesson_indicator} {lesson.class_num}. {lesson.subject}{lesson_type_display}\n"
                response += f"   🕐 {time_str}\n"
                response += f"   👨‍🏫 {lesson.teacher}\n"
                response += f"   🏢 {lesson.room}\n\n"
        
        # Редактируем текст сообщения
        await callback.message.edit_text(
            response,
            reply_markup=dayNavigationKeyboard(day_index, show_image=False, week_type=new_week_type)
        )
    
    await callback.answer()
