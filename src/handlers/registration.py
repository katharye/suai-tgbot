from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.inline import generateGroupsKeyboard, applyResetKeyboard, notifyBeforeLessonsKeyboard
from keyboards.reply import notifyBeforeAllLessonsKeyboard, mainMenuKeyboard

from database.requests import find_groups, get_user, get_or_create_group, create_user, delete_user, update_user_notify_time, update_user_notify_before_min
from services.get_time import get_time_notifications_all_session, get_time_notifications_one_session

registration_router = Router()

class Registration(StatesGroup):
    waitingResetConfirm    = State()   # Ожидание подтверждения ресета 
    waitingForGroup        = State()   # Ожидание ввода группы
    waitingConfirmation    = State()   # Ожидание подтверждения группы
    waitingTimeNotify      = State()   # Ожидание выбора времени уведомлений перед парой
    waitingWriteTimeNotify = State()   # Ожидание выбора времени уведомлений перед парой
    waitingAllDayNotyfy    = State()   # Ожидание выбора времени уведомлений перед всеми парами

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


# Если пользователь подтверждает группу, появляется выбор времени для уведомлений 
@registration_router.callback_query(Registration.waitingConfirmation, F.data.startswith("group_"))
async def confirmation(callback: CallbackQuery, state: FSMContext, session: AsyncSession):
    await callback.answer()
    selected_group = callback.data.replace("group_", "", 1)
    
    group = await get_or_create_group(session=session, name=selected_group)
    await state.update_data(groupName=selected_group)
    await state.update_data(groupId=group.id)
    await state.update_data(tgId=callback.from_user.id)
        
    await callback.message.edit_text("Я могу присылать уведомления о предстоящей паре за несколько минут до неё. Если нужно, укажи за сколько.",
                                     reply_markup=notifyBeforeLessonsKeyboard())
    await state.set_state(Registration.waitingTimeNotify)

# Пользователь возвращается назад к выбору группы 
@registration_router.callback_query(Registration.waitingConfirmation, F.data == "SETTUP_BACK")
async def backToGroupSelection(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.edit_text(f"Привет, {callback.from_user.full_name}, напиши свою группу!")
    await state.set_state(Registration.waitingForGroup)

# Пользователь решил написать время для оповещения о паре сам
@registration_router.callback_query(Registration.waitingTimeNotify, F.data.startswith("USERS_TIME_BEFORELESSONS"))
async def writeUsersTime(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await callback.message.answer("Напиши время, за которое тебе надо отправлять уведомление о парах (максимум 3 часа, формат времени ЧЧ:ММ)")
    await state.set_state(Registration.waitingWriteTimeNotify)

# Ванидация времени, которое ввёл пользователь
@registration_router.message(Registration.waitingWriteTimeNotify)
async def usersNotifyBeforeLessonConfirm(message: Message, state: FSMContext):
    result = get_time_notifications_one_session(message.text)
    if not result: 
        await message.answer("Время написано некорректно! Напиши время в формате ЧЧ:ММ, не более 3 часов (к примеру 02:21)")
    else:
        await message.answer("Ещё я могу присылать уведомления о целом дне в указанное тобой время. Если нужно, укажи за сколько. Так же ты можешь указать своё время в формате <b>ЧЧ:ММ</b>",
                                     parse_mode="HTML", reply_markup=notifyBeforeAllLessonsKeyboard())
        await state.update_data(notifyBeforeLessons=result)
        await state.set_state(Registration.waitingAllDayNotyfy)


# Пользователь выбрал время уведомлений о конкретной паре
@registration_router.callback_query(Registration.waitingTimeNotify, F.data.startswith("BEFORELESSONS_"))
async def notifyBeforeLessonsConfirm(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    selected_variant = callback.data.replace("BEFORELESSONS_", "", 1)
    if selected_variant == "DONT_NOTIFY":
        await state.update_data(notifyBeforeLessons=None)
    else:
        await state.update_data(notifyBeforeLessons=(int(selected_variant) * 60))
    
    await callback.message.answer("Ещё я могу присылать уведомления о целом дне в указанное тобой время. Если нужно, укажи за сколько. Так же ты можешь указать своё время в формате <b>ЧЧ:ММ</b>",
                                     parse_mode="HTML", reply_markup=notifyBeforeAllLessonsKeyboard())
    await state.set_state(Registration.waitingAllDayNotyfy)
    
@registration_router.message(Registration.waitingAllDayNotyfy)
async def notifyBeforeAllLessonsConfirm(message: Message, state: FSMContext, session: AsyncSession):
    result = get_time_notifications_all_session(message.text)
    if not result and message.text != "Не присылать":
        await message.answer(text="<b>Время должно быть в формате ЧЧ:ММ!</b> \nДля продолжения введи корректное время или выбери из предложенного", parse_mode="HTML")
    else:
        await state.update_data(timeAllNotify=result)
        data = await state.get_data()
        
        # Сохраняем пользователя в базу данных
        user = await create_user(
            session=session,
            tg_id=data.get("tgId"),
            group_id=data.get("groupId")
        )
        
        # Обновляем время уведомлений перед учебным днём (в секундах)
        await update_user_notify_time(
            session=session,
            tg_id=data.get("tgId"),
            notify_time=data.get("timeAllNotify")
        )
        
        # Обновляем время уведомления перед парой (в минутах)
        await update_user_notify_before_min(
            session=session,
            tg_id=data.get("tgId"),
            notify_before_min=data.get("notifyBeforeLessons") or 15
        )
        
        await message.answer(f"<b>Регистрация окончена!</b>\nГруппа: {data.get("groupName")}\nВремя уведомлений перед парой: {data.get("notifyBeforeLessons") if data.get("notifyBeforeLessons") else "Не присылать"}\nВремя уведомлений перед учебным днём: {data.get("timeAllNotify") if data.get("timeAllNotify") else "Не присылать"}",
                             parse_mode="HTML",
                             reply_markup=mainMenuKeyboard())
        await state.clear()