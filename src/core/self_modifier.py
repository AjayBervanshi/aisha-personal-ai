"""
self_modifier.py
================
Aisha's Autonomous Self-Modification Engine.

THE FULL FLOW:
  1. Aisha tries to do a task
  2. She hits a CapabilityError or catches an exception
  3. She calls self_modifier.handle_missing_skill(task_description)
  4. She researches, writes, and saves a new Python skill
  5. She loads it dynamically (no restart needed)
  6. She retries the task with the new skill
  7. She notifies Ajay: "I levelled up!"

This makes Aisha truly self-improving.
"""

import os
import ast
import sys
import logging
import importlib
import importlib.util
from pathlib import Path
from datetime import datetime

log = logging.getLogger("Aisha.SelfModifier")

PROJECT_ROOT = Path(__file__).parent.parent.parent
SKILLS_DIR   = PROJECT_ROOT / "src" / "skills"
SKILLS_DIR.mkdir(parents=True, exist_ok=True)


class CapabilityError(Exception):
    """Raise this when Aisha doesn't have a skill yet."""
    pass


class SelfModifier:
    """
    Aisha's self-modification engine.
    She detects gaps in her abilities and fills them herself.
    """

    def __init__(self):
        from src.core.ai_router import AIRouter
        self.ai  = AIRouter()
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        self.ajay_id   = os.getenv("AJAY_TELEGRAM_ID")
        self._skill_registry = {}  # name -> loaded module
        self._gap_log = []         # Track what she tried to learn

    # ── CAPABILITY CHECK ──────────────────────────────────────────────────────

    def has_skill(self, skill_name: str) -> bool:
        """Check if a skill module exists."""
        skill_file = SKILLS_DIR / f"{skill_name}.py"
        return skill_file.exists() or skill_name in self._skill_registry

    def get_skill(self, skill_name: str):
        """Load and return a skill module. Returns None if not found."""
        if skill_name in self._skill_registry:
            return self._skill_registry[skill_name]

        skill_file = SKILLS_DIR / f"{skill_name}.py"
        if skill_file.exists():
            return self._load_skill_from_file(skill_name, skill_file)

        return None

    def _load_skill_from_file(self, skill_name: str, skill_file: Path):
        """Dynamically import a skill Python file."""
        try:
            spec = importlib.util.spec_from_file_location(skill_name, skill_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            self._skill_registry[skill_name] = module
            log.info(f"[SelfModifier] Skill loaded: {skill_name}")
            return module
        except Exception as e:
            log.error(f"[SelfModifier] Failed to load skill {skill_name}: {e}")
            return None

    # ── CORE SELF-MODIFICATION FLOW ───────────────────────────────────────────

    def handle_missing_skill(self, task_description: str, skill_name: str = None) -> dict:
        """
        THE MAIN FLOW:
        Aisha detects she can't do something → researches → writes code → loads it.

        Args:
            task_description: What she was trying to do (natural language)
            skill_name: Optional specific name for the skill module

        Returns:
            dict: {success, skill_name, module, message}
        """
        if not skill_name:
            # Auto-generate skill name from description
            words = task_description.lower().split()[:5]
            skill_name = "_".join(w.strip(".,!?") for w in words if w.isalnum())

        log.info(f"[SelfModifier] Missing skill detected: '{task_description}'")
        self._gap_log.append({
            "timestamp": datetime.now().isoformat(),
            "task": task_description,
            "skill": skill_name,
        })

        # Step 1: Research & Write the code
        new_code = self._research_and_write(task_description, skill_name)
        if not new_code:
            return {"success": False, "message": "Could not generate code for this skill."}

        # Step 2: Validate syntax
        try:
            ast.parse(new_code)
        except SyntaxError as e:
            log.error(f"[SelfModifier] Generated code has syntax errors: {e}")
            # Try to fix it
            new_code = self._fix_syntax(new_code, str(e))
            try:
                ast.parse(new_code)
            except SyntaxError:
                return {"success": False, "message": f"Could not fix syntax: {e}"}

        # Step 3: Save to skills directory
        skill_file = SKILLS_DIR / f"{skill_name}.py"
        skill_file.write_text(new_code, encoding="utf-8")
        log.info(f"[SelfModifier] New skill saved: {skill_file}")

        # Step 4: Load it dynamically (no restart!)
        module = self._load_skill_from_file(skill_name, skill_file)
        if not module:
            return {"success": False, "message": "Code saved but couldn't load the module."}

        # Step 5: Notify Ajay
        msg = (
            f"Ajju, I just levelled up! I built a new skill for myself.\n\n"
            f"Task I needed to do: {task_description}\n"
            f"New skill saved: src/skills/{skill_name}.py\n\n"
            f"I can now do this on my own without help! 💜🆙"
        )
        self._notify_ajay(msg)

        # Step 6: Git commit the new skill
        self._auto_commit(skill_name, task_description)

        return {
            "success": True,
            "skill_name": skill_name,
            "module": module,
            "file": str(skill_file.relative_to(PROJECT_ROOT)),
            "message": f"New skill created: {skill_name}"
        }

    def _research_and_write(self, task_description: str, skill_name: str) -> str:
        """Ask AI to write a complete Python skill for the given task."""
        prompt = f"""You are Aisha's developer brain. Aisha is a Python AI assistant and she needs to learn a new skill.

Task she needs to do: {task_description}

Write a COMPLETE, WORKING Python module that gives Aisha this capability.

Requirements:
- Module name will be: {skill_name}
- Must have a main class or top-level function Aisha can call
- Proper error handling (try/except) on every external call
- Uses only standard library OR libraries already installed (requests, openai, google-generativeai, supabase, telebot)
- Logging with: log = logging.getLogger("Aisha.Skills.{skill_name}")
- Must have a clear docstring explaining what this skill does
- Must work on first run — no setup required

Write ONLY the raw Python code. No markdown. No backticks. No explanations outside the code."""

        result = self.ai.generate(
            system_prompt="You are an expert Python developer writing production code for an AI assistant.",
            user_message=prompt
        )
        code = result.text.strip()

        # Strip markdown if AI added it
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        return code

    def _fix_syntax(self, code: str, error: str) -> str:
        """Ask AI to fix a syntax error in generated code."""
        prompt = f"""This Python code has a syntax error: {error}

Fix ONLY the syntax error. Return the complete corrected Python code with no markdown:

{code}"""
        result = self.ai.generate("You are a Python debugger.", prompt)
        fixed = result.text.strip()
        if "```" in fixed:
            fixed = fixed.split("```python")[1].split("```")[0].strip() if "```python" in fixed else fixed.split("```")[1].split("```")[0].strip()
        return fixed

    def _notify_ajay(self, message: str):
        """Send Telegram message to Ajay."""
        try:
            import telebot
            bot = telebot.TeleBot(self.bot_token)
            bot.send_message(self.ajay_id, message)
        except Exception as e:
            log.warning(f"[SelfModifier] Telegram notify failed: {e}")

    def _auto_commit(self, skill_name: str, description: str):
        """Auto-commit new skill to git."""
        try:
            import subprocess
            subprocess.run(
                ["git", "add", f"src/skills/{skill_name}.py"],
                cwd=PROJECT_ROOT, capture_output=True
            )
            subprocess.run(
                ["git", "commit", "-m", f"feat(self): Aisha auto-built skill '{skill_name}' — {description[:60]}"],
                cwd=PROJECT_ROOT, capture_output=True
            )
            subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=PROJECT_ROOT, capture_output=True
            )
            log.info(f"[SelfModifier] New skill committed and pushed: {skill_name}")
        except Exception as e:
            log.warning(f"[SelfModifier] Git commit failed: {e}")

    # ── REPORT ────────────────────────────────────────────────────────────────

    def get_skill_list(self) -> list:
        """Return all skills Aisha has learned."""
        return [f.stem for f in SKILLS_DIR.glob("*.py") if f.stem != "__init__"]

    def get_gap_report(self) -> str:
        """Return a report of everything Aisha tried (and failed) to do."""
        if not self._gap_log:
            return "No capability gaps logged yet."
        lines = ["Aisha Capability Gap Report:"]
        for g in self._gap_log:
            lines.append(f"- [{g['timestamp']}] {g['task']} → skill: {g['skill']}")
        return "\n".join(lines)


# ── GLOBAL INSTANCE (shared across the app) ───────────────────────────────────
_modifier = None

def get_modifier() -> SelfModifier:
    """Get or create the global SelfModifier instance."""
    global _modifier
    if _modifier is None:
        _modifier = SelfModifier()
    return _modifier


def try_with_self_learn(task_fn, task_description: str, skill_name: str = None):
    """
    Wrapper: Try a function. If it raises CapabilityError,
    Aisha auto-builds the missing skill and retries once.

    Usage:
        result = try_with_self_learn(
            lambda: my_function(),
            "Post a reel to Instagram",
            "instagram_reel_poster"
        )
    """
    modifier = get_modifier()
    try:
        return task_fn()
    except CapabilityError:
        log.info(f"[SelfModifier] CapabilityError caught. Learning: {task_description}")
        result = modifier.handle_missing_skill(task_description, skill_name)
        if result["success"]:
            # Retry now that the skill exists
            return task_fn()
        else:
            raise RuntimeError(f"Aisha couldn't learn: {task_description}")
