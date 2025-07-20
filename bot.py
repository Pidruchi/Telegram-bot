import asyncio
import os
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from dotenv import load_dotenv
load_dotenv()

API_TOKEN = os.getenv("API_TOKEN")
ADMIN_IDS = [290137835, 343133386]  # заміни на свій Telegram user ID

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Ініціалізація бази даних
conn = sqlite3.connect("appointments.db")
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        date TEXT,
        symptoms TEXT
    )
''')
conn.commit()

# FSM для запису на прийом
class AppointmentForm(StatesGroup):
    name = State()
    date = State()
    symptoms = State()

# Функція головного меню
async def send_main_menu(message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Записатись на прийом", callback_data="book")],
        [InlineKeyboardButton(text="❓ Найчастіші питання", callback_data="faq_menu")],
        [InlineKeyboardButton(text="🚑 Термінова платна онлайн консультація з лікарем", callback_data="urgent_consult")],
        [InlineKeyboardButton(text="🎓 Придбати курс по догляду за дитиною", callback_data="buy_course")]
    ])
    await message.answer("Вітаю! Я ваш сімейний лікар. Оберіть опцію:", reply_markup=keyboard)

# Команда старт
@dp.message(F.text == "/start")
async def start_handler(message: Message):
    await send_main_menu(message)

# Команда /admin для перегляду записів
@dp.message(F.text == "/admin")
async def admin_handler(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ У вас немає доступу до цієї команди.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🗑️ Видалити всі записи", callback_data="confirm_delete")]
    ])

    cursor.execute("SELECT * FROM appointments ORDER BY date")
    rows = cursor.fetchall()

    if not rows:
        await message.answer("📭 Наразі немає записів.")
        return

    text = "📋 Записи пацієнтів:\n\n"
    for row in rows:
        text += f"🆔 {row[0]} | 👤 {row[1]} | 📅 {row[2]}\n💬 {row[3]}\n\n"

    await message.answer(text, reply_markup=keyboard)

@dp.callback_query(F.data == "confirm_delete")
async def confirm_delete(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ У вас немає доступу.", show_alert=True)
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Так, видалити", callback_data="delete_records")],
        [InlineKeyboardButton(text="❌ Ні, скасувати", callback_data="back_to_menu")]
    ])
    await callback.message.answer("⚠️ Ви впевнені, що хочете видалити всі записи?", reply_markup=keyboard)

@dp.callback_query(F.data == "delete_records")
async def delete_records(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ У вас немає доступу до цієї дії.", show_alert=True)
        return

    cursor.execute("DELETE FROM appointments")
    conn.commit()

    await callback.answer("✅ Всі записи видалено.", show_alert=True)
    await callback.message.edit_text("✅ Всі записи було успішно видалено.")

# Обробка кнопок
@dp.callback_query(F.data == "book")
async def book_appointment(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Як вас звати?", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ]))
    await state.set_state(AppointmentForm.name)

@dp.message(AppointmentForm.name)
async def enter_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("На яку дату бажаєте записатись? (Формат: ДД.ММ.РРРР)", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ]))
    await state.set_state(AppointmentForm.date)

@dp.message(AppointmentForm.date)
async def enter_date(message: Message, state: FSMContext):
    await state.update_data(date=message.text)
    await message.answer("Опишіть коротко симптоми або причину візиту", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ]))
    await state.set_state(AppointmentForm.symptoms)

@dp.message(AppointmentForm.symptoms)
async def enter_symptoms(message: Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    date = data["date"]
    symptoms = message.text

    cursor.execute("INSERT INTO appointments (name, date, symptoms) VALUES (?, ?, ?)", (name, date, symptoms))
    conn.commit()

    await message.answer(f"Дякую! Ви записані на {date} як {name}. Симптоми: {symptoms}")

    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, f"🆕 Новий запис:\n👤 {name}\n📅 {date}\n💬 {symptoms}")

    await state.clear()
    await send_main_menu(message)

@dp.callback_query(F.data == "faq_menu")
async def show_faq_menu(callback: CallbackQuery):
    faq_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌡 Що робити якщо температура?", callback_data="faq_temp")],
        [InlineKeyboardButton(text="🦷 Ріжуться зубки", callback_data="faq_teeth")],
        [InlineKeyboardButton(text="🤒 Нежить у дитини", callback_data="faq_nose")],
        [InlineKeyboardButton(text="💤 Поганий сон у немовляти", callback_data="faq_sleep")],
        [InlineKeyboardButton(text="🤢 Відмова від їжі", callback_data="faq_eating")],
        [InlineKeyboardButton(text="💩 Часті проноси", callback_data="faq_diarrhea")],
        [InlineKeyboardButton(text="🫁 Кашель та хрипи", callback_data="faq_cough")],
        [InlineKeyboardButton(text="👶 Як міряти температуру немовляті?", callback_data="faq_measure_temp")],
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
    ])
    await callback.message.answer("Оберіть питання:", reply_markup=faq_keyboard)

@dp.callback_query(F.data.startswith("faq_"))
async def handle_faq(callback: CallbackQuery):
    faq_answers = {
        "faq_temp": "🌡 Якщо у дитини підвищена температура, дайте жарознижуюче (парацетамол/ібупрофен) згідно віку. Зверніться до лікаря, якщо температура > 38,5°C понад 2 дні.",
        "faq_teeth": "🦷 Під час прорізування зубів можливий дискомфорт, слинотеча, підвищення температури. Використовуйте охолоджені прорізувачі або гелі з лідокаїном.",
        "faq_nose": "🤒 Якщо у дитини нежить — промивайте ніс фізіологічним розчином та відсмоктуйте слиз за допомогою аспіратора.",
        "faq_sleep": "💤 Поганий сон може бути через коліки, голод або прорізування зубів. Створіть комфортну атмосферу та режим сну.",
        "faq_eating": "🤢 Відмова від їжі може бути симптомом захворювання або прорізування зубів. Якщо це триває >2 днів — зверніться до лікаря.",
        "faq_diarrhea": "💩 Часті проноси можуть свідчити про кишкову інфекцію. Слідкуйте за гідратацією, при погіршенні — до лікаря.",
        "faq_cough": "🫁 При кашлі з хрипами — зверніться до педіатра. Уникайте самолікування антибіотиками.",
        "faq_measure_temp": "👶 Вимірюйте температуру ректально у немовлят — це найбільш точний метод. Нормальна температура — до 37.5°C."
    }
    response = faq_answers.get(callback.data)
    if response:
        await callback.message.answer(response)

@dp.callback_query(F.data == "urgent_consult")
async def urgent_consult(callback: CallbackQuery):
    await callback.message.answer(
        "💳 Для термінової онлайн консультації потрібно сплатити послугу:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Оплатити", url="https://your-payment-link.com")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ])
    )

@dp.callback_query(F.data == "buy_course")
async def buy_course(callback: CallbackQuery):
    await callback.message.answer(
        "Курс по догляду за дитиною доступний тут:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Перейти до курсу", url="https://your-course-link.com")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_menu")]
        ])
    )

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await send_main_menu(callback.message)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
