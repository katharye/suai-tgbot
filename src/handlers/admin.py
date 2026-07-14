from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from sqlalchemy.ext.asyncio import AsyncSession

from services.parser_schedule import get_ids_group
from database.requests import get_or_create_group


admin_router = Router()

@admin_router.message(F.text == "load all groups")
async def load_all_group_in_db(message: Message, session: AsyncSession):
    groupsDict = await get_ids_group() 
    for group in groupsDict.keys():
        await get_or_create_group(session=session, name=group)
    await message.reply(text="Готово")
    