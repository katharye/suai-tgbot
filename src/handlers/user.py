from aiogram import Router, F
from aiogram.filters import Command, CommandStart, CommandObject
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InputMediaPhoto
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.inline import generateGroupsKeyboard, dayNavigationKeyboard, weekViewKeyboard, daySelectionKeyboard, nextWeekViewKeyboard, nextDaySelectionKeyboard, weekToggleKeyboard, nextWeekToggleKeyboard, hideSubjectDayKeyboard, viewHiddenSubjectDayKeyboard
from keyboards.reply import mainMenuKeyboard
from database.requests import get_user, get_schedule, add_hidden_subject, get_hidden_subjects_by_day, remove_hidden_subject
from services.gen_schedule import generate_schedule_image, generate_week_schedule_image
from datetime import datetime, date, timedelta

user_router = Router()

class ScheduleNavigation(StatesGroup):
    navigating = State()
    week_viewing = State()


class HideSubject(StatesGroup):
    selecting_day = State()
    selecting_subject = State()


class ViewHiddenSubjects(StatesGroup):
    selecting_day = State()
    viewing_subjects = State()

# Хранилище для сообщений с расписанием (для редактирования)
schedule_messages = {}

def get_week_type(current_date: date = None) -> str:
    """Определяет тип недели: 'up' (нечётная), 'down' (чётная) или 'all' (все).
    Сентябрь - начало учебного года, всегда нечётная неделя."""
    if current_date is None:
        current_date = date.today()
    
    # Начало учебного года - 1 сентября (нечётная неделя)
    start_date = date(current_date.year, 9, 1)
    
    # Если текущая дата до 1 сентября, считаем от прошлого года
    if current_date < start_date:
        start_date = date(current_date.year - 1, 9, 1)
    
    # Количество дней от начала учебного года
    days_diff = (current_date - start_date).days
    
    # Номер недели (начиная с 0)
    week_number = days_diff // 7
    
    # Нечётные недели - week_number чётный (0, 2, 4...)
    # Чётные недели - week_number нечётный (1, 3, 5...)
    if week_number % 2 == 0:
        return "up"  # Нечётная
    else:
        return "down"  # Чётная

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
            
            response += f"{lesson_indicator} {lesson.class_num}. {lesson.subject}\n"
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
            
            response += f"� {lesson.class_num}. {lesson.subject}\n"
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

@user_router.message(F.text == "⚙️ Настройки")
async def cmd_settings(message: Message):
    await message.answer("Настройки ⚙️")

@user_router.message(F.text == "📝 Домашка")
async def cmd_homework(message: Message):
    await message.answer("Домашка 📝")

@user_router.message(F.text == "🙈 Скрыть предметы")
async def cmd_hide_subject(message: Message, state: FSMContext):
    await message.answer("Выберите день недели, на котором хотите скрыть предмет:", reply_markup=hideSubjectDayKeyboard())
    await state.set_state(HideSubject.selecting_day)


@user_router.message(F.text == "👁️ Скрытые предметы")
async def cmd_view_hidden_subjects(message: Message, state: FSMContext):
    await message.answer("Выберите день недели для просмотра скрытых предметов:", reply_markup=viewHiddenSubjectDayKeyboard())
    await state.set_state(ViewHiddenSubjects.selecting_day)


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
    await state.update_data(selected_day=selected_day)
    await state.set_state(HideSubject.selecting_subject)
    
    # Получаем расписание на выбранный день
    schedule = await get_schedule(
        session=session,
        group_id=user.group_id,
        week="all",
        weekday=selected_day
    )
    
    if not schedule:
        await callback.message.edit_text(f"На {selected_day} нет пар.")
        await state.clear()
        await callback.answer()
        return
    
    # Создаём клавиатуру с предметами
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
    
    subject_keyboard.adjust(1)
    
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
    await state.update_data(selected_day=selected_day)
    await state.set_state(ViewHiddenSubjects.viewing_subjects)
    
    # Получаем скрытые предметы для этого дня
    hidden_subjects = await get_hidden_subjects_by_day(session=session, tg_id=user.tg_id, weekday=selected_day)
    
    if not hidden_subjects:
        await callback.message.edit_text(f"На {selected_day} нет скрытых предметов.")
        await state.clear()
        await callback.answer()
        return
    
    # Создаём клавиатуру с предметами
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    subject_keyboard = InlineKeyboardBuilder()
    
    # Сохраняем список предметов в состоянии
    await state.update_data(hidden_subjects=hidden_subjects)
    
    # Используем индексы для callback data
    for idx, subject in enumerate(hidden_subjects):
        subject_keyboard.button(text=subject, callback_data=f"view_subj_{idx}")
    
    subject_keyboard.adjust(1)
    
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
    
    if not hidden_subjects:
        await callback.message.edit_text(f"На {selected_day} нет скрытых предметов.")
        await state.clear()
        await callback.answer()
        return
    
    # Создаём клавиатуру с предметами
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    subject_keyboard = InlineKeyboardBuilder()
    
    for idx, subject in enumerate(hidden_subjects):
        subject_keyboard.button(text=subject, callback_data=f"view_subj_{idx}")
    
    subject_keyboard.adjust(1)
    
    await callback.message.edit_text(f"Скрытые предметы на {selected_day}:", reply_markup=subject_keyboard.as_markup())
    await callback.answer()

@user_router.message(F.text == "ℹ️ Помощь")
async def cmd_help(message: Message):
    await message.answer(
        "ℹ️ *Помощь*\n\n"
        "📅 *Сегодня* - расписание на текущий день\n"
        "📆 *Завтра* - расписание на завтра\n"
        "🗓 *Эта неделя* - расписание на текущую неделю\n"
        "📋 *След. неделя* - расписание на следующую неделю\n"
        "⚙️ *Настройки* - настройка уведомлений и группы\n"
        "ℹ️ *Помощь* - это сообщение",
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
                    "teacher": lesson.teacher
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
                
                response += f"{lesson_indicator} {lesson.class_num}. {lesson.subject}\n"
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
                "teacher": lesson.teacher
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
            
            response += f"{lesson_indicator} {lesson.class_num}. {lesson.subject}\n"
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
            
            response += f"{lesson_indicator} {lesson.class_num}. {lesson.subject}\n"
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
                
                response += f"  {lesson_indicator} {lesson.class_num}. {lesson.subject} ({time_str})\n"
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
            
            response += f"{lesson_indicator} {lesson.class_num}. {lesson.subject}\n"
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
                
                response += f"  {lesson_indicator} {lesson.class_num}. {lesson.subject} ({time_str})\n"
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
                    "teacher": lesson.teacher
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
                
                response += f"  {lesson_indicator} {lesson.class_num}. {lesson.subject} ({time_str})\n"
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
                    "teacher": lesson.teacher
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
                
                response += f"  {lesson_indicator} {lesson.class_num}. {lesson.subject} ({time_str})\n"
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
                    "teacher": lesson.teacher
                })
        
        # Генерируем картинку
        week_text = "нечётной" if new_week_type == "up" else "чётной" if new_week_type == "down" else "всех недель"
        image_buffer = generate_schedule_image(current_day, schedule_list)
        photo_file = BufferedInputFile(image_buffer.getvalue(), filename="schedule.png")
        media_photo = InputMediaPhoto(media=photo_file, caption=f"📅 Расписание на {current_day.capitalize()} ({week_text})")
        
        # Редактируем сообщение с новой картинкой
        await callback.message.edit_media(
            media=media_photo,
            reply_markup=dayNavigationKeyboard(day_index, show_image=True, week_type=new_week_type)
        )
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
                
                response += f"{lesson_indicator} {lesson.class_num}. {lesson.subject}\n"
                response += f"   🕐 {time_str}\n"
                response += f"   👨‍🏫 {lesson.teacher}\n"
                response += f"   🏢 {lesson.room}\n\n"
        
        # Редактируем текст сообщения
        await callback.message.edit_text(
            response,
            reply_markup=dayNavigationKeyboard(day_index, show_image=False, week_type=new_week_type)
        )
    
    await callback.answer()
