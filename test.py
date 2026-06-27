# minimal_test.py
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

TOKEN = "8846144422:AAGoH7i8v_aYG_daHxjRvfXXJuM4b_SjlfY"
FILE_ID = "CQACAgIAAxkBAAM_aju_c5A5OsOaP6lxljBVpfGAI1gAApmZAAKWz-FJHic0tbW8QX88BA"

async def start_cmd(message: types.Message):
    await message.answer("Привет! Напиши 1707")

async def send_song(message: types.Message):
    if message.text and "1707" in message.text:
        await message.answer_audio(
            audio=FILE_ID,
            performer="Неизвестный исполнитель",
            title="вышел покурить - 1707",
            caption="🎵 Твоя песня!"
        )

async def main():
    logging.basicConfig(level=logging.INFO)
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
    dp = Dispatcher()
    dp.message.register(start_cmd, Command("start"))
    dp.message.register(send_song)
    
    logging.info("🚀 Тестовый бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())