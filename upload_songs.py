import asyncio
import os
import logging
import sqlite3
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import FSInputFile

from config import settings

# БД
def init_db():
    conn = sqlite3.connect("songs.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT UNIQUE NOT NULL,
        file_id TEXT NOT NULL,
        title TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_song(keyword, file_id, title):
    conn = sqlite3.connect("songs.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO songs (keyword, file_id, title) VALUES (?, ?, ?)",
        (keyword.lower(), file_id, title)
    )
    conn.commit()
    conn.close()

def get_song_count():
    conn = sqlite3.connect("songs.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM songs")
    count = cursor.fetchone()[0]
    conn.close()
    return count

# Настройки
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

FOLDER_PATH = r"C:\Users\dripp\Downloads\YaMusic_PRO"
YOUR_CHAT_ID = 1524535591

bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="Markdown")
)

# Парсинг имени файла
def parse_filename(filename: str) -> dict:
    name = filename.replace('.mp3', '').replace('.wav', '').replace('.ogg', '').strip()
    
    if ' - ' in name:
        parts = name.split(' - ', 1)
        return {"title": parts[1].strip()}
    
    return {"title": name}

# Загрузка песен
async def upload_songs():
    if not os.path.exists(FOLDER_PATH):
        logging.error(f"Папка не найдена: {FOLDER_PATH}")
        return

    mp3_files = [f for f in os.listdir(FOLDER_PATH) if f.endswith('.mp3')]
    
    if not mp3_files:
        logging.warning("В папке нет MP3 файлов!")
        return

    logging.info(f"Найдено {len(mp3_files)} MP3 файлов")

    successful = 0
    failed = 0

    for i, filename in enumerate(mp3_files, 1):
        file_path = os.path.join(FOLDER_PATH, filename)
        
        try:
            metadata = parse_filename(filename)
            
            logging.info(f"[{i}/{len(mp3_files)}] {metadata['title']}")

            audio_file = FSInputFile(file_path)
            
            message = await bot.send_audio(
                chat_id=YOUR_CHAT_ID,
                audio=audio_file,
                title=metadata['title']
            )

            file_id = message.audio.file_id
            
            add_song(
                keyword=metadata['title'].lower(),
                file_id=file_id,
                title=metadata['title']
            )

            successful += 1
            logging.info(f"Загружено: {metadata['title']}")

        except Exception as e:
            logging.error(f"Ошибка загрузки {filename}: {e}")
            failed += 1

    logging.info(" ")
    logging.info(f"ЗАВЕРШЕНО!")
    logging.info(f"Успешно загружено: {successful}")
    logging.info(f"Ошибок: {failed}")
    logging.info(f"Всего песен в БД: {get_song_count()}")
    logging.info(" ")

async def main():
    try:
        init_db()
        await upload_songs()
    except Exception as e:
        logging.error(f"Критическая ошибка: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
