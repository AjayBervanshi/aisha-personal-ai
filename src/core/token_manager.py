"""
token_manager.py
================
Monitors and refreshes API tokens before they expire.
- Instagram: 60-day token expiry, refresh at 30 days
- YouTube: OAuth token — validate and refresh via google-auth
- Supabase: service keys don't expire (skip)
- Telegram: bot tokens don't expire (skip)
"""
import os
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger("Aisha.TokenManager")

TOKENS_DIR = Path(__file__).parent.parent.parent / "tokens"


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text()) if path.exists() else {}
    except Exception as e:
        log.error(f"[TokenManager] load_json {path}: {e}")
        return {}


def _save_json(path: Path, data: dict) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))
        return True
    except Exception as e:
        log.error(f"[TokenManager] save_json {path}: {e}")
        return False


def check_instagram_token() -> dict:
    """
    Check Instagram token health.
    Instagram long-lived tokens expire in 60 days.
    Refresh if within 30 days of expiry.
    Returns {'status': 'ok'|'refreshed'|'expired'|'missing', 'expires_at': ...}
    """
    token_path = TOKENS_DIR / "instagram_token.json"
    data = _load_json(token_path)

    if not data or not data.get("access_token"):
        log.warning("[TokenManager] Instagram token missing")
        return {"status": "missing"}

    expires_at_str = data.get("expires_at") or data.get("token_expiry")
    if not expires_at_str:
        log.warning("[TokenManager] Instagram token has no expiry date — treating as valid")
        return {"status": "ok", "note": "no expiry date"}

    try:
        expires_at = datetime.fromisoformat(str(expires_at_str).replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        days_left = (expires_at - now).days

        log.info(f"[TokenManager] Instagram token expires in {days_left} days")

        if days_left < 0:
            return {"status": "expired", "days_left": days_left}

        if days_left < 30:
            # Attempt refresh via Instagram Graph API
            refreshed = _refresh_instagram_token(data["access_token"], token_path, data)
            return {"status": "refreshed" if refreshed else "expiring_soon", "days_left": days_left}

        return {"status": "ok", "days_left": days_left}
    except Exception as e:
        log.error(f"[TokenManager] Instagram token check error: {e}")
        return {"status": "error", "error": str(e)}


def _refresh_instagram_token(access_token: str, token_path: Path, existing_data: dict) -> bool:
    """Refresh Instagram long-lived token."""
    try:
        import requests
        # Instagram token refresh endpoint
        resp = requests.get(
            "https://graph.instagram.com/refresh_access_token",
            params={
                "grant_type": "ig_refresh_token",
                "access_token": access_token,
            },
            timeout=30
        )

        if resp.status_code == 200:
            new_data = resp.json()
            # Calculate new expiry (typically 60 days from now)
            expires_in = new_data.get("expires_in", 5183944)  # ~60 days in seconds
            new_expiry = (datetime.now(timezone.utc) + timedelta(seconds=expires_in)).isoformat()

            updated = {**existing_data, **new_data, "expires_at": new_expiry, "refreshed_at": datetime.now(timezone.utc).isoformat()}
            _save_json(token_path, updated)
            log.info(f"[TokenManager] Instagram token refreshed, new expiry: {new_expiry}")
            return True
        else:
            log.error(f"[TokenManager] Instagram refresh failed: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        log.error(f"[TokenManager] Instagram refresh error: {e}")
        return False


def check_youtube_token() -> dict:
    """
    Validate YouTube OAuth token. Refresh if expired.
    Returns {'status': 'ok'|'refreshed'|'expired'|'missing'}
    """
    token_path = TOKENS_DIR / "youtube_token.json"
    data = _load_json(token_path)

    if not data:
        return {"status": "missing"}

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request as GoogleRequest

        creds = Credentials(
            token=data.get("token") or data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            token_uri=data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=data.get("client_id") or os.getenv("YOUTUBE_CLIENT_ID", ""),
            client_secret=data.get("client_secret") or os.getenv("YOUTUBE_CLIENT_SECRET", ""),
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(GoogleRequest())
            # Save refreshed token
            updated = {**data, "token": creds.token, "expiry": creds.expiry.isoformat() if creds.expiry else None}
            _save_json(token_path, updated)
            log.info("[TokenManager] YouTube token refreshed")
            return {"status": "refreshed"}

        return {"status": "ok"}
    except ImportError:
        # google-auth not available, just check if token file exists and is non-empty
        log.warning("[TokenManager] google-auth not available, skipping YouTube OAuth refresh")
        return {"status": "ok", "note": "google-auth unavailable"}
    except Exception as e:
        log.error(f"[TokenManager] YouTube token check error: {e}")
        return {"status": "error", "error": str(e)}


def run_token_health_check() -> dict:
    """
    Run full token health check. Called daily by autonomous_loop.
    Returns summary dict.
    """
    results = {}

    log.info("[TokenManager] Running token health check...")

    results["instagram"] = check_instagram_token()
    results["youtube"] = check_youtube_token()

    # Log summary
    for service, result in results.items():
        status = result.get("status", "unknown")
        if status in ("expired", "missing"):
            log.error(f"[TokenManager] {service.upper()} TOKEN {status.upper()} — manual action required!")
        elif status == "refreshed":
            log.info(f"[TokenManager] {service} token auto-refreshed successfully")
        else:
            log.info(f"[TokenManager] {service} token status: {status}")

    return results
