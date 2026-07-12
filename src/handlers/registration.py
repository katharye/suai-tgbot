from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from keyboards.inline import generateGroupsKeyboard
user_router = Router()

# Изменить при появлении интерфейса для взаимодеййствия с БД
async def getGroupNumZATYCHKA(group: str) -> list[str]:
    if group == "1446": return [ "1446" ]
    return ["1445" , "1443"]

class Registration(StatesGroup):
    waitingForGroup     = State()
    waitingConfirmation = State()


@user_router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext):
    await message.answer(f"Привет, {message.from_user.full_name}, напиши свою группу!")
    await state.set_state(Registration.waitingForGroup)

@user_router.message(Registration.waitingForGroup)
async def readGroupNum(message: Message, state: FSMContext):
    groups = await getGroupNumZATYCHKA(f"{message.text}")
    await message.reply(
        "Пожалуйста, подтвердите выбор, нажав на кнопку", 
        reply_markup=generateGroupsKeyboard(groups)
    )
    await state.set_state(Registration.waitingConfirmation)

# Изменить при появлении интерфейса для взаимодеййствия с БД
@user_router.callback_query(Registration.waitingConfirmation, F.data.startswith("group_"))
async def confirmation(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    selected_group = callback.data.replace("group_", "", 1)

    await callback.message.edit_text(f"Успешно выбранна группа <b>{selected_group}</b>!", parse_mode="HTML")
    await state.clear()