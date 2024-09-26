from tgtoken import tgtoken
import json
import os
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
    CallbackContext,
)
from datetime import datetime
import pytz

# Пути к файлам
TASKS_FILE = 'tasks.json'
USERS_FILE = 'users.json'

# Константы для состояний
AWAITING_NAME, AWAITING_TASKS = range(2)

# Константа для максимального количества задач и их максимального значения
MAX_TASKS = 5
MAX_TASK_NUMBER = 22

# Функция для сохранения данных в файл
def save_data(filename, data):
    print(f"Сохраняем данные в файл: {filename}")  # Debug
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Функция для загрузки данных из файла
def load_data(filename):
    print(f"Загружаем данные из файла: {filename}")  # Debug
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

# Функция для архивирования данных
def archive_tasks():
    current_time = datetime.now(pytz.timezone('Europe/Moscow'))
    if current_time.weekday() == 4 and current_time.hour == 22:  # Пятница и 22:00
        old_tasks_filename = f"old_tasks_{current_time.strftime('%Y-%m-%d')}.json"
        tasks_data = load_data(TASKS_FILE)
        save_data(old_tasks_filename, tasks_data)  # Сохраняем текущие задачи в архив
        save_data(TASKS_FILE, {})  # Очищаем файл tasks.json
        print(f"Архивирование выполнено: {old_tasks_filename} создан и {TASKS_FILE} очищен.")

# Стартовая команда
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    user_id = str(user.id)

    print(f"Получен запрос /start от пользователя {user_id}")  # Debug

    # Загружаем данные о пользователях
    users_data = load_data(USERS_FILE)

    # Если пользователь уже существует, не запрашиваем имя
    if user_id in users_data:
        user_name = users_data[user_id]
        context.user_data['full_name'] = user_name
        context.user_data['state'] = None  # Сброс состояния
        print(f"Пользователь найден: {user_name}")  # Debug
        await update.message.reply_text(f"Добро пожаловать, {user_name}! Введите /tasks, чтобы отправить номера задач.")
        return ConversationHandler.END
    else:
        print("Пользователь новый, запрашиваем имя и фамилию")  # Debug
        await update.message.reply_html(
            rf"Привет, {user.mention_html()}! Пожалуйста, введите ваше имя и фамилию."
        )
        context.user_data['state'] = AWAITING_NAME  # Устанавливаем состояние
        return AWAITING_NAME

# Получение имени и фамилии
async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    full_name = update.message.text.strip()
    user_id = str(update.effective_user.id)

    print(f"Получено имя: {full_name} от пользователя {user_id}")  # Debug

    # Сохраняем имя пользователя
    user_data['full_name'] = full_name

    # Загружаем данные пользователей и добавляем нового пользователя
    users_data = load_data(USERS_FILE)
    users_data[user_id] = full_name
    save_data(USERS_FILE, users_data)

    print(f"Имя пользователя сохранено: {full_name}")  # Debug
    await update.message.reply_text(f"Спасибо, {full_name}! Теперь введите /tasks, чтобы отправить номера задач.")
    context.user_data['state'] = None  # Сброс состояния
    return ConversationHandler.END

# Команда для отправки номеров задач
async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    print("Запущена команда /tasks")  # Debug

    if 'full_name' not in user_data:
        print("Ошибка: пользователь не ввел имя и фамилию")  # Debug
        await update.message.reply_text("Пожалуйста, сначала введите свое имя с помощью команды /start.")
        return ConversationHandler.END

    print(f"Пользователь {user_data['full_name']} вводит задачи")  # Debug
    await update.message.reply_text(f"Введите ровно {MAX_TASKS} номеров задач через пробел.")
    context.user_data['state'] = AWAITING_TASKS  # Устанавливаем состояние
    return AWAITING_TASKS  # Важно вернуть правильное состояние

# Получение номеров задач
async def receive_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    tasks_input = update.message.text.strip()  # Получаем ввод пользователя

    print(f"Получен ввод задач: '{tasks_input}' от пользователя {user_data['full_name']}")  # Debug

    # Проверка на правильный формат ввода
    tasks = [task.strip() for task in tasks_input.split()]  # Разделяем по пробелу

    if len(tasks) != MAX_TASKS:
        print(f"Ошибка: неверное количество задач (ожидалось {MAX_TASKS}, получено {len(tasks)})")  # Debug
        await update.message.reply_text(f"Пожалуйста, введите ровно {MAX_TASKS} номеров задач, разделенных пробелами.")
        return AWAITING_TASKS

    # Проверка на то, что все задачи - целые числа в пределах от 1 до MAX_TASK_NUMBER
    try:
        task_numbers = [int(task) for task in tasks]
        if any(task < 1 or task > MAX_TASK_NUMBER for task in task_numbers):
            raise ValueError("Некорректные номера задач")
        user_data['task_numbers'] = task_numbers
    except ValueError:
        print("Ошибка: введены некорректные данные для задач")  # Debug
        await update.message.reply_text(f"Пожалуйста, вводите только целые числа от 1 до {MAX_TASK_NUMBER}, разделенные пробелами.")
        return AWAITING_TASKS

    # Сохраняем данные о задачах
    all_data = load_data(TASKS_FILE)
    full_name = user_data['full_name']
    all_data[full_name] = user_data['task_numbers']  # Перезаписываем задачи, если пользователь их уже вводил
    save_data(TASKS_FILE, all_data)  # Сохраняем данные в tasks.json

    print(f"Задачи сохранены для пользователя {full_name}: {user_data['task_numbers']}")  # Debug

    # Подтверждаем введенные задачи
    await update.message.reply_text(f"Вы ввели следующие номера задач: {', '.join(map(str, user_data['task_numbers']))}.")
    context.user_data['state'] = None  # Сброс состояния
    return ConversationHandler.END

# Команда для проверки задач пользователя
async def check_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    full_name = user_data.get('full_name')

    if full_name is None:
        await update.message.reply_text("Пожалуйста, введите свое имя с помощью команды /start.")
        return

    all_data = load_data(TASKS_FILE)
    tasks = all_data.get(full_name, None)

    if tasks is None:
        await update.message.reply_text("У вас нет сохраненных задач.")
    else:
        await update.message.reply_text(f"Ваши сохраненные задачи: {', '.join(map(str, tasks))}.")

# Универсальный обработчик сообщений
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    current_state = user_data.get('state', None)  # Получаем текущее состояние

    print(f"Обрабатываем сообщение: '{update.message.text}' в состоянии {current_state}")  # Debug

    if current_state == AWAITING_TASKS:
        await receive_tasks(update, context)  # Обрабатываем как ввод задач
    elif current_state == AWAITING_NAME:
        await receive_name(update, context)  # Обрабатываем как ввод имени
    else:
        await update.message.reply_text("Я не знаю, что с этим делать. Пожалуйста, введите /start или /tasks.")

# Команда для получения справки
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("Команда /help")  # Debug
    await update.message.reply_text("Этот бот поможет вам управлять вашими задачами. "
                                     "Введите /start для регистрации или /tasks для отправки задач.")

# Основная функция
def main() -> None:
    print("Запуск бота...")  # Debug
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

    # Обработчик для универсальных сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Обработчики команд
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("tasks", tasks_command))
    app.add_handler(CommandHandler("check", check_tasks))
    app.add_handler(CommandHandler("help", help_command))

    # Запуск бота
    print("Бот запущен, ожидаем взаимодействия...")  # Debug
    app.run_polling()

    # Запуск архивации задач каждую пятницу в 22:00 по Московскому времени
    while True:
        archive_tasks()
        asyncio.sleep(3600)  # Проверяем каждый час

if __name__ == '__main__':
    main()
