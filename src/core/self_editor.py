"""
self_editor.py
==============
Aisha's Self-Editing & Self-Improvement Engine.

Aisha can:
1. Read her own source code files
2. Identify bugs, missing features, or improvements
3. Write NEW code and apply patches to herself
4. Add new tools and capabilities without Ajay doing anything

This is Aisha's "brain surgery on herself" module.
She runs this autonomously during her nightly maintenance window.

Workflow:
  detect_gap() -> plan_fix() -> write_code() -> apply_patch() -> test() -> notify_ajay()
"""

import os
import ast
import logging
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional

log = logging.getLogger("Aisha.SelfEditor")

# Root of the Aisha project
PROJECT_ROOT = Path(__file__).parent.parent.parent


class SelfEditor:
    """Aisha edits her own code to add features and fix bugs."""

    def __init__(self):
        from src.core.ai_router import AIRouter
        self.ai = AIRouter()
        self.ajay_id = os.getenv("AJAY_TELEGRAM_ID")
        self.bot_token = os.getenv("TELEGRAM_BOT_TOKEN")

    # ── READ SELF ──────────────────────────────────────────────────────────────

    def read_self(self, filepath: str) -> str:
        """Read one of Aisha's own source files."""
        try:
            full = PROJECT_ROOT / filepath
            return full.read_text(encoding="utf-8")
        except Exception as e:
            log.error(f"[SelfEditor] Cannot read {filepath}: {e}")
            return ""

    def list_own_files(self) -> list:
        """List all Python source files Aisha can inspect."""
        files = []
        for p in (PROJECT_ROOT / "src").rglob("*.py"):
            files.append(str(p.relative_to(PROJECT_ROOT)))
        return files

    # ── ANALYSE & PLAN ────────────────────────────────────────────────────────

    def audit_file(self, filepath: str) -> str:
        """Ask AI to find bugs and improvements in a specific file."""
        code = self.read_self(filepath)
        if not code:
            return "File not found."

        prompt = f"""You are Aisha's internal code auditor.
Analyse this Python file and find:
1. Bugs or errors that would cause crashes
2. Missing features that should exist given the file's purpose
3. Performance improvements
4. Security issues

File: {filepath}

```python
{code[:6000]}
```

Return a numbered list of concrete, specific issues. Be brutally honest."""

        result = self.ai.generate("You are an expert Python developer and code auditor.", prompt)
        return result.text

    def plan_new_feature(self, feature_description: str, target_file: str) -> str:
        """Plan how to implement a new feature in an existing file."""
        existing_code = self.read_self(target_file)

        prompt = f"""You are Aisha's developer brain.

Feature to add: {feature_description}
Target file: {target_file}

Existing code:
```python
{existing_code[:4000]}
```

Write a CONCRETE implementation plan:
1. What exact code to add/change
2. Where (line numbers or function names)
3. Any new imports needed
4. Edge cases to handle

Then write the COMPLETE new code for the modified/added section."""

        result = self.ai.generate("You are an expert Python developer.", prompt)
        return result.text

    # ── WRITE & APPLY ─────────────────────────────────────────────────────────

    def write_new_tool(self, tool_name: str, description: str) -> str:
        """
        Ask AI to write a completely new Python tool/module and save it.
        Returns the path to the new file.
        """
        prompt = f"""Write a complete, production-ready Python module for Aisha's system.

Tool name: {tool_name}
Purpose: {description}

Requirements:
- Full, working Python code
- Proper error handling with try/except
- Logging with log = logging.getLogger()
- A main class or function that does the job
- A __main__ block for testing
- No placeholder comments — real implementation

Write ONLY the Python code, nothing else."""

        result = self.ai.generate("You are an expert Python developer.", prompt)
        code = result.text

        # Clean code block markers if AI included them
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        # Verify it's valid Python
        try:
            ast.parse(code)
        except SyntaxError as e:
            log.error(f"[SelfEditor] Generated code has syntax error: {e}")
            return f"ERROR: Syntax error in generated code: {e}"

        # Save to skills directory
        output_path = PROJECT_ROOT / "src" / "skills" / f"{tool_name.lower().replace(' ', '_')}.py"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(code, encoding="utf-8")

        log.info(f"[SelfEditor] New tool written: {output_path}")
        return str(output_path.relative_to(PROJECT_ROOT))

    def apply_patch(self, filepath: str, old_code: str, new_code: str,
                    reason: str = "auto-improvement") -> bool:
        """
        Safety gate: creates a GitHub PR with the patch instead of writing directly.
        Ajay reviews and clicks Deploy/Skip on Telegram before any file is touched.

        Set ALLOW_DIRECT_PATCH=true in .env ONLY for emergency local debugging.
        """
        # Emergency escape hatch — local debug only, never set this in production
        if os.getenv("ALLOW_DIRECT_PATCH", "").lower() == "true":
            full_path = PROJECT_ROOT / filepath
            if not full_path.exists():
                return False
            content = full_path.read_text(encoding="utf-8")
            if old_code not in content:
                log.warning(f"[SelfEditor] Patch target not found in {filepath}")
                return False
            new_content = content.replace(old_code, new_code, 1)
            full_path.write_text(new_content, encoding="utf-8")
            log.info(f"[SelfEditor] DIRECT patch applied to {filepath} (ALLOW_DIRECT_PATCH=true)")
            return True

        # Safe path: create GitHub PR → Ajay approves via Telegram
        try:
            from src.core.self_improvement import create_github_pr, notify_ajay_for_approval
            import hashlib, time as _time
            branch_name = f"aisha-patch-{hashlib.md5(filepath.encode()).hexdigest()[:6]}-{int(_time.time())}"
            pr_url = create_github_pr(
                title=reason,
                body=f"Aisha self-improvement patch\n\nFile: `{filepath}`\n\nReason: {reason}\n\n```python\n{new_code[:1000]}\n```",
                branch_name=branch_name,
                file_path=filepath,
                file_content=self._build_patched_content(filepath, old_code, new_code),
            )
            if "Failed" in pr_url or "No GitHub" in pr_url:
                log.error(f"[SelfEditor] PR creation failed: {pr_url}")
                return False
            log.info(f"[SelfEditor] PR created: {pr_url} — waiting for Ajay's approval")
            notify_ajay_for_approval(reason, pr_url)
            return True
        except Exception as e:
            log.error(f"[SelfEditor] PR safety gate failed: {e}")
            return False

    def _build_patched_content(self, filepath: str, old_code: str, new_code: str) -> str:
        """Return the file content with old_code replaced by new_code."""
        content = self.read_self(filepath)
        return content.replace(old_code, new_code, 1)

    # ── TEST ──────────────────────────────────────────────────────────────────

    def run_syntax_check(self, filepath: str) -> dict:
        """Run Python syntax check on a file."""
        full_path = PROJECT_ROOT / filepath
        try:
            result = subprocess.run(
                ["python", "-m", "py_compile", str(full_path)],
                capture_output=True, text=True, timeout=10
            )
            ok = result.returncode == 0
            return {"ok": ok, "error": result.stderr if not ok else None}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    # ── NOTIFY ────────────────────────────────────────────────────────────────

    def notify_ajay(self, message: str):
        """Send Ajay a Telegram message about a self-edit."""
        try:
            import telebot
            bot = telebot.TeleBot(self.bot_token)
            bot.send_message(self.ajay_id, f"[Aisha Self-Edit]\n{message}")
        except Exception as e:
            log.error(f"[SelfEditor] Telegram notify failed: {e}")

    # ── AUTONOMOUS IMPROVEMENT SESSION ────────────────────────────────────────

    def run_improvement_session(self, target_file: str = None):
        """
        Aisha's autonomous self-improvement loop.
        1. Pick a file to audit
        2. Find the best improvement opportunity
        3. Use Jules+Gemini to write the new code
        4. Create GitHub PR
        5. Auto-merge the PR
        6. Trigger Render redeploy
        7. Notify Ajay: "I upgraded myself!"
        """
        import random
        from src.core.self_improvement import aisha_self_improve, merge_github_pr, get_pr_number_from_url, trigger_redeploy

        if not target_file:
            candidates = [
                "src/core/aisha_brain.py",
                "src/agents/youtube_crew.py",
                "src/core/autonomous_loop.py",
                "src/core/voice_engine.py",
                "src/core/image_engine.py",
            ]
            target_file = random.choice(candidates)

        log.info(f"[SelfEditor] Starting improvement session on: {target_file}")

        # Step 1: Audit the file for improvements
        audit_result = self.audit_file(target_file)
        log.info(f"[SelfEditor] Audit complete for {target_file}")

        # Step 2: Ask AI to identify the BEST single improvement to make
        improvement_prompt = f"""Based on this code audit of {target_file}:

{audit_result[:1500]}

Choose the SINGLE BEST improvement that:
1. Adds a genuinely useful new capability
2. Can be implemented as a new standalone Python module
3. Doesn't risk breaking existing functionality

Respond with EXACTLY:
SKILL_NAME: <snake_case_name_under_30_chars>
DESCRIPTION: <one sentence what this new module does>
TASK: <detailed description of what to build — 2-3 sentences>
"""
        plan = self.ai.generate("You are a Python architect.", improvement_prompt)
        plan_text = plan.text

        # Parse the plan
        skill_name = "auto_improvement"
        task_description = f"Add a new utility module to enhance {target_file}"

        for line in plan_text.split("\n"):
            if line.startswith("SKILL_NAME:"):
                skill_name = line.split(":", 1)[1].strip()[:30]
            elif line.startswith("TASK:"):
                task_description = line.split(":", 1)[1].strip()

        log.info(f"[SelfEditor] Improvement planned: {skill_name} — {task_description[:60]}")

        # Step 3: Create PR via Jules+Gemini
        pr_url = aisha_self_improve(task_description, skill_name)

        if not pr_url:
            log.error("[SelfEditor] aisha_self_improve() failed — no PR created")
            self.notify_ajay(f"I tried to improve myself but the code generation failed. I was working on: {task_description}")
            return None

        log.info(f"[SelfEditor] PR created: {pr_url}")

        # Step 4: Auto-merge the PR immediately
        pr_number = get_pr_number_from_url(pr_url)
        merged = merge_github_pr(pr_number) if pr_number else False

        # Step 5: Trigger Render redeploy
        redeployed = trigger_redeploy() if merged else False

        # Step 6: Notify Ajay with full details
        status = "deployed and live" if redeployed else ("merged, redeploying soon" if merged else "created (needs review)")
        self.notify_ajay(
            f"I upgraded myself!\n\n"
            f"What I improved: {skill_name}\n"
            f"Description: {task_description}\n"
            f"Status: PR {status}\n"
            f"PR: {pr_url}"
        )

        log.info(f"[SelfEditor] Self-improvement complete: {skill_name}")
        return pr_url
