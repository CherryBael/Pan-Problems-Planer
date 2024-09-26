from random import shuffle, seed, random
from utils import list_min_values
# Задаем сид генерации для воспроизводимости результатов рандомайзера
# Нужно, чтобы каждый у себя на машине мог убедиться, что код на сервере отработал честно 
seed(2201)
# Словарь оценок в формате: Имя -- количество баллов
marks = {}
# Словарь предпочтений в формате: Имя -- отсортированный по убыванию предпочтений массив номеров задач
preferences = {}
# Массив имен исключенных из раздачи задач людей
blacklist = []
# Количество задач
problems_quantity = 0

class Planner:
    def __init__(self, marks, preferences, blacklist, problems_quantity):
        # Длина списка предпочтений
        self.pref_len = len(list(preferences.values())[0])
        # Проверяем корректность данных
        for x in list(preferences.keys()):
            assert(type(marks[x]) == int)
            assert(len(preferences[x]) == self.pref_len)
        self.marks = marks
        self.preferences = preferences
        self.blacklist = blacklist
        self.problems_quantity = problems_quantity
    # Возвращает массив имен, который отображает порядок распределения задач (все люди из self.blacklist исключаются)
    def calculate_order(self, marks):
        #order = [x for x in sorted(self.preferences.keys(), key = lambda y: marks[y]) if x not in self.blacklist]
        # Когда задаем порядок, то для равных по оценкам людей сортируем в случайном порядке
        order = [x for x in sorted(self.preferences.keys(), key = lambda y: (marks[y], random())) if x not in self.blacklist]
        return order
    # Возвращает словарь распределенных задач для одного прохода по списку людей в формате: Имя -- номер задачи
    def iterate_order(self, marks, unselected):
        order = self.calculate_order(marks)
        # Массив с количеством людей, поставивших задачу в приоритетные среди всех оставшихся людей
        # Нужен для определения задач, которые имеются в приоритете среди еще не проверенных людей
        problem_prefs = {i:0 for i in range(1, self.pref_len + 1)}
        # Новые оценки из предположения, что человек, которому выдали задачу, получит за нее балл
        new_marks = marks
        # Вычисляем начальное состояние этого массива
        for x in order:
            for j in range(self.pref_len):
                problem_prefs[self.preferences[x][j]] += 1
        # Словарь распределения задач в формате: Имя -- номер задачи
        distribution = {}
        # Считаем задачи
        for x in order:
            # Проверяем наличие задач
            if len(unselected) == 0:
                break
            fl = False
            for j in range(self.pref_len):
                if self.preferences[x][j] in unselected:
                    distribution[x] = self.preferences[x][j]
                    new_marks[x] += 1
                    unselected.remove(self.preferences[x][j])
                    fl = True
                    break
            # Убираем его голоса из массива приоритетных задач
            for j in range(self.pref_len):
                problem_prefs[self.preferences[x][j]] -= 1
            if fl:
                continue
            # Если не нашли задачу в приоритетах, то ищем те, которые в приоритете у как можно меньшего количества людей
            # Cписок задач, которые еще никто не выбрал (Выбранные помечаются количеством людей равным 10e6)
            tmplst = [x if i in unselected else 10e6 for i,x in problem_prefs.items()]
            # Находим случайную задачу среди тех, которые минимальное количество людей поставили в приоритетные и выдаем ее человеку
            mins = list_min_values(tmplst)
            shuffle(mins)
            distribution[x] = mins[0]
            new_marks[x] += 1
        return distribution, new_marks, unselected
    # Итоговый подсчет
    def distribute_problems(self):
        unselected = set([i for i in range(1, self.problems_quantity + 1)])
        marks = self.marks
        # Словарь итогового распределения вида: Имя -- массив номеров задач
        distribution = {x:[] for x in list(self.preferences.keys())}
        while len(unselected) != 0:
            tmpdistr,marks,unselected = self.iterate_order(marks, unselected)
            for x in list(tmpdistr.keys()):
                distribution[x].append(tmpdistr[x])
        return distribution


            

            

                     

            
            

        

            

