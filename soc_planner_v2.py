from random import shuffle, seed, random
from utils import list_min_values, map_tasks
# Словарь оценок в формате: Имя -- количество баллов
marks = {}
# Словарь предпочтений в формате: Имя -- отсортированный по убыванию предпочтений массив номеров задач
preferences = {}
# Массив имен исключенных из раздачи задач людей
blacklist = []
# Количество задач
problems_quantity = 0

class Planner:
    def __init__(self, marks, preferences, blacklist, initial_numbers, sup_grade, rand_seed):
        # Задаем сид генерации для воспроизводимости результатов рандомайзера
        # Нужно, чтобы каждый у себя на машине мог убедиться, что код на сервере отработал честно 
        seed(rand_seed)
        # Длина списка предпочтений
        self.pref_len = len(list(preferences.values())[0])
        # количество задач
        problems_quantity = len(initial_numbers)
        # Проверяем корректность данных
        for x in list(preferences.keys()):
            assert(type(marks[x]) == int)
            assert(len(preferences[x]) == self.pref_len)
        self.marks = marks
        # словарь отображения задач
        self.mapping_inside = map_tasks(initial_numbers)
        # словарь обратного отображения задач
        self.mapping_outside = {y:x for x,y in self.mapping_inside.items()}
        # Отображаем номера задач из предпочтений
        print("------------------------")
        print(self.mapping_inside)
        self.mapped_preferences = {x:[self.mapping_inside[z] for z in y] for x,y in preferences.items()}
        print(self.mapped_preferences)
        self.blacklist = blacklist
        self.problems_quantity = problems_quantity
        self.sup_grade = sup_grade
    def calculate_order(self, marks):
        # Когда задаем порядок, то для равных по оценкам людей сортируем в случайном порядке
        order = [x for x in sorted(self.mapped_preferences.keys(), key = lambda y: (marks[y], random())) if (x not in self.blacklist and marks[x] < self.sup_grade)]
        print(marks)
        assert(len(order) > 0)
        return order
    # Возвращает словарь распределенных задач для одного прохода по списку людей в формате: Имя -- номер задачи
    def iterate_order(self, marks, unselected):
        order = self.calculate_order(marks)
        # Массив с количеством людей, поставивших задачу в приоритетные среди всех оставшихся людей
        # Нужен для определения задач, которые имеются в приоритете среди еще не проверенных людей

        problem_prefs = {i:0 for i in range(1, self.problems_quantity + 1)}
        # Новые оценки из предположения, что человек, которому выдали задачу, получит за нее балл
        new_marks = marks
        # Вычисляем начальное состояние этого массива
        for x in order:
            for j in range(self.pref_len):
                problem_prefs[self.mapped_preferences[x][j]] += 1
        # Словарь распределения задач в формате: Имя -- номер задачи
        distribution = {}
        # Считаем задачи
        for x in order:
            # Проверяем наличие задач
            if len(unselected) == 0:
                break
            fl = False
            for j in range(self.pref_len):
                if self.mapped_preferences[x][j] in unselected:
                    distribution[x] = self.mapped_preferences[x][j]
                    new_marks[x] += 1
                    unselected.remove(self.mapped_preferences[x][j])
                    fl = True
                    break
            # Убираем его голоса из массива приоритетных задач
            for j in range(self.pref_len):
                problem_prefs[self.mapped_preferences[x][j]] -= 1
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
            unselected.remove(mins[0])
        return distribution, new_marks, unselected
    # Итоговый подсчет
    def distribute_problems(self):
        unselected = set([i for i in range(1, self.problems_quantity + 1)])
        marks = self.marks
        # Словарь итогового распределения вида: Имя -- массив номеров задач
        distribution = {x:[] for x in list(self.mapped_preferences.keys())}
        while len(unselected) != 0:
            tmpdistr,marks,unselected = self.iterate_order(marks, unselected)
            for x in list(tmpdistr.keys()):
                distribution[x].append(tmpdistr[x])
        # Возвращаем отображенные обратно номера задач
        return {x: [self.mapping_outside[z] for z in y] for x,y in distribution.items()}


            

            

                     

            
            

        

            

