"""
Sync keys from Supabase `api_keys` table into local `.env`.

Behavior:
1) Fetch key rows (`name`, `key`) from Supabase using local SUPABASE_SERVICE_KEY.
2) Validate supported providers via lightweight auth checks.
3) Optionally apply only passing keys to `.env` (`--apply`).

Usage:
  python scripts/sync_env_from_api_keys.py
  python scripts/sync_env_from_api_keys.py --apply
"""

from __future__ import annotations

import json
import os
import sys

# Fix Windows cp1252 console encoding
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
from pathlib import Path
from typing import Callable, Dict, Tuple

import requests
from dotenv import dotenv_values, load_dotenv


ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"


def _mask(value: str) -> str:
    if not value:
        return "<empty>"
    if len(value) <= 8:
        return "****"
    return f"{value[:4]}...{value[-4:]}"


def _ok_status(resp: requests.Response, allowed: Tuple[int, ...] = (200,)) -> Tuple[bool, str]:
    return (resp.status_code in allowed, f"status={resp.status_code}")


def _validate_gemini(key: str) -> Tuple[bool, str]:
    resp = requests.get(
        f"https://generativelanguage.googleapis.com/v1beta/models?key={key}",
        timeout=20,
    )
    return _ok_status(resp, (200,))


def _validate_openai(key: str) -> Tuple[bool, str]:
    resp = requests.get(
        "https://api.openai.com/v1/models",
        headers={"Authorization": f"Bearer {key}"},
        timeout=20,
    )
    return _ok_status(resp, (200,))


def _validate_anthropic(key: str) -> Tuple[bool, str]:
    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-3-5-haiku-latest",
            "max_tokens": 8,
            "messages": [{"role": "user", "content": "ping"}],
        },
        timeout=20,
    )
    return _ok_status(resp, (200,))


def _validate_groq(key: str) -> Tuple[bool, str]:
    resp = requests.get(
        "https://api.groq.com/openai/v1/models",
        headers={"Authorization": f"Bearer {key}"},
        timeout=20,
    )
    return _ok_status(resp, (200,))


def _validate_xai(key: str) -> Tuple[bool, str]:
    resp = requests.get(
        "https://api.x.ai/v1/models",
        headers={"Authorization": f"Bearer {key}"},
        timeout=20,
    )
    return _ok_status(resp, (200,))


def _validate_hf(key: str) -> Tuple[bool, str]:
    resp = requests.get(
        "https://huggingface.co/api/whoami-v2",
        headers={"Authorization": f"Bearer {key}"},
        timeout=20,
    )
    return _ok_status(resp, (200,))


def _validate_elevenlabs(key: str) -> Tuple[bool, str]:
    resp = requests.get(
        "https://api.elevenlabs.io/v1/user",
        headers={"xi-api-key": key},
        timeout=20,
    )
    return _ok_status(resp, (200,))


def _validate_telegram(key: str) -> Tuple[bool, str]:
    resp = requests.get(f"https://api.telegram.org/bot{key}/getMe", timeout=20)
    return _ok_status(resp, (200,))


def _validate_yt_api_key(key: str) -> Tuple[bool, str]:
    resp = requests.get(
        "https://www.googleapis.com/youtube/v3/videoCategories",
        params={"part": "snippet", "regionCode": "US", "key": key},
        timeout=20,
    )
    return _ok_status(resp, (200,))


VALIDATORS: Dict[str, Callable[[str], Tuple[bool, str]]] = {
    "GEMINI_API_KEY": _validate_gemini,
    "OPENAI_API_KEY": _validate_openai,
    "ANTHROPIC_API_KEY": _validate_anthropic,
    "GROQ_API_KEY": _validate_groq,
    "XAI_API_KEY": _validate_xai,
    "HUGGINGFACE_API_KEY": _validate_hf,
    "ELEVENLABS_API_KEY": _validate_elevenlabs,
    "TELEGRAM_BOT_TOKEN": _validate_telegram,
    "YOUTUBE_API_KEY": _validate_yt_api_key,
}


def fetch_api_keys_table() -> Dict[str, str]:
    load_dotenv(ENV_PATH)
    url = os.getenv("SUPABASE_URL")
    service_key = os.getenv("SUPABASE_SERVICE_KEY")
    if not url or not service_key:
        raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in local .env")

    resp = requests.get(
        f"{url}/rest/v1/api_keys?select=name,key",
        headers={"apikey": service_key, "Authorization": f"Bearer {service_key}"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"api_keys fetch failed: status={resp.status_code} body={resp.text[:250]}")
    rows = resp.json()
    return {row["name"]: row.get("key", "") for row in rows if row.get("name")}


def apply_to_env(valid_pairs: Dict[str, str]) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    index: Dict[str, int] = {}
    for i, line in enumerate(lines):
        if "=" in line and not line.strip().startswith("#"):
            k = line.split("=", 1)[0].strip()
            index[k] = i

    for k, v in valid_pairs.items():
        if k in index:
            lines[index[k]] = f"{k}={v}"
        else:
            lines.append(f"{k}={v}")

    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    apply = "--apply" in sys.argv
    table_keys = fetch_api_keys_table()

    results = []
    passing: Dict[str, str] = {}

    for name, value in sorted(table_keys.items()):
        if not value:
            results.append((name, "SKIP", "empty"))
            continue
        if "your_" in value.lower():
            results.append((name, "SKIP", "placeholder"))
            continue

        validator = VALIDATORS.get(name)
        if not validator:
            results.append((name, "SKIP", "no-validator"))
            continue

        try:
            ok, detail = validator(value)
            if ok:
                passing[name] = value
                results.append((name, "PASS", detail))
            else:
                results.append((name, "FAIL", detail))
        except Exception as exc:  # pragma: no cover
            results.append((name, "FAIL", f"error={exc}"))

    print("Validation report (masked):")
    for name, status, detail in results:
        raw = table_keys.get(name, "")
        print(f"  {name:28s} {status:5s} {_mask(raw):16s} {detail}")

    print("\nSummary:")
    print(f"  total rows      : {len(table_keys)}")
    print(f"  validated pass  : {len(passing)}")
    print(f"  apply requested : {'yes' if apply else 'no'}")

    if apply:
        apply_to_env(passing)
        print(f"  .env updated with {len(passing)} validated keys")
    else:
        print("  dry run only (no .env changes)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

