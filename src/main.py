import asyncio
from aiogram import Dispatcher, Bot
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config_data.config import getToken, getDatabaseUrl
from handlers.user import user_router
from handlers.admin import admin_router
from handlers.registration import registration_router
from database.middleware import DbSessionMiddleware
from services.notifications import notification_scheduler
from database.models import Base

async def main():
    bot = Bot(token=getToken())
    dp = Dispatcher()

    dp.include_router(registration_router)
    dp.include_router(user_router)
    dp.include_router(admin_router)

    # Database
    DATABASE_URL = getDatabaseUrl()
    engine = create_async_engine(DATABASE_URL)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)
    
    dp.update.middleware(DbSessionMiddleware())
    
    # Start notification scheduler
    asyncio.create_task(notification_scheduler(bot, async_session_maker))
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__  == "__main__":
    asyncio.run(main())