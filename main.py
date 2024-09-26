from tgtoken import tgtoken
import json
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# Путь к файлу
JSON_FILE = 'tasks.json'

# Константы для состояний
AWAITING_NAME, AWAITING_TASKS = range(2)

# Функция для сохранения данных
def save_data(data):
    with open(JSON_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Функция для загрузки данных
def load_data():
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# Стартовая команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    await update.message.reply_html(
        rf"Привет, {user.mention_html()}! Пожалуйста, введите вашу Фамилию и Имя."
    )
    return AWAITING_NAME

# Получение имени и фамилии
async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    user_data['full_name'] = update.message.text
    await update.message.reply_text("Спасибо! Теперь введите номера 5 наиболее приоритетных задач через запятую.")
    return AWAITING_TASKS

# Получение номеров задач
async def receive_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    tasks = update.message.text.split(',')

    try:
        # Преобразуем в список целых чисел
        task_numbers = [int(task.strip()) for task in tasks]
        user_data['task_numbers'] = task_numbers[:5]  # Берем только 5 задач
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите только целые числа, разделенные запятыми.")
        return AWAITING_TASKS

    # Сохраняем данные
    all_data = load_data()
    all_data[user_data['full_name']] = user_data['task_numbers']
    save_data(all_data)

    await update.message.reply_text(f"Вы ввели следующие номера задач: {', '.join(map(str, user_data['task_numbers']))}.")
    
    # Завершаем диалог
    return ConversationHandler.END

# Команда для получения справки
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Этот бот поможет вам управлять вашими задачами. "
                                    "Введите /start для начала, и следуйте инструкциям.")

# Основная функция
def main() -> None:
    app = ApplicationBuilder().token(tgtoken()).build()

    # Определяем ConversationHandler для управления состояниями
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AWAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            AWAITING_TASKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_tasks)],
        },
        fallbacks=[CommandHandler("help", help_command)],
    )

    # Добавляем обработчики
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("help", help_command))

    # Запуск бота
    app.run_polling()

if __name__ == '__main__':
    main()
