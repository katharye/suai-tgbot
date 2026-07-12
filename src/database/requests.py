from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Group, TgUser, Schedule, Homework, Filter

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


async def get_schedule(session: AsyncSession, group_id: int, week: str, weekday: str) -> list[Schedule]:
    """Вернуть пары группы на конкретную неделю и день недели."""
    stmt = select(Schedule).where(
        Schedule.group_id == group_id,
        Schedule.week == week,
        Schedule.weekday == weekday
    )
    result = await session.execute(stmt)
    schedule = list(result.scalars().all())

    return schedule


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