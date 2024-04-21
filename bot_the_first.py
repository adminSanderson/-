import asyncio
import logging
import sqlite3
import datetime
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from html import escape
import config

# Настройка логгирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# Создание соединения с базой данных
conn = sqlite3.connect('events.db')
cursor = conn.cursor()

# Создание таблицы мероприятий
cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_name TEXT,
        event_description TEXT,
        event_photo TEXT,
        event_author TEXT,
        event_date TEXT,
        city TEXT,
        entities TEXT
    )
""")

# Создание таблицы пользователей и их городов
cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_cities (
        user_id INTEGER PRIMARY KEY,
        city TEXT
    )
""")

# Создание класса состояний для настроек
class SettingsStates(StatesGroup):
    city = State()

# Функция для проверки, является ли пользователь администратором
def is_admin(user_id):
    return user_id in config.ADMINS_ID

# Функция для проверки, является ли пользователь постером
def is_poster(user_id):
    return user_id in config.POSTERS_ID

# Функция для сохранения города пользователя в базе данных
def save_user_city(user_id, city):
    cursor.execute("INSERT OR REPLACE INTO user_cities (user_id, city) VALUES (?, ?)", (user_id, city))
    conn.commit()

# Функция для получения города пользователя из базы данных
def get_user_city(user_id):
    cursor.execute("SELECT city FROM user_cities WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return None

from html import escape

# Функция для сохранения данных о мероприятии в базу данных с экранированием HTML
def save_event(event_name, event_description, event_photo, event_author, event_date, city, entities):
    cursor.execute("INSERT INTO events (event_name, event_description, event_photo, event_author, event_date, city, entities) VALUES (?, ?, ?, ?, ?, ?, ?)",
                   (escape(event_name), escape(event_description), event_photo, escape(event_author), event_date, city, str(entities)))
    conn.commit()

# Функция для получения активных мероприятий по городу
def get_active_events_by_city(city):
    cursor.execute("SELECT * FROM events WHERE city = ? AND event_date >= ?", (city, datetime.datetime.now()))
    return cursor.fetchall()

import datetime

# Функция для удаления истекших мероприятий из базы данных
async def delete_expired_events():
    cursor.execute("DELETE FROM events WHERE event_date < ?", (datetime.datetime.now(),))
    conn.commit()

# Регулярная проверка и удаление истекших мероприятий
async def check_expired_events():
    while True:
        await asyncio.sleep(86400)  # Проверяем каждые 24 часа (86400 секунд)
        await delete_expired_events()

# Создание клавиатуры основного меню
async def main_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("🎉 Мероприятия"))
    keyboard.add(types.KeyboardButton("📊 Информация"), types.KeyboardButton("📊 Группы и каналы"))
    keyboard.add(types.KeyboardButton("⚙️ Настройки"))
    return keyboard

# Обработчик кнопки "Информация" в главном меню
@dp.message_handler(lambda message: message.text == "📊 Информация")
async def information(message: types.Message):
    await message.answer("Выберите раздел информации:", reply_markup=await information_menu())

# Создание клавиатуры для раздела "Информация"
async def information_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Контакты"))
    keyboard.add(types.KeyboardButton("⬅️ Назад"))
    return keyboard

# Обработчик кнопки "Контакты" в разделе "Информация"
@dp.message_handler(lambda message: message.text == "Контакты")
async def contacts(message: types.Message):
    # Создание клавиатуры с категориями контактов
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(
        types.KeyboardButton("👥 Кураторы"),
        types.KeyboardButton("🎓 Наставники"),
        types.KeyboardButton("👔 Руководители"),
    )
    keyboard.add(
        types.KeyboardButton("🏆 Участники прошлых сезонов БП"),
        types.KeyboardButton("💬 Участники движения"),
        types.KeyboardButton("⬅️ Назад"),
    )
    await message.answer("Выберите категорию контактов:", reply_markup=keyboard)

# Обработчик кнопок категорий контактов
@dp.message_handler(lambda message: message.text in ["👥 Кураторы", "🎓 Наставники", "👔 Руководители", "🏆 Участники прошлых сезонов БП", "💬 Участники движения"])
async def contact_category(message: types.Message):
    category = message.text
    if category == "👥 Кураторы":
        # Отправка контактов кураторов
        await message.answer("Контакты кураторов:")
    elif category == "🎓 Наставники":
        # Отправка контактов наставников
        await message.answer("Контакты наставников:")
    elif category == "👔 Руководители":
        # Отправка контактов руководителей
        await message.answer("Контакты руководителей:")
    elif category == "🏆 Участники прошлых сезонов БП":
        # Отправка контактов участников прошлых сезонов БП
        await message.answer("Контакты участников прошлых сезонов БП:")
    elif category == "💬 Участники движения":
        # Отправка контактов участников движения
        await message.answer("Контакты участников движения:")


# Команда /start
@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Для начала выберите свой город через кнопку Настройки.", reply_markup=await main_menu())

# Обработчик команды "Настройки"
@dp.message_handler(lambda message: message.text == "⚙️ Настройки")
async def settings(message: types.Message):
    await message.answer("Выберите настройку:", reply_markup=await settings_menu())

# Создание клавиатуры для настроек
async def settings_menu():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton("Изменить город"))
    keyboard.add(types.KeyboardButton("Написать разработчику"), types.KeyboardButton("⬅️ Назад"))
    return keyboard

# Обработчик кнопки "Назад" в меню настроек
@dp.message_handler(lambda message: message.text == "⬅️ Назад")
async def back_to_main_menu(message: types.Message):
    await message.answer("Переходим...", reply_markup=await main_menu())

# Обработчик команды "Изменить город"
@dp.message_handler(lambda message: message.text == "Изменить город")
async def change_city(message: types.Message):
    await message.answer("Введите новый город:")
    await SettingsStates.city.set()

# Обработчик команды "Мероприятия"
@dp.message_handler(lambda message: message.text == "🎉 Мероприятия")
async def activities(message: types.Message):
    user_city = get_user_city(message.from_user.id)
    if user_city:
        events = get_active_events_by_city(user_city)
        if events:
            # Отправляем информацию о первом мероприятии
            await send_event_info(message, events, 0)
        else:
            await message.answer("Пока что нет мероприятий для вашего города :(")
    else:
        await message.answer("Для начала выберите свой город через кнопку Настройки.", reply_markup=await main_menu())

# Функция для отправки информации о мероприятии в виде сообщения с кнопками для переключения
async def send_event_info(message: types.Message, events: list, index: int):
    event = events[index]
    event_name = event[1]
    event_description = event[2]
    event_date = event[5]
    event_author = event[4]  # Добавляем получение автора мероприятия
    event_photo = event[3]   # Добавляем получение фото мероприятия

    # Создаем кнопки для переключения между мероприятиями
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    if index > 0:
        keyboard.insert(types.InlineKeyboardButton(text="⬅️", callback_data=f"prev_event_{index}"))
    if index < len(events) - 1:
        keyboard.insert(types.InlineKeyboardButton(text="➡️", callback_data=f"next_event_{index}"))

    # Отправляем информацию о мероприятии в виде сообщения
    await message.answer_photo(
        photo=event_photo,
        caption=f"<b>{event_name}</b>\n\n"
                f"<i>Автор:</i> {event_author}\n"
                f"<i>Дата:</i> {event_date}\n\n"
                f"{event_description}",
        reply_markup=keyboard,
        parse_mode=types.ParseMode.HTML
    )


# Обработчик нажатия на кнопки для переключения между мероприятиями
@dp.callback_query_handler(lambda query: query.data.startswith(("prev_event_", "next_event_")))
async def switch_event(call: types.CallbackQuery):
    # Извлекаем индекс мероприятия из callback_data
    index = int(call.data.split("_")[-1])  # Теперь используем последний элемент после разделения
    # Извлекаем список мероприятий из базы данных
    user_city = get_user_city(call.from_user.id)
    events = get_active_events_by_city(user_city)
    # Обрабатываем действие, в зависимости от нажатой кнопки
    if call.data.startswith("prev_event_"):
        index -= 1
    elif call.data.startswith("next_event_"):
        index += 1
    # Проверяем границы списка мероприятий
    if 0 <= index < len(events):
        # Отправляем информацию о новом мероприятии
        await send_event_info(call.message, events, index)
        # Удаляем предыдущее сообщение с кнопками
        await call.message.delete()
    else:
        await call.answer("Нет больше мероприятий", show_alert=True)

# Обработчик ввода нового города
@dp.message_handler(state=SettingsStates.city)
async def process_city_input(message: types.Message, state: FSMContext):
    new_city = message.text
    save_user_city(message.from_user.id, new_city)
    await state.finish()
    await message.answer("Город успешно изменен!", reply_markup=await main_menu())

# Обработчик команды "Отмена"
@dp.message_handler(lambda message: message.text == "Отмена", state="*")
async def cancel(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Действие отменено.", reply_markup=await main_menu())

# Обработчик команды "Создать мероприятие"
@dp.message_handler(lambda message: message.text == "Создать мероприятие")
async def create_event(message: types.Message):
    if is_poster or is_admin(message.from_user.id):
        await message.answer("Введите название мероприятия:")
        await EventsStates.name.set()
    else:
        await message.answer("У вас нет доступа к созданию мероприятий.")


# Создание класса состояний для создания мероприятия
class EventsStates(StatesGroup):
    name = State()
    description = State()
    city = State()
    photo = State()
    date = State()
    author = State()

# Обработчик ввода названия мероприятия
@dp.message_handler(state=EventsStates.name)
async def process_event_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await EventsStates.next()
    await message.answer("Введите описание мероприятия:")

# Обработчик ввода описания мероприятия
@dp.message_handler(state=EventsStates.description)
async def process_event_description(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['description'] = message.text
    await EventsStates.next()
    await message.answer("Введите город проведения мероприятия:")

# Обработчик ввода города проведения мероприятия
@dp.message_handler(state=EventsStates.city)
async def process_event_city(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['city'] = message.text
    await EventsStates.next()
    await message.answer("Пришлите фото мероприятия:")

# Обработчик приема фото мероприятия
@dp.message_handler(content_types=types.ContentType.PHOTO, state=EventsStates.photo)
async def process_event_photo(message: types.Message, state: FSMContext):
    photo_id = message.photo[-1].file_id
    async with state.proxy() as data:
        data['photo'] = photo_id
    await EventsStates.next()
    await message.answer("Введите дату и время мероприятия в формате ГГГГ-ММ-ДД ЧЧ:ММ:")

# Обработчик ввода даты и времени мероприятия
@dp.message_handler(state=EventsStates.date)
async def process_event_date(message: types.Message, state: FSMContext):
    date_str = message.text
    try:
        event_date = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M")
    except ValueError:
        await message.answer("Неверный формат даты и времени. Введите дату и время в формате ГГГГ-ММ-ДД ЧЧ:ММ:")
        return
    async with state.proxy() as data:
        data['date'] = event_date
    await EventsStates.next()
    await message.answer("Введите ваше имя (автора мероприятия):")

# Обработчик ввода имени автора мероприятия
@dp.message_handler(state=EventsStates.author)
async def process_event_author(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['author'] = message.text
    # Сохранение данных о мероприятии в базу данных
    async with state.proxy() as data:
        save_event(data['name'], data['description'], data['photo'], data['author'], data['date'], data['city'], "")
    await state.finish()
    await message.answer("Мероприятие успешно создано!", reply_markup=await main_menu())

# Обработчик команды "Удалить мероприятие"
@dp.message_handler(lambda message: message.text.startswith("Удалить мероприятие"))
async def delete_event(message: types.Message):
    if is_poster or is_admin(message.from_user.id):
        event_name = message.text.removeprefix("Удалить мероприятие").strip()
        # Проверяем, существует ли мероприятие с таким названием
        cursor.execute("SELECT id FROM events WHERE event_name = ?", (event_name,))
        result = cursor.fetchone()
        if result:
            # Если мероприятие существует, удаляем его из базы данных
            cursor.execute("DELETE FROM events WHERE event_name = ?", (event_name,))
            conn.commit()
            await message.answer(f"Мероприятие '{event_name}' успешно удалено.")
        else:
            await message.answer(f"Мероприятие '{event_name}' не найдено.")
    else:
        await message.answer("У вас нет доступа к удалению мероприятий.")

# Запуск бота
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
    asyncio.ensure_future(check_expired_events())
