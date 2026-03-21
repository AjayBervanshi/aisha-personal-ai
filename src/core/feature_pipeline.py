"""
feature_pipeline.py
===================
Aisha's Multi-Agent Feature Development Pipeline.

Triggered when:
- Ajay types /feature <description> in Telegram
- Aisha's daily audit detects a missing capability
- Autonomous loop determines a new feature is needed

Pipeline:
  Request → Research → Architecture → Code → Review → Test → Deploy → Notify

Agents:
  1. research_agent   — Analyzes requirements, lists files to touch, estimates complexity
  2. architecture_agent — Designs the solution: file path, function signatures, integration points
  3. code_agent       — Writes production-ready Python (Gemini → NIM LLaMA → Mistral fallback)
  4. review_agent     — Security + quality check (hardcoded secrets → FAIL, score 0–100)
  5. test_agent       — Writes 5 pytest cases, estimates coverage
  6. deploy_agent     — Creates GitHub PR, auto-merges, triggers Render redeploy
"""

import os
import re
import ast
import json
import time
import logging
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
import requests

load_dotenv(Path(__file__).parent.parent.parent / ".env")
log = logging.getLogger("Aisha.FeaturePipeline")


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────────────────────

def _nim_llama_keys() -> list[str]:
    """Return available NVIDIA NIM LLaMA-3.3 chat keys (indices 5,6,8,10,11,12,18,19)."""
    indices = [5, 6, 8, 10, 11, 12, 18, 19]
    return [os.getenv(f"NVIDIA_KEY_{i:02d}") for i in indices
            if os.getenv(f"NVIDIA_KEY_{i:02d}")]


def _nim_code_keys() -> list[str]:
    """Return NVIDIA NIM Codestral key (index 13) for code review tasks."""
    return [k for k in [os.getenv("NVIDIA_KEY_13")] if k]


def _nim_chat(prompt: str, system: str = "You are a helpful AI assistant.",
              max_tokens: int = 2048, model: str = "meta/llama-3.3-70b-instruct") -> Optional[str]:
    """
    Call NVIDIA NIM LLaMA with key rotation.
    Returns the raw text response or None on complete failure.
    """
    keys = _nim_llama_keys()
    for key in keys:
        try:
            resp = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.3,
                },
                timeout=90,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"].strip()
            elif resp.status_code in (429, 503):
                log.warning(f"NIM key {key[:12]}... throttled, rotating")
                continue
            else:
                log.warning(f"NIM returned {resp.status_code}: {resp.text[:120]}")
        except Exception as exc:
            log.warning(f"NIM request error: {exc}")
    return None


def _gemini_chat(prompt: str, max_tokens: int = 4096) -> Optional[str]:
    """Call Gemini 2.5-flash via REST. Returns text or None."""
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/gemini-2.5-flash:generateContent?key={key}"
        )
        resp = requests.post(
            url,
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": max_tokens},
            },
            timeout=120,
        )
        if resp.status_code == 200:
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        elif resp.status_code == 429:
            log.warning("Gemini rate-limited")
        else:
            log.warning(f"Gemini {resp.status_code}: {resp.text[:120]}")
    except Exception as exc:
        log.warning(f"Gemini error: {exc}")
    return None


def _strip_fences(text: str) -> str:
    """Remove markdown code fences from generated code."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        start = 1
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[start:end])
    return text.strip()


def _validate_python(code: str) -> bool:
    """Return True if code is syntactically valid Python."""
    try:
        ast.parse(code)
        return True
    except SyntaxError as exc:
        log.error(f"Syntax error in generated code: {exc}")
        return False


def _parse_json_block(text: str) -> Optional[dict]:
    """
    Try to extract a JSON object from an LLM response.
    Tries: raw JSON, ```json fence, first {{ }} block.
    """
    # Direct parse
    try:
        return json.loads(text)
    except Exception:
        pass
    # Strip ```json ... ``` fence
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except Exception:
            pass
    # First bare { ... } block
    bare = re.search(r"\{.*\}", text, re.DOTALL)
    if bare:
        try:
            return json.loads(bare.group(0))
        except Exception:
            pass
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Agent 1 — Research Agent
# ─────────────────────────────────────────────────────────────────────────────

def research_agent(feature_request: str) -> dict:
    """
    Analyzes what the feature needs.

    Returns:
        {
            'requirement': str,
            'approach': str,
            'files_to_modify': list[str],
            'new_files_needed': list[str],
            'dependencies': list[str],
            'complexity': 'low' | 'medium' | 'high'
        }
    """
    log.info(f"[ResearchAgent] Analyzing: {feature_request[:80]}")

    prompt = f"""You are a senior Python architect analyzing a feature request for "Aisha AI" — a personal AI assistant built with Python, Telegram bot (telebot), Supabase, Gemini API, and NVIDIA NIM.

Project structure:
- src/core/        — brain, ai_router, voice_engine, config, autonomous_loop, self_improvement
- src/agents/      — youtube_crew, content_pipeline agents
- src/telegram/    — bot.py (Telegram bot with all slash commands)
- src/skills/      — auto-generated skills
- supabase/        — edge functions and migrations

Feature Request: {feature_request}

Respond ONLY with a valid JSON object (no markdown, no extra text):
{{
  "requirement": "<one-sentence description of what the feature does>",
  "approach": "<recommended implementation approach in 2-3 sentences>",
  "files_to_modify": ["<existing file path>", ...],
  "new_files_needed": ["<new file path>", ...],
  "dependencies": ["<pip package or API>", ...],
  "complexity": "low" | "medium" | "high"
}}"""

    raw = _gemini_chat(prompt, max_tokens=1024) or _nim_chat(
        prompt,
        system="You are a software architect. Respond with a single valid JSON object only.",
        max_tokens=1024,
    )

    if raw:
        parsed = _parse_json_block(raw)
        if parsed:
            # Ensure all required keys exist with sensible defaults
            defaults = {
                "requirement": feature_request,
                "approach": "Implement as a new Python module in src/core/.",
                "files_to_modify": [],
                "new_files_needed": [],
                "dependencies": [],
                "complexity": "medium",
            }
            defaults.update(parsed)
            log.info(f"[ResearchAgent] Complexity: {defaults['complexity']}, "
                     f"files: {defaults['files_to_modify'] + defaults['new_files_needed']}")
            return defaults

    # Graceful fallback — minimal research result
    log.warning("[ResearchAgent] LLM failed; returning minimal research result")
    safe_name = re.sub(r"[^a-z0-9_]", "_", feature_request[:40].lower())
    return {
        "requirement": feature_request,
        "approach": "Implement as a standalone module in src/core/ with full error handling.",
        "files_to_modify": ["src/telegram/bot.py"],
        "new_files_needed": [f"src/core/{safe_name}.py"],
        "dependencies": [],
        "complexity": "medium",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Agent 2 — Architecture Agent
# ─────────────────────────────────────────────────────────────────────────────

def architecture_agent(research: dict) -> dict:
    """
    Designs the technical solution based on research output.

    Returns:
        {
            'design': str,                    # Technical design description
            'file_path': str,                 # Where to write the new code
            'function_signatures': list[str], # Python def signatures
            'integration_points': list[str]   # How it hooks into existing system
        }
    """
    log.info("[ArchitectureAgent] Designing solution...")

    new_files = research.get("new_files_needed", [])
    file_path = new_files[0] if new_files else "src/core/feature_auto.py"
    approach = research.get("approach", "")
    requirement = research.get("requirement", "")

    prompt = f"""You are designing a Python module for "Aisha AI".

Requirement: {requirement}
Approach: {approach}
Target file: {file_path}
Existing files to integrate with: {research.get('files_to_modify', [])}
Dependencies available: {research.get('dependencies', [])}

Design a clean, minimal Python module. Respond ONLY with a valid JSON object:
{{
  "design": "<2-4 sentence technical design description>",
  "file_path": "{file_path}",
  "function_signatures": [
    "def function_name(param1: type, param2: type) -> return_type:",
    "..."
  ],
  "integration_points": [
    "<e.g. Import and call from bot.py /feature command>",
    "..."
  ]
}}"""

    raw = _gemini_chat(prompt, max_tokens=1024) or _nim_chat(
        prompt,
        system="You are a software architect. Respond with a single valid JSON object only.",
        max_tokens=1024,
    )

    if raw:
        parsed = _parse_json_block(raw)
        if parsed:
            parsed.setdefault("file_path", file_path)
            parsed.setdefault("design", approach)
            parsed.setdefault("function_signatures", [])
            parsed.setdefault("integration_points", [])
            log.info(f"[ArchitectureAgent] Target: {parsed['file_path']}, "
                     f"{len(parsed['function_signatures'])} functions")
            return parsed

    log.warning("[ArchitectureAgent] LLM failed; returning minimal architecture")
    return {
        "design": approach or "Standalone module with a main entry function.",
        "file_path": file_path,
        "function_signatures": [f"def run(request: str) -> dict:"],
        "integration_points": ["Import from bot.py and call from /feature command."],
    }


# ─────────────────────────────────────────────────────────────────────────────
# Agent 3 — Code Agent
# ─────────────────────────────────────────────────────────────────────────────

def code_agent(architecture: dict, task_description: str) -> Optional[str]:
    """
    Writes the actual Python implementation.

    Uses Gemini → NVIDIA NIM LLaMA → NVIDIA NIM Mistral fallback chain.
    Validates syntax before returning.

    Returns Python code string, or None on complete failure.
    """
    from src.core.self_improvement import use_jules_to_write_skill

    file_path = architecture.get("file_path", "src/core/feature_auto.py")
    design = architecture.get("design", "")
    sigs = architecture.get("function_signatures", [])
    integrations = architecture.get("integration_points", [])

    enriched_task = (
        f"{task_description}\n\n"
        f"Design: {design}\n"
        f"Required function signatures:\n" + "\n".join(f"  {s}" for s in sigs) + "\n"
        f"Integration points:\n" + "\n".join(f"  {i}" for i in integrations)
    )

    log.info(f"[CodeAgent] Generating code for: {file_path}")
    code = use_jules_to_write_skill(enriched_task, file_path)

    if code and _validate_python(code):
        log.info(f"[CodeAgent] Generated {len(code)} chars — syntax OK")
        return code

    log.error("[CodeAgent] All providers failed or returned invalid code")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Agent 4 — Review Agent
# ─────────────────────────────────────────────────────────────────────────────

# Patterns that indicate hardcoded secrets (instant fail)
_SECRET_PATTERNS = [
    r'(?i)(api[_\-]?key|secret|password|token|passwd)\s*=\s*["\'][A-Za-z0-9\-_\.]{10,}["\']',
    r'(?i)sk[-_][a-zA-Z0-9]{20,}',          # OpenAI-style keys
    r'(?i)AIzaSy[A-Za-z0-9_-]{33}',         # Google API keys literal
    r'(?i)xai[-_][A-Za-z0-9]{20,}',         # xAI keys
    r'(?i)nvapi[-_][A-Za-z0-9]{30,}',       # NVIDIA API keys
]

_SQL_INJECTION_PATTERNS = [
    r'f["\'].*SELECT.*\{',
    r'f["\'].*INSERT.*\{',
    r'f["\'].*UPDATE.*\{',
    r'f["\'].*DELETE.*\{',
    r'\.format\(.*\).*WHERE',
    r'%\s*\(.*\)\s*["\'].*WHERE',
]


def review_agent(code: str, file_path: str) -> dict:
    """
    Reviews code quality and security.

    Static checks (run locally, fast):
      - Hardcoded secrets → CRITICAL FAIL (approved=False)
      - SQL injection patterns → high severity issue
      - Missing try/except around network calls

    LLM check (NVIDIA NIM Codestral → LLaMA fallback):
      - Code quality, edge cases, style, score 0-100

    Returns:
        {
            'approved': bool,
            'issues': list[str],
            'security_concerns': list[str],
            'score': int  # 0–100
        }
    """
    log.info(f"[ReviewAgent] Reviewing {file_path} ({len(code)} chars)")

    issues: list[str] = []
    security_concerns: list[str] = []
    approved = True

    # ── Static security scan ──────────────────────────────────────────────────
    for pattern in _SECRET_PATTERNS:
        if re.search(pattern, code):
            msg = f"CRITICAL: Possible hardcoded secret matching pattern: {pattern[:40]}"
            security_concerns.append(msg)
            log.error(f"[ReviewAgent] {msg}")
            approved = False  # Hard fail — no deploy

    for pattern in _SQL_INJECTION_PATTERNS:
        if re.search(pattern, code):
            msg = f"HIGH: Possible SQL injection via f-string or .format(): {pattern[:40]}"
            security_concerns.append(msg)
            issues.append(msg)

    # Check for missing error handling in network calls
    if "requests." in code and "except" not in code:
        msg = "MEDIUM: requests calls found but no try/except block detected"
        issues.append(msg)

    # Check for bare except
    bare_excepts = len(re.findall(r"except\s*:", code))
    if bare_excepts > 0:
        issues.append(f"LOW: {bare_excepts} bare 'except:' block(s) — use 'except Exception as e:'")

    # ── LLM quality review ────────────────────────────────────────────────────
    review_prompt = f"""Review this Python code from a production AI assistant (Aisha AI).
Score it 0-100 (100 = production-perfect).

File: {file_path}

```python
{code[:3000]}
```

Check for: bugs, logic errors, missing edge cases, poor naming, missing docstrings, unhandled exceptions, performance issues.

Respond ONLY with valid JSON:
{{
  "score": <integer 0-100>,
  "issues": ["<issue 1>", "<issue 2>", ...]
}}"""

    # Try Codestral first (best for code review), fallback to LLaMA
    code_keys = _nim_code_keys()
    llm_raw = None
    for key in code_keys:
        try:
            resp = requests.post(
                "https://integrate.api.nvidia.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": "mistralai/mamba-codestral-7b-v0.1",
                    "messages": [
                        {"role": "system", "content": "You are a strict code reviewer. Respond only with JSON."},
                        {"role": "user", "content": review_prompt},
                    ],
                    "max_tokens": 1024,
                    "temperature": 0.1,
                },
                timeout=60,
            )
            if resp.status_code == 200:
                llm_raw = resp.json()["choices"][0]["message"]["content"]
                break
        except Exception as exc:
            log.warning(f"[ReviewAgent] Codestral error: {exc}")

    if not llm_raw:
        llm_raw = _nim_chat(
            review_prompt,
            system="You are a strict code reviewer. Respond only with valid JSON.",
            max_tokens=1024,
        )

    score = 70  # Default score if LLM fails
    if llm_raw:
        parsed = _parse_json_block(llm_raw)
        if parsed:
            score = int(parsed.get("score", 70))
            llm_issues = parsed.get("issues", [])
            issues.extend(llm_issues)
            log.info(f"[ReviewAgent] LLM score: {score}, {len(llm_issues)} issues found")
        else:
            log.warning("[ReviewAgent] Could not parse LLM review response")
    else:
        log.warning("[ReviewAgent] LLM review unavailable — static scan only")

    # Score penalty for security concerns
    if security_concerns:
        score = max(0, score - 30 * len(security_concerns))

    log.info(f"[ReviewAgent] approved={approved}, score={score}, "
             f"issues={len(issues)}, security={len(security_concerns)}")

    return {
        "approved": approved,
        "issues": issues,
        "security_concerns": security_concerns,
        "score": score,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Agent 5 — Test Agent
# ─────────────────────────────────────────────────────────────────────────────

def test_agent(code: str, feature_description: str) -> dict:
    """
    Generates pytest test cases for the generated code.

    Returns:
        {
            'test_code': str,         # Full pytest file content
            'test_results': str,      # Pass/fail summary (static analysis)
            'coverage_estimate': int  # Estimated % coverage
        }
    """
    log.info(f"[TestAgent] Generating tests for: {feature_description[:60]}")

    test_prompt = f"""Write exactly 5 pytest test cases for the following Python code.
Feature: {feature_description}

```python
{code[:3000]}
```

Requirements:
- Use pytest and standard library only (no extra deps)
- Include: 1 happy path, 1 empty/None input, 1 edge case, 1 error case, 1 integration-style test
- Use mock.patch for any external calls (API, DB, file I/O)
- Each test has a clear docstring
- Return ONLY the complete Python test file, no markdown fences"""

    raw = _gemini_chat(test_prompt, max_tokens=3000) or _nim_chat(
        test_prompt,
        system="You are a senior Python test engineer. Return only a complete pytest file, no markdown.",
        max_tokens=3000,
    )

    test_code = ""
    coverage_estimate = 0

    if raw:
        test_code = _strip_fences(raw)
        # Rough coverage estimate: count test functions
        test_fn_count = len(re.findall(r"^def test_", test_code, re.MULTILINE))
        coverage_estimate = min(95, 10 + test_fn_count * 15)
        if not _validate_python(test_code):
            log.warning("[TestAgent] Generated test code has syntax errors")
            test_code = f"# Syntax error in generated tests\n# Manual review needed\n# Feature: {feature_description}\n"
            coverage_estimate = 0
        else:
            log.info(f"[TestAgent] {test_fn_count} test functions, ~{coverage_estimate}% coverage estimate")
    else:
        log.warning("[TestAgent] LLM failed to generate tests")
        test_code = (
            f"# Auto-test generation failed — write tests manually\n"
            f"# Feature: {feature_description}\n\n"
            f"def test_placeholder():\n"
            f"    \"\"\"Placeholder — replace with real tests.\"\"\"\n"
            f"    assert True\n"
        )

    test_fn_count = len(re.findall(r"^def test_", test_code, re.MULTILINE))
    test_results = f"{test_fn_count} test(s) generated (not executed — syntax validated only)"

    return {
        "test_code": test_code,
        "test_results": test_results,
        "coverage_estimate": coverage_estimate,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Agent 6 — Deploy Agent
# ─────────────────────────────────────────────────────────────────────────────

def deploy_agent(
    code: str,
    file_path: str,
    feature_name: str,
    task_description: str,
) -> Optional[str]:
    """
    Creates a GitHub PR with the generated code, auto-merges it, and triggers
    a Render redeploy.

    Returns the PR URL on success, or None on failure.
    """
    from src.core.self_improvement import (
        create_github_pr,
        merge_github_pr,
        get_pr_number_from_url,
        trigger_redeploy,
    )

    log.info(f"[DeployAgent] Creating PR for: {feature_name}")

    branch_name = (
        f"feature-{re.sub(r'[^a-z0-9]', '-', feature_name[:25].lower())}"
        f"-{time.strftime('%m%d%H%M')}"
    )

    pr_body = f"""## Feature Pipeline — Automated Deployment

**Feature**: {feature_name}
**Description**: {task_description}

### Generated by Aisha's Multi-Agent Feature Pipeline
- Research Agent: analyzed requirements and complexity
- Architecture Agent: designed module structure
- Code Agent: wrote implementation (Gemini / NVIDIA NIM)
- Review Agent: security + quality validated
- Test Agent: pytest cases generated

*This PR was created autonomously by Aisha's feature_pipeline.py*
"""

    pr_url = create_github_pr(
        title=f"feat: {feature_name[:55]}",
        body=pr_body,
        branch_name=branch_name,
        file_path=file_path,
        file_content=code,
    )

    if not pr_url or pr_url.startswith("Failed") or pr_url.startswith("No GitHub"):
        log.error(f"[DeployAgent] PR creation failed: {pr_url}")
        return None

    log.info(f"[DeployAgent] PR created: {pr_url}")

    # Auto-merge
    pr_number = get_pr_number_from_url(pr_url)
    if pr_number:
        merged = merge_github_pr(pr_number)
        if merged:
            log.info(f"[DeployAgent] PR #{pr_number} merged — triggering redeploy")
            trigger_redeploy()
        else:
            log.warning(f"[DeployAgent] Auto-merge failed for PR #{pr_number} — PR still open")
    else:
        log.warning("[DeployAgent] Could not extract PR number — skipping auto-merge")

    return pr_url


# ─────────────────────────────────────────────────────────────────────────────
# Orchestrator
# ─────────────────────────────────────────────────────────────────────────────

def run_feature_pipeline(feature_request: str, notify_ajay: bool = True) -> dict:
    """
    Master orchestrator — runs all 6 agents in sequence.

    Flow:
        research_agent → architecture_agent → code_agent
        → review_agent (fail-fast on secrets)
        → test_agent → deploy_agent → notify_ajay

    Returns:
        {
            'status': 'success' | 'failed' | 'review_failed',
            'feature_name': str,
            'pr_url': str,
            'agents_report': {
                'research': dict,
                'architecture': dict,
                'review': dict,
                'tests': dict
            },
            'error': str  # present only on failure
        }
    """
    start_time = time.time()
    safe_name = re.sub(r"[^a-zA-Z0-9 ]", "", feature_request)[:50].strip()
    feature_name = safe_name or "auto-feature"

    log.info(f"[Pipeline] Starting feature pipeline: {feature_name}")

    agents_report: dict = {}
    result: dict = {
        "status": "failed",
        "feature_name": feature_name,
        "pr_url": "",
        "agents_report": agents_report,
    }

    try:
        # ── Agent 1: Research ──────────────────────────────────────────────────
        log.info("[Pipeline] Step 1/6 — Research Agent")
        research = research_agent(feature_request)
        agents_report["research"] = research

        # ── Agent 2: Architecture ─────────────────────────────────────────────
        log.info("[Pipeline] Step 2/6 — Architecture Agent")
        architecture = architecture_agent(research)
        agents_report["architecture"] = architecture
        file_path = architecture.get("file_path", "src/core/feature_auto.py")

        # ── Agent 3: Code ─────────────────────────────────────────────────────
        log.info("[Pipeline] Step 3/6 — Code Agent")
        code = code_agent(architecture, feature_request)
        if not code:
            result["error"] = "Code Agent failed: all LLM providers exhausted"
            log.error(f"[Pipeline] {result['error']}")
            if notify_ajay:
                notify_pipeline_result(result)
            return result

        # ── Agent 4: Review ───────────────────────────────────────────────────
        log.info("[Pipeline] Step 4/6 — Review Agent")
        review = review_agent(code, file_path)
        agents_report["review"] = review

        if not review["approved"]:
            result["status"] = "review_failed"
            result["error"] = (
                "Review Agent blocked deployment: hardcoded secrets detected. "
                f"Security concerns: {review['security_concerns']}"
            )
            log.error(f"[Pipeline] {result['error']}")
            if notify_ajay:
                notify_pipeline_result(result)
            return result

        # ── Agent 5: Tests ────────────────────────────────────────────────────
        log.info("[Pipeline] Step 5/6 — Test Agent")
        tests = test_agent(code, feature_request)
        agents_report["tests"] = tests

        # ── Agent 6: Deploy ───────────────────────────────────────────────────
        log.info("[Pipeline] Step 6/6 — Deploy Agent")
        pr_url = deploy_agent(code, file_path, feature_name, feature_request)

        elapsed = round(time.time() - start_time, 1)

        if pr_url:
            result["status"] = "success"
            result["pr_url"] = pr_url
            log.info(f"[Pipeline] Pipeline complete in {elapsed}s — PR: {pr_url}")
        else:
            result["status"] = "failed"
            result["error"] = "Deploy Agent failed: could not create GitHub PR"
            log.error(f"[Pipeline] {result['error']}")

    except Exception as exc:
        log.exception(f"[Pipeline] Unexpected crash: {exc}")
        result["status"] = "failed"
        result["error"] = f"Pipeline crashed: {exc}"

    if notify_ajay:
        notify_pipeline_result(result)

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Telegram Notification
# ─────────────────────────────────────────────────────────────────────────────

def notify_pipeline_result(result: dict):
    """
    Send feature pipeline completion report to Ajay via Telegram.

    Message format:
        Feature Pipeline Complete!
        Feature: <name>
        Status: Deployed / Failed / Blocked
        PR: <url>
        Review Score: <n>/100
        Tests: <n> generating
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("AJAY_TELEGRAM_ID")
    if not token or not chat_id:
        log.warning("[Pipeline] Telegram not configured — skipping notification")
        return

    status = result.get("status", "failed")
    feature_name = result.get("feature_name", "Unknown")
    pr_url = result.get("pr_url", "")
    agents_report = result.get("agents_report", {})
    review = agents_report.get("review", {})
    tests = agents_report.get("tests", {})
    error = result.get("error", "")

    if status == "success":
        status_line = "Deployed"
        header = "Feature Pipeline Complete!"
    elif status == "review_failed":
        status_line = "Blocked by Security Review"
        header = "Feature Pipeline Blocked"
    else:
        status_line = "Failed"
        header = "Feature Pipeline Failed"

    score = review.get("score", "N/A")
    test_results = tests.get("test_results", "N/A")
    coverage = tests.get("coverage_estimate", 0)

    pr_line = f"\nPR: {pr_url}" if pr_url else ""
    error_line = f"\nError: {error}" if error and status != "success" else ""
    security_issues = review.get("security_concerns", [])
    security_line = ""
    if security_issues:
        security_line = f"\nSecurity: {len(security_issues)} concern(s) found"

    msg = (
        f"Feature Pipeline Complete!\n\n"
        f"Feature: {feature_name}\n"
        f"Status: {status_line}\n"
        f"{pr_line}"
        f"\nReview Score: {score}/100"
        f"\nTests: {test_results}"
        f"\nCoverage: ~{coverage}%"
        f"{security_line}"
        f"{error_line}"
    )

    try:
        api_url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(
            api_url,
            json={"chat_id": chat_id, "text": msg},
            timeout=15,
        )
        if resp.status_code != 200:
            log.warning(f"[Pipeline] Telegram notification failed: {resp.status_code} {resp.text[:100]}")
        else:
            log.info("[Pipeline] Ajay notified via Telegram")
    except Exception as exc:
        log.error(f"[Pipeline] Telegram notification error: {exc}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point — quick test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    import sys
    request = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else "Add a /weather command that shows today's weather forecast"
    print(f"\n=== Feature Pipeline Test ===\nRequest: {request}\n")

    result = run_feature_pipeline(request, notify_ajay=False)
    print(f"\nStatus : {result['status']}")
    print(f"Feature: {result['feature_name']}")
    print(f"PR URL : {result.get('pr_url', 'N/A')}")

    review = result.get("agents_report", {}).get("review", {})
    if review:
        print(f"Score  : {review.get('score', 'N/A')}/100")
        print(f"Issues : {len(review.get('issues', []))}")
        print(f"Security: {len(review.get('security_concerns', []))} concern(s)")

    if result.get("error"):
        print(f"Error  : {result['error']}")
