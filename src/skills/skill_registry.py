import importlib
import inspect
import pkgutil
from typing import Dict, Any, Callable

class SkillRegistry:
    def __init__(self):
        self.skills: Dict[str, Callable] = {}
        self._load_skills()

    def _load_skills(self):
        import src.skills
        for _, module_name, _ in pkgutil.iter_modules(src.skills.__path__):
            if module_name == 'skill_registry': continue
            module = importlib.import_module(f"src.skills.{module_name}")
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if hasattr(func, 'is_skill'):
                    self.skills[name] = func

    def get_skill(self, name: str) -> Callable:
        return self.skills.get(name)

    def list_skills(self) -> Dict[str, str]:
        return {name: func.__doc__ or "No description" for name, func in self.skills.items()}

def aisha_skill(func):
    """Decorator to mark a function as an Aisha skill."""
    func.is_skill = True
    return func
