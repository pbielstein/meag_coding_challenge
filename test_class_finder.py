#%% test class_finder

from class_finder import MatchClassToGoal, GoalInput

matcher = MatchClassToGoal()
result = matcher(input=GoalInput(
    module_path="C:/githome/coding_challange/example_module.py",
    goal="process financial transactions"
))
print(result.match_name)
