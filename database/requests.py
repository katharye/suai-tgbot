from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Group, TgUser, Schedule, Homework, Filter


async def get_user(session: AsyncSession, tg_id: int) -> TgUser | None:
    return await session.get(TgUser, tg_id) 


async def create_user(session: AsyncSession, tg_id: int, group_id: int) -> TgUser:
    user = TgUser(tg_id=tg_id, group_id=group_id)
    session.add(user)
    await session.commit()

    return user 


async def get_or_create_user(session: AsyncSession, tg_id: int, group_id: int) -> TgUser:
    user = await session.get(TgUser, tg_id)
    
    if user is None:
        user = TgUser(tg_id=tg_id, group_id=group_id)
        session.add(user)
        await session.commit()

    return user


async def get_or_create_group(session: AsyncSession, name: str) -> Group:
    stmt = select(Group).where(Group.name == name)
    result = await session.execute(stmt)
    group = result.scalar_one_or_none()

    if group is None:
        group = Group(name = name)
        session.add(group)
        await session.commit()

    return group


async def find_groups(session: AsyncSession, name: str) -> list[Group]:
    stmt = select(Group).where(Group.name == name)
    result = await session.execute(stmt)
    groups = list(result.scalars().all())

    if groups:
        return groups

    stmt = select(Group).where(Group.name.ilike(f"%{name}%"))
    result = await session.execute(stmt)
    groups = list(result.scalars().all())

    return groups


async def delete_user(session: AsyncSession, tg_id: int) -> None:
    user = await session.get(TgUser, tg_id)
    if user is not None:
        await session.delete(user)
        await session.commit()