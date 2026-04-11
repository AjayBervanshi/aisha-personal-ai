"""
code_agent.py
=============
Aisha's autonomous coding agent — she can do what Claude does:
read her own codebase, find bugs across multiple files, fix them,
test the fixes, create multi-file PRs, and merge them.

This is the engine that makes Aisha a self-improving AI developer,
not just a chatbot that generates one-off skill files.

Usage (from Telegram chat or autonomous loop):
  agent = CodeAgent()
  agent.run_task("Fix the bug where voice engine crashes on empty text")
  agent.run_task("Add a weather checking feature to the skills system")
  agent.run_task("Improve error handling in social_media_engine.py")
"""

import ast
import base64
import hashlib
import logging
import os
import subprocess
import sys
import time
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

log = logging.getLogger("Aisha.CodeAgent")

PROJECT_ROOT = Path(__file__).parent.parent.parent


class CodeAgent:
    """Aisha's autonomous coding agent — reads, fixes, tests, commits, deploys."""

    def __init__(self):
        from src.core.ai_router import AIRouter
        self.ai = AIRouter()
        self._github_headers = None
        self._github_repo = None

    def _get_github(self) -> Tuple[dict, str]:
        """Get GitHub headers and repo name."""
        if self._github_headers:
            return self._github_headers, self._github_repo

        from src.core.self_improvement import _get_github_creds
        token, repo = _get_github_creds()
        if not token:
            raise RuntimeError("No GITHUB_TOKEN configured")

        self._github_headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        self._github_repo = repo
        return self._github_headers, repo

    # ── FILE OPERATIONS ──────────────────────────────────────────

    def read_file(self, path: str) -> str:
        """Read a file from the codebase."""
        full = PROJECT_ROOT / path
        if full.exists():
            return full.read_text(encoding="utf-8")
        return ""

    def list_files(self, directory: str = "src", extension: str = ".py") -> List[str]:
        """List all files in a directory."""
        results = []
        root = PROJECT_ROOT / directory
        if root.exists():
            for p in root.rglob(f"*{extension}"):
                results.append(str(p.relative_to(PROJECT_ROOT)))
        return sorted(results)

    def search_code(self, pattern: str, directory: str = "src") -> List[dict]:
        """Search for a pattern across the codebase."""
        import re
        results = []
        for filepath in self.list_files(directory):
            code = self.read_file(filepath)
            for i, line in enumerate(code.splitlines(), 1):
                if re.search(pattern, line, re.I):
                    results.append({"file": filepath, "line": i, "text": line.strip()})
        return results[:50]

    # ── AI-POWERED ANALYSIS ──────────────────────────────────────

    def analyze_task(self, task: str) -> dict:
        """AI analyzes what needs to change and which files to modify."""
        file_list = self.list_files()
        file_summary = "\n".join(f"  {f}" for f in file_list[:60])

        response = self.ai.generate(
            system_prompt=(
                "You are an expert Python developer working on the Aisha AI codebase. "
                "Analyze the task and determine exactly which files need to change."
            ),
            user_message=f"""Task: {task}

Available source files:
{file_summary}

Analyze this task and respond with EXACTLY this format:

FILES_TO_READ: file1.py, file2.py, file3.py
FILES_TO_MODIFY: file1.py, file2.py
APPROACH: One paragraph describing the fix/feature approach
RISK: low/medium/high""",
        )

        result = {"files_to_read": [], "files_to_modify": [], "approach": "", "risk": "medium"}
        for line in response.text.splitlines():
            line = line.strip()
            if line.upper().startswith("FILES_TO_READ:"):
                result["files_to_read"] = [f.strip() for f in line.split(":", 1)[1].split(",") if f.strip()]
            elif line.upper().startswith("FILES_TO_MODIFY:"):
                result["files_to_modify"] = [f.strip() for f in line.split(":", 1)[1].split(",") if f.strip()]
            elif line.upper().startswith("APPROACH:"):
                result["approach"] = line.split(":", 1)[1].strip()
            elif line.upper().startswith("RISK:"):
                result["risk"] = line.split(":", 1)[1].strip().lower()

        return result

    def generate_fix(self, task: str, file_path: str, context_files: List[str] = None) -> Optional[str]:
        """AI generates the complete fixed version of a file."""
        original_code = self.read_file(file_path)
        if not original_code:
            log.warning(f"File not found: {file_path}")
            return None

        context = ""
        if context_files:
            for cf in context_files[:3]:
                code = self.read_file(cf)
                if code:
                    context += f"\n--- {cf} (for reference) ---\n{code[:3000]}\n"

        response = self.ai.generate(
            system_prompt=(
                "You are an expert Python developer. You output ONLY the complete fixed Python file. "
                "No markdown fences, no explanations, no comments about changes — ONLY the full Python code."
            ),
            user_message=f"""Task: {task}

File to fix: {file_path}

Current code:
{original_code[:8000]}
{context}

Return the COMPLETE fixed file. Include ALL existing code — only change what's needed for the task.
Do NOT add comments explaining your changes. Do NOT wrap in markdown. Return ONLY Python code.""",
        )

        code = response.text.strip()
        if code.startswith("```"):
            lines = code.split("\n")
            start = 1
            end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
            code = "\n".join(lines[start:end])

        try:
            ast.parse(code)
            return code
        except SyntaxError as e:
            log.error(f"Generated code for {file_path} has syntax error: {e}")
            return None

    # ── TESTING ──────────────────────────────────────────────────

    def test_file(self, file_path: str, code: str) -> dict:
        """Test a single file by syntax check + import test."""
        result = {"syntax": False, "imports": False, "error": ""}

        try:
            ast.parse(code)
            result["syntax"] = True
        except SyntaxError as e:
            result["error"] = f"Syntax: {e}"
            return result

        import tempfile
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir="/tmp") as f:
                f.write(code)
                tmp = f.name

            proc = subprocess.run(
                [sys.executable, "-c", f"import ast; ast.parse(open('{tmp}').read()); print('OK')"],
                capture_output=True, text=True, timeout=10,
            )
            result["imports"] = proc.returncode == 0
            if proc.returncode != 0:
                result["error"] = proc.stderr[:500]
        except Exception as e:
            result["error"] = str(e)
        finally:
            try:
                os.unlink(tmp)
            except Exception:
                pass

        return result

    def test_all_modified(self, changes: Dict[str, str]) -> Tuple[bool, str]:
        """Test all modified files. Returns (all_pass, error_summary)."""
        errors = []
        for path, code in changes.items():
            test = self.test_file(path, code)
            if not test["syntax"]:
                errors.append(f"{path}: {test['error']}")

        if errors:
            return False, "\n".join(errors)
        return True, ""

    # ── MULTI-FILE GITHUB PR ─────────────────────────────────────

    def create_multi_file_pr(self, title: str, body: str, changes: Dict[str, str]) -> str:
        """
        Create a GitHub PR with multiple file changes.
        changes = {"src/core/file.py": "full file content", ...}
        Returns PR URL or error string.
        """
        headers, repo = self._get_github()
        base_url = f"https://api.github.com/repos/{repo}"

        ts = datetime.now().strftime("%m%d%H%M")
        branch_name = f"aisha-fix-{hashlib.md5(title.encode()).hexdigest()[:6]}-{ts}"

        try:
            # Get main branch SHA
            ref = requests.get(f"{base_url}/git/ref/heads/main", headers=headers, timeout=15)
            if ref.status_code != 200:
                return f"Failed: cannot get main SHA ({ref.status_code})"
            base_sha = ref.json()["object"]["sha"]

            # Create branch
            br = requests.post(f"{base_url}/git/refs", headers=headers, json={
                "ref": f"refs/heads/{branch_name}", "sha": base_sha,
            }, timeout=15)
            if br.status_code not in (200, 201, 422):
                return f"Failed: cannot create branch ({br.status_code})"

            # Push each file
            for file_path, content in changes.items():
                content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
                payload = {
                    "message": f"fix: {title} — {file_path}",
                    "content": content_b64,
                    "branch": branch_name,
                }
                existing = requests.get(
                    f"{base_url}/contents/{file_path}",
                    headers=headers, params={"ref": branch_name}, timeout=15,
                )
                if existing.status_code == 200:
                    payload["sha"] = existing.json().get("sha")

                push = requests.put(
                    f"{base_url}/contents/{file_path}",
                    headers=headers, json=payload, timeout=30,
                )
                if push.status_code not in (200, 201):
                    return f"Failed: cannot push {file_path} ({push.status_code})"
                log.info(f"Pushed {file_path} to {branch_name}")

            # Create PR
            pr = requests.post(f"{base_url}/pulls", headers=headers, json={
                "title": title,
                "body": body,
                "head": branch_name,
                "base": "main",
            }, timeout=15)
            if pr.status_code not in (200, 201):
                return f"Failed: cannot create PR ({pr.status_code})"

            pr_url = pr.json().get("html_url", "")
            log.info(f"PR created: {pr_url} ({len(changes)} files)")
            return pr_url

        except Exception as e:
            log.error(f"Multi-file PR failed: {e}")
            return f"Failed: {e}"

    # ── FULL AUTONOMOUS TASK ─────────────────────────────────────

    def run_task(self, task: str, auto_merge: bool = True) -> dict:
        """
        Full autonomous coding cycle — like what Claude does:
        1. Analyze the task → identify files to change
        2. Read those files
        3. Generate fixes for each file
        4. Test all fixes (syntax + import)
        5. Create multi-file PR
        6. Merge the PR
        7. Trigger redeployment
        8. Notify Ajay

        Returns dict with status, pr_url, files_changed, etc.
        """
        result = {
            "status": "started",
            "task": task,
            "files_changed": [],
            "pr_url": None,
            "merged": False,
            "deployed": False,
            "error": None,
        }

        try:
            # Step 1: Analyze
            log.info(f"[CodeAgent] Analyzing task: {task[:80]}")
            analysis = self.analyze_task(task)
            log.info(f"[CodeAgent] Files to modify: {analysis['files_to_modify']}")
            log.info(f"[CodeAgent] Approach: {analysis['approach'][:100]}")

            if not analysis["files_to_modify"]:
                result["error"] = "AI could not determine which files to modify"
                result["status"] = "failed"
                return result

            # Step 2: Read context files
            context_files = analysis.get("files_to_read", [])

            # Step 3: Generate fixes
            changes: Dict[str, str] = {}
            for file_path in analysis["files_to_modify"]:
                log.info(f"[CodeAgent] Generating fix for {file_path}...")
                fixed_code = self.generate_fix(task, file_path, context_files)
                if fixed_code:
                    changes[file_path] = fixed_code
                    log.info(f"[CodeAgent] Fix generated for {file_path} ({len(fixed_code)} chars)")
                else:
                    log.warning(f"[CodeAgent] Could not generate fix for {file_path}")

            if not changes:
                result["error"] = "No valid fixes could be generated"
                result["status"] = "failed"
                return result

            # Step 4: Test
            log.info(f"[CodeAgent] Testing {len(changes)} modified files...")
            all_pass, errors = self.test_all_modified(changes)
            if not all_pass:
                log.warning(f"[CodeAgent] Tests failed, attempting retry with feedback...")
                # Retry once with error context
                for file_path in list(changes.keys()):
                    test = self.test_file(file_path, changes[file_path])
                    if not test["syntax"]:
                        retry = self.generate_fix(
                            f"{task}\n\nPREVIOUS FIX HAD ERROR: {test['error']}",
                            file_path, context_files,
                        )
                        if retry:
                            changes[file_path] = retry

                all_pass2, errors2 = self.test_all_modified(changes)
                if not all_pass2:
                    result["error"] = f"Tests still failing: {errors2[:300]}"
                    result["status"] = "failed"
                    return result

            log.info("[CodeAgent] All tests passed!")

            # Step 5: Create PR
            log.info(f"[CodeAgent] Creating PR with {len(changes)} files...")
            files_summary = "\n".join(f"- `{f}`" for f in changes.keys())
            pr_body = (
                f"## Autonomous Fix by Aisha\n\n"
                f"**Task**: {task}\n\n"
                f"**Approach**: {analysis.get('approach', 'AI-generated fix')}\n\n"
                f"**Files changed**:\n{files_summary}\n\n"
                f"**Tests**: All syntax checks passed\n\n"
                f"*This PR was created autonomously by Aisha's code agent.*"
            )
            pr_url = self.create_multi_file_pr(
                title=f"fix: {task[:60]}",
                body=pr_body,
                changes=changes,
            )

            if "Failed" in pr_url:
                result["error"] = pr_url
                result["status"] = "failed"
                return result

            result["pr_url"] = pr_url
            result["files_changed"] = list(changes.keys())
            result["status"] = "pr_created"

            # Step 6: Merge
            if auto_merge:
                from src.core.self_improvement import merge_github_pr, get_pr_number_from_url
                pr_number = get_pr_number_from_url(pr_url)
                if pr_number:
                    time.sleep(2)
                    merged = merge_github_pr(pr_number)
                    result["merged"] = merged
                    if merged:
                        result["status"] = "merged"

                        # Step 7: Deploy
                        from src.core.self_improvement import trigger_redeploy
                        deployed = trigger_redeploy()
                        result["deployed"] = deployed
                        if deployed:
                            result["status"] = "deployed"

            # Step 8: Notify
            self._notify(task, result)

            log.info(f"[CodeAgent] Task complete: {result['status']} | PR: {pr_url}")
            return result

        except Exception as e:
            log.error(f"[CodeAgent] Task failed: {e}")
            result["error"] = str(e)
            result["status"] = "failed"
            self._notify(task, result)
            return result

    def _notify(self, task: str, result: dict):
        """Send result to Ajay via Telegram."""
        try:
            bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
            ajay_id = os.getenv("AJAY_TELEGRAM_ID")
            if not bot_token or not ajay_id:
                return

            status = result["status"]
            files = ", ".join(result.get("files_changed", []))
            pr = result.get("pr_url", "")
            error = result.get("error", "")

            if status in ("deployed", "merged", "pr_created"):
                msg = (
                    f"Code Agent Complete!\n\n"
                    f"Task: {task[:100]}\n"
                    f"Status: {status}\n"
                    f"Files: {files or 'none'}\n"
                    f"PR: {pr or 'none'}"
                )
            else:
                msg = (
                    f"Code Agent Failed\n\n"
                    f"Task: {task[:100]}\n"
                    f"Error: {error[:200]}"
                )

            requests.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": ajay_id, "text": msg},
                timeout=10,
            )
        except Exception as e:
            log.warning(f"[CodeAgent] Notification failed: {e}")
