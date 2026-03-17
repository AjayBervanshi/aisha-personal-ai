"""
social_media_engine.py
======================
Aisha's Social Media Command Center.
One-account-first compatible, then scalable to multi-account.
Tokens are loaded from Supabase api_keys table (secret column).
"""

import os
import json
import logging
import tempfile

log = logging.getLogger("Aisha.SocialMedia")


def _get_supabase():
    """Return a Supabase client using service role key."""
    from supabase import create_client
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL / SUPABASE_SERVICE_KEY not set")
    return create_client(url, key)


def _load_db_secret(name: str) -> str | None:
    """Fetch a secret from api_keys table by name. Returns None if not found."""
    try:
        sb = _get_supabase()
        row = sb.table("api_keys").select("secret").eq("name", name).eq("active", True).single().execute()
        return row.data["secret"] if row.data else None
    except Exception as e:
        log.warning(f"[api_keys] Could not load '{name}' from DB: {e}")
        return None


class SocialMediaEngine:
    """
    Unified social media manager.
    Tokens are loaded from Supabase api_keys table; env vars used as fallback.
    """

    # DB key names for each channel's credentials
    CHANNEL_TO_DB_KEY = {
        "Story With Aisha": {
            "instagram": "INSTAGRAM_TOKEN",
            "youtube": "YOUTUBE_OAUTH_TOKEN",
        },
        "Riya's Dark Whisper": {
            "instagram": "INSTAGRAM_TOKEN",
            "youtube": "YOUTUBE_OAUTH_TOKEN",
        },
        "Riya's Dark Romance Library": {
            "instagram": "INSTAGRAM_TOKEN",
            "youtube": "YOUTUBE_OAUTH_TOKEN",
        },
        "Aisha & Him": {
            "instagram": "INSTAGRAM_TOKEN",
            "youtube": "YOUTUBE_OAUTH_TOKEN",
        },
    }

    def __init__(self):
        self.youtube_client_id = os.getenv("YOUTUBE_CLIENT_ID")
        self.youtube_client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")
        # Cache loaded tokens to avoid repeated DB round-trips
        self._token_cache: dict = {}

    def _get_instagram_creds(self, channel: str) -> tuple[str, str]:
        """Load Instagram credentials from DB, falling back to env vars."""
        cache_key = f"ig_{channel}"
        if cache_key not in self._token_cache:
            raw = _load_db_secret("INSTAGRAM_TOKEN")
            if raw:
                try:
                    parsed = json.loads(raw)
                    self._token_cache[cache_key] = (
                        parsed.get("access_token", ""),
                        parsed.get("business_id", ""),
                    )
                except (json.JSONDecodeError, TypeError):
                    # raw value is a plain token string
                    self._token_cache[cache_key] = (raw, "")

        token, biz_id = self._token_cache.get(cache_key, ("", ""))

        # Env-var fallback
        if not token:
            token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
        if not biz_id:
            biz_id = os.getenv("INSTAGRAM_BUSINESS_ID", "")

        return token, biz_id

    def _get_youtube_credentials(self, channel: str):
        """
        Load YouTube OAuth credentials from DB (or token file as fallback).
        Returns a google.oauth2.credentials.Credentials object.
        """
        from google.oauth2.credentials import Credentials

        cache_key = f"yt_{channel}"
        if cache_key not in self._token_cache:
            raw = _load_db_secret("YOUTUBE_OAUTH_TOKEN")
            if raw:
                try:
                    self._token_cache[cache_key] = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    pass

        token_data = self._token_cache.get(cache_key)

        if token_data:
            return Credentials(
                token=token_data.get("token"),
                refresh_token=token_data.get("refresh_token"),
                token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
                client_id=token_data.get("client_id") or self.youtube_client_id,
                client_secret=token_data.get("client_secret") or self.youtube_client_secret,
                scopes=token_data.get("scopes"),
            )

        # File-based fallback (tokens/ directory)
        candidates = [
            f"tokens/youtube_token_{channel.replace(' ', '_').replace(\"'\", '')}.json",
            "tokens/youtube_token.json",
        ]
        for path in candidates:
            if os.path.exists(path):
                log.warning(f"[YouTube] Using token file fallback: {path}")
                return Credentials.from_authorized_user_file(path)

        raise FileNotFoundError(f"No YouTube OAuth token found for channel '{channel}'. Run setup_youtube_oauth.py or insert into api_keys table.")

    def post_instagram_reel(self, video_url: str, caption: str, hashtags: list | None = None, channel: str = "Story With Aisha", job_id: str | None = None) -> dict:
        # Idempotency guard — skip if already posted
        if job_id:
            try:
                sb = _get_supabase()
                existing = sb.table("content_queue").select("instagram_post_id").eq("id", job_id).single().execute()
                if existing.data and existing.data.get("instagram_post_id"):
                    log.info(f"[Instagram] Job {job_id} already posted: {existing.data['instagram_post_id']}")
                    return {"success": True, "post_id": existing.data["instagram_post_id"], "skipped": True}
            except Exception:
                pass

        token, biz_id = self._get_instagram_creds(channel)
        if not token or not biz_id:
            return {"success": False, "error": "No Instagram credentials configured"}

        import requests
        import time

        full_caption = caption
        if hashtags:
            full_caption += "\n\n" + " ".join(f"#{h.strip('#')}" for h in hashtags[:30])

        base_url = f"https://graph.facebook.com/v19.0/{biz_id}"

        try:
            create_resp = requests.post(
                f"{base_url}/media",
                params={
                    "media_type": "REELS",
                    "video_url": video_url,
                    "caption": full_caption,
                    "access_token": token,
                },
                timeout=30,
            ).json()
            container_id = create_resp.get("id")
            if not container_id:
                return {"success": False, "error": create_resp}

            for _ in range(12):
                status_resp = requests.get(
                    f"https://graph.facebook.com/v19.0/{container_id}",
                    params={"fields": "status_code", "access_token": token},
                    timeout=20,
                ).json()
                if status_resp.get("status_code") == "FINISHED":
                    break
                time.sleep(5)

            publish_resp = requests.post(
                f"{base_url}/media_publish",
                params={"creation_id": container_id, "access_token": token},
                timeout=30,
            ).json()

            post_id = publish_resp.get("id")

            # Persist post ID for idempotency
            if job_id and post_id:
                try:
                    _get_supabase().table("content_queue").update({
                        "instagram_post_id": post_id,
                        "instagram_status": "published",
                    }).eq("id", job_id).execute()
                except Exception as db_err:
                    log.warning(f"[Instagram] Could not persist post_id to DB: {db_err}")

            return {"success": True, "post_id": post_id}
        except Exception as e:
            log.error(f"[Instagram] Reel post failed: {e}")
            if job_id:
                try:
                    _get_supabase().table("content_queue").update({"instagram_status": "failed"}).eq("id", job_id).execute()
                except Exception:
                    pass
            return {"success": False, "error": str(e)}

    def post_instagram_image(self, image_url: str, caption: str, hashtags: list | None = None, channel: str = "Story With Aisha") -> dict:
        token, biz_id = self._get_instagram_creds(channel)
        if not token or not biz_id:
            return {"success": False, "error": "No Instagram credentials configured"}

        import requests

        full_caption = caption
        if hashtags:
            full_caption += "\n\n" + " ".join(f"#{h.strip('#')}" for h in hashtags[:30])

        base_url = f"https://graph.facebook.com/v19.0/{biz_id}"

        try:
            create_resp = requests.post(
                f"{base_url}/media",
                params={"image_url": image_url, "caption": full_caption, "access_token": token},
                timeout=30,
            ).json()
            container_id = create_resp.get("id")
            if not container_id:
                return {"success": False, "error": create_resp}

            publish_resp = requests.post(
                f"{base_url}/media_publish",
                params={"creation_id": container_id, "access_token": token},
                timeout=30,
            ).json()
            return {"success": True, "post_id": publish_resp.get("id")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def upload_youtube_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list,
        channel_name: str = "Story With Aisha",
        privacy: str = "public",
        job_id: str | None = None,
    ) -> dict:
        # Idempotency guard — skip if already uploaded
        if job_id:
            try:
                sb = _get_supabase()
                existing = sb.table("content_queue").select("youtube_video_id", "youtube_url").eq("id", job_id).single().execute()
                if existing.data and existing.data.get("youtube_video_id"):
                    log.info(f"[YouTube] Job {job_id} already uploaded: {existing.data['youtube_url']}")
                    return {"success": True, "video_id": existing.data["youtube_video_id"], "url": existing.data["youtube_url"], "skipped": True}
            except Exception:
                pass

        try:
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload

            creds = self._get_youtube_credentials(channel_name)
            youtube = build("youtube", "v3", credentials=creds)

            body = {
                "snippet": {
                    "title": title[:100],
                    "description": description,
                    "tags": tags[:15],
                    "categoryId": "22",
                },
                "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
            }

            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)

            response = None
            while response is None:
                _, response = request.next_chunk()

            video_id = response.get("id")
            url = f"https://youtube.com/watch?v={video_id}"

            # Persist video ID for idempotency
            if job_id:
                try:
                    sb = _get_supabase()
                    sb.table("content_queue").update({
                        "youtube_video_id": video_id,
                        "youtube_url": url,
                        "youtube_status": "published",
                    }).eq("id", job_id).execute()
                except Exception as db_err:
                    log.warning(f"[YouTube] Could not persist video_id to DB: {db_err}")

            return {"success": True, "video_id": video_id, "url": url}

        except ImportError:
            return {"success": False, "error": "Install: pip install google-api-python-client google-auth"}
        except Exception as e:
            log.error(f"[YouTube] Upload failed: {e}")
            if job_id:
                try:
                    _get_supabase().table("content_queue").update({"youtube_status": "failed"}).eq("id", job_id).execute()
                except Exception:
                    pass
            return {"success": False, "error": str(e)}

    def cross_post(self, content_package: dict) -> dict:
        results = {}
        channel = content_package.get("channel", "Story With Aisha")

        if content_package.get("video_path"):
            results["youtube"] = self.upload_youtube_video(
                video_path=content_package["video_path"],
                title=content_package.get("title", "New Video"),
                description=content_package.get("description", ""),
                tags=content_package.get("tags", []),
                channel_name=channel,
            )

        if content_package.get("video_url"):
            results["instagram"] = self.post_instagram_reel(
                video_url=content_package["video_url"],
                caption=content_package.get("caption", ""),
                hashtags=content_package.get("tags", []),
                channel=channel,
            )

        return results

    def status(self, channel: str = "Story With Aisha") -> str:
        ig_token, ig_biz = self._get_instagram_creds(channel)

        yt_ok = False
        try:
            self._get_youtube_credentials(channel)
            yt_ok = True
        except Exception:
            pass

        lines = ["=== Social Media Status ==="]
        lines.append(f"Channel       : {channel}")
        lines.append(f"YouTube API   : {'Connected' if self.youtube_client_id else 'Missing YOUTUBE_CLIENT_ID'}")
        lines.append(f"YouTube OAuth : {'Loaded from DB' if yt_ok else 'Missing — run setup_youtube_oauth.py or insert into api_keys'}")
        lines.append(f"Instagram API : {'Connected' if (ig_token and ig_biz) else 'Missing — insert INSTAGRAM_TOKEN into api_keys or set env vars'}")
        return "\n".join(lines)
