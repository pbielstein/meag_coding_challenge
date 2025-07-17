#%% bonus question: 

import os
# I had some problems with symai's splash screen, this line is a workaround
os.environ["KMP_DUPLICATE_LIB_OK"] = "True"

import importlib.util
import inspect
import difflib
from symai import Expression
from symai.strategy import contract
from symai.models import LLMDataModel
from pydantic import Field


class GoalInput(LLMDataModel):
    module_path: str = Field(description="Path to Python module or package")
    goal: str = Field(description="Goal description to match against class docstrings")

class ClassMatchOutput(LLMDataModel):
    match_name: str = Field(description="Name of the best-matching class or error message")


@contract(verbose=True)
class MatchClassToGoal(Expression):

    def scan_classes(self, module_path: str) -> dict:
        classes = {}

        if os.path.isdir(module_path):
            # scan all .py files 
            for fname in os.listdir(module_path):
                if fname.endswith(".py"):
                    fpath = os.path.join(module_path, fname)
                    classes.update(self.load_classes_from_file(fpath))
        else:
            # single module file
            classes = self.load_classes_from_file(module_path)

        return classes


    def load_classes_from_file(self, path: str) -> dict:
        # dynamically load module
        module_name = os.path.splitext(os.path.basename(path))[0]
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            print(f"Failed to load spec for: {path}")
            return {}
        module = importlib.util.module_from_spec(spec)

        try:
            spec.loader.exec_module(module)
        except Exception as e:
            return {}

        # extract all classes with their docstrings
        return {
            name: cls.__doc__ or ""
            for name, cls in inspect.getmembers(module, inspect.isclass)
            if cls.__module__ == module.__name__
        }


    def find_best_match(self, class_docs: dict, goal: str) -> str:
        best_score = 0
        best_match = None

        for name, doc in class_docs.items():
            # for debugging
            # print(f"[DEBUG] Scanning {name} -> Doc: {repr(doc)}")
            if not isinstance(doc, str):
                continue  
            score = difflib.SequenceMatcher(None, doc.lower(), goal.lower()).ratio()
            if score > best_score:
                best_score = score
                best_match = name

        # this can be tuned
        if best_score < 0.1:
            return "No class found that matches the goal."
        return best_match

    def forward(self, input: GoalInput) -> ClassMatchOutput:
        classes = self.scan_classes(input.module_path)
        if not classes:
            return ClassMatchOutput(match_name="No classes found or module failed to load.")
        best_match = self.find_best_match(classes, input.goal)
        # print(f"[DEBUG] Best match type: {type(best_match)} -> {repr(best_match)}")
        if not isinstance(best_match, str):
            return ClassMatchOutput(match_name="Internal error: Match is not a string.")
        response_data = {"match_name": best_match.strip()}
        # for debugging
        # print(f"[DEBUG] ClassMatchOutput kwargs: {response_data}")
        # print("[DEBUG] Output repr:", repr(ClassMatchOutput(match_name="TransactionProcessor")))
        # print("[DEBUG] Output dict:", ClassMatchOutput(match_name="TransactionProcessor").dict())

        return ClassMatchOutput(**response_data)
  

