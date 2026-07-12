import asyncio
from aiogram import Dispatcher, Router, F, Bot

from config_data.config import getToken
from handlers.user import user_router
async def main():
    bot = Bot(token=getToken())
    dp = Dispatcher()

    dp.include_router(user_router)

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__  == "__main__":
    asyncio.run(main())