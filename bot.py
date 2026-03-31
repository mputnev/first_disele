import os
from datetime import datetime
from threading import Thread
from flask import Flask

from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

# ================= Flask (для Render) =================
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

# ================= Telegram Bot =================
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не установлен!")

FUEL, PRICE, DISTANCE = range(3)

history = {}

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "друг"
    await update.message.reply_text(
        f"Привет, {name}! 🚗\nДавай посчитаем расход топлива.\n"
        "Введи расход топлива на 100 км:"
    )
    return FUEL

# расход
async def get_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = float(update.message.text.replace(",", "."))
        if r <= 0:
            raise ValueError
        context.user_data['r'] = r
        await update.message.reply_text("Теперь введи цену литра:")
        return PRICE
    except:
        await update.message.reply_text("Введите корректное число!")
        return FUEL

# цена
async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        s = float(update.message.text.replace(",", "."))
        if s <= 0:
            raise ValueError
        context.user_data['s'] = s
        await update.message.reply_text("Теперь введи расстояние (км):")
        return DISTANCE
    except:
        await update.message.reply_text("Введите корректное число!")
        return PRICE

# расстояние + расчет
async def get_distance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d = float(update.message.text.replace(",", "."))
        if d <= 0:
            raise ValueError

        r = context.user_data['r']
        s = context.user_data['s']

        l = (d / 100) * r
        q = l * s

        if l > 999999 or q > 999999:
            await update.message.reply_text("Слишком большие значения 🚨")
            return ConversationHandler.END

        await update.message.reply_text(
            f"🚗 Топливо: {l:.2f} л\n"
            f"💰 Стоимость: {q:.2f}\n\n"
            "Удачной поездки! 🎉"
        )

        # сохраняем историю
        user_id = update.effective_user.id
        date = datetime.now().strftime("%d.%m.%Y %H:%M")
        record = f"{date} — {l:.2f} л / {q:.2f} ₽"
        history.setdefault(user_id, []).append(record)

        return ConversationHandler.END

    except:
        await update.message.reply_text("Введите корректное число!")
        return DISTANCE

# история
async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    records = history.get(user_id, [])

    if not records:
        await update.message.reply_text("История пуста.")
    else:
        await update.message.reply_text("📊 История:\n" + "\n".join(records[-5:]))

# отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено ❌")
    return ConversationHandler.END

# ================= Запуск =================

def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            FUEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fuel)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            DISTANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_distance)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("history", show_history))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    Thread(target=run_flask).start()
    run_bot()
