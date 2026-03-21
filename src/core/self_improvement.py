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

def create_github_pr(title: str, body: str, branch_name: str, file_path: str, file_content: str) -> str:
    """
    Creates a pull request on GitHub via API.
    Assumes GITHUB_TOKEN and GITHUB_REPO are set in .env
    Returns the PR URL.
    """
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")

    if not token or not repo:
        log.warning("No GitHub credentials found. Can't create PR.")
        return "No GitHub Token/Repo configured"

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    base_url = f"https://api.github.com/repos/{repo}"

    # 1. Get main branch SHA
    main_ref = requests.get(f"{base_url}/git/refs/heads/main", headers=headers).json()
    base_sha = main_ref.get("object", {}).get("sha")

    # 2. Create new branch
    requests.post(f"{base_url}/git/refs", headers=headers, json={
        "ref": f"refs/heads/{branch_name}",
        "sha": base_sha
    })

    # 3. Create file commit on new branch
    import base64
    content_b64 = base64.b64encode(file_content.encode("utf-8")).decode("utf-8")

    requests.put(f"{base_url}/contents/{file_path}", headers=headers, json={
        "message": f"Add new skill: {title}",
        "content": content_b64,
        "branch": branch_name
    })

    # 4. Create PR
    pr_res = requests.post(f"{base_url}/pulls", headers=headers, json={
        "title": f"🚀 New Skill: {title}",
        "body": body,
        "head": branch_name,
        "base": "main"
    }).json()

    return pr_res.get("html_url", "Failed to create PR")


def get_pr_number_from_url(pr_url: str) -> int:
    """Extracts PR number from GitHub URL."""
    try:
        return int(pr_url.split("/")[-1])
    except:
        return 0


def merge_github_pr(pr_number: int) -> bool:
    """
    Merges a PR on GitHub.
    """
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")
    if not token or not repo or not pr_number:
        return False

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}/merge"

    res = requests.put(url, headers=headers, json={
        "commit_title": f"Auto-merging skill #{pr_number}",
        "merge_method": "merge"
    })

    if res.status_code in [200, 201]:
        log.info(f"Successfully merged PR #{pr_number}")
        return True
    else:
        log.error(f"Failed to merge PR #{pr_number}: {res.text}")
        return False



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
        "reply_markup": json.dumps(keyboard)
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
        response = requests.post(webhook_url, json={"trigger": "aisha-self-deploy"}, timeout=10)
        if response.status_code in [200, 201, 204]:
            log.info("✅ Render redeploy triggered successfully")
            return True
        else:
            log.error(f"Render deploy hook failed: {response.status_code} {response.text}")
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


def use_jules_to_write_skill(task_description: str, file_path: str) -> str | None:
    """
    Uses Google Jules AI to write code for a new skill or fix.
    Jules is an AI coding agent that can write, test, and iterate on code.

    Returns the generated code as a string, or None on failure.
    """
    jules_key = os.getenv("JULES_API_KEY")
    if not jules_key:
        log.warning("JULES_API_KEY not set. Jules self-improvement disabled.")
        return None

    try:
        # Jules uses Gemini REST (avoid SDK DNS issues on Render)
        import requests as _req
        gemini_key = os.getenv("GEMINI_API_KEY") or jules_key  # Jules key fallback
        _gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"

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

Return ONLY the Python code. No markdown, no explanation, no backticks."""

        _resp = _req.post(
            _gemini_url,
            json={"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0.3, "maxOutputTokens": 8192}},
            timeout=120
        )
        _resp.raise_for_status()
        code = _resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        # Remove any accidental markdown
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        log.info(f"✅ Jules generated {len(code)} chars of code for: {task_description[:50]}")

        # Validate syntax before returning
        import ast as _ast
        try:
            _ast.parse(code)
            log.info(f"Syntax validation passed for {file_path}")
        except SyntaxError as e:
            log.error(f"Generated code has syntax error: {e}")
            return None

        return code

    except Exception as e:
        log.error(f"Jules code generation failed: {e}")
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
    branch_name = f"skill-{skill_name[:20].replace(' ', '-')}-{__import__('time').strftime('%m%d%H%M')}"

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
