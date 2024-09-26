from soc_planner_v2 import Planner
from utils import google_sheet_to_json, generate_entry
def exec_distribution():
    marks = google_sheet_to_json("https://docs.google.com/spreadsheets/d/1yNata06mQnIxJ4y5Ad936cDFiUvH2SToFn1nfkjrswc", "marks.json")
    marks = {x:int(y) for x,y in marks.items()}
    preferences = generate_entry("preferences.json") 
    blacklist = []
    plr = Planner(marks, preferences, blacklist)
    ans = plr.distribute_problems()
    for x in list(ans.keys()):
        print(x, ans[x])
    return
