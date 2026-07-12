import asyncio
import io
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from PIL import Image
from aiogram.types import BufferedInputFile
from dotenv import load_dotenv
from aiogram.types import WebAppInfo

WEB_APP_URL = "https://pro.guap.ru/inside/profile"

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

dp = Dispatcher(storage=MemoryStorage())

def get_suai():
    button = InlineKeyboardButton(text="SUAI", web_app=WebAppInfo(url=WEB_APP_URL), style="success", icon_custom_emoji_id='5402502124548405263')
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[button]])
    return keyboard


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Привет!👋\nНажмите кнопку, чтобы перейти на сайт гуапа!", reply_markup=get_suai())

async def main():
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())