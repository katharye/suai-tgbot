from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.inline import generateGroupsKeyboard
user_router = Router()
from database.requests import find_groups, create_user, get_or_create_group

class Registration(StatesGroup):
    waitingForGroup     = State()
    waitingConfirmation = State()


@user_router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await message.answer(f"Привет, {message.from_user.full_name}, напиши свою группу!")
    await state.set_state(Registration.waitingForGroup)

@user_router.message(Registration.waitingForGroup)
async def readGroupNum(message: Message, state: FSMContext, session: AsyncSession):
    groups = await find_groups(session=session, name=message.text)
    if not groups:
        await message.answer(text="Схожей группы не нашлось. Повторите попытку")
    else:
        await message.reply(
            f"Пожалуйста, подтвердите выбор, нажав на кнопку {groups}", 
            reply_markup=generateGroupsKeyboard(groups)
        )
        await state.set_state(Registration.waitingConfirmation)

# Изменить при появлении интерфейса для взаимодеййствия с БД
@user_router.callback_query(Registration.waitingConfirmation, F.data.startswith("group_"))
async def confirmation(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    selected_group = callback.data.replace("group_", "", 1)
    
    group = await get_or_create_group(session=session, name=selected_group)
    await create_user(session=session, tg_id=callback.from_user.id, group_id=group.id)
    
    await callback.message.edit_text(f"Успешно выбранна группа <b>{selected_group}</b>!", parse_mode="HTML")
    await state.clear()