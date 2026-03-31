from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

import os
TOKEN = os.getenv("TOKEN")

user_data = {}

# клавиатуры
main_kb = ReplyKeyboardMarkup([["🚗 Рассчитать топливо"]], resize_keyboard=True)
cancel_kb = ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет 👋 Выбери действие:", reply_markup=main_kb)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # отмена
    if text == "❌ Отмена":
        user_data[user_id] = {}
        await update.message.reply_text("Отменено ❌", reply_markup=main_kb)
        return

    # запуск
    if text == "🚗 Рассчитать топливо":
        user_data[user_id] = {"step": "r"}
        await update.message.reply_text("⛽ Введите расход (л/100 км):", reply_markup=cancel_kb)
        return

    if user_id not in user_data:
        await update.message.reply_text("Нажми кнопку 👇", reply_markup=main_kb)
        return

    data = user_data[user_id]

    # проверка числа
    try:
        value = float(text)
    except:
        await update.message.reply_text("❌ Введите число!")
        return

    # шаги
    if data["step"] == "r":
        data["r"] = value
        data["step"] = "s"
        await update.message.reply_text("💰 Введите цену за литр:")
    
    elif data["step"] == "s":
        data["s"] = value
        data["step"] = "d"
        await update.message.reply_text("📍 Введите расстояние (км):")
    
    elif data["step"] == "d":
        data["d"] = value

        r = data["r"]
        s = data["s"]
        d = data["d"]

        l = (d / 100) * r
        q = l * s

        await update.message.reply_text(
            f"🚗 *Результат:*\n\n"
            f"⛽ Топливо: *{l:.2f} л*\n"
            f"💸 Стоимость: *{q:.2f}*",
            parse_mode="Markdown"
        )

        user_data[user_id] = {}
        await update.message.reply_text("Готово ✅", reply_markup=main_kb)

# запуск
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))

app.run_polling()