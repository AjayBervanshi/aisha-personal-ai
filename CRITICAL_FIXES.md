# 🚨 AISHA — CRITICAL FIXES (P0/P1)

This document contains only the highest priority security holes, data corruption risks, and breaking architecture flaws that require immediate remediation.

### 1. SSRF in `action.http_request` (Security Hole)
**Issue:** `workflow_engine.py` directly executes `urllib.request.urlopen` with user/LLM-provided URLs.
**Fix required:** Implement a safe URL wrapper that parses the URL, enforces `https://`, resolves the hostname to ensure it does not map to private IP space (`10.0.0.0/8`, `127.0.0.0/8`, `169.254.169.254`), and disables automatic arbitrary redirects.

### 2. Privacy Leakage of Desktop Screens (Security Hole)
**Issue:** `goal_engine.py` extracts `screen_text` from the awareness logs and feeds it directly into external LLMs.
**Fix required:** Sanitize the text locally (e.g., stripping identifiable numbers, emails, or high-entropy strings) OR switch to an explicitly local, private model (Ollama) exclusively for this evaluation step.

### 3. Infinite Workflow Self-Healing (Architecture Flaw)
**Issue:** Workflow nodes that fail are instantly passed to an LLM to be "fixed" and retried, forever.
**Fix required:** Add a `retry_count` boundary to the `self_healing` loop. Max 1 or 2 retries per node, after which the workflow transitions to a hard `failed` state.

### 4. OOM Memory Exhaustion via `_oauth_states` (Architecture Flaw)
**Issue:** Unbounded dictionary storing OAuth CSRF states in `bot.py`.
**Fix required:** Remove `_oauth_states` completely. Use Supabase to store CSRF states with a TTL, or use signed JWTs as the `state` parameter to make the OAuth flow entirely stateless.
