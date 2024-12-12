from tgtoken import tgtoken
from planner_wrap import exec_distribution, get_marks
import json
import os
import asyncio
import threading
import time
import random
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
NOTIF_OFF_USERS_FILE = 'notif_off_users.json'
# Константы
AWAITING_NAME, AWAITING_TASKS, AWAITING_MESSAGE = range(3)
AWAITING_FILE = range(1)


QUANTITY_OF_PREFS = 0
QUANTITY_OF_TASKS = 0
SUP_GRADE = 0
RANDOM_SEED = 0
SHEET_URL = ""
BLACKLIST = []
ADMINS = []
TASKS = []
NOTIF_OFF_USERS = []
# Константы дедлайна подачи заявок
# DEADLINE_DAY -- 1 понедельник, итд
DEADLINE_DAY = 0
DEADLINE_HOUR = 0
DEADLINE_MINUTE = 0
# Константы времени архивирования данных
CLEANUP_DAY = 0
CLEANUP_HOUR = 0
CLEANUP_MINUTE = 0

# Функция для распаковки настроек
def load_settings():
    global QUANTITY_OF_PREFS, RANDOM_SEED, ADMINS, TASKS, SHEET_URL, SUP_GRADE
    global DEADLINE_DAY, DEADLINE_HOUR, DEADLINE_MINUTE, CLEANUP_DAY, CLEANUP_HOUR, CLEANUP_MINUTE
    try:
        with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
            settings_data = json.load(f)
        QUANTITY_OF_PREFS = settings_data['QUANTITY_OF_PREFS']
        SUP_GRADE = settings_data['SUP_GRADE']
        RANDOM_SEED = settings_data['RANDOM_SEED']
        SHEET_URL = settings_data['SHEET_URL']
        CLEANUP_DAY = settings_data['CLEANUP_DAY']
        CLEANUP_HOUR = settings_data['CLEANUP_HOUR']
        CLEANUP_MINUTE = settings_data['CLEANUP_MINUTE']
        DEADLINE_DAY = settings_data['DEADLINE_DAY']
        DEADLINE_HOUR = settings_data['DEADLINE_HOUR']
        DEADLINE_MINUTE = settings_data['DEADLINE_MINUTE']
        ADMINS = settings_data['ADMINS']
        TASKS =  list(map(str, settings_data['TASKS']))
        print("Настройки успешно загружены.")
    
    except FileNotFoundError:
        print(f"Файл {SETTINGS_FILE} не найден.")
    except json.JSONDecodeError:
        print("Ошибка при чтении файла настроек. Некорректный формат JSON.")
    QUANTITY_OF_TASKS = len(TASKS)
def load_state():
    global NOTIF_OFF_USERS

    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state_data = json.load(f)
        NOTIF_OFF_USERS = state_data['NOTIF_OFF_USERS']
    
    except FileNotFoundError:
        NOTIF_OFF_USERS = []
        save_state()
        print(f"Файл {STATE_FILE} не найден, будет сгенерирован стандартный")
    except json.JSONDecodeError:
        print("Ошибка при чтении файла настроек. Некорректный формат JSON.")

def save_state():
    global NOTIF_OFF_USERS

    # Формируем данные для сохранения
    state_data = {
        'NOTIF_OFF_USERS': NOTIF_OFF_USERS,
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
    marks = get_marks(SHEET_URL)
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
# Команда для отправки сообщения всем пользователям
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    print("Запущена команда /broadcast")  # Debug
    user_id = str(update.effective_user.id)
    if user_id not in ADMINS:
            await update.message.reply_text("У вас нет прав доступа для выполнения этой команды.")
            return ConversationHandler.END

    await update.message.reply_text("Введите сообщение для отправки пользователям")
    # Устанавливаем состояние ожидания сообщения
    context.user_data['state'] = AWAITING_MESSAGE
    return AWAITING_MESSAGE

# Получение сообщения
async def receive_broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    message = update.message.text
    message = "BROADCAST MESSAGE\n\n" + message
    await notify_all_users(update, context, message)
    # Сбрасываем состояние после выполнения команды
    context.user_data['state'] = None
    return ConversationHandler.END
    
# Команда для отправки номеров задач
async def tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    print("Запущена команда /tasks")  # Debug
    
    if 'full_name' not in user_data:
        # Загружаем данные о пользователях
        users_data = load_data(USERS_FILE)
        # Если пользователь уже существует, не запрашиваем имя
        user = update.effective_user
        user_id = str(user.id)
        if user_id in users_data:
            user_name = users_data[user_id]
            context.user_data['full_name'] = user_name
            user_data = context.user_data
        else:
            print("Ошибка: пользователь не ввел Фамилию и Имя")  # Debug
            await update.message.reply_text("Пожалуйста, сначала введите свое имя с помощью команды /start.")
            return ConversationHandler.END

    print(f"Пользователь {user_data['full_name']} вводит задачи")  # Debug
    await update.message.reply_text("Введите номера 5 наиболее приоритетных задач через пробел.")
    await update.message.reply_text(f"Доступные номера задач:{", ".join(map(str, TASKS))}")
    
    # Устанавливаем состояние ожидания задач
    context.user_data['state'] = AWAITING_TASKS
    return AWAITING_TASKS  # Важно вернуть правильное состояние


# Получение номеров задач
async def receive_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    tasks = update.message.text.split()  # Разделяем по пробелу

    print(f"Получены задачи: {tasks} от пользователя {user_data['full_name']}")  # Debug

    try:
        str_tasks = ", ".join(map(str, TASKS))
        task_numbers = [str(task.strip()) for task in tasks]
        print(TASKS, task_numbers, sep = "\n")
        print(any(task not in TASKS for task in task_numbers))
        if (any(task not in TASKS for task in task_numbers) or 
            len(task_numbers) != QUANTITY_OF_PREFS or  # Проверка на соответствие заданному количеству
            len(set(task_numbers)) != len(task_numbers)):  # Проверка на уникальность
            await update.message.reply_text(f"Пожалуйста, введите ровно {QUANTITY_OF_PREFS} уникальных чисел из следующего списка {str_tasks}.")
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
    await update.message.reply_text(f"Теперь вы записаны на следующие задачи: {', '.join(map(str, user_data['task_numbers']))}.")
    
    # Сбрасываем состояние после выполнения команды
    context.user_data['state'] = None
    return ConversationHandler.END

# Команда для получения справки
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Бот для распределения задач по Макро 2 группы ПАН\n"
                                     "Введите /start для регистрации пользователя,/tasks для отправки задач, /check для проверки того, заявки на какие задачи система зачла, /notify_off для отключения уведомлений о неотправленных задачах, /notify_on для включения уведомлений о неотправленных задачах")
    return ConversationHandler.END
# Команда для получения справки по админ панели                                     
async def admin_help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Помощь по админ панели\n"
                                    "Введите /exec_distr для немедленного распределения задач, /exec_cleanup для сброса всех заявок на задачи, /update_settings для обновления файла настроек, /time для выведения текущего времени, /broadcast для отправки широковещательного сообщения")
    return ConversationHandler.END
# Команда отключения уведомлений для пользователя
async def notify_off(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    if user_id not in NOTIF_OFF_USERS:
        NOTIF_OFF_USERS.append(user_id)
        save_state()
    await update.message.reply_text("Уведомления о неотправленых задачах отключены, чтобы повторно их включить используйте команду /notify_on\n")
    return ConversationHandler.END
# Команда включения уведомлений для пользователя
async def notify_on(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    if user_id in NOTIF_OFF_USERS:
        NOTIF_OFF_USERS.remove(user_id)
        save_state()
    await update.message.reply_text("Уведомления о неотправленых задачах включены\n")
    return ConversationHandler.END                                      
# Команда для проверки задач пользователя
async def check_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_data = context.user_data
    full_name = user_data.get('full_name')

    if not full_name:
        # Загружаем данные о пользователях
        users_data = load_data(USERS_FILE)
        # Если пользователь уже существует, не запрашиваем имя
        user = update.effective_user
        user_id = str(user.id)
        if user_id in users_data:
            user_name = users_data[user_id]
            context.user_data['full_name'] = user_name
            full_name = user_data.get('full_name')
        else:
            await update.message.reply_text("Не могу найти вас в списке пользователей, пожалуйста, введите свое имя с помощью команды /start.")
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
    if now.weekday() == CLEANUP_DAY and now.hour == CLEANUP_HOUR and now.minute == CLEANUP_MINUTE:  # Среда в полночь
        archive_tasks()
        asyncio.run(simulate_and_notify_all_users("Начинается прием заявок на задачи следующей недели"))

# Хендлер для всех сообщений
async def handle_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print(f"Обрабатываем сообщение: '{update.message.text}' в состоянии {context.user_data.get('state', 'None')}")  # Debug

    if context.user_data.get('state') == AWAITING_TASKS:
        await receive_tasks(update, context)
    elif context.user_data.get('state') == AWAITING_NAME:
        await receive_name(update, context)
    elif context.user_data.get('state') == AWAITING_MESSAGE:
        await receive_broadcast_message(update, context)
    else:
        await update.message.reply_text("Неизвестная команда, введите /help для вывода справки.")

async def execute_archive(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ADMINS:
        await update.message.reply_text("У вас нет прав доступа для выполнения этой команды.")
        return
    archive_tasks()
    await update.message.reply_text("Сброс задач успешно выполнен")
    await notify_all_users(update, context, "Начинается прием заявок на задачи следующей недели")

# Новые функции
# Обертка над exec_distribution
# Обертка для выполнения распределения задач и сохранения данных
# Обертка для выполнения распределения задач и сохранения данных
def exec_distribution_wrapper(blacklist, problem_numbers, random_seed):
    # Вызов функции exec_distribution
    ans, marks, preferences, blacklist, rand_seed = exec_distribution(blacklist, problem_numbers, random_seed, SHEET_URL, SUP_GRADE)
    # Сохранение данных в файл info.json
    info_data = {
        'preferences': preferences,
        'marks': marks,
        'blacklist': blacklist,
        'rand_seed': rand_seed,
        'quantity': QUANTITY_OF_TASKS,
        'sup_grade': SUP_GRADE,
    }
    save_data('info.json', info_data)  # Сохраняем данные в info.json
    
    return ans  # Возвращаем результаты распределения


# Команда для выполнения задач
async def execute_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in ADMINS:
        await update.message.reply_text("У вас нет прав доступа для выполнения этой команды.")
        return ConversationHandler.END

    # Вызов обертки для выполнения распределения задач
    ans = exec_distribution_wrapper(BLACKLIST, TASKS, RANDOM_SEED)
    # Форматируем сообщение для пользователей
    ans_message = "\n".join([f"{name}: {', '.join(map(str, tasks))}" for name, tasks in ans.items()])
    
    # Отправляем сообщение всем пользователям
    users_data = load_data(USERS_FILE)
    for user_id in users_data.keys():
        await context.bot.send_message(chat_id=user_id, text=f"Распределение задач завершено:\n{ans_message}")
        if os.path.exists('info.json'):
            with open('info.json', 'rb') as file:
                await update.message.reply_document(file, caption="Файл с информацией по распределению задач")
        else:
            await update.message.reply_text("Файл info.json не найден.")
    await update.message.reply_text("Задачи успешно распределены.")


async def notify_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE, message):
    users_data = load_data(USERS_FILE)
    for user_id in users_data.keys():
        try:
            await context.bot.send_message(chat_id=user_id, text=f"{message}")
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
# Функция отправки уведомлений пользователям, которые не отправили задачи
async def simulate_and_notify_unst_users(ans):
    # Получаем токен для подключения к боту
    bot = Bot(token=tgtoken())
    # Получаем вектор юзеров, у которых включены уведолмения и нет задач
    users_data = load_data(USERS_FILE)
    inverted_users = {value: key for key, value in users_data.items()}
    users_names = set(users_data.values())
    st_users = set(load_data(TASKS_FILE).keys())
    users_names = users_names - st_users
    users_ids = set([inverted_users[x] for x in users_names])
    users_ids -= set(NOTIF_OFF_USERS)
    users_ids = list(users_ids)
    #print(f"Изначальное множетсво {load_data(USERS_FILE).keys()}\n Юзеры, отправившие задачи {st_users} \n Список юзеров, отлючивших уведомления {set(NOTIF_OFF_USERS)}\n Итоговое множество {users_ids}")
    context = SimpleNamespace(bot=bot)
    # Отправляем сообщение пользователям
    message = ans + "\nОтключить уведомления можно командой /notify_off"
    for user_id in users_ids:
        try:
            await context.bot.send_message(chat_id=user_id, text=f"{message}")
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

async def simulate_and_notify_all_users(ans):
    print("функция уведомления юзеров только что была выполнена")
    bot = Bot(token=tgtoken())
    # Загружаем данные пользователей из файла
    users_data = load_data(USERS_FILE)
    context = SimpleNamespace(bot=bot)
    if isinstance(ans, str):
        ans_message = ans
    else:
        ans_message = "\n".join([f"{name}: {', '.join(map(str, tasks))}" for name, tasks in ans.items()])
    # Отправляем сообщение всем пользователям
    for user_id in users_data.keys():
        try:
            if not isinstance(ans, str):
                await bot.send_message(chat_id=user_id, text=f"Распределение задач завершено:\n{ans_message}")
                if os.path.exists('info.json'):
                    with open('info.json', 'rb') as file:
                        print("вошел в нужный иф")
                        await bot.send_document(chat_id=user_id, document=file, caption="Файл с информацией о распределении задач")

                else:
                    await bot.send_message(chat_id=user_id, text=f"Файл info.json не найден.")
            else:
                await bot.send_message(chat_id=user_id, text=f"{ans_message}")
        except Exception as e:
            print(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

def check_and_execute_distribution():
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    if now.weekday() == DEADLINE_DAY -1  and now.hour == DEADLINE_HOUR and now.minute == DEADLINE_MINUTE:
        ans = exec_distribution_wrapper(BLACKLIST, TASKS,  RANDOM_SEED)
        asyncio.run(simulate_and_notify_all_users(ans))
    return
def check_and_notify():
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    if now.weekday() == DEADLINE_DAY -1  and now.hour == DEADLINE_HOUR - 1 and now.minute == DEADLINE_MINUTE:
        asyncio.run(simulate_and_notify_unst_users("Напоминаю, что вы не отправили задачи, а до дедлайна остался час, отправить задачи можно командой /tasks"))
    elif now.weekday() == (DEADLINE_DAY + 6) % 7  and now.hour == DEADLINE_HOUR - 12 and now.minute == DEADLINE_MINUTE or now.weekday() == (DEADLINE_DAY + 5) % 7  and now.hour == DEADLINE_HOUR + 12 and now.minute == DEADLINE_MINUTE:
        asyncio.run(simulate_and_notify_unst_users("Напоминаю, что вы не отправили задачи, а до дедлайна осталось 12 часов, отправить задачи можно командой /tasks"))
    return
async def time_correct_work_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    print(now.weekday, now.hour, now.minute)
    await update.message.reply_text(f"Сейчас {now.hour} часов и {now.minute} минут")
    return ConversationHandler.END
async def goyda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    def get_random_goida():
        options = [
            "Гойда !!!",
            "Гойда, Братцы!",
            "Слава России!",
            "Объявляется Гойда",
            "ГОЙДААААА",
            "Приветствую тебя, Гойдаслав",
            "Гойда, Гойда, Гойда!!!"
        ]
        return random.choice(options)
    await update.message.reply_text(get_random_goida())
    return ConversationHandler.END
# Команда изменения файла настроек
async def update_settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Проверяем, что пользователь является администратором
    if user_id not in ADMINS:
        await update.message.reply_text("У вас нет прав администратора для выполнения этой команды.")
        return ConversationHandler.END

    # Просим отправить файл
    await update.message.reply_text("Пожалуйста, отправьте файл с настройками (settings.json).")
    
    # Переходим в состояние ожидания файла
    return AWAITING_FILE

# Прием файла
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

# Обработка отмены
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    return ConversationHandler.END

def background_tasks():
    time.sleep(10)
    while True:
        print("Running background tasks...")
        archive_tasks_wrapper()
        check_and_execute_distribution()
        check_and_notify()
        time.sleep(60)  # Проверяем раз в 60 секунд


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
            AWAITING_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_broadcast_message)],
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
    app.add_handler(CommandHandler("goyda", goyda))  # Команда для "Гойды"
    app.add_handler(CommandHandler("tasks", tasks_command))  # Команда для отправки задач
    app.add_handler(CommandHandler("check", check_tasks))  # Команда для проверки задач
    app.add_handler(CommandHandler("exec_distr", execute_tasks))  # Команда для немедленного распределения задач (требует прав адмна)
    app.add_handler(CommandHandler("exec_cleanup", execute_archive))  # Команда для немедленной очистки присланных задач (требует прав админа)
    app.add_handler(CommandHandler("broadcast", broadcast)) # Комманда для отправки сообщения всем пользователяи (требует прав админа)
    app.add_handler(CommandHandler("help", help_command))  # Команда помощи
    app.add_handler(CommandHandler("admin_help", admin_help_command))  # Команда помощи панели админа
    #app.add_handler(CommandHandler("send_info", send_info_file)) # Отправялет файл с информацией о распределенных задачах
    app.add_handler(CommandHandler("time", time_correct_work_check)) # Выводит время
    app.add_handler(CommandHandler("notify_off", notify_off)) # Отключает уведолмения о неоптравленных задачах
    app.add_handler(CommandHandler("notify_on", notify_on)) # Включает уведолмения о неоптравленных задачах
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
