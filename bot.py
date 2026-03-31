import os
import json
from threading import Thread
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

# ================== Настройки ==================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")  # токен от @BotFather
DATA_FILE = "records.json"

services = {
    "Замена масла": 3000,
    "Диагностика": 2000,
    "Шиномонтаж": 1500
}

ADDRESS = "ул. Примерная 12, г. Москва"
ADMINS = [123456789, 987654321]

# ================== Flask keep-alive ==================
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Бот автосервиса работает 24/7 🚀"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

# ================== Бот ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['step'] = 'car_info'
    await update.message.reply_text("Здравствуйте! Укажите марку и год вашего автомобиля (например, Toyota 2015):")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    step = context.user_data.get('step', '')

    if step == 'car_info':
        context.user_data['car'] = update.message.text
        context.user_data['step'] = 'select_services'
        context.user_data['selected_services'] = []

        # Кнопки для выбора услуг
        keyboard = [
            [InlineKeyboardButton(s, callback_data=s)] for s in services.keys()
        ]
        keyboard.append([InlineKeyboardButton("Завершить выбор", callback_data="finish")])
        keyboard.append([InlineKeyboardButton("История посещений", callback_data="history")])
        await update.message.reply_text("Выберите услуги (можно несколько):", reply_markup=InlineKeyboardMarkup(keyboard))

    elif step == 'wheel_radius':
        context.user_data['wheel_radius'] = update.message.text
        await show_confirmation(update, context)

async def service_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "finish":
        # Если выбран хотя бы один сервис
        if not context.user_data.get('selected_services'):
            await query.edit_message_text("Выберите хотя бы одну услугу!")
            return
        await show_confirmation(query, context)
        return

    if data == "history":
        await show_history(query, context)
        return

    # Добавляем выбранную услугу
    selected = context.user_data.get('selected_services', [])
    if data not in selected:
        selected.append(data)
        context.user_data['selected_services'] = selected
        await query.edit_message_text(f"Выбраны услуги: {', '.join(selected)}\nПродолжайте выбирать или нажмите 'Завершить выбор'.")
    else:
        await query.edit_message_text(f"Услуга {data} уже выбрана.\nПродолжайте выбирать или нажмите 'Завершить выбор'.")

    # Если выбрана Шиномонтаж — запрос радиуса колес
    if data == "Шиномонтаж":
        context.user_data['step'] = 'wheel_radius'
        await query.edit_message_text("Вы выбрали Шиномонтаж. Укажите радиус колес (например, R16):")

async def show_confirmation(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['step'] = 'confirm'
    # Кнопки подтверждения
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data="confirm")],
        [InlineKeyboardButton("❌ Отменить", callback_data="cancel")]
    ]
    services_list = context.user_data.get('selected_services', [])
    price = sum([services[s] for s in services_list])
    wheel_radius = context.user_data.get('wheel_radius', None)
    msg = f"Вы выбрали:\n{', '.join(services_list)}\n"
    if wheel_radius:
        msg += f"Радиус колес: {wheel_radius}\n"
    msg += f"Ориентировочная сумма: {price} руб.\n\nПроверьте и подтвердите запись:"
    if hasattr(update_or_query, 'edit_message_text'):
        await update_or_query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update_or_query.reply_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

async def confirmation_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "cancel":
        context.user_data.clear()
        await query.edit_message_text("Запись отменена. Чтобы начать заново, напишите любое сообщение.")
        return
    if data == "confirm":
        services_list = context.user_data.get('selected_services', [])
        price = sum([services[s] for s in services_list])
        wheel_radius = context.user_data.get('wheel_radius', None)
        car = context.user_data.get('car')
        datetime = "не указано"  # можем позже добавить дату/время
        record = {
            "name": query.from_user.full_name,
            "car": car,
            "services": services_list,
            "wheel_radius": wheel_radius,
            "price": price,
            "datetime": datetime
        }
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = []
        data.append(record)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # Сообщение пользователю
        msg = f"Запись подтверждена!\nВы записаны на {', '.join(services_list)}.\nПо адресу: {ADDRESS}.\nДата и время уточняются."
        await query.edit_message_text(msg)

        # Уведомление админов
        for admin_id in ADMINS:
            try:
                admin_msg = (
                    f"🆕 Новая запись:\n"
                    f"Имя: {record['name']}\n"
                    f"Марка/Год авто: {record['car']}\n"
                    f"Услуги: {', '.join(record['services'])}\n"
                    f"Радиус колес: {wheel_radius}\n"
                    f"Ориентировочная сумма: {price} руб."
                )
                await context.bot.send_message(chat_id=admin_id, text=admin_msg)
            except Exception as e:
                print(f"Не удалось уведомить администратора {admin_id}: {e}")

        context.user_data.clear()

async def show_history(update_or_query, context: ContextTypes.DEFAULT_TYPE):
    user_name = update_or_query.from_user.full_name
    if not os.path.exists(DATA_FILE):
        await update_or_query.edit_message_text("История пуста.")
        return
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    user_records = [r for r in data if r['name'] == user_name]
    if not user_records:
        await update_or_query.edit_message_text("История пуста.")
        return
    msg = "Ваша история посещений:\n"
    for r in user_records:
        services_str = ', '.join(r['services'])
        msg += f"- {services_str}, стоимость: {r['price']} руб.\n"
    await update_or_query.edit_message_text(msg)

# ================== Админ ==================
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id not in ADMINS:
        await update.message.reply_text("❌ У вас нет доступа к админ-панели.")
        return
    if not os.path.exists(DATA_FILE):
        await update.message.reply_text("Пока нет записей.")
        return
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not data:
        await update.message.reply_text("Пока нет записей.")
        return
    text = "\n\n".join([
        f"{r['name']} | {r['car']} | {', '.join(r['services'])} | "
        f"{r['wheel_radius'] or '-'} | {r['datetime']} | {r['price']} руб."
        for r in data
    ])
    await update.message.reply_text(f"Все записи:\n\n{text}")

# ================== Запуск ==================
def run_bot():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(service_choice, pattern="^(?!confirm$|cancel$).+"))
    app.add_handler(CallbackQueryHandler(confirmation_handler, pattern="^(confirm|cancel)$"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CommandHandler("admin", admin))
    print("Бот автосервиса запущен...")
    app.run_polling()

if __name__ == "__main__":
    Thread(target=run_flask).start()
    run_bot()
