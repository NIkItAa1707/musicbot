import asyncio
import os
import logging
import sqlite3
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import FSInputFile

from config import settings

# ========== БАЗА ДАННЫХ (из main.py) ==========
def init_db():
    conn = sqlite3.connect("songs.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT UNIQUE NOT NULL,
        file_id TEXT NOT NULL,
        title TEXT,
        artist TEXT
    )
    """)
    cursor.execute("PRAGMA table_info(songs)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'artist' not in columns:
        cursor.execute("ALTER TABLE songs ADD COLUMN artist TEXT")
    conn.commit()
    conn.close()

def add_song(keyword, file_id, title, artist=""):
    conn = sqlite3.connect("songs.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO songs (keyword, file_id, title, artist) VALUES (?, ?, ?, ?)",
        (keyword.lower(), file_id, title, artist)
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

# ========== НАСТРОЙКИ ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

FOLDER_PATH = r"C:\Users\dripp\Downloads\YaMusic_PRO"  # <-- ИЗМЕНИ НА СВОЙ ПУТЬ!
YOUR_CHAT_ID = 1524535591  # <-- ТВОЙ TELEGRAM ID (из @userinfobot)

bot = Bot(
    token=settings.BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="Markdown")
)

# ========== ПАРСИНГ ИМЕНИ ФАЙЛА ==========
def parse_filename(filename: str) -> dict:
    """Парсит имя файла для извлечения исполнителя и названия"""
    name = filename.replace('.mp3', '').replace('.wav', '').replace('.ogg', '').strip()
    
    if ' - ' in name:
        parts = name.split(' - ', 1)
        return {
            "artist": parts[0].strip(),
            "title": parts[1].strip()
        }
    
    return {
        "artist": "Неизвестный исполнитель",
        "title": name
    }

# ========== ЗАГРУЗКА ПЕСЕН ==========
async def upload_songs():
    """Загружает все MP3 файлы из папки в Telegram и сохраняет их ID в БД"""
    
    # Проверяем, существует ли папка
    if not os.path.exists(FOLDER_PATH):
        logging.error(f"❌ Папка не найдена: {FOLDER_PATH}")
        return

    # Собираем все MP3 файлы
    mp3_files = [f for f in os.listdir(FOLDER_PATH) if f.endswith('.mp3')]
    
    if not mp3_files:
        logging.warning("⚠️ В папке нет MP3 файлов!")
        return

    logging.info(f"📁 Найдено {len(mp3_files)} MP3 файлов")

    successful = 0
    failed = 0

    for i, filename in enumerate(mp3_files, 1):
        file_path = os.path.join(FOLDER_PATH, filename)
        
        try:
            metadata = parse_filename(filename)
            
            logging.info(f"📤 [{i}/{len(mp3_files)}] {metadata['artist']} - {metadata['title']}")

            audio_file = FSInputFile(file_path)
            
            # Отправляем файл в Telegram
            message = await bot.send_audio(
                chat_id=YOUR_CHAT_ID,
                audio=audio_file,
                title=metadata['title'],
                performer=metadata['artist']
            )

            file_id = message.audio.file_id
            
            # Сохраняем в базу данных
            add_song(
                keyword=metadata['title'].lower(),
                file_id=file_id,
                title=metadata['title'],
                artist=metadata['artist']
            )

            successful += 1
            logging.info(f"✅ Загружено: {metadata['title']} - {metadata['artist']}")

        except Exception as e:
            logging.error(f"❌ Ошибка загрузки {filename}: {e}")
            failed += 1

    logging.info("=" * 50)
    logging.info(f"🎉 ЗАВЕРШЕНО!")
    logging.info(f"✅ Успешно загружено: {successful}")
    logging.info(f"❌ Ошибок: {failed}")
    logging.info(f"📊 Всего песен в БД: {get_song_count()}")
    logging.info("=" * 50)


async def main():
    try:
        init_db()  # Создаём БД, если её нет
        await upload_songs()
    except Exception as e:
        logging.error(f"❌ Критическая ошибка: {e}")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())