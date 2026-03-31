import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # URL Render

if not TOKEN or not WEBHOOK_URL:
    raise ValueError("TOKEN или WEBHOOK_URL не установлены!")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! 🚗\nЯ могу посчитать расход топлива для поездки.\n"
        "Напиши данные в формате: расход_на_100_км, стоимость_литра, расстояние_поездки\n"
        "Пример: 7.5, 60, 200"
    )

async def calculate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.replace(",", " ").split()
    try:
        if len(text) < 3:
            await update.message.reply_text("Ошибка: нужно 3 числа (расход, цена, расстояние)")
            return
        r = float(text[0])      # расход на 100 км
        s = float(text[1])      # цена литра
        d = float(text[2])      # расстояние
        if r <= 0 or s <= 0 or d <= 0:
            await update.message.reply_text("Все числа должны быть больше 0")
            return
        l = (d / 100) * r
        q = l * s
        await update.message.reply_text(f"Для поездки потребуется {l:.2f} литров топлива.\nНа сумму {q:.2f}")
    except ValueError:
        await update.message.reply_text("Ошибка: введи числа корректно через пробел или запятую")

# Создание приложения
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, calculate))

# Настройка Webhook
PORT = int(os.getenv("PORT", 8443))
app.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")
app.run_webhook(
    listen="0.0.0.0",
    port=PORT,
    webhook_path=f"/{TOKEN}"
)
