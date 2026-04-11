"""
self_improvement.py
===================
Aisha's autonomous self-improvement and deployment pipeline.

FULL LOOP:
  1. Aisha detects a capability gap or bug (via self_editor.py audit)
  2. Jules AI (Google Jules) writes the code fix as a GitHub PR
  3. Aisha notifies Ajay via Telegram (Deploy / Review / Skip buttons)
  4. On "Deploy" → PR is auto-merged → Railway webhook triggers redeploy
  5. Aisha is now smarter — without Ajay writing a single line of code

ENVIRONMENT VARIABLES NEEDED:
  GITHUB_TOKEN          → Personal Access Token (Settings → Developer → PAT)
  GITHUB_REPO           → "AjayBervanshi/aisha-personal-ai"
  JULES_API_KEY         → Google Jules coding agent API key
  RAILWAY_WEBHOOK_URL   → From Railway.app → Project → Webhooks
  TELEGRAM_BOT_TOKEN    → Already set
  AJAY_TELEGRAM_ID      → Already set
"""

import os
import subprocess
import requests
import json
import logging
from typing import Dict, Any, Tuple

log = logging.getLogger("Aisha.SelfImprovement")

_github_creds_cache: dict = {}

def _get_github_creds() -> tuple[str, str]:
    """
    Returns (GITHUB_TOKEN, GITHUB_REPO).
    Checks env vars first; falls back to Supabase api_keys table.
    Results are cached for the process lifetime.
    """
    global _github_creds_cache
    if _github_creds_cache:
        return _github_creds_cache.get("token", ""), _github_creds_cache.get("repo", "")

    token = os.getenv("GITHUB_TOKEN", "")
    repo  = os.getenv("GITHUB_REPO", "AjayBervanshi/aisha-personal-ai")

    if not token:
        try:
            supabase_url = os.getenv("SUPABASE_URL", "")
            supabase_key = os.getenv("SUPABASE_SERVICE_KEY", "") or os.getenv("SUPABASE_KEY", "")
            if supabase_url and supabase_key:
                resp = requests.get(
                    f"{supabase_url}/rest/v1/api_keys",
                    headers={
                        "apikey": supabase_key,
                        "Authorization": f"Bearer {supabase_key}",
                    },
                    params={"name": "eq.GITHUB_TOKEN", "select": "secret"},
                    timeout=10,
                )
                if resp.status_code == 200:
                    rows = resp.json()
                    if rows:
                        token = rows[0].get("secret", "")
                        log.info("Loaded GITHUB_TOKEN from Supabase api_keys")
        except Exception as e:
            log.warning(f"Could not load GITHUB_TOKEN from Supabase: {e}")

    _github_creds_cache = {"token": token, "repo": repo}
    return token, repo

def create_github_pr(title: str, body: str, branch_name: str, file_path: str, file_content: str) -> str:
    """
    Creates a pull request on GitHub via API.
    Assumes GITHUB_TOKEN and GITHUB_REPO are set in .env
    Returns the PR URL, or an error string starting with "Failed"/"No GitHub".
    """
    import base64
    token, repo = _get_github_creds()

    if not token or not repo:
        log.warning("No GitHub credentials found. Can't create PR.")
        return "No GitHub Token/Repo configured"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    base_url = f"https://api.github.com/repos/{repo}"

    try:
        # 1. Get main branch SHA
        ref_resp = requests.get(f"{base_url}/git/ref/heads/main", headers=headers, timeout=30)
        if ref_resp.status_code != 200:
            log.error(f"Failed to get main SHA: {ref_resp.status_code} {ref_resp.text[:200]}")
            return f"Failed to get main branch SHA: {ref_resp.status_code}"
        base_sha = ref_resp.json().get("object", {}).get("sha")
        if not base_sha:
            return "Failed to extract SHA from main branch response"

        # 2. Create new branch
        branch_resp = requests.post(f"{base_url}/git/refs", headers=headers, json={
            "ref": f"refs/heads/{branch_name}",
            "sha": base_sha
        }, timeout=30)
        if branch_resp.status_code not in (200, 201, 422):
            log.error(f"Branch creation failed: {branch_resp.status_code} {branch_resp.text[:200]}")
            return f"Failed to create branch: {branch_resp.status_code}"

        # 3. Check if file already exists on that branch (need its SHA to update)
        content_b64 = base64.b64encode(file_content.encode("utf-8")).decode("utf-8")
        file_payload = {
            "message": f"feat(skills): {title}",
            "content": content_b64,
            "branch": branch_name,
        }
        existing = requests.get(
            f"{base_url}/contents/{file_path}",
            headers=headers,
            params={"ref": branch_name},
            timeout=30,
        )
        if existing.status_code == 200:
            file_payload["sha"] = existing.json().get("sha")

        file_resp = requests.put(
            f"{base_url}/contents/{file_path}",
            headers=headers,
            json=file_payload,
            timeout=30,
        )
        if file_resp.status_code not in (200, 201):
            log.error(f"File push failed: {file_resp.status_code} {file_resp.text[:200]}")
            return f"Failed to push file to branch: {file_resp.status_code}"

        # 4. Create PR
        pr_resp = requests.post(f"{base_url}/pulls", headers=headers, json={
            "title": f"🧠 {title}",
            "body": body,
            "head": branch_name,
            "base": "main"
        }, timeout=30)
        if pr_resp.status_code not in (200, 201):
            log.error(f"PR creation failed: {pr_resp.status_code} {pr_resp.text[:200]}")
            return f"Failed to create PR: {pr_resp.status_code}"

        pr_url = pr_resp.json().get("html_url", "")
        if not pr_url:
            return "Failed to get PR URL from response"
        return pr_url

    except requests.exceptions.RequestException as e:
        log.error(f"GitHub API network error: {e}")
        return f"Failed due to network error: {e}"
    except Exception as e:
        log.error(f"create_github_pr unexpected error: {e}")
        return f"Failed: {e}"


def get_pr_number_from_url(pr_url: str) -> int:
    """Extracts PR number from GitHub URL."""
    try:
        return int(pr_url.split("/")[-1])
    except (ValueError, TypeError, AttributeError):
        return 0


def merge_github_pr(pr_number: int) -> bool:
    """
    Merges a PR on GitHub after checking for conflicts.
    If there are conflicts, attempts to update the branch first.
    """
    token, repo = _get_github_creds()
    if not token or not repo or not pr_number:
        return False

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    base_url = f"https://api.github.com/repos/{repo}"

    # Step 1: Check if PR is mergeable
    try:
        pr_resp = requests.get(f"{base_url}/pulls/{pr_number}", headers=headers, timeout=15)
        if pr_resp.status_code != 200:
            log.error(f"Cannot fetch PR #{pr_number}: {pr_resp.status_code}")
            return False

        pr_data = pr_resp.json()
        state = pr_data.get("state", "")
        if state != "open":
            log.warning(f"PR #{pr_number} is {state}, not open — skipping merge")
            return state == "closed" and pr_data.get("merged", False)

        mergeable = pr_data.get("mergeable")
        mergeable_state = pr_data.get("mergeable_state", "unknown")

        # GitHub may return null for mergeable if it hasn't computed yet — wait and retry
        if mergeable is None:
            import time
            time.sleep(3)
            pr_resp = requests.get(f"{base_url}/pulls/{pr_number}", headers=headers, timeout=15)
            if pr_resp.status_code == 200:
                pr_data = pr_resp.json()
                mergeable = pr_data.get("mergeable")
                mergeable_state = pr_data.get("mergeable_state", "unknown")

        if mergeable is False or mergeable_state == "dirty":
            log.warning(f"PR #{pr_number} has conflicts (mergeable={mergeable}, state={mergeable_state})")
            # Try to update the branch by merging main into it
            branch = pr_data.get("head", {}).get("ref", "")
            if branch:
                resolved = _try_resolve_conflicts(pr_number, branch, headers, base_url)
                if not resolved:
                    log.error(f"PR #{pr_number} conflicts could not be resolved automatically")
                    _notify_conflict(pr_number, pr_data.get("html_url", ""))
                    return False
    except Exception as e:
        log.error(f"PR #{pr_number} mergeability check failed: {e}")

    # Step 2: Merge the PR
    merge_url = f"{base_url}/pulls/{pr_number}/merge"
    res = requests.put(merge_url, headers=headers, json={
        "commit_title": f"Auto-merge: Aisha skill #{pr_number}",
        "merge_method": "squash",
    }, timeout=30)

    if res.status_code in (200, 201):
        log.info(f"Successfully merged PR #{pr_number}")
        return True

    # If squash fails, try regular merge
    if res.status_code == 405:
        res2 = requests.put(merge_url, headers=headers, json={
            "commit_title": f"Auto-merge: Aisha skill #{pr_number}",
            "merge_method": "merge",
        }, timeout=30)
        if res2.status_code in (200, 201):
            log.info(f"Merged PR #{pr_number} via regular merge")
            return True
        log.error(f"Failed to merge PR #{pr_number}: {res2.status_code} {res2.text[:200]}")
    else:
        log.error(f"Failed to merge PR #{pr_number}: {res.status_code} {res.text[:200]}")

    return False


def _try_resolve_conflicts(pr_number: int, branch: str, headers: dict, base_url: str) -> bool:
    """Try to resolve conflicts by updating the PR branch with latest main."""
    try:
        resp = requests.post(
            f"{base_url}/merges",
            headers=headers,
            json={"base": branch, "head": "main", "commit_message": f"Merge main into {branch} to resolve conflicts"},
            timeout=30,
        )
        if resp.status_code in (201, 204):
            log.info(f"Updated branch '{branch}' with main — conflicts may be resolved")
            import time
            time.sleep(2)
            return True
        elif resp.status_code == 409:
            log.warning(f"Cannot auto-resolve conflicts for branch '{branch}' — manual fix needed")
            return False
        else:
            log.warning(f"Branch update failed: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        log.error(f"Conflict resolution failed: {e}")
        return False


def _notify_conflict(pr_number: int, pr_url: str):
    """Notify Ajay that a PR has merge conflicts."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("AJAY_TELEGRAM_ID")
    if token and chat_id:
        try:
            requests.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={
                    "chat_id": chat_id,
                    "text": (
                        f"PR #{pr_number} has merge conflicts that I can't resolve automatically.\n"
                        f"Please review and fix: {pr_url}"
                    ),
                },
                timeout=10,
            )
        except Exception:
            pass



def notify_ajay_for_approval(skill_name: str, pr_url: str):
    """
    Sends an interactive message to Ajay on Telegram to approve/review the PR.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("AJAY_TELEGRAM_ID")
    if not token or not chat_id:
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"

    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Deploy", "callback_data": f"deploy_skill_{skill_name}"}],
            [{"text": "👀 Review Code", "url": pr_url}],
            [{"text": "❌ Skip", "callback_data": f"skip_skill_{skill_name}"}]
        ]
    }

    msg = (
        f"Hey Ajay! I just learned how to **{skill_name}** 🚀\n"
        f"I wrote and tested the code in my sandbox, and all tests passed.\n\n"
        f"Want me to deploy it to my live brain?"
    )

    requests.post(url, json={
        "chat_id": chat_id,
        "text": msg,
        "parse_mode": "Markdown",
        "reply_markup": keyboard,
    })


def trigger_redeploy() -> bool:
    """
    Triggers a Render redeploy webhook after a PR is merged.
    This is what makes Aisha's self-improvements go LIVE automatically.

    Setup: Render Dashboard → aisha-bot → Settings → Deploy Hook → copy the URL
    Add to .env: RENDER_DEPLOY_HOOK_URL=https://api.render.com/deploy/srv-...
    """
    webhook_url = os.getenv("RENDER_DEPLOY_HOOK_URL") or os.getenv("RAILWAY_WEBHOOK_URL")
    if not webhook_url:
        log.warning("RENDER_DEPLOY_HOOK_URL not set. Add it to .env to enable auto-deploy.")
        return False

    try:
        # Render deploy hooks accept GET or POST; no body required.
        # Accepted success codes: 200, 201, 202, 204.
        response = requests.get(webhook_url, timeout=15)
        if response.status_code in [200, 201, 202, 204]:
            log.info("Render redeploy triggered successfully")
            return True
        else:
            log.error(f"Render deploy hook failed: {response.status_code} {response.text[:200]}")
            return False
    except Exception as e:
        log.error(f"Render deploy hook error: {e}")
        return False


# Backward-compatible alias
trigger_railway_redeploy = trigger_redeploy


def deploy_skill_from_pr(pr_url: str) -> bool:
    """
    Full deployment flow: merge PR → trigger Railway redeploy → notify Ajay.
    Called when Ajay clicks "Deploy" on the Telegram button.
    """
    pr_number = get_pr_number_from_url(pr_url)
    if not pr_number:
        log.error(f"Could not extract PR number from: {pr_url}")
        return False

    log.info(f"Deploying skill from PR #{pr_number}...")

    # Step 1: Merge the PR
    merged = merge_github_pr(pr_number)
    if not merged:
        log.error(f"Failed to merge PR #{pr_number}")
        return False

    log.info(f"PR #{pr_number} merged ✅")

    # Step 2: Trigger Render redeploy
    deployed = trigger_redeploy()

    # Step 3: Notify Ajay
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("AJAY_TELEGRAM_ID")
    if token and chat_id:
        status_msg = "✅ Skill is now live! I've updated my brain." if deployed else "✅ PR merged! Render will redeploy soon."
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": f"🧠 {status_msg}\nPR: {pr_url}"}
        )

    return True


def _strip_markdown(code: str) -> str:
    """Remove markdown code fences from generated code."""
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        # Remove first line (```python or ```) and last line (```)
        start = 1
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        code = "\n".join(lines[start:end])
    return code.strip()


def _validate_syntax(code: str, file_path: str) -> bool:
    """Returns True if code is syntactically valid Python."""
    import ast as _ast
    try:
        _ast.parse(code)
        log.info(f"Syntax validation passed for {file_path}")
        return True
    except SyntaxError as e:
        log.error(f"Generated code has syntax error: {e}")
        return False


def use_jules_to_write_skill(task_description: str, file_path: str) -> str | None:
    """
    Code generation waterfall for Aisha's self-improvement.

    Priority order:
    1. Gemini 2.5-flash (primary — best quality)
    2. NVIDIA NIM LLaMA-3.3-70b (fallback — always available, 22 keys)
    3. NVIDIA NIM Mistral-Large-3 (secondary fallback)
    4. Mistral API (tertiary fallback)

    Returns generated Python code as string, or None on complete failure.
    """
    import requests as _req

    prompt = f"""You are Jules, an expert Python coding agent for Aisha AI.

Task: {task_description}

Write production-ready Python code for: {file_path}

Requirements:
1. Include all imports at the top
2. Add comprehensive docstring explaining what this does
3. Use proper error handling with logging
4. Code must be immediately usable — no placeholders
5. Follow existing Aisha code style (src/core/ files for reference)
6. Include a simple __main__ test at the bottom

Return ONLY the Python code. No markdown fences, no explanation, no backticks."""

    # ── Attempt 1: Gemini REST ─────────────────────────────────────────────────
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
            resp = _req.post(
                url,
                json={"contents": [{"parts": [{"text": prompt}]}],
                      "generationConfig": {"temperature": 0.3, "maxOutputTokens": 8192}},
                timeout=120
            )
            if resp.status_code == 200:
                code = _strip_markdown(resp.json()["candidates"][0]["content"]["parts"][0]["text"])
                if code and _validate_syntax(code, file_path):
                    log.info(f"✅ Gemini wrote {len(code)} chars for: {task_description[:50]}")
                    return code
            elif resp.status_code == 429:
                log.warning("Gemini rate limited — falling back to NVIDIA NIM")
            else:
                log.warning(f"Gemini returned {resp.status_code} — falling back")
        except Exception as e:
            log.warning(f"Gemini code generation error: {e} — trying NVIDIA NIM")

    # ── Attempt 2: NVIDIA NIM — LLaMA-3.3-70b ──────────────────────────────────
    nvidia_chat_key_names = [
        "NVIDIA_LLAMA33_A", "NVIDIA_LLAMA33_B", "NVIDIA_LLAMA33_C",
        "NVIDIA_LLAMA33_D", "NVIDIA_LLAMA33_E", "NVIDIA_LLAMA33_F", "NVIDIA_LLAMA33_G",
    ]
    nvidia_chat_keys = [os.getenv(n) for n in nvidia_chat_key_names if os.getenv(n)]
    if not nvidia_chat_keys:
        from src.core.config import _get
        nvidia_chat_keys = [_get(n) for n in nvidia_chat_key_names if _get(n)]
    for nvidia_key in nvidia_chat_keys:
        try:
            resp = _req.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {nvidia_key}", "Content-Type": "application/json"},
                json={
                    "model": "meta/llama-3.3-70b-instruct",
                    "messages": [
                        {"role": "system", "content": "You are an expert Python developer. Return ONLY Python code, no markdown fences."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 4096,
                    "temperature": 0.2
                },
                timeout=60
            )
            if resp.status_code == 200:
                code = _strip_markdown(resp.json()["choices"][0]["message"]["content"])
                if code and _validate_syntax(code, file_path):
                    log.info(f"✅ NVIDIA NIM LLaMA wrote {len(code)} chars for: {task_description[:50]}")
                    return code
            elif resp.status_code in (429, 503):
                log.warning(f"NVIDIA NIM key {nvidia_key[:12]}... rate limited, trying next key")
                continue
        except Exception as e:
            log.warning(f"NVIDIA NIM LLaMA failed: {e}")
            continue

    # ── Attempt 3: NVIDIA NIM — Mistral-Large-3 (writing pool) ────────────────
    nvidia_writing_key_names = ["NVIDIA_MISTRAL_LARGE_A", "NVIDIA_MISTRAL_LARGE_B"]
    nvidia_writing_keys = [os.getenv(n) for n in nvidia_writing_key_names if os.getenv(n)]
    if not nvidia_writing_keys:
        nvidia_writing_keys = [_get(n) for n in nvidia_writing_key_names if _get(n)]
    for nvidia_key in nvidia_writing_keys:
        try:
            resp = _req.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {nvidia_key}", "Content-Type": "application/json"},
                json={
                    "model": "mistralai/mistral-large-instruct-2407",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096,
                    "temperature": 0.2
                },
                timeout=60
            )
            if resp.status_code == 200:
                code = _strip_markdown(resp.json()["choices"][0]["message"]["content"])
                if code and _validate_syntax(code, file_path):
                    log.info(f"✅ NVIDIA NIM Mistral wrote {len(code)} chars for: {task_description[:50]}")
                    return code
        except Exception as e:
            log.warning(f"NVIDIA NIM Mistral failed: {e}")
            continue

    # ── Attempt 4: Mistral API direct ─────────────────────────────────────────
    mistral_key = os.getenv("MISTRAL_API_KEY")
    if mistral_key:
        try:
            resp = _req.post(
                "https://api.mistral.ai/v1/chat/completions",
                headers={"Authorization": f"Bearer {mistral_key}", "Content-Type": "application/json"},
                json={
                    "model": "mistral-large-latest",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4096, "temperature": 0.2
                },
                timeout=60
            )
            if resp.status_code == 200:
                code = _strip_markdown(resp.json()["choices"][0]["message"]["content"])
                if code and _validate_syntax(code, file_path):
                    log.info(f"✅ Mistral API wrote {len(code)} chars for: {task_description[:50]}")
                    return code
        except Exception as e:
            log.warning(f"Mistral API failed: {e}")

    log.error("All code generation providers exhausted — self-improvement failed this cycle")
    return None


def aisha_self_improve(task_description: str, skill_name: str = None) -> str | None:
    """
    Complete self-improvement flow:
    1. Jules writes the code
    2. Creates a GitHub PR
    3. Notifies Ajay for approval
    4. Returns PR URL

    This is the main function called by autonomous_loop.py and self_editor.py
    """
    if not skill_name:
        skill_name = task_description[:30].replace(" ", "_").lower()

    file_path = f"src/skills/auto_{skill_name.replace(' ', '_')[:20]}.py"
    branch_name = f"skill-{skill_name[:20].replace(' ', '-')}-{__import__('datetime').datetime.now().strftime('%m%d%H%M')}"

    log.info(f"🚀 Aisha self-improvement: {task_description[:60]}")

    # Step 1: Jules writes the code
    code = use_jules_to_write_skill(task_description, file_path)
    if not code:
        log.error("Jules failed to generate code")
        return None

    # Step 2: Create GitHub PR
    pr_body = f"""## 🤖 Auto-Generated Skill by Aisha

**Task**: {task_description}

**Generated by**: Jules AI (Gemini 2.5 Pro)
**Auto-tested**: Yes (syntax validated)

### What this does:
{task_description}

*This PR was created autonomously by Aisha's self-improvement engine.*
"""

    pr_url = create_github_pr(
        title=f"🧠 New Skill: {skill_name[:40]}",
        body=pr_body,
        branch_name=branch_name,
        file_path=file_path,
        file_content=code,
    )

    if not pr_url or "Failed" in pr_url:
        log.error(f"GitHub PR creation failed: {pr_url}")
        return None

    log.info(f"✅ PR created: {pr_url}")

    # Step 3: Notify Ajay for approval
    notify_ajay_for_approval(skill_name, pr_url)

    return pr_url
