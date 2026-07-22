from vkbottle.bot import BotLabeler, Message
from sqlalchemy.ext.asyncio import AsyncSession

from services.parser_schedule import get_ids_group
from database.requests import get_or_create_group, clear_schedule, init_default_class_times, update_schedule_times

admin_labeler = BotLabeler()


@admin_labeler.message(text="load all groups")
async def load_all_group_in_db(message: Message, session: AsyncSession):
    groups_dict = await get_ids_group()
    for group in groups_dict.keys():
        await get_or_create_group(session=session, name=group)
    await message.reply("Готово")


@admin_labeler.message(text="clear schedule")
async def clear_schedule_handler(message: Message, session: AsyncSession):
    deleted_count = await clear_schedule(session=session)
    await message.reply(f"Расписание очищено. Удалено {deleted_count} записей.")


@admin_labeler.message(text="init class times")
async def init_class_times_handler(message: Message, session: AsyncSession):
    await init_default_class_times(session=session)
    await message.reply("Стандартные времена пар инициализированы (ГУАП).")


@admin_labeler.message(text="update schedule times")
async def update_schedule_times_handler(message: Message, session: AsyncSession):
    updated_count = await update_schedule_times(session=session)
    await message.reply(f"Время в расписании обновлено. Обновлено {updated_count} записей.")


@admin_labeler.message(text="load all lessons")
async def load_all_lessons_in_db(message: Message, session: AsyncSession):
    await message.reply("Этап 1: Загрузка групп...")

    groups_dict = await get_ids_group()
    for group in groups_dict.keys():
        await get_or_create_group(session=session, name=group)

    await message.reply(f"Группы загружены: {len(groups_dict)}. Этап 2: Загрузка расписания...")

    from datetime import datetime
    import hashlib
    import json
    from sqlalchemy import select
    from database.models import Schedule
    from database.requests import get_class_time
    from services.parser_schedule import get_schedule_group

    total_lessons = 0
    skipped_lessons = 0

    for group_name, group_id in groups_dict.items():
        print(f"Загрузка расписания для группы: {group_name}")

        schedule = await get_schedule_group(group_id)
        group = await get_or_create_group(session=session, name=group_name)

        schedule_json = json.dumps(schedule, sort_keys=True, ensure_ascii=False)
        schedule_hash = hashlib.md5(schedule_json.encode()).hexdigest()

        for weekday, lessons in schedule.items():
            if weekday == "Вне сетки расписания":
                continue

            for lesson_data in lessons:
                for subject_name, lesson_info in lesson_data.items():
                    existing_lesson = await session.execute(
                        select(Schedule).where(
                            Schedule.group_id == group.id,
                            Schedule.week == lesson_info['type_week'],
                            Schedule.weekday == weekday,
                            Schedule.class_num == lesson_info['number_session'],
                            Schedule.subject == subject_name,
                            Schedule.teacher == lesson_info['teacher'],
                            Schedule.room == lesson_info['audience'],
                        )
                    )
                    if existing_lesson.scalar_one_or_none():
                        skipped_lessons += 1
                        continue

                    lesson_hash = schedule_hash

                    class_num = lesson_info['number_session']
                    start_time = await get_class_time(session=session, class_num=class_num)

                    if start_time is None:
                        now = datetime.now()
                        start_time = now.hour * 3600 + now.minute * 60 + now.second

                    from database.requests import create_lesson

                    await create_lesson(
                        session=session,
                        group_id=group.id,
                        week=lesson_info['type_week'],
                        weekday=weekday,
                        class_num=class_num,
                        subject=subject_name,
                        start_time=start_time,
                        teacher=lesson_info['teacher'],
                        room=lesson_info['audience'],
                        lesson_hash=lesson_hash,
                        lesson_type=lesson_info.get('type_session'),
                    )
                    total_lessons += 1

    await message.reply(f"Загрузка завершена! Добавлено {total_lessons} пар. Пропущено дубликатов: {skipped_lessons}.")
