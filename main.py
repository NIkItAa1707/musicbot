import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

TOKEN = "8846144422:AAFx5PiJeWTcuaU9FWMrwqnHVakAnpH2JV4"


# БД песен
def init_db():
    conn = sqlite3.connect("songs.db")
    cursor = conn.cursor()
    cursor.execute(
        """
    CREATE TABLE IF NOT EXISTS songs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        keyword TEXT UNIQUE NOT NULL,
        file_id TEXT NOT NULL,
        title TEXT
    )
    """
    )
    conn.commit()
    conn.close()


def get_all_songs(limit=10, offset=0):
    conn = sqlite3.connect("songs.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, keyword, file_id, title FROM songs ORDER BY id LIMIT ? OFFSET ?",
        (limit, offset),
    )
    results = []
    for row in cursor.fetchall():
        results.append(
            {"id": row[0], "keyword": row[1], "file_id": row[2], "title": row[3]}
        )
    conn.close()
    return results


def get_total_songs():
    conn = sqlite3.connect("songs.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM songs")
    count = cursor.fetchone()[0]
    conn.close()
    return count


def search_songs(query):
    conn = sqlite3.connect("songs.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, keyword, file_id, title FROM songs WHERE LOWER(keyword) LIKE ? OR LOWER(title) LIKE ? LIMIT 20",
        (f"%{query}%", f"%{query}%"),
    )
    results = []
    for row in cursor.fetchall():
        results.append(
            {"id": row[0], "keyword": row[1], "file_id": row[2], "title": row[3]}
        )
    conn.close()
    return results


def get_song_by_id(song_id):
    conn = sqlite3.connect("songs.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, keyword, file_id, title FROM songs WHERE id = ?", (song_id,)
    )
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "id": result[0],
            "keyword": result[1],
            "file_id": result[2],
            "title": result[3],
        }
    return None


def get_song_by_keyword(keyword):
    conn = sqlite3.connect("songs.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, keyword, file_id, title FROM songs WHERE LOWER(keyword) = ?",
        (keyword.lower(),),
    )
    result = cursor.fetchone()
    conn.close()
    if result:
        return {
            "id": result[0],
            "keyword": result[1],
            "file_id": result[2],
            "title": result[3],
        }
    return None


def add_song(keyword, file_id, title):
    conn = sqlite3.connect("songs.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO songs (keyword, file_id, title) VALUES (?, ?, ?)",
        (keyword.lower(), file_id, title),
    )
    conn.commit()
    conn.close()


# FSM для добавления песен
class AddSongStates(StatesGroup):
    waiting_for_title = State()


# Работа с менюшкой
def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🎵 Поиск", callback_data="menu_search"),
        InlineKeyboardButton(text="📋 Список песен", callback_data="menu_list"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="menu_stats"),
        InlineKeyboardButton(text="❓ Помощь", callback_data="menu_help"),
    )
    builder.row(
        InlineKeyboardButton(text="➕ Добавить песню", callback_data="menu_add")
    )
    return builder.as_markup()


def get_songs_list(page=0):
    per_page = 10
    total = get_total_songs()
    offset = page * per_page
    songs = get_all_songs(per_page, offset)

    builder = InlineKeyboardBuilder()

    for song in songs:
        builder.row(
            InlineKeyboardButton(
                text=f"🎵 {song['title']}", callback_data=f"play_{song['id']}"
            )
        )

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page_{page-1}"))
    if offset + per_page < total:
        nav.append(
            InlineKeyboardButton(text="➡️ Вперед", callback_data=f"page_{page+1}")
        )
    if nav:
        builder.row(*nav)

    total_pages = (total + per_page - 1) // per_page if total > 0 else 1
    builder.row(
        InlineKeyboardButton(
            text=f"📄 Страница {page+1}/{total_pages}", callback_data="noop"
        )
    )
    builder.row(InlineKeyboardButton(text="🏠 В меню", callback_data="menu_main"))

    return builder.as_markup()


# Информация о боте
bot = Bot(token=TOKEN)
dp = Dispatcher()

search_history = []


# Команды
@dp.message(Command("start"))
async def start(message: types.Message):
    count = get_total_songs()
    await message.answer(
        f"🎵 Привет!\n\n📊 В коллекции {count} песен\n\nВыбери действие:",
        reply_markup=get_main_menu(),
    )


@dp.message(Command("list"))
async def list_cmd(message: types.Message):
    total = get_total_songs()
    if total == 0:
        await message.answer(
            "📋 В коллекции пока нет песен!", reply_markup=get_main_menu()
        )
        return
    await message.answer(
        f"📋 Список песен\n\nВсего: {total}", reply_markup=get_songs_list(0)
    )


@dp.message(Command("add_song"))
async def add_song_cmd(message: types.Message, state: FSMContext):
    await state.set_state(AddSongStates.waiting_for_title)
    await message.answer(
        "📝 Отправь мне MP3 файл, а затем напиши название песни!",
        reply_markup=get_main_menu(),
    )


# Обработка добавления
@dp.message(
    lambda msg: msg.audio
    or (
        msg.document
        and msg.document.file_name
        and msg.document.file_name.endswith(".mp3")
    )
)
async def handle_audio(message: types.Message, state: FSMContext):
    if message.audio:
        file_id = message.audio.file_id
    else:
        file_id = message.document.file_id

    await state.update_data(file_id=file_id)
    await state.set_state(AddSongStates.waiting_for_title)
    await message.answer("📝 Введите название песни:", reply_markup=get_main_menu())


@dp.message(AddSongStates.waiting_for_title)
async def process_title(message: types.Message, state: FSMContext):
    title = message.text.strip()
    data = await state.get_data()
    file_id = data.get("file_id")

    if not file_id:
        await message.answer("❌ Ошибка: не найден файл", reply_markup=get_main_menu())
        await state.clear()
        return

    existing = get_song_by_keyword(title)
    if existing:
        await message.answer(
            f"⚠️ Песня '{title}' уже есть!", reply_markup=get_main_menu()
        )
        await state.clear()
        return

    add_song(title, file_id, title)
    count = get_total_songs()
    await state.clear()

    await message.answer(
        f"✅ Песня добавлена!\n\n🎵 {title}\n📊 Всего песен: {count}",
        reply_markup=get_main_menu(),
    )


# Поиск песен
@dp.message()
async def search(message: types.Message):
    query = message.text.lower()

    search_history.append(query)
    if len(search_history) > 10:
        search_history.pop(0)

    song = get_song_by_keyword(query)
    if song:
        await message.bot.send_chat_action(message.chat.id, "upload_audio")
        await message.answer_audio(
            audio=song["file_id"], title=song["title"], caption=f"🎵 {song['title']}"
        )
        await message.answer("🎵 Главное меню", reply_markup=get_main_menu())
        return

    results = search_songs(query)
    if results:
        text = "\n".join([f"• {r['title']}" for r in results[:10]])
        await message.answer(
            f"🔍 Нашёл похожие:\n\n{text}\n\n💡 Напиши точное название",
            reply_markup=get_main_menu(),
        )
    else:
        await message.answer(
            f"❌ Не нашёл: {query}\n\nПопробуй /list", reply_markup=get_main_menu()
        )


# Кнопки меню
@dp.callback_query()
async def callback(call: types.CallbackQuery):
    await call.answer()
    data = call.data

    if data == "menu_main":
        await call.message.edit_text(
            "🎵 Главное меню\n\nВыбери действие:", reply_markup=get_main_menu()
        )

    elif data == "menu_search":
        await call.message.edit_text(
            "🔍 Поиск песни\n\nПросто напиши название в чат!",
            reply_markup=get_main_menu(),
        )

    elif data == "menu_list":
        total = get_total_songs()
        if total == 0:
            await call.message.edit_text(
                "📋 В коллекции пока нет песен!", reply_markup=get_main_menu()
            )
            return
        await call.message.edit_text(
            f"📋 Список песен\n\nВсего: {total}", reply_markup=get_songs_list(0)
        )

    elif data == "menu_stats":
        total = get_total_songs()
        history_text = (
            "\n".join([f"{i+1}. {h}" for i, h in enumerate(search_history[::-1])])
            if search_history
            else "Пока пусто"
        )
        await call.message.edit_text(
            f"📊 Статистика\n\n🎵 Всего песен: {total}\n\n📝 История поиска:\n{history_text}",
            reply_markup=get_main_menu(),
        )

    elif data == "menu_help":
        await call.message.edit_text(
            "❓ Помощь\n\n"
            "📌 Команды:\n"
            "/start - Главное меню\n"
            "/list - Список песен\n"
            "/add_song - Добавить песню\n\n"
            "📌 Как найти песню:\n"
            "Напиши название в чат",
            reply_markup=get_main_menu(),
        )

    elif data == "menu_add":
        await call.message.edit_text(
            "➕ Добавление песни\n\n"
            "1. Отправь MP3 файл\n"
            "2. Напиши название\n"
            "3. Готово!\n\n"
            "Или используй /add_song",
            reply_markup=get_main_menu(),
        )

    elif data.startswith("page_"):
        page = int(data.split("_")[1])
        total = get_total_songs()
        await call.message.edit_text(
            f"📋 Список песен\n\nВсего: {total}", reply_markup=get_songs_list(page)
        )

    elif data.startswith("play_"):
        try:
            song_id = int(data.replace("play_", ""))
            song = get_song_by_id(song_id)
            if song:
                await call.message.delete()
                await call.message.answer_audio(
                    audio=song["file_id"],
                    title=song["title"],
                    caption=f"🎵 {song['title']}",
                )
                await call.message.answer(
                    "🎵 Главное меню", reply_markup=get_main_menu()
                )
        except ValueError:
            pass

    elif data == "noop":
        pass


# Запуск ботика
async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    logging.info("🚀 Бот запущен!")

    while True:
        try:
            await dp.start_polling(bot)
            break
        except Exception as e:
            logging.error(f"Ошибка: {e}")
            await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(main())
