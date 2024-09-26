import requests
import csv
import json
##################
# Дальше идет функция для загрузки гугл таблицы с оценками в словарь и json файл, она написана через gpt, комменты не трогал
#################
def google_sheet_to_json(sheet_url, json_filename=''):
    """
    Загружает данные из Google Таблицы и преобразует их в словарь.
    
    :param sheet_url: Обычная ссылка на Google Таблицу
    :param json_filename: Имя файла для сохранения данных в JSON формате (по умолчанию пустая строка)
    :return: Словарь с данными студентов и их суммами
    """
    
    def convert_to_csv_url(sheet_url):
        """
        Преобразует обычную ссылку на Google Таблицу в CSV-ссылку.
        
        :param sheet_url: Обычная ссылка на Google Таблицу
        :return: CSV-ссылка
        """
        # Извлекаем идентификатор таблицы из URL
        sheet_id = sheet_url.split('/d/')[1].split('/')[0]
        csv_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&id={sheet_id}'
        return csv_url

    # Получаем CSV-ссылку
    csv_url = convert_to_csv_url(sheet_url)

    # Загрузка данных из CSV
    response = requests.get(csv_url)
    response.raise_for_status()  # Проверка на ошибки запроса

    # Декодируем текст и разбираем CSV
    decoded_content = response.content.decode('utf-8')
    reader = csv.DictReader(decoded_content.splitlines())

    # Создаем словарь с ключом -- Студент и значением -- Сумма для первой группы
    result_dict = {}
    for row in reader:
        if row['Группа'] == 'Группа 1':  # Замените на название вашей группы
            student = row['Студент']
            total_sum = row['Сумма']
            result_dict[student] = total_sum

    # Сохраняем словарь в JSON файл, если указано имя файла
    if json_filename:
        with open(json_filename, 'w', encoding='utf-8') as json_file:
            json.dump(result_dict, json_file, ensure_ascii=False, indent=4)
        print(f"Данные успешно сохранены в {json_filename}")

    return result_dict


def list_min_values(lst):
    minval = min(lst)
    mins = [i for i,x in enumerate(lst) if x == minval]
    return mins

def generate_entry(inp_entries):
    with open(inp_entries, 'r') as file:
        entry = json.load(file)
        return entry
