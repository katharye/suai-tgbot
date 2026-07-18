import asyncio
from datetime import datetime, time, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database.models import TgUser
from database.requests import (
    get_schedule,
    get_due_homework_reminders,
    clear_homework_remind_time,
)
from services.get_time import get_week_type


DAYS_OF_WEEK = [
    "понедельник", "вторник", "среда", "четверг",
    "пятница", "суббота", "воскресенье",
]

DAYS_TITLE = {
    "понедельник": "Понедельник",
    "вторник": "Вторник",
    "среда": "Среду",
    "четверг": "Четверг",
    "пятница": "Пятницу",
    "суббота": "Субботу",
    "воскресенье": "Воскресенье",
}


def notify_before_as_minutes(value: int | None) -> int | None:
    """Нормализует notify_before_min к минутам.

    0 / None — уведомления отключены.
    Раньше значение иногда сохраняли в секундах (15 мин → 900).
    Максимум при вводе — 3 часа = 180 минут, поэтому большие числа считаем секундами.
    """
    if value is None or value <= 0:
        return None
    if value > 180:
        return value // 60
    return value


async def check_and_send_notifications(bot, session: AsyncSession):
    """Проверяет и отправляет уведомления о расписании и домашках."""
    now = datetime.now()
    current_time = now.time().replace(second=0, microsecond=0)
    current_weekday = DAYS_OF_WEEK[now.weekday()]
    week_type = get_week_type(now.date())

    print(f"[{now.strftime('%Y-%m-%d %H:%M:%S')}] Checking notifications...")
    print(f"  Current time (rounded): {current_time.strftime('%H:%M')}")
    print(f"  Current weekday: {current_weekday}")
    print(f"  Week type: {week_type}")

    stmt = select(TgUser).where(TgUser.notify_enabled == True)
    result = await session.execute(stmt)
    users = result.scalars().all()

    print(f"  Users with notifications enabled: {len(users)}")

    for user in users:
        if user.notify_time is not None:
            notify_time = time(
                user.notify_time // 3600,
                (user.notify_time % 3600) // 60,
            )
            if current_time.hour == notify_time.hour and current_time.minute == notify_time.minute:
                print(f"    -> Sending day notification to user {user.tg_id}")
                await send_day_notification(bot, user, session, current_weekday, week_type)

        if notify_before_as_minutes(user.notify_before_min) is not None:
            await send_lesson_notifications(bot, user, session, current_weekday, week_type, now)

    await send_homework_reminders(bot, session, now)


async def send_day_notification(bot, user: TgUser, session: AsyncSession, weekday: str, week_type: str):
    """Отправляет уведомление о всех парах на день."""
    try:
        schedule = await get_schedule(
            session=session,
            group_id=user.group_id,
            week=week_type,
            weekday=weekday,
            tg_id=user.tg_id,
        )

        day_title = DAYS_TITLE.get(weekday, weekday.capitalize())

        if not schedule:
            await bot.send_message(user.tg_id, f"📅 На {day_title.lower()} пар нет 🎉")
            print(f"    [send_day_notification] Sent 'no lessons' to {user.tg_id}")
            return

        schedule_sorted = sorted(schedule, key=lambda x: x.class_num)
        response = f"📅 Расписание на {day_title}:\n\n"

        for lesson in schedule_sorted:
            hours = lesson.start_time // 3600
            minutes = (lesson.start_time % 3600) // 60
            time_str = f"{hours:02d}:{minutes:02d}"
            lesson_type_display = f" [{lesson.lesson_type}]" if lesson.lesson_type else ""
            response += f"🔹 {lesson.class_num}. {lesson.subject}{lesson_type_display} - {time_str}\n"
            response += f"   🏢 Кабинет: {lesson.room}\n"
            response += f"   👨‍🏫 {lesson.teacher}\n\n"

        await bot.send_message(user.tg_id, response)
        print(f"    [send_day_notification] Sent schedule ({len(schedule_sorted)} lessons) to {user.tg_id}")

    except Exception as e:
        print(f"Error sending day notification to user {user.tg_id}: {e}")


async def send_lesson_notifications(bot, user: TgUser, session: AsyncSession, weekday: str, week_type: str, now: datetime):
    """Отправляет уведомления перед каждой парой (расчет по минутам)."""
    try:
        notify_before = notify_before_as_minutes(user.notify_before_min)
        if notify_before is None:
            return

        schedule = await get_schedule(
            session=session,
            group_id=user.group_id,
            week=week_type,
            weekday=weekday,
            tg_id=user.tg_id,
        )

        if not schedule:
            return

        current_minutes = now.hour * 60 + now.minute

        for lesson in schedule:
            lesson_start_minutes = lesson.start_time // 60
            minutes_left = lesson_start_minutes - current_minutes

            if minutes_left == notify_before:
                lesson_type_display = f" [{lesson.lesson_type}]" if lesson.lesson_type else ""
                message = (
                    f"⏰ Пара {lesson.subject}{lesson_type_display} "
                    f"в кабинете {lesson.room} начнётся через {notify_before} минут!"
                )
                await bot.send_message(user.tg_id, message)
                print(f"    [send_lesson_notifications] Sent warning to {user.tg_id} about {lesson.subject}")

    except Exception as e:
        print(f"Error sending lesson notification to user {user.tg_id}: {e}")


async def send_homework_reminders(bot, session: AsyncSession, now: datetime):
    """Отправляет напоминания о домашках с наступившим remind_time."""
    try:
        homeworks = await get_due_homework_reminders(session, now)
        if not homeworks:
            return

        print(f"  Homework reminders due: {len(homeworks)}")

        for homework in homeworks:
            message = f"📝 Напоминание о домашке:\n\n{homework.name}"
            if homework.description:
                message += f"\n\n{homework.description}"

            try:
                if homework.file_id:
                    await bot.send_document(homework.tg_user_id, homework.file_id, caption=message)
                else:
                    await bot.send_message(homework.tg_user_id, message)

                await clear_homework_remind_time(session, homework.id)
                print(f"    [send_homework_reminders] Sent to {homework.tg_user_id}: {homework.name}")
            except Exception as e:
                print(f"    [send_homework_reminders] Error for homework {homework.id}: {e}")
    except Exception as e:
        print(f"Error sending homework reminders: {e}")


async def notification_scheduler(bot, session_factory):
    """Фоновая задача: проверка каждую минуту, выравнивание по стенным часам."""
    while True:
        try:
            async with session_factory() as session:
                await check_and_send_notifications(bot, session)
        except Exception as e:
            print(f"Error in notification scheduler: {e}")

        now = datetime.now()
        next_minute = (now.replace(second=0, microsecond=0) + timedelta(minutes=1))
        sleep_seconds = max((next_minute - datetime.now()).total_seconds(), 0.5)
        await asyncio.sleep(sleep_seconds)
