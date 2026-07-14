import asyncio
from aiogram import Dispatcher, Bot

from config_data.config import getToken
from handlers.user import user_router
from handlers.admin import admin_router
from handlers.registration import registration_router
from database.middleware import DbSessionMiddleware

async def main():
    bot = Bot(token=getToken())
    dp = Dispatcher()

    dp.include_router(registration_router)
    dp.include_router(user_router)
    dp.include_router(admin_router)

    #database
    dp.update.middleware(DbSessionMiddleware())
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__  == "__main__":
    asyncio.run(main())