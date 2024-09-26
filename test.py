from soc_planner_v2 import Planner
from utils import generate_entry
def test_main():
    marks = generate_entry("marks.json")
    marks = {x:int(y) for x,y in marks.items()}
    preferences = generate_entry("preferences.json") 
    blacklist = []
    plr = Planner(marks, preferences, blacklist, 5)
    ans = plr.distribute_problems()
    for x in list(ans.keys()):
        print(x, ans[x])
    return
test_main()
