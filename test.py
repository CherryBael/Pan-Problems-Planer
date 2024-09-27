from soc_planner_v2 import Planner
from utils import generate_entry
def test_main():
    info = generate_entry("info.json")
    marks = info["marks"]
    preferences = info["preferences"]
    marks = {x:int(y) for x,y in marks.items()}
    blacklist = info["blacklist"]
    rand_seed = info["rand_seed"]
    quantity_of_tasks = info["quantity"]
    plr = Planner(marks, preferences, blacklist, quantity_of_tasks, rand_seed)
    ans = plr.distribute_problems()
    for x in list(ans.keys()):
        print(x, ans[x])
    return
test_main()
