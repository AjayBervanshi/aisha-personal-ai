import importlib
import inspect
import pkgutil
import logging
from typing import Dict, Any, Callable, List

log = logging.getLogger("Aisha.Skills")

def aisha_skill(func):
    """Decorator to mark a function as an Aisha skill that she can use dynamically."""
    func.is_skill = True
    return func

class SkillRegistry:
    def __init__(self):
        self.skills: Dict[str, Callable] = {}
        self._load_skills()

    def _load_skills(self):
        import src.skills
        for _, module_name, _ in pkgutil.iter_modules(src.skills.__path__):
            if module_name == 'skill_registry': continue
            try:
                module = importlib.import_module(f"src.skills.{module_name}")
                # Reload module so hot-reloading works if Aisha adds a file
                importlib.reload(module)
                for name, func in inspect.getmembers(module, inspect.isfunction):
                    if getattr(func, 'is_skill', False):
                        self.skills[name] = func
                        log.info(f"Loaded skill: {name} from {module_name}.py")
            except Exception as e:
                log.error(f"Failed to load skill module {module_name}: {e}")

    def get_skill(self, name: str) -> Callable:
        return self.skills.get(name)

    def list_skills_for_ai(self) -> List[Dict[str, Any]]:
        """
        Converts all loaded Python functions into the JSON Schema format
        required by Gemini/OpenAI for function calling (tools).
        """
        tools = []
        for name, func in self.skills.items():
            sig = inspect.signature(func)
            doc = inspect.getdoc(func) or f"Executes the {name} skill."

            # Build parameter schema based on type hints
            properties = {}
            required = []

            for param_name, param in sig.parameters.items():
                if param_name == 'self': continue

                param_type = "string" # Default
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == list or getattr(param.annotation, '__origin__', None) == list:
                    param_type = "array"

                properties[param_name] = {
                    "type": param_type,
                    "description": f"Parameter {param_name}"
                }

                if param.default == inspect.Parameter.empty:
                    required.append(param_name)

            tool_schema = {
                "name": name,
                "description": doc,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
            tools.append({"type": "function", "function": tool_schema})

        return tools

    def execute_skill(self, name: str, kwargs: Dict[str, Any]) -> Any:
        """Executes a skill by name with the given arguments."""
        func = self.skills.get(name)
        if not func:
            return f"Error: Skill '{name}' not found."

        try:
            log.info(f"Executing skill: {name} with args: {kwargs}")
            return func(**kwargs)
        except Exception as e:
            log.error(f"Error executing skill {name}: {e}")
            return f"Error executing {name}: {str(e)}"

    def list_skills(self) -> Dict[str, str]:
        """Returns a simple dictionary mapping skill names to their descriptions."""
        return {name: func.__doc__ or "No description" for name, func in self.skills.items()}
