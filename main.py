from tgtoken import tgtoken
from planner_wrap import exec_distribution, get_marks
import json
import os
import asyncio
import threading
import time
from datetime import datetime
import pytz
import signal
from telegram import Update, InputFile, Bot, Message, User, Chat
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
    Application,
    CallbackContext,
    ContextTypes
)
from types import SimpleNamespace
# Пути к файлам
TASKS_FILE = 'tasks.json'
USERS_FILE = 'users.json'
SETTINGS_FILE = 'settings.json'
STATE_FILE = 'state.json'
# Константы
AWAITING_NAME, AWAITING_TASKS, AWAITING_PASSWORD = range(3)
AWAITING_FILE = range(1)

# Константы, которые будут загружены из файла
QUANTITY_OF_PREFS = 0
QUANTITY_OF_TASKS = 0
RANDOM_SEED = 0
blacklist = []
ADMINS = []
DEADLINE_DAY = 0
DEADLINE_HOUR = 0
DEADLINE_MINUTE = 0
# Флаги
POST_EXEC_STATE = False

# Функция для распаковки настроек
def load_settings():
    global QUANTITY_OF_PREFS, QUANTITY_OF_TASKS, RANDOM_SEED, ADMINS
    global DEADLINE_DAY, DEADLINE_HOUR, DEADLINE_MINUTE
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
        QUANTITY_OF_PREFS = settings_data['QUANTITY_OF_PREFS']
        QUANTITY_OF_TASKS = settings_data['QUANTITY_OF_TASKS']
        RANDOM_SEED = settings_data['RANDOM_SEED']
        DEADLINE_DAY = settings_data['DEADLINE_DAY']
        DEADLINE_HOUR = settings_data['DEADLINE_HOUR']
        DEADLINE_MINUTE = settings_data['DEADLINE_MINUTE']
        ADMINS = settings_data['admins']
        print("Настройки успешно загружены.")
    
    except FileNotFoundError:
        print(f"Файл {SETTINGS_FILE} не найден.")
    except json.JSONDecodeError:
        print("Ошибка при чтении файла настроек. Некорректный формат JSON.")

def load_state():
    global blacklist
    global POST_EXEC_STATE

    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)

        blacklist = settings_data['blacklist']
        POST_EXEC_STATE = settings_data['POST_EXEC_STATE']

        print("Состояние успешно загружено.")
    
    except FileNotFoundError:
        print(f"Файл {STATE_FILE} не найден.")
    except json.JSONDecodeError:
        print("Ошибка при чтении файла настроек. Некорректный формат JSON.")

def save_state():
    global blacklist, POST_EXEC_STATE

    # Формируем данные для сохранения
    state_data = {
        'blacklist': blacklist,
        'POST_EXEC_STATE': POST_EXEC_STATE
    }

    # Пишем данные в файл state.json
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, ensure_ascii=False, indent=4)
        print("Состояние успешно сохранено в state.json.")
    except Exception as e:
        print(f"Ошибка при сохранении состояния: {e}")


def shutdown_handler(signum, frame):
    print("Завершение работы бота...")
    save_state()  # Сохраняем состояние перед завершением
    exit(0)

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
    marks = get_marks()
    user_data = context.user_data
    full_name = update.message.text
    user_id = str(update.effective_user.id)

    print(f"Получено имя: {full_name} от пользователя {user_id}")  # Debug

    # Проверяем, есть ли имя пользователя в словаре marks
    if full_name not in marks:
        await update.message.reply_text(f"Ошибка: Человека с таким именем и фамилией нет в группе, введи фамилию и имя точно также, как они заданы в гугл таблице (но без отчества)")
        return ConversationHandler.END

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
    await update.message.reply_text("Бот для распределения задач по Макро 2 группы пан"
                                     "Введите /start для регистрации пользователя,/tasks для отправки задач, /check для проверки того, заявки на какие задачи система зачла, /send_info, чтобы получить файл с паарметрами для сверки результатов распределения")

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
    global POST_EXEC_STATE
    POST_EXEC_STATE = False
    print(f"Архив сохранен в файл: {archive_filename}")  # Debug

# Обертка для архивирования задач с проверкой времени
def archive_tasks_wrapper():
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    if now.weekday() == 2 and now.hour == 0 and now.minute == 0:  # Среда в полночь
        archive_tasks()


async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    # Проверить, есть ли пользователь в списке администраторов
    if user_id in ADMINS:
        await update.message.reply_text("Вы авторизованы как администратор.")
        return ConversationHandler.END
    
    # Если не администратор, запросить пароль для доступа
    await update.message.reply_text("К сожалению (или счастью), вы не админ")
    return ConversationHandler.END

# Хендлер для всех сообщений
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Обрабатываем сообщение: '{update.message.text}' в состоянии {context.user_data.get('state', 'None')}")  # Debug

    if context.user_data.get('state') == AWAITING_TASKS:
        await receive_tasks(update, context)
    elif context.user_data.get('state') == AWAITING_NAME:
        await receive_name(update, context)
    else:
        await update.message.reply_text("Неизвестная команда, введите /help для вывода справки.")

async def execute_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in context.user_data or not context.user_data[user_id].get('is_admin'):
        await update.message.reply_text("У вас нет прав доступа для выполнения этой команды.")
        return
    archive_tasks()
    await update.message.reply_text("Архивирование успешно выполнено")

# Функция для отправки файла info.json
async def send_info_file(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if POST_EXEC_STATE == True:
        # Проверяем, существует ли файл info.json
        if os.path.exists('info.json'):
            with open('info.json', 'rb') as file:
                await update.message.reply_document(file, caption="Вот файл с информацией о распределении задач.")
        else:
            await update.message.reply_text("Файл info.json не найден.")
    else:
        await update.message.reply_text("Распределения задач еще не было.")

# Новые функции
# Обертка над exec_distribution
# Обертка для выполнения распределения задач и сохранения данных
# Обертка для выполнения распределения задач и сохранения данных
def exec_distribution_wrapper(blacklist, quantity_of_tasks, random_seed):
    # Вызов функции exec_distribution
    ans, marks, preferences, blacklist, rand_seed = exec_distribution(blacklist, quantity_of_tasks, random_seed)
    global POST_EXEC_STATE
    POST_EXEC_STATE = True
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

async def simulate_and_notify_all_users(ans):
    # Создаем поддельный объект бота
    bot = Bot(token=tgtoken())
    # Загружаем данные пользователей из файла
    users_data = load_data('users.json')
    # Создаем поддельные объекты контекста и обновления
    context = SimpleNamespace(bot=bot)
    ans_message = "\n".join([f"{name}: {', '.join(map(str, tasks))}" for name, tasks in ans.items()])
    # Отправляем сообщение всем пользователям
    for user_id in users_data.keys():
        try:
            await bot.send_message(chat_id=user_id, text=f"Распределение задач завершено:\n{ans_message}")
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

def check_and_execute_distribution():
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    if now.weekday() == DEADLINE_DAY and now.hour == DEADLINE_HOUR and now.minute == DEADLINE_MINUTE:
        ans = exec_distribution_wrapper(blacklist, QUANTITY_OF_TASKS,  RANDOM_SEED)
        asyncio.run(simulate_and_notify_all_users(ans))
    return

# Шаг 1: Команда /update_settings, бот просит отправить файл
async def update_settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Проверяем, что пользователь является администратором
    if user_id not in context.user_data or not context.user_data.get(user_id, {}).get('is_admin'):
        await update.message.reply_text("У вас нет прав администратора для выполнения этой команды.")
        return ConversationHandler.END

    # Просим отправить файл
    await update.message.reply_text("Пожалуйста, отправьте файл с настройками (settings.json).")
    
    # Переходим в состояние ожидания файла
    return AWAITING_FILE

# Шаг 2: Прием и обработка файла settings.json
async def receive_settings_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    # Проверяем, что файл был отправлен
    if not document:
        await update.message.reply_text("Пожалуйста, прикрепите файл с настройками.")
        return AWAITING_FILE

    # Проверяем, что это файл с расширением .json
    if not document.file_name.endswith(".json"):
        await update.message.reply_text("Пожалуйста, отправьте файл формата JSON.")
        return AWAITING_FILE

    # Получаем файл и сохраняем его
    file = await document.get_file()
    file_path = os.path.join(os.getcwd(), SETTINGS_FILE)

    try:
        # Сохраняем файл
        await file.download_to_drive(file_path)
        await update.message.reply_text("Файл settings.json успешно загружен и сохранен.")
    except Exception as e:
        await update.message.reply_text(f"Произошла ошибка при сохранении файла: {e}")

    # Завершаем диалог
    load_settings()
    return ConversationHandler.END

# Шаг 3: Обработка отмены
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

def background_tasks():
    time.sleep(10)
    while True:
        print("Running background tasks...")
        archive_tasks_wrapper()
        check_and_execute_distribution()
        time.sleep(60)  # Проверяем раз в 10 секунд


def main() -> None:
    load_settings()
    load_state()
    signal.signal(signal.SIGINT, shutdown_handler)
    print("Запуск бота...")  # Debug
    app = ApplicationBuilder().token(tgtoken()).build()

    # Определяем ConversationHandler для управления состояниями
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AWAITING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_name)],
            AWAITING_TASKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_tasks)],
            AWAITING_FILE: [MessageHandler(filters.Document.ALL, receive_settings_file)],
        },
        fallbacks=[CommandHandler("help", help_command)],
    )
    # Новый ConversationHandler для команды /update_settings
    update_settings_handler = ConversationHandler(
        entry_points=[CommandHandler("update_settings", update_settings_command)],
        states={
            AWAITING_FILE: [MessageHandler(filters.Document.ALL, receive_settings_file)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Обработчики команд
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler("tasks", tasks_command))  # Команда для отправки задач
    app.add_handler(CommandHandler("check", check_tasks))  # Команда для проверки задач
    app.add_handler(CommandHandler("admin", admin_command))  # Команда для администрирования
    app.add_handler(CommandHandler("exec_distr", execute_tasks))  # Команда для выполнения задач администратором
    app.add_handler(CommandHandler("exec_archive", execute_archive))  # Команда для выполнения задач администратором
    app.add_handler(CommandHandler("help", help_command))  # Команда помощи
    app.add_handler(CommandHandler("send_info", send_info_file))  # Команда помощи
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_messages))  # Хендлер для всех сообщений
    # хендлер для изменения настроек
    app.add_handler(update_settings_handler)
    # Запуск фоновых задач
    thread = threading.Thread(target=background_tasks, daemon=True)
    thread.start()
    # Запуск бота
    print("Бот запущен, ожидаем взаимодействия...")  # Debug
    app.run_polling()

if __name__ == '__main__':
    main()
