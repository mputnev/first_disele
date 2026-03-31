import os
from datetime import datetime
import pytz
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

TOKEN = os.getenv("TOKEN")
if TOKEN is None:
    raise ValueError("TOKEN не найден! Установите переменную окружения.")

user_data = {}
history = {}

main_kb = ReplyKeyboardMarkup([["🚗 Рассчитать", "📜 История"]], resize_keyboard=True)
cancel_kb = ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True)

# Таймзона Москва
moscow_tz = pytz.timezone("Europe/Moscow")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет 👋 Выбери действие:", reply_markup=main_kb)

async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if text == "❌ Отмена":
        user_data[user_id] = {}
        await update.message.reply_text("Отменено ❌", reply_markup=main_kb)
        return

    if text == "📜 История":
        user_history = history.get(user_id, [])
        if not user_history:
            await update.message.reply_text("История пуста 📭", reply_markup=main_kb)
            return
        msg = "📜 Последние расчёты:\n\n" + "\n\n".join(user_history[-5:])
        await update.message.reply_text(msg, reply_markup=main_kb)
        return

    if text == "🚗 Рассчитать":
        user_data[user_id] = {"step": "r"}
        await update.message.reply_text("⛽ Введите расход (или сразу три параметра через пробел: Расход на 100\км | Цена топлива | Необходимое расстояние):", reply_markup=cancel_kb)
        return

    parts = text.split()
    if len(parts) == 3:
        try:
            r, s, d = map(float, parts)
            await calculate_and_send(update, user_id, r, s, d)
            return
        except:
            pass

    if user_id not in user_data:
        await update.message.reply_text("Нажми кнопку 👇", reply_markup=main_kb)
        return

    data = user_data[user_id]
    try:
        value = float(text)
    except:
        await update.message.reply_text("❌ Введите число!")
        return

    if data["step"] == "r":
        data["r"] = value
        data["step"] = "s"
        await update.message.reply_text("💰 Введите цену:")
    elif data["step"] == "s":
        data["s"] = value
        data["step"] = "d"
        await update.message.reply_text("📍 Введите расстояние:")
    elif data["step"] == "d":
        data["d"] = value
        await calculate_and_send(update, user_id, data["r"], data["s"], data["d"])

async def calculate_and_send(update, user_id, r, s, d):
    l = (d / 100) * r
    q = l * s
    now = datetime.now(moscow_tz).strftime("%d.%m.%Y %H:%M")  # дата и время по Москве

    result = f"{now} — ⛽ {l:.2f} л | 💸 {q:.2f}"

    await update.message.reply_text(f"🚗 *Результат:*\n\n{result}", parse_mode="Markdown")

    history.setdefault(user_id, []).append(result)
    user_data[user_id] = {}
    await update.message.reply_text("Готово ✅", reply_markup=main_kb)

# Запуск
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle))
app.run_polling()
