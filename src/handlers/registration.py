from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.inline import generateGroupsKeyboard, applyResetKeyboard
registration_router = Router()
from database.requests import find_groups, get_user, get_or_create_group, create_user, delete_user

class Registration(StatesGroup):
    waitingResetConfirm = State()   # Ожидание подтверждения ресета 
    waitingForGroup     = State()   # Ожидание ввода группы
    waitingConfirmation = State()   # Ожидание подтверждения группы
    waitingTimeNotify   = State()   # Ожидание выбора времени уведомлений перед парой
    waitingAllDayNotyfy = State()   # Ожидание выбора времени уведомлений перед всеми парами

# Если пользователь уже регистрировался, ему предложат ресетнуть настройки с удалением всех данных, иначе регистрация
@registration_router.message(CommandStart())
async def start_handler(message: Message, state: FSMContext, session: AsyncSession):
    if await get_user(session=session, tg_id=message.from_user.id) is not None:
        await message.answer(text=f"Привет, ты уже зарегистрирован. Хочешь пройи регистрацию заново? <b>Все данные, включая домашние задания, будут удалены!</b>",
                             reply_markup=applyResetKeyboard(),
                             parse_mode="HTML"
        )
        await state.set_state(Registration.waitingResetConfirm)
    else:
        await message.answer(f"Привет, {message.from_user.full_name}, напиши свою группу!")
        await state.set_state(Registration.waitingForGroup)

#Если сброс подтверждён, данные удаляются и регистрация начинается заново
@registration_router.callback_query(Registration.waitingResetConfirm, F.data == "RESET_YES")
async def acceptReseting(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    if await get_user(session=session, tg_id=callback.from_user.id) is not None:
        await delete_user(session=session,  tg_id=callback.from_user.id)
    await callback.message.edit_text(f"Привет, {callback.from_user.full_name}, напиши свою группу!")
    await state.set_state(Registration.waitingForGroup)

# Если сброс отклонён выходим из FSM
@registration_router.callback_query(Registration.waitingResetConfirm, F.data == "RESET_NO")
async def denyReseting(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.delete()
    await state.clear()

# При получении сообщения от пользователя, ищет схожие с сообщением группы. 
# Если не нашёл, просит ввесли заново, иначе выводит клавиатуру с похожими на введённый текст группами
@registration_router.message(Registration.waitingForGroup)
async def readGroupNum(message: Message, state: FSMContext, session: AsyncSession):
    groupsModels = await find_groups(session=session, name=message.text)
    groups = [group.name for group in groupsModels]
    try:
        if not groups: raise
        await message.reply(
            "Пожалуйста, подтвердите выбор, нажав на кнопку", 
            reply_markup=generateGroupsKeyboard(groups)
        )
        await state.set_state(Registration.waitingConfirmation)
    except Exception:
        await message.answer(text="Схожей группы не нашлось. Повторите попытку")


# Если пользователь подтверждает группу, регистрация проходит успешно, выход из FSM 
@registration_router.callback_query(Registration.waitingConfirmation, F.data.startswith("group_"))
async def confirmation(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    selected_group = callback.data.replace("group_", "", 1)
    
    group = await get_or_create_group(session=session, name=selected_group)
    await create_user(session=session, tg_id=callback.from_user.id, group_id=group.id)
    
    await callback.message.edit_text(f"Успешно выбранна группа <b>{selected_group}</b>!", parse_mode="HTML")
    await state.clear()

# Пользователь возвращается назад к выбору группы 
@registration_router.callback_query(Registration.waitingConfirmation, F.data == "SETTUP_BACK")
async def backToGroupSelection(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(f"Привет, {callback.from_user.full_name}, напиши свою группу!")
    await state.set_state(Registration.waitingForGroup)
