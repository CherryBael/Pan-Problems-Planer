from tgtoken import tgtoken
from passwd import check_password
from planner_wrap import exec_distribution
import json
import os
import asyncio
from datetime import datetime
import pytz
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)

# Пути к файлам
TASKS_FILE = 'tasks.json'
USERS_FILE = 'users.json'

# Константы
AWAITING_NAME, AWAITING_TASKS, AWAITING_PASSWORD = range(3)
MAX_ATTEMPTS = 3
QUANTITY_OF_PREFS = 5
QUANTITY_OF_TASKS = 22
RANDOM_SEED = 2201
blacklist = []

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
        print(f"Пользователь найден: {user_name}")  # Debug
        await update.message.reply_text(f"Добро пожаловать, {user_name}! Введите /tasks, чтобы отправить номера задач.")
        return ConversationHandler.END
    else:
        print("Пользователь новый, запрашиваем Фамилию и Имя")  # Debug
        await update.message.reply_html(
            rf"Привет, {user.mention_html()}! Пожалуйста, введите вашу Фамилию и Имя."
        )
        return AWAITING_NAME

# Получение имени и фамилии
async def receive_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    full_name = update.message.text
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
    return ConversationHandler.END

# Команда для отправки номеров задач
async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    print("Запущена команда /tasks")  # Debug

    if 'full_name' not in user_data:
        print("Ошибка: пользователь не ввел Фамилию и Имя")  # Debug
        await update.message.reply_text("Пожалуйста, сначала введите свое имя с помощью команды /start.")
        return ConversationHandler.END

    print(f"Пользователь {user_data['full_name']} вводит задачи")  # Debug
    await update.message.reply_text("Введите номера 5 наиболее приоритетных задач через пробел.")
    
    # Устанавливаем состояние ожидания задач
    context.user_data['state'] = AWAITING_TASKS
    return AWAITING_TASKS  # Важно вернуть правильное состояние

# Получение номеров задач
async def receive_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    tasks = update.message.text.split()  # Разделяем по пробелу

    print(f"Получены задачи: {tasks} от пользователя {user_data['full_name']}")  # Debug

    try:
        # Преобразуем в список целых чисел и проверяем условия
        task_numbers = [int(task.strip()) for task in tasks]
        if (any(task < 1 or task > QUANTITY_OF_TASKS for task in task_numbers) or 
            len(task_numbers) != QUANTITY_OF_PREFS or 
            len(set(task_numbers)) != len(task_numbers)):  # Проверка на уникальность
            await update.message.reply_text(f"Пожалуйста, введите ровно {QUANTITY_OF_PREFS} уникальных целых чисел от 1 до {QUANTITY_OF_TASKS}.")
            return AWAITING_TASKS

        user_data['task_numbers'] = task_numbers
    except ValueError:
        print("Ошибка: введены некорректные данные для задач")  # Debug
        await update.message.reply_text("Пожалуйста, введите только целые числа, разделенные пробелами.")
        return AWAITING_TASKS

    # Сохраняем данные о задачах
    all_data = load_data(TASKS_FILE)
    full_name = user_data['full_name']
    all_data[full_name] = user_data['task_numbers']  # Перезаписываем задачи, если пользователь их уже вводил
    save_data(TASKS_FILE, all_data)  # Сохраняем данные в tasks.json

    print(f"Задачи сохранены для пользователя {full_name}: {user_data['task_numbers']}")  # Debug

    # Подтверждаем введенные задачи
    await update.message.reply_text(f"Вы ввели следующие номера задач: {', '.join(map(str, user_data['task_numbers']))}.")
    
    # Сбрасываем состояние после выполнения команды
    context.user_data['state'] = None
    return ConversationHandler.END

# Команда для получения справки
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("Команда /help")  # Debug
    await update.message.reply_text("Этот бот поможет вам управлять вашими задачами. "
                                     "Введите /start для регистрации или /tasks для отправки задач.")

# Команда для проверки задач пользователя
async def check_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    full_name = user_data.get('full_name')

    if not full_name:
        await update.message.reply_text("Пожалуйста, введите свое имя с помощью команды /start.")
        return

    all_data = load_data(TASKS_FILE)
    tasks = all_data.get(full_name, "У вас нет сохраненных задач.")
    await update.message.reply_text(f"Ваши задачи: {tasks}")

# Архивирование задач
# Функция для архивирования задач
def archive_tasks():
    archive_filename = f"old_tasks_{datetime.now(pytz.timezone('Europe/Moscow')).strftime('%Y-%m-%d')}.json"
    all_data = load_data(TASKS_FILE)
    save_data(archive_filename, all_data)  # Сохраняем данные в архив
    save_data(TASKS_FILE, {})  # Обнуляем файл задач
    print(f"Архив сохранен в файл: {archive_filename}")  # Debug

# Обертка для архивирования задач с проверкой времени
def archive_tasks_wrapper():
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    if now.weekday() == 2 and now.hour == 0:  # Среда в полночь
        archive_tasks()


# Команда для авторизации админа
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)

    if user_id in context.user_data and context.user_data[user_id].get('is_admin'):
        await update.message.reply_text("Вы уже авторизованы как администратор.")
        return ConversationHandler.END

    await update.message.reply_text("Введите пароль для доступа к админским функциям.")
    
    # Устанавливаем состояние ожидания пароля
    context.user_data['state'] = AWAITING_PASSWORD
    return AWAITING_PASSWORD

# Проверка пароля
async def receive_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)

    # Проверка на количество попыток
    if user_id in context.user_data and 'attempts' in context.user_data[user_id]:
        attempts = context.user_data[user_id]['attempts']
        if attempts >= MAX_ATTEMPTS:
            await update.message.reply_text("Превышено максимальное количество попыток.")
            return ConversationHandler.END

    password = update.message.text

    if check_password(password):  # Функция проверки пароля из модуля passwd
        context.user_data[user_id] = {'is_admin': True}  # Устанавливаем статус администратора
        context.user_data[user_id].pop('attempts', None)  # Удаляем данные о попытках
        await update.message.reply_text("Вы успешно авторизованы как администратор.")
        return ConversationHandler.END
    else:
        # Увеличиваем количество попыток
        if user_id not in context.user_data:
            context.user_data[user_id] = {}
        context.user_data[user_id]['attempts'] = context.user_data[user_id].get('attempts', 0) + 1
        
        remaining_attempts = MAX_ATTEMPTS - context.user_data[user_id]['attempts']
        await update.message.reply_text(f"Неверный пароль. Осталось попыток: {remaining_attempts}.")
        
        if remaining_attempts <= 0:
            await update.message.reply_text("Превышено максимальное количество попыток.")
            del context.user_data[user_id]  # Удаляем данные пользователя из контекста
            return ConversationHandler.END

    return AWAITING_PASSWORD

# Хендлер для всех сообщений
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Обрабатываем сообщение: '{update.message.text}' в состоянии {context.user_data.get('state', 'None')}")  # Debug

    if context.user_data.get('state') == AWAITING_TASKS:
        await receive_tasks(update, context)
    elif context.user_data.get('state') == AWAITING_NAME:
        await receive_name(update, context)
    elif context.user_data.get('state') == AWAITING_PASSWORD:
        await receive_password(update, context)
    else:
        await update.message.reply_text("Я не понимаю. Пожалуйста, используйте команды /start, /tasks или /help.")

async def execute_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in context.user_data or not context.user_data[user_id].get('is_admin'):
        await update.message.reply_text("У вас нет прав доступа для выполнения этой команды.")
        return
    print("starting archieve check")
    archive_tasks()
    await update.message.reply_text("Архивирование успешно выполнено")

# Новые функции
# Обертка над exec_distribution
# Обертка для выполнения распределения задач и сохранения данных
# Обертка для выполнения распределения задач и сохранения данных
def exec_distribution_wrapper(blacklist, quantity_of_tasks, random_seed):
    # Вызов функции exec_distribution
    ans, marks, preferences, blacklist, rand_seed = exec_distribution(blacklist, quantity_of_tasks, random_seed)
    
    # Сохранение данных в файл info.json
    info_data = {
        'preferences': preferences,
        'marks': marks,
        'blacklist': blacklist,
        'rand_seed': rand_seed,
        'quantity': QUANTITY_OF_TASKS,
    }
    save_data('info.json', info_data)  # Сохраняем данные в info.json
    
    return ans  # Возвращаем результаты распределения


# Команда для выполнения задач
async def execute_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in context.user_data or not context.user_data[user_id].get('is_admin'):
        await update.message.reply_text("У вас нет прав доступа для выполнения этой команды.")
        return

    # Вызов обертки для выполнения распределения задач
    ans = exec_distribution_wrapper(blacklist, QUANTITY_OF_TASKS, RANDOM_SEED)

    # Форматируем сообщение для пользователей
    ans_message = "\n".join([f"{name}: {', '.join(map(str, tasks))}" for name, tasks in ans.items()])
    
    # Отправляем сообщение всем пользователям
    users_data = load_data(USERS_FILE)
    for user_id in users_data.keys():
        await context.bot.send_message(chat_id=user_id, text=f"Распределение задач завершено:\n{ans_message}")

    await update.message.reply_text("Задачи успешно распределены.")


def check_and_execute_distribution():
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    if now.weekday() == 4 and now.hour == 22:  # Пятница в 22:00
        execute_distribution()

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
            AWAITING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_password)],
        },
        fallbacks=[CommandHandler("help", help_command)],
    )

    # Обработчики команд
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("tasks", tasks_command))  # Команда для отправки задач
    app.add_handler(CommandHandler("check", check_tasks))  # Команда для проверки задач
    app.add_handler(CommandHandler("admin", admin_command))  # Команда для администрирования
    app.add_handler(CommandHandler("exec_distr", execute_tasks))  # Команда для выполнения задач администратором
    app.add_handler(CommandHandler("exec_archive", execute_archive))  # Команда для выполнения задач администратором
    app.add_handler(CommandHandler("help", help_command))  # Команда помощи
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))  # Хендлер для всех сообщений

    # Запуск бота
    print("Бот запущен, ожидаем взаимодействия...")  # Debug
    app.run_polling()

    # Запуск проверки каждые 10 секунд
    while True:
        asyncio.run(archive_tasks_wrapper())
        asyncio.run(check_and_execute_distribution())
        asyncio.sleep(10)  # Проверяем раз в 10 секунд

if __name__ == '__main__':
    main()
