from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Group, TgUser, Schedule, Homework, Filter, HiddenSubject

#  Пользователи
async def get_user(session: AsyncSession, tg_id: int) -> TgUser | None:
    """Достать пользователя по его telegram-id."""
    return await session.get(TgUser, tg_id)


async def create_user(session: AsyncSession, tg_id: int, group_id: int) -> TgUser:
    """Создать нового пользователя и сохранить в базу."""
    user = TgUser(tg_id=tg_id, group_id=group_id)
    session.add(user)
    await session.commit()

    return user


async def get_or_create_user(session: AsyncSession, tg_id: int, group_id: int) -> TgUser:
    """Достать пользователя, а если его нет — создать."""
    user = await session.get(TgUser, tg_id)

    if user is None:
        user = TgUser(tg_id=tg_id, group_id=group_id)
        session.add(user)
        await session.commit()

    return user


async def delete_user(session: AsyncSession, tg_id: int) -> None:
    """Удалить пользователя по tg_id.
    Домашки и фильтры этого пользователя удалятся автоматически.
    """
    user = await session.get(TgUser, tg_id)
    if user is not None:
        await session.delete(user)
        await session.commit()


async def update_user_notify_time(session: AsyncSession, tg_id: int, notify_time: int | None) -> None:
    """Обновить время уведомлений пользователя (в секундах от начала дня)."""
    user = await session.get(TgUser, tg_id)
    if user is not None:
        user.notify_time = notify_time
        await session.commit()


async def update_user_notify_before_min(session: AsyncSession, tg_id: int, notify_before_min: int) -> None:
    """Обновить время уведомления перед парой (в минутах)."""
    user = await session.get(TgUser, tg_id)
    if user is not None:
        user.notify_before_min = notify_before_min
        await session.commit()


async def update_user_notify_enabled(session: AsyncSession, tg_id: int, notify_enabled: bool) -> None:
    """Включить/выключить уведомления пользователя."""
    user = await session.get(TgUser, tg_id)
    if user is not None:
        user.notify_enabled = notify_enabled
        await session.commit()


#  Группы
async def get_or_create_group(session: AsyncSession, name: str) -> Group:
    """Достать группу по названию, а если её нет — создать."""
    stmt = select(Group).where(Group.name == name)
    result = await session.execute(stmt)
    group = result.scalar_one_or_none()

    if group is None:
        group = Group(name=name)
        session.add(group)
        await session.commit()

    return group


async def find_groups(session: AsyncSession, name: str) -> list[Group]:
    """Найти группы по введённому названию."""
    stmt = select(Group).where(Group.name == name)
    result = await session.execute(stmt)
    groups = list(result.scalars().all())

    if groups:
        return groups

    stmt = select(Group).where(Group.name.ilike(f"%{name}%"))
    result = await session.execute(stmt)
    groups = list(result.scalars().all())

    return groups


#  Домашки
async def add_homework(session: AsyncSession, tg_id: int, name: str, file_id: str) -> Homework:
    """Сохранить домашку пользователя."""
    homework = Homework(tg_user_id=tg_id, name=name, file_id=file_id)
    session.add(homework)
    await session.commit()

    return homework


async def get_user_homeworks(session: AsyncSession, tg_id: int) -> list[Homework]:
    """Вернуть список всех домашек пользователя."""
    stmt = select(Homework).where(Homework.tg_user_id == tg_id)
    result = await session.execute(stmt)
    homeworks = list(result.scalars().all())

    return homeworks


async def get_homework(session: AsyncSession, homework_id: int) -> Homework | None:
    """Достать одну домашку по её id."""
    return await session.get(Homework, homework_id)


async def delete_homework(session: AsyncSession, homework_id: int) -> None:
    """Удалить домашку по её id.
    Если домашки нет — ничего не делает (без ошибки).
    """
    homework = await session.get(Homework, homework_id)
    if homework is not None:
        await session.delete(homework)
        await session.commit()


#  Расписание
async def get_group_subjects(session: AsyncSession, group_id: int) -> list[str]:
    """Вернуть список уникальных названий предметов группы."""
    stmt = select(Schedule.subject).where(Schedule.group_id == group_id).distinct()
    result = await session.execute(stmt)
    subjects = list(result.scalars().all())

    return subjects


async def get_schedule(session: AsyncSession, group_id: int, week: str, weekday: str, tg_id: int = None) -> list[Schedule]:
    """Вернуть пары группы на конкретную неделю и день недели.
    Если week='all', возвращает пары для всех недель.
    Если week='up' (нечётная), возвращает пары для нечётных и всех недель.
    Если week='down' (чётная), возвращает пары для чётных и всех недель.
    Если tg_id указан, фильтрует скрытые предметы пользователя."""
    from sqlalchemy import or_
    
    if week == "all":
        stmt = select(Schedule).where(
            Schedule.group_id == group_id,
            Schedule.weekday == weekday
        ).distinct()
    elif week == "up":
        stmt = select(Schedule).where(
            Schedule.group_id == group_id,
            Schedule.weekday == weekday,
            or_(Schedule.week == "up", Schedule.week == "all")
        ).distinct()
    elif week == "down":
        stmt = select(Schedule).where(
            Schedule.group_id == group_id,
            Schedule.weekday == weekday,
            or_(Schedule.week == "down", Schedule.week == "all")
        ).distinct()
    else:
        stmt = select(Schedule).where(
            Schedule.group_id == group_id,
            Schedule.week == week,
            Schedule.weekday == weekday
        ).distinct()
    
    result = await session.execute(stmt)
    schedule = list(result.scalars().all())
    
    # Фильтруем скрытые предметы, если указан tg_id
    if tg_id is not None:
        hidden_subjects = await get_hidden_subjects_by_day(session=session, tg_id=tg_id, weekday=weekday)
        schedule = [lesson for lesson in schedule if lesson.subject not in hidden_subjects]

    return schedule


async def create_lesson(
    session: AsyncSession,
    group_id: int,
    week: str,
    weekday: str,
    class_num: int,
    subject: str,
    start_time: int,
    teacher: str,
    room: str,
    lesson_hash: str
) -> Schedule:
    """Создать запись о паре в расписании."""
    lesson = Schedule(
        group_id=group_id,
        week=week,
        weekday=weekday,
        class_num=class_num,
        subject=subject,
        start_time=start_time,
        teacher=teacher,
        room=room,
        hash=lesson_hash
    )
    session.add(lesson)
    await session.commit()

    return lesson


async def clear_schedule(session: AsyncSession) -> int:
    """Очистить всё расписание из базы данных. Возвращает количество удалённых записей."""
    from sqlalchemy import delete
    
    stmt = delete(Schedule)
    result = await session.execute(stmt)
    await session.commit()
    
    return result.rowcount


async def get_class_time(session: AsyncSession, class_num: int) -> int | None:
    """Получить время начала пары по её номеру. Возвращает секунды от начала дня или None."""
    from database.models import ClassTime
    from sqlalchemy import select
    
    stmt = select(ClassTime.start_time).where(ClassTime.class_num == class_num)
    result = await session.execute(stmt)
    time = result.scalar_one_or_none()
    
    return time


async def set_class_time(session: AsyncSession, class_num: int, start_time: int) -> None:
    """Установить время начала пары по её номеру."""
    from database.models import ClassTime
    from sqlalchemy import select
    
    # Проверяем, существует ли уже запись
    existing = await session.execute(
        select(ClassTime).where(ClassTime.class_num == class_num)
    )
    class_time = existing.scalar_one_or_none()
    
    if class_time:
        class_time.start_time = start_time
    else:
        class_time = ClassTime(class_num=class_num, start_time=start_time)
        session.add(class_time)
    
    await session.commit()


async def get_all_class_times(session: AsyncSession) -> dict[int, int]:
    """Получить все времена пар. Возвращает словарь {class_num: start_time}."""
    from database.models import ClassTime
    from sqlalchemy import select
    
    stmt = select(ClassTime)
    result = await session.execute(stmt)
    class_times = result.scalars().all()
    
    return {ct.class_num: ct.start_time for ct in class_times}


async def init_default_class_times(session: AsyncSession) -> None:
    """Инициализировать стандартные времена пар (ГУАП)."""
    from database.models import ClassTime
    from sqlalchemy import delete
    
    # Сначала удаляем все существующие записи
    stmt = delete(ClassTime)
    await session.execute(stmt)
    await session.commit()
    
    # Стандартное расписание пар ГУАП (время в секундах от начала дня)
    default_times = {
        1:  9 * 3600 + 30 * 60,   # 09:30
        2: 11 * 3600 + 10 * 60,   # 11:10
        3: 13 * 3600,             # 13:00
        4: 15 * 3600 + 10 * 60,   # 15:10
        5: 17 * 3600,             # 17:00
        6: 18 * 3600 + 40 * 60,   # 18:40
        7: 20 * 3600 + 30 * 60,   # 20:30
    }
    
    # Создаём новые записи напрямую (без проверки на существование)
    for class_num, start_time in default_times.items():
        class_time = ClassTime(class_num=class_num, start_time=start_time)
        session.add(class_time)
    
    await session.commit()


async def update_schedule_times(session: AsyncSession) -> int:
    """Обновить время во всех парах расписания на основе данных из class_times.
    Возвращает количество обновлённых записей."""
    from database.models import Schedule
    from sqlalchemy import select, update
    
    # Получаем все времена пар
    class_times = await get_all_class_times(session=session)
    
    updated_count = 0
    
    # Обновляем каждую пару
    for class_num, start_time in class_times.items():
        stmt = (
            update(Schedule)
            .where(Schedule.class_num == class_num)
            .values(start_time=start_time)
        )
        result = await session.execute(stmt)
        updated_count += result.rowcount
    
    await session.commit()
    return updated_count


#  Фильтры  — скрытые предметы
async def get_hidden_subjects(session: AsyncSession, tg_id: int) -> list[str]:
    """Вернуть список предметов, которые пользователь скрыл."""
    stmt = select(Filter.subject).where(Filter.tg_user_id == tg_id)
    result = await session.execute(stmt)
    subjects = list(result.scalars().all())

    return subjects


async def hide_subject(session: AsyncSession, tg_id: int, subject: str) -> None:
    """Скрыть предмет для пользователя (добавить в фильтры)."""
    stmt = select(Filter).where(Filter.tg_user_id == tg_id, Filter.subject == subject)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is None:
        new_filter = Filter(tg_user_id=tg_id, subject=subject)
        session.add(new_filter)
        await session.commit()


async def unhide_subject(session: AsyncSession, tg_id: int, subject: str) -> None:
    """Вернуть скрытый предмет (убрать из фильтров)."""
    stmt = select(Filter).where(Filter.tg_user_id == tg_id, Filter.subject == subject)
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        await session.delete(existing)
        await session.commit()


#  Скрытые предметы по дням недели
async def add_hidden_subject(session: AsyncSession, tg_id: int, subject: str, weekday: str) -> None:
    """Добавить предмет в список скрытых для конкретного дня недели."""
    stmt = select(HiddenSubject).where(
        HiddenSubject.tg_user_id == tg_id,
        HiddenSubject.subject == subject,
        HiddenSubject.weekday == weekday
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is None:
        hidden_subject = HiddenSubject(tg_user_id=tg_id, subject=subject, weekday=weekday)
        session.add(hidden_subject)
        await session.commit()


async def get_hidden_subjects_by_day(session: AsyncSession, tg_id: int, weekday: str) -> list[str]:
    """Вернуть список предметов, скрытых для конкретного дня недели."""
    stmt = select(HiddenSubject.subject).where(
        HiddenSubject.tg_user_id == tg_id,
        HiddenSubject.weekday == weekday
    )
    result = await session.execute(stmt)
    subjects = list(result.scalars().all())

    return subjects


async def remove_hidden_subject(session: AsyncSession, tg_id: int, subject: str, weekday: str) -> None:
    """Убрать предмет из списка скрытых для конкретного дня недели."""
    stmt = select(HiddenSubject).where(
        HiddenSubject.tg_user_id == tg_id,
        HiddenSubject.subject == subject,
        HiddenSubject.weekday == weekday
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is not None:
        await session.delete(existing)
        await session.commit()