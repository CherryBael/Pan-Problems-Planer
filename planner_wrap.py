from soc_planner_v2 import Planner
from utils import google_sheet_to_json, generate_entry
def get_marks(url):
    marks = google_sheet_to_json(url)
    marks = {x:int(y) for x,y in marks.items()}
    return marks
def exec_distribution(blacklist, problem_numbers, rand_seed, url, sup_grade):
    marks = google_sheet_to_json(url, "marks.json")
    marks = {x:int(y) for x,y in marks.items()}
    # пользователи, набравшие максимум баллов
    #sup_grade_users = [key for key, value in marks.items() if value >= sup_grade]
    marks_backup = marks.copy()
    preferences = generate_entry("tasks.json") 
    #plr = Planner(marks, preferences, list(set(blacklist + sup_grade_users)), problem_numbers, sup_grade,rand_seed)
    plr = Planner(marks, preferences, blacklist, problem_numbers, sup_grade, rand_seed)
    ans = plr.distribute_problems()
    for x in list(ans.keys()):
        print(x, ans[x])
    #return ans, marks_backup, preferences, list(set(blacklist + sup_grade_users)), rand_seed
    return ans, marks_backup, preferences, blacklist, rand_seed
