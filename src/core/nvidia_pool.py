"""
nvidia_pool.py
==============
NVIDIA NIM Pool Orchestrator — 22 keys × 1,000 credits/month = 22,000 total credits.

╔══════════════════════════════════════════════════════════════════════════════╗
║  KEY MAP — Descriptive env var → Model → Purpose                            ║
╠══════════════════════════════════════════════════════════════════════════════╣
║  NVIDIA_QWEN_122B          qwen/qwen3.5-122b-a10b                           ║
║  → Massive 122B MoE model. Best for long-form content, reasoning            ║
║                                                                              ║
║  NVIDIA_MISTRAL_LARGE_A    mistralai/mistral-large-3-675b                   ║
║  → 675B param writing giant. Best for Hindi stories, scripts                ║
║                                                                              ║
║  NVIDIA_GEMMA3_27B         google/gemma-3-27b-it                            ║
║  → Google's latest 27B. Good for structured tasks, SEO, summaries           ║
║                                                                              ║
║  NVIDIA_PHI4_VISION        microsoft/phi-4-multimodal-instruct              ║
║  → Reads images/screenshots. Use for image analysis, OCR, review            ║
║                                                                              ║
║  NVIDIA_LLAMA33_A          meta/llama-3.3-70b-instruct                      ║
║  NVIDIA_LLAMA33_B          meta/llama-3.3-70b-instruct                      ║
║  NVIDIA_LLAMA33_C          meta/llama-3.3-70b-instruct  (re-enabled 03-26)  ║
║  NVIDIA_LLAMA33_D          meta/llama-3.3-70b-instruct                      ║
║  NVIDIA_LLAMA33_E          meta/llama-3.3-70b-instruct                      ║
║  NVIDIA_LLAMA33_F          meta/llama-3.3-70b-instruct                      ║
║  NVIDIA_LLAMA33_G          meta/llama-3.3-70b-instruct                      ║
║  → 7-key LLaMA-3.3 chat pool. Fast, sharp, great for conversation           ║
║                                                                              ║
║  NVIDIA_LLAMA4_SCOUT       meta/llama-4-scout-17b-16e-instruct              ║
║  → MoE 17B×16E multimodal. Fast vision+text (404 on some regions)           ║
║                                                                              ║
║  NVIDIA_FALCON3_7B         tiiuae/falcon3-7b-instruct                       ║
║  → UAE's 7B model. Lightweight chat, casual responses                       ║
║                                                                              ║
║  NVIDIA_USDCODE            nvidia/usdcode-llama-3.1-70b-instruct            ║
║  → Specialised 3D/USD scene code generation (404 on some regions)           ║
║                                                                              ║
║  NVIDIA_PHI35_MINI         microsoft/phi-3.5-mini-instruct                  ║
║  → Small but capable. Good for classification, quick responses              ║
║                                                                              ║
║  NVIDIA_GEMMA2_2B          google/gemma-2-2b-it                             ║
║  → Tiny 2B model. Fastest possible response, minimal credits                ║
║                                                                              ║
║  NVIDIA_CHATGLM3           thudm/chatglm3-6b                                ║
║  → Chinese/English bilingual 6B. Good for quick tasks                       ║
║                                                                              ║
║  NVIDIA_CODESTRAL          mistralai/mamba-codestral-7b-v0.1                ║
║  → Mistral's code model. Python, JS, SQL generation & review                ║
║                                                                              ║
║  NVIDIA_PHI3_128K          microsoft/phi-3-medium-128k-instruct             ║
║  → 128K context window. Best for reading long docs, full scripts            ║
║                                                                              ║
║  NVIDIA_GEMMA2_27B         google/gemma-2-27b-it                            ║
║  → Google 27B. Strong reasoning, good fallback for writing                  ║
║                                                                              ║
║  NVIDIA_PHI3_SMALL         microsoft/phi-3-small-8k-instruct                ║
║  → Compact & fast. Good for SEO tags, metadata, short tasks                 ║
║                                                                              ║
║  NVIDIA_MISTRAL_LARGE_B    mistralai/mistral-large-3-675b                   ║
║  → Same giant writer, second key. Full backup for story writing             ║
╚══════════════════════════════════════════════════════════════════════════════╝

Task -> Pool routing:
  "writing" -> NVIDIA_MISTRAL_LARGE_A/B (Mistral-Large-3, best for Hindi stories/scripts)
  "chat"    -> NVIDIA_LLAMA33_A..G + NVIDIA_FALCON3_7B (fast conversation, 8 keys)
  "code"    -> NVIDIA_CODESTRAL, NVIDIA_USDCODE (code generation/review)
  "vision"  -> NVIDIA_PHI4_VISION, NVIDIA_LLAMA4_SCOUT (image analysis, screenshot reading)
  "video"   -> NVIDIA_PHI3_128K (128K context for full video scripts)
  "fast"    -> NVIDIA_GEMMA2_2B, NVIDIA_CHATGLM3, NVIDIA_PHI3_SMALL, NVIDIA_FALCON3_7B
  "general" -> NVIDIA_QWEN_122B, NVIDIA_GEMMA3_27B, NVIDIA_PHI35_MINI, NVIDIA_GEMMA2_27B

Total credits: 22,000/month. Aisha uses credits conservatively:
  - Fast tasks (SEO, metadata) -> fast pool (cheapest)
  - Stories/scripts -> writing pool (quality)
  - Chat -> chat pool (balanced)
"""

import os
import time
import logging
import threading
import requests
from pathlib import Path
from typing import Optional, Dict, List

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent.parent.parent / ".env")
except ImportError:
    pass

log = logging.getLogger("Aisha.NvidiaPool")

# ── Key pool definition ────────────────────────────────────────────────────────
# Format: (env_var_name, model, pool_category)
# Keys with 404 models auto-fail and skip to fallback pool on first use.

_KEY_DEFINITIONS = [
    # env_var,                  model,                                               pool
    ("NVIDIA_QWEN_122B",        "qwen/qwen3.5-122b-a10b",                           "general"), # Massive 122B MoE
    ("NVIDIA_MISTRAL_LARGE_A",  "mistralai/mistral-large-3-675b-instruct-2512",     "writing"), # 675B Writer A
    ("NVIDIA_GEMMA3_27B",       "google/gemma-3-27b-it",                            "general"), # Gemma-3 27B
    ("NVIDIA_PHI4_VISION",      "microsoft/phi-4-multimodal-instruct",              "vision"),  # Vision/OCR
    ("NVIDIA_LLAMA33_A",        "meta/llama-3.3-70b-instruct",                      "chat"),    # Chat A
    ("NVIDIA_LLAMA33_B",        "meta/llama-3.3-70b-instruct",                      "chat"),    # Chat B
    ("NVIDIA_LLAMA4_SCOUT",     "meta/llama-4-scout-17b-16e-instruct",              "vision"),  # Multimodal Scout
    ("NVIDIA_FALCON3_7B",       "tiiuae/falcon3-7b-instruct",                       "fast"),    # Falcon3 Fast
    ("NVIDIA_USDCODE",          "nvidia/usdcode-llama-3.1-70b-instruct",            "code"),    # 3D/USD Code
    ("NVIDIA_PHI35_MINI",       "microsoft/phi-3.5-mini-instruct",                  "general"), # Phi-3.5 Mini
    ("NVIDIA_GEMMA2_2B",        "google/gemma-2-2b-it",                             "fast"),    # Tiny/cheapest
    ("NVIDIA_CHATGLM3",         "thudm/chatglm3-6b",                                "fast"),    # Bilingual 6B
    ("NVIDIA_CODESTRAL",        "mistralai/mamba-codestral-7b-v0.1",                "code"),    # Python/JS/SQL
    ("NVIDIA_PHI3_128K",        "microsoft/phi-3-medium-128k-instruct",             "video"),   # 128K long docs
    ("NVIDIA_GEMMA2_27B",       "google/gemma-2-27b-it",                            "general"), # Gemma-2 27B
    ("NVIDIA_PHI3_SMALL",       "microsoft/phi-3-small-8k-instruct",                "fast"),    # SEO/metadata
    ("NVIDIA_MISTRAL_LARGE_B",  "mistralai/mistral-large-3-675b-instruct-2512",     "writing"), # 675B Writer B
    ("NVIDIA_LLAMA33_C",        "meta/llama-3.3-70b-instruct",                      "chat"),    # Chat C (re-enabled 2026-03-26)
    ("NVIDIA_LLAMA33_D",        "meta/llama-3.3-70b-instruct",                      "chat"),    # Chat D
    ("NVIDIA_LLAMA33_E",        "meta/llama-3.3-70b-instruct",                      "chat"),    # Chat E
    ("NVIDIA_LLAMA33_F",        "meta/llama-3.3-70b-instruct",                      "chat"),    # Chat F
    ("NVIDIA_LLAMA33_G",        "meta/llama-3.3-70b-instruct",                      "chat"),    # Chat G
]

# Fallback chain: if primary pool exhausted, try these pools in order
_FALLBACK_CHAINS: Dict[str, List[str]] = {
    "writing":  ["general", "chat"],
    "chat":     ["general", "fast"],
    "code":     ["general", "chat"],
    "vision":   ["general", "chat"],
    "image":    ["vision", "general"],
    "video":    ["writing", "general"],
    "fast":     ["general", "chat"],
    "general":  ["chat", "fast"],
}

_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
_COOLDOWN_SECONDS = 60
_MAX_FAILURES_BEFORE_SKIP = 3


class NvidiaPool:
    """
    NVIDIA NIM Pool Orchestrator.

    Usage:
        pool = NvidiaPool()
        text = pool.generate("chat", "You are helpful.", "Say hi in 3 words")
        stats = pool.get_stats()
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._pools: Dict[str, List[dict]] = {}
        self._pool_indices: Dict[str, int] = {}
        self._build_pools()

    def _build_pools(self):
        """Load all keys from environment and organize into pools."""
        pools: Dict[str, List[dict]] = {
            "writing": [],
            "chat":    [],
            "code":    [],
            "vision":  [],
            "image":   [],
            "video":   [],
            "fast":    [],
            "general": [],
        }

        for env_var, model, pool_name in _KEY_DEFINITIONS:
            key = os.getenv(env_var, "").strip()
            if not key or "your_" in key or not key.startswith("nvapi-"):
                log.warning(f"[NvidiaPool] {env_var} missing or invalid — skipping")
                continue
            entry = {
                "env_var":        env_var,
                "key":            key,
                "model":          model,
                "pool":           pool_name,
                "calls":          0,
                "failures":       0,
                "cooldown_until": 0.0,
            }
            pools[pool_name].append(entry)

        self._pools = pools
        self._pool_indices = {name: 0 for name in pools}

        total = sum(len(v) for v in pools.values())
        log.info(f"[NvidiaPool] Loaded {total} keys across {len(pools)} pools")
        for name, entries in pools.items():
            if entries:
                log.info(f"  {name}: {len(entries)} keys")

    def _is_key_available(self, entry: dict) -> bool:
        if entry["failures"] >= _MAX_FAILURES_BEFORE_SKIP:
            return False
        if time.time() < entry["cooldown_until"]:
            return False
        return True

    def _get_key(self, task_type: str) -> Optional[dict]:
        with self._lock:
            pool = self._pools.get(task_type, [])
            if not pool:
                return None

            start_idx = self._pool_indices.get(task_type, 0)
            n = len(pool)

            for i in range(n):
                idx = (start_idx + i) % n
                entry = pool[idx]
                if self._is_key_available(entry):
                    self._pool_indices[task_type] = (idx + 1) % n
                    return entry

            return None

    def _mark_success(self, entry: dict):
        with self._lock:
            entry["calls"] += 1
            entry["failures"] = 0
            entry["cooldown_until"] = 0.0

    def _mark_failure(self, entry: dict, is_rate_limit: bool = False):
        with self._lock:
            entry["failures"] += 1
            if is_rate_limit:
                entry["cooldown_until"] = time.time() + _COOLDOWN_SECONDS
            else:
                backoff = min(30 * (2 ** min(entry["failures"] - 1, 3)), 300)
                entry["cooldown_until"] = time.time() + backoff
            log.warning(
                f"[NvidiaPool] {entry['env_var']} failure #{entry['failures']} "
                f"— cooldown +{int(entry['cooldown_until'] - time.time())}s"
            )

    def _call_key(
        self,
        entry: dict,
        system_prompt: str,
        user_message: str,
        history: list,
        max_tokens: int = 16384,
        temperature: float = 0.7,
    ) -> str:
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history[-8:]:
            role = "assistant" if msg.get("role") in ("model", "assistant") else "user"
            messages.append({"role": role, "content": msg["content"]})
        messages.append({"role": "user", "content": user_message})

        resp = requests.post(
            _NVIDIA_BASE_URL,
            headers={
                "Authorization": f"Bearer {entry['key']}",
                "Accept":        "application/json",
            },
            json={
                "model":       entry["model"],
                "messages":    messages,
                "max_tokens":  max_tokens,
                "temperature": temperature,
                "top_p":       0.95,
            },
            timeout=60,
        )

        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        elif resp.status_code == 402:
            raise Exception(f"NVIDIA credits exhausted for {entry['env_var']}")
        elif resp.status_code == 429:
            raise Exception(f"NVIDIA rate limit 429 for {entry['env_var']}")
        elif resp.status_code == 404:
            entry["failures"] = _MAX_FAILURES_BEFORE_SKIP
            raise Exception(f"NVIDIA 404 model not found: {entry['model']} ({entry['env_var']})")
        else:
            raise Exception(
                f"NVIDIA {resp.status_code} from {entry['env_var']}: {resp.text[:150]}"
            )

    def generate(
        self,
        task_type: str,
        system_prompt: str,
        user_message: str,
        history: list = None,
        max_tokens: int = 16384,
        temperature: float = 0.7,
    ) -> str:
        history = history or []

        if task_type not in self._pools:
            log.warning(f"[NvidiaPool] Unknown task_type '{task_type}', defaulting to 'general'")
            task_type = "general"

        pools_to_try = [task_type] + _FALLBACK_CHAINS.get(task_type, ["general"])
        attempted_keys = set()

        for pool_name in pools_to_try:
            while True:
                entry = self._get_key(pool_name)
                if entry is None:
                    break

                key_id = entry["env_var"]
                if key_id in attempted_keys:
                    break
                attempted_keys.add(key_id)

                try:
                    log.info(f"[NvidiaPool] {pool_name}/{key_id} -> {entry['model'][:40]}")
                    result = self._call_key(
                        entry, system_prompt, user_message, history,
                        max_tokens=max_tokens, temperature=temperature
                    )
                    self._mark_success(entry)
                    return result

                except Exception as e:
                    err = str(e)
                    is_rate = "429" in err or "rate limit" in err.lower()
                    is_credits = "402" in err or "credits" in err.lower()
                    is_404 = "404" in err

                    if not is_404:
                        self._mark_failure(entry, is_rate_limit=is_rate or is_credits)

                    log.warning(f"[NvidiaPool] {key_id} failed: {err[:100]}")
                    continue

        raise Exception(
            "All NVIDIA pools exhausted — no working keys available. "
            "Check credits or cooldown status with get_stats()."
        )

    def get_stats(self) -> Dict[str, dict]:
        with self._lock:
            stats = {}
            now = time.time()
            for pool_name, entries in self._pools.items():
                available = sum(1 for e in entries if self._is_key_available(e))
                total_calls = sum(e["calls"] for e in entries)
                key_details = []
                for e in entries:
                    key_details.append({
                        "env_var":            e["env_var"],
                        "model":              e["model"],
                        "calls":              e["calls"],
                        "failures":           e["failures"],
                        "available":          self._is_key_available(e),
                        "cooldown_remaining": max(0, int(e["cooldown_until"] - now)),
                    })
                stats[pool_name] = {
                    "total_keys":  len(entries),
                    "available":   available,
                    "total_calls": total_calls,
                    "keys":        key_details,
                }
            return stats

    def reset_failures(self, env_var: str = None):
        with self._lock:
            for entries in self._pools.values():
                for e in entries:
                    if env_var is None or e["env_var"] == env_var:
                        e["failures"] = 0
                        e["cooldown_until"] = 0.0
            log.info(f"[NvidiaPool] Reset failures for: {env_var or 'ALL'}")

    def __repr__(self) -> str:
        total = sum(len(v) for v in self._pools.values())
        avail = sum(
            1 for entries in self._pools.values()
            for e in entries if self._is_key_available(e)
        )
        return f"<NvidiaPool keys={total} available={avail}>"
