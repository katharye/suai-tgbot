import asyncio

from vkbottle.bot import Bot

from config_data.config import getToken
from database.engine import async_session
from database.middleware import DbSessionMiddleware
from services.fsm import state_dispenser
from services.notifications import notification_scheduler

from handlers.registration import registration_labeler
from handlers.user import user_labeler
from handlers.admin import admin_labeler
from handlers.callbacks import callbacks_labeler
from handlers.debug import debug_labeler


async def main():
    bot = Bot(token=getToken(), state_dispenser=state_dispenser)

    # DEBUG: временный лог всех входящих событий, см. handlers/debug.py
    bot.labeler.load(debug_labeler)

    # Порядок важен: registration_labeler должен идти первым, чтобы его
    # обработчик команды /start перехватывал сообщение раньше остальных.
    bot.labeler.load(registration_labeler)
    bot.labeler.load(user_labeler)
    bot.labeler.load(admin_labeler)
    bot.labeler.load(callbacks_labeler)

    bot.labeler.message_view.middlewares.append(DbSessionMiddleware)
    bot.labeler.raw_event_view.middlewares.append(DbSessionMiddleware)

    # Фоновая задача с уведомлениями о расписании и домашках
    asyncio.create_task(notification_scheduler(bot, async_session))

    await bot.run_polling()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен.")
