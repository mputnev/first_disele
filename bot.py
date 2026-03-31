import os
from datetime import datetime, timedelta
from threading import Thread
from flask import Flask

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)

# ================= Flask =================
app_flask = Flask(__name__)

@app_flask.route("/")
def home():
    return "Bot is running!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app_flask.run(host="0.0.0.0", port=port)

# ================= BOT =================
TOKEN = os.getenv("TOKEN")
FUEL, PRICE, DISTANCE = range(3)
history = {}

# Клавиатура
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Рассчитать", callback_data="calc")],
        [InlineKeyboardButton("📜 История", callback_data="history")]
    ])

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.effective_user.first_name or "друг"
    await update.message.reply_text(
        f"Привет, {name}! 🚗\n"
        "Что умеет этот бот:\n"
        "- Рассчитать стоимость и количество топлива для вашей поездки\n"
        "Выбери действие:",
        reply_markup=main_menu()
    )

# Обработка кнопок
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "calc":
        await query.message.reply_text("Введи расход топлива на 100 км:")
        return FUEL

    elif query.data == "history":
        user_id = query.from_user.id
        records = history.get(user_id, [])

        if not records:
            await query.message.reply_text("История пуста.")
        else:
            await query.message.reply_text(
                "📊 История последних расчетов:\n" + "\n".join(records[-5:])
            )

# ======== ШАГИ ========

async def get_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = float(update.message.text.replace(",", "."))
        if r <= 0:
            raise ValueError
        context.user_data['r'] = r
        await update.message.reply_text("Введи цену литра:")
        return PRICE
    except:
        await update.message.reply_text("Введите корректное число!")
        return FUEL

async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        s = float(update.message.text.replace(",", "."))
        if s <= 0:
            raise ValueError
        context.user_data['s'] = s
        await update.message.reply_text("Введи расстояние (км):")
        return DISTANCE
    except:
        await update.message.reply_text("Введите корректное число!")
        return PRICE

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
            f"💰 Стоимость: {q:.2f} ₽\n\n"
            "Соблюдайте ПДД, берегите себя и пассажиров, и удачной поездки! 🎉",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔄 Заново", callback_data="calc")],
                [InlineKeyboardButton("📜 История", callback_data="history")]
            ])
        )

        # история с корректировкой времени МСК (+3 часа)
        user_id = update.effective_user.id
        date = (datetime.utcnow() + timedelta(hours=3)).strftime("%d.%m.%Y %H:%M")
        record = f"{date} — {l:.2f} л / {q:.2f} ₽"
        history.setdefault(user_id, []).append(record)

        return ConversationHandler.END

    except:
        await update.message.reply_text("Введите корректное число!")
        return DISTANCE

# ================= Запуск =================

def run_bot():
    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(buttons, pattern="calc")],
        states={
            FUEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fuel)],
            PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
            DISTANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_distance)],
        },
        fallbacks=[]
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(buttons))

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    Thread(target=run_flask).start()
    run_bot()
