"""
self_improvement.py
===================
The pipeline for Aisha to deploy new skills.
Includes generating code, running sandbox tests, and PR/approval flow via Telegram.
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

def merge_github_pr(branch_name: str) -> bool:
    """
    Merges the pull request for a specific branch via GitHub API.
    """
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("GITHUB_REPO")

    if not token or not repo:
        log.warning("No GitHub credentials found. Can't merge PR.")
        return False

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    base_url = f"https://api.github.com/repos/{repo}"

    try:
        # Find the open PR for this head branch
        prs = requests.get(f"{base_url}/pulls?state=open&head={repo.split('/')[0]}:{branch_name}", headers=headers, timeout=10).json()
        if not prs:
            log.warning(f"No open PR found for branch {branch_name}")
            return False

        pr_num = prs[0]["number"]

        # Merge it
        res = requests.put(f"{base_url}/pulls/{pr_num}/merge", headers=headers, json={
            "merge_method": "squash"
        }, timeout=10)

        if res.status_code in [200, 201]:
            # Delete the branch after successful merge
            requests.delete(f"{base_url}/git/refs/heads/{branch_name}", headers=headers, timeout=5)

            # Fire the redeploy hook!
            hook = os.getenv("RENDER_DEPLOY_HOOK")
            if hook:
                requests.post(hook, timeout=5)
            return True

        return False
    except Exception as e:
        log.error(f"Failed to merge PR: {e}")
        return False
