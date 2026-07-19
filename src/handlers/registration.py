from vkbottle import BaseStateGroup
from vkbottle.bot import BotLabeler, Message
from sqlalchemy.ext.asyncio import AsyncSession

from keyboards.inline import applyResetKeyboard
from keyboards.reply import mainMenuKeyboard

from database.requests import find_groups, get_user
from services.fsm import set_state, clear_state, advance_state

registration_labeler = BotLabeler()


class Registration(BaseStateGroup):
    waiting_reset_confirm = "waiting_reset_confirm"       # Ожидание подтверждения ресета
    waiting_for_group = "waiting_for_group"                # Ожидание ввода группы
    waiting_confirmation = "waiting_confirmation"          # Ожидание подтверждения группы
    waiting_time_notify = "waiting_time_notify"            # Ожидание выбора времени уведомлений перед парой
    waiting_write_time_notify = "waiting_write_time_notify"  # Ожидание ввода своего времени перед парой
    waiting_all_day_notify = "waiting_all_day_notify"      # Ожидание выбора времени уведомлений перед всеми парами


# Если пользователь уже регистрировался, ему предложат ресетнуть настройки с удалением всех данных, иначе регистрация
@registration_labeler.message(command="start")
@registration_labeler.message(text=["начать", "Начать", "старт", "Старт"])
async def start_handler(message: Message, session: AsyncSession):
    user = await get_user(session=session, vk_id=message.from_id)

    if user is not None:
        await message.answer(
            "Привет, ты уже зарегистрирован. Хочешь пройти регистрацию заново? "
            "Все данные, включая домашние задания, будут удалены!",
            keyboard=applyResetKeyboard(),
        )
        await set_state(message.peer_id, Registration.waiting_reset_confirm)
    else:
        await message.answer(f"Привет, напиши свою группу!")
        await set_state(message.peer_id, Registration.waiting_for_group)


# При получении сообщения от пользователя, ищет схожие с сообщением группы.
# Если не нашёл, просит ввести заново, иначе выводит клавиатуру с похожими на введённый текст группами
@registration_labeler.message(state=Registration.waiting_for_group)
async def read_group_num(message: Message, session: AsyncSession):
    from keyboards.inline import generateGroupsKeyboard

    groups_models = await find_groups(session=session, name=message.text)
    groups = [group.name for group in groups_models]

    if not groups:
        await message.answer("Схожей группы не нашлось. Повторите попытку")
        return

    await message.reply(
        "Пожалуйста, подтвердите выбор, нажав на кнопку",
        keyboard=generateGroupsKeyboard(groups),
    )
    await set_state(message.peer_id, Registration.waiting_confirmation)


@registration_labeler.message(state=Registration.waiting_write_time_notify)
async def users_notify_before_lesson_confirm(message: Message):
    from services.get_time import get_time_notifications_one_session
    from keyboards.reply import notifyBeforeAllLessonsKeyboard

    result = get_time_notifications_one_session(message.text)
    if result is None:
        await message.answer("Время написано некорректно! Напиши время в формате ЧЧ:ММ, не более 3 часов (к примеру 02:21)")
        return

    await message.answer(
        "Ещё я могу присылать уведомления о целом дне в указанное тобой время. Если нужно, укажи за сколько. "
        "Так же ты можешь указать своё время в формате ЧЧ:ММ",
        keyboard=notifyBeforeAllLessonsKeyboard(),
    )
    # get_time_notifications_one_session возвращает секунды → сохраняем минуты
    await advance_state(message.peer_id, Registration.waiting_all_day_notify, notifyBeforeLessons=result // 60)


@registration_labeler.message(state=Registration.waiting_all_day_notify)
async def notify_before_all_lessons_confirm(message: Message, session: AsyncSession):
    from services.get_time import get_time_notifications_all_session
    from database.requests import create_user, update_user_notify_time, update_user_notify_before_min
    from services.fsm import get_state_data

    result = get_time_notifications_all_session(message.text)
    if result is None and message.text != "Не присылать":
        await message.answer("Время должно быть в формате ЧЧ:ММ!\nДля продолжения введи корректное время или выбери из предложенного")
        return

    data = await get_state_data(message.peer_id)

    user = await create_user(
        session=session,
        vk_id=data.get("vkId"),
        group_id=data.get("groupId"),
    )

    await update_user_notify_time(session=session, vk_id=data.get("vkId"), notify_time=result)

    before = data.get("notifyBeforeLessons")
    await update_user_notify_before_min(
        session=session,
        vk_id=data.get("vkId"),
        notify_before_min=15 if before is None else before,
    )

    before_text = "Не присылать" if not before else f"{before} минут"
    day_text = _format_time(result) if result is not None else "Не присылать"

    await message.answer(
        f"Регистрация окончена!\nГруппа: {data.get('groupName')}\n"
        f"Время уведомлений перед парой: {before_text}\n"
        f"Время уведомлений перед учебным днём: {day_text}",
        keyboard=mainMenuKeyboard(),
    )
    await clear_state(message.peer_id)


def _format_time(seconds: int | None) -> str:
    if seconds is None:
        return "Не указано"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours:02d}:{minutes:02d}"
