import os
from datetime import datetime
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)

TOKEN = os.getenv("TOKEN")
if not TOKEN:
    raise ValueError("TOKEN не установлен!")

# Этапы разговора
FUEL, PRICE, DISTANCE = range(3)

# Словарь для хранения истории (можно заменить на базу для многопользовательского)
history = {}

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name or "друг"
    await update.message.reply_text(
        f"Привет, {user_name}! 🚗\nДавай посчитаем расход топлива.\n"
        "Сначала введи расход топлива на 100 км (например 7.5):"
    )
    return FUEL

# Получаем расход
async def get_fuel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        r = float(update.message.text.replace(",", "."))
        if r <= 0:
            await update.message.reply_text("Расход должен быть больше 0. Попробуй еще раз:")
            return FUEL
        context.user_data['r'] = r
        await update.message.reply_text("Отлично! Теперь введи цену литра бензина (например 60):")
        return PRICE
    except ValueError:
        await update.message.reply_text("Ошибка! Введи число:")
        return FUEL

# Получаем цену
async def get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        s = float(update.message.text.replace(",", "."))
        if s <= 0:
            await update.message.reply_text("Цена должна быть больше 0. Попробуй еще раз:")
            return PRICE
        context.user_data['s'] = s
        await update.message.reply_text("Хорошо! Теперь введи расстояние поездки в километрах (например 200):")
        return DISTANCE
    except ValueError:
        await update.message.reply_text("Ошибка! Введи число:")
        return PRICE

# Получаем расстояние и считаем
async def get_distance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        d = float(update.message.text.replace(",", "."))
        if d <= 0:
            await update.message.reply_text("Расстояние должно быть больше 0. Попробуй еще раз:")
            return DISTANCE

        r = context.user_data['r']
        s = context.user_data['s']

        l = (d / 100) * r
        q = l * s

        # Ограничение до 6 цифр
        if l > 999999 or q > 999999:
            await update.message.reply_text("Сумма или расход слишком большие! 🚨")
            return ConversationHandler.END

        msg = (
            f"Для поездки потребуется 🚗 {l:.2f} литров топлива.\n"
            f"На сумму 💰 {q:.2f}\n\n"
            "Удачной поездки! 🎉"
        )
        await update.message.reply_text(msg)

        # Сохраняем в историю
        user_id = update.effective_user.id
        date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        record = f"{date_str}: {l:.2f} л, {q:.2f} ₽"
        history.setdefault(user_id, []).append(record)

        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("Ошибка! Введи число:")
        return DISTANCE

# Команда /history
async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    records = history.get(user_id, [])
    if not records:
        await update.message.reply_text("История расчетов пуста.")
    else:
        await update.message.reply_text("История твоих расчетов:\n" + "\n".join(records))

# Отмена
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Расчет отменен ❌")
    return ConversationHandler.END

# Создаем приложение
app = ApplicationBuilder().token(TOKEN).build()

conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        FUEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fuel)],
        PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_price)],
        DISTANCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_distance)],
    },
    fallbacks=[CommandHandler('cancel', cancel)]
)

app.add_handler(conv_handler)
app.add_handler(CommandHandler('history', show_history))

if __name__ == "__main__":
    print("Бот запущен через polling...")
    app.run_polling()
