"""
skill_registry.py
==================
Aisha's Live Skill Registry — skills she creates persist and are reused forever.

When a user asks for something Aisha can't do natively (e.g. "find flights",
"check cricket score"), she:
  1. Checks if she already has a skill for it
  2. If yes: loads and runs it immediately (no re-creation)
  3. If no: writes code via AI, tests it in sandbox, saves it, then runs it

Skills are Python files in src/skills/ decorated with @aisha_skill.
They're loaded at startup and can be hot-loaded when new ones are created.
"""

import importlib
import inspect
import logging
import os
import pkgutil
import sys
from pathlib import Path
from typing import Callable, Dict, Optional

log = logging.getLogger("Aisha.Skills")

PROJECT_ROOT = Path(__file__).parent.parent.parent


def aisha_skill(func):
    """Decorator to mark a function as an Aisha skill."""
    func.is_skill = True
    return func


class SkillRegistry:
    """
    Live skill registry. Loads all @aisha_skill-decorated functions from src/skills/
    at init, and can hot-load new skills created at runtime.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.skills: Dict[str, Callable] = {}
        self.skill_descriptions: Dict[str, str] = {}
        self._load_all_skills()
        self._initialized = True

    def _load_all_skills(self):
        """Scan src/skills/ and load all @aisha_skill-decorated functions."""
        import src.skills
        loaded = 0
        for _, module_name, _ in pkgutil.iter_modules(src.skills.__path__):
            if module_name == "skill_registry":
                continue
            try:
                module = importlib.import_module(f"src.skills.{module_name}")
                for name, func in inspect.getmembers(module, inspect.isfunction):
                    if getattr(func, "is_skill", False):
                        self.skills[name] = func
                        self.skill_descriptions[name] = (func.__doc__ or "").strip().split("\n")[0]
                        loaded += 1
            except Exception as e:
                log.debug(f"Skipped skill module {module_name}: {e}")
        log.info(f"Loaded {loaded} skills from {len(self.skills)} functions")

    def get_skill(self, name: str) -> Optional[Callable]:
        """Get a skill by exact name."""
        return self.skills.get(name)

    def find_skill(self, query: str) -> Optional[tuple]:
        """
        Find the best matching skill for a natural language query.
        Returns (name, function) or None.
        """
        query_lower = query.lower()
        query_words = set(query_lower.split())

        best_match = None
        best_score = 0

        for name, func in self.skills.items():
            name_words = set(name.lower().replace("_", " ").split())
            doc = (func.__doc__ or "").lower()

            # Score: how many query words appear in skill name or docstring
            score = 0
            for word in query_words:
                if len(word) < 3:
                    continue
                if word in name.lower():
                    score += 3
                if word in doc:
                    score += 1

            if score > best_score:
                best_score = score
                best_match = (name, func)

        if best_score >= 3:
            return best_match
        return None

    def list_skills(self) -> Dict[str, str]:
        """Return all skills with descriptions."""
        return {name: self.skill_descriptions.get(name, "No description") for name in self.skills}

    def run_skill(self, name: str, *args, **kwargs) -> str:
        """Execute a skill by name and return its output as a string."""
        func = self.skills.get(name)
        if not func:
            return f"Skill '{name}' not found"
        try:
            result = func(*args, **kwargs)
            return str(result) if result is not None else "Done (no output)"
        except Exception as e:
            log.error(f"Skill '{name}' failed: {e}")
            return f"Skill '{name}' failed: {e}"

    def hot_load_skill(self, module_name: str) -> bool:
        """Load (or reload) a single skill module at runtime."""
        full_name = f"src.skills.{module_name}"
        try:
            if full_name in sys.modules:
                module = importlib.reload(sys.modules[full_name])
            else:
                module = importlib.import_module(full_name)

            loaded = 0
            for name, func in inspect.getmembers(module, inspect.isfunction):
                if getattr(func, "is_skill", False):
                    self.skills[name] = func
                    self.skill_descriptions[name] = (func.__doc__ or "").strip().split("\n")[0]
                    loaded += 1

            log.info(f"Hot-loaded {loaded} skills from {module_name}")
            return loaded > 0
        except Exception as e:
            log.error(f"Failed to hot-load {module_name}: {e}")
            return False

    def create_and_register_skill(self, task: str, ai_router=None) -> Optional[str]:
        """
        Create a new skill from a natural language task description.
        Generates code, tests it, saves to src/skills/, hot-loads it.
        Returns the skill function name, or None on failure.
        """
        import re

        skill_name = re.sub(r"[^a-z0-9]+", "_", task.lower())[:25].strip("_")
        if not skill_name:
            skill_name = "custom_task"
        file_name = f"auto_{skill_name}"
        file_path = PROJECT_ROOT / "src" / "skills" / f"{file_name}.py"

        # Check if skill file already exists
        if file_path.exists():
            self.hot_load_skill(file_name)
            match = self.find_skill(task)
            if match:
                log.info(f"Reusing existing skill: {match[0]}")
                return match[0]

        if not ai_router:
            from src.core.ai_router import AIRouter
            ai_router = AIRouter()

        prompt = f"""Write a Python function for Aisha AI that does:
{task}

RULES:
1. The function MUST be decorated with @aisha_skill (import from src.skills.skill_registry)
2. The function should take minimal or no arguments
3. Use requests library for any HTTP/API calls
4. Return a human-readable string result
5. Handle ALL errors with try/except — never crash
6. Include a clear docstring explaining what the skill does
7. Include if __name__ == "__main__": block that calls the function and prints result

Example structure:
from src.skills.skill_registry import aisha_skill
import requests

@aisha_skill
def {skill_name}():
    \"\"\"Does the thing the user asked for.\"\"\"
    try:
        # actual implementation
        return "result"
    except Exception as e:
        return f"Error: {{e}}"

if __name__ == "__main__":
    print({skill_name}())

Return ONLY Python code. No markdown, no explanation."""

        result = ai_router.generate(
            system_prompt="You are an expert Python developer. Write clean, working code.",
            user_message=prompt,
        )
        code = result.text.strip()

        # Strip markdown if AI included it
        if "```python" in code:
            code = code.split("```python", 1)[1].split("```", 1)[0].strip()
        elif "```" in code:
            code = code.split("```", 1)[1].split("```", 1)[0].strip()

        # Validate syntax
        import ast
        try:
            ast.parse(code)
        except SyntaxError as e:
            log.error(f"Generated skill has syntax error: {e}")
            return None

        # Sandbox test
        from src.core.self_improvement import _run_code_sandbox
        test = _run_code_sandbox(code, str(file_path))
        if not test["passed"]:
            log.warning(f"Skill sandbox test failed: {test['error'][:200]}")
            # One retry with error feedback
            retry_result = ai_router.generate(
                system_prompt="You are an expert Python developer. Fix this code.",
                user_message=f"This code failed with error:\n{test['error'][:500]}\n\nOriginal code:\n{code}\n\nFix it and return ONLY the corrected Python code.",
            )
            code = retry_result.text.strip()
            if "```python" in code:
                code = code.split("```python", 1)[1].split("```", 1)[0].strip()
            elif "```" in code:
                code = code.split("```", 1)[1].split("```", 1)[0].strip()
            try:
                ast.parse(code)
            except SyntaxError:
                return None
            test2 = _run_code_sandbox(code, str(file_path))
            if not test2["passed"]:
                log.error("Skill retry also failed — giving up")
                return None

        # Save the skill
        file_path.write_text(code, encoding="utf-8")
        log.info(f"Skill saved: {file_path}")

        # Hot-load into registry
        self.hot_load_skill(file_name)

        # Find the skill function name
        match = self.find_skill(task)
        if match:
            return match[0]

        # Fallback: find any new @aisha_skill function in the code
        for name in self.skills:
            if skill_name in name:
                return name

        return None
