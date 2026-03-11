"""
social_media_engine.py
======================
Aisha's Social Media Command Center.

Handles posting, scheduling, and analytics for:
  - YouTube (script + upload)
  - Instagram (caption + reel/post)
  - Future: Twitter/X, Facebook, LinkedIn

Aisha runs this autonomously. She creates content, posts it,
and reports back to Ajay on Telegram.
"""

import os
import logging
from datetime import datetime
from typing import Optional

log = logging.getLogger("Aisha.SocialMedia")


class SocialMediaEngine:
    """
    Aisha's unified social media manager.
    ONE codebase manages ALL channel accounts.
    Routing: channel name → correct account credentials.
    """

    # Maps channel names to their .env token keys
    CHANNEL_TO_ENV = {
        "Story With Aisha": {
            "instagram_token": "INSTAGRAM_TOKEN_STORY_WITH_AISHA",
            "instagram_biz":   "INSTAGRAM_BIZ_ID_STORY_WITH_AISHA",
            "youtube_token":   "youtube_token_Story_With_Aisha.json",
        },
        "Riya's Dark Whisper": {
            "instagram_token": "INSTAGRAM_TOKEN_RIYAS_DARK_WHISPER",
            "instagram_biz":   "INSTAGRAM_BIZ_ID_RIYAS_DARK_WHISPER",
            "youtube_token":   "youtube_token_Riyas_Dark_Whisper.json",
        },
        "Riya's Dark Romance Library": {
            "instagram_token": "INSTAGRAM_TOKEN_RIYAS_DARK_LIBRARY",
            "instagram_biz":   "INSTAGRAM_BIZ_ID_RIYAS_DARK_LIBRARY",
            "youtube_token":   "youtube_token_Riyas_Dark_Romance_Library.json",
        },
        "Aisha & Him": {
            "instagram_token": "INSTAGRAM_TOKEN_AISHA_AND_HIM",
            "instagram_biz":   "INSTAGRAM_BIZ_ID_AISHA_AND_HIM",
            "youtube_token":   "youtube_token_Aisha_Him.json",
        },
    }

    def __init__(self):
        self.youtube_client_id     = os.getenv("YOUTUBE_CLIENT_ID")
        self.youtube_client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")

    def _get_instagram_creds(self, channel: str) -> tuple:
        """Get the Instagram token + biz_id for a specific channel."""
        mapping = self.CHANNEL_TO_ENV.get(channel, {})
        token  = os.getenv(mapping.get("instagram_token", ""), "")
        biz_id = os.getenv(mapping.get("instagram_biz", ""), "")
        return token, biz_id

    def _get_youtube_token_file(self, channel: str) -> str:
        """Get the YouTube OAuth token file path for a specific channel."""
        mapping = self.CHANNEL_TO_ENV.get(channel, {})
        return mapping.get("youtube_token", "youtube_token_default.json")

    # ── INSTAGRAM ──────────────────────────────────────────────────────────────

    def post_instagram_reel(self, video_url: str, caption: str, hashtags: list = None) -> dict:
        """
        Post a Reel to Instagram Business account via Graph API.
        Requires: INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ID in .env

        Steps: Create media container → Publish
        """
        if not self.instagram_token or not self.instagram_biz_id:
            log.warning("[Instagram] No credentials. Set INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_BUSINESS_ID in .env")
            return {"success": False, "error": "No Instagram credentials"}

        import requests

        full_caption = caption
        if hashtags:
            full_caption += "\n\n" + " ".join(f"#{h.strip('#')}" for h in hashtags[:30])

        base_url = f"https://graph.facebook.com/v19.0/{self.instagram_biz_id}"

        try:
            # Step 1: Create media container
            create_resp = requests.post(f"{base_url}/reels", params={
                "video_url": video_url,
                "caption": full_caption,
                "access_token": self.instagram_token,
            })
            container_data = create_resp.json()
            container_id = container_data.get("id")

            if not container_id:
                return {"success": False, "error": container_data}

            log.info(f"[Instagram] Container created: {container_id}. Waiting for processing...")

            import time
            # Step 2: Wait for video to process (poll status)
            for _ in range(10):
                status_resp = requests.get(f"https://graph.facebook.com/v19.0/{container_id}", params={
                    "fields": "status_code",
                    "access_token": self.instagram_token
                })
                status = status_resp.json().get("status_code")
                if status == "FINISHED":
                    break
                time.sleep(5)

            # Step 3: Publish
            publish_resp = requests.post(f"{base_url}/media_publish", params={
                "creation_id": container_id,
                "access_token": self.instagram_token,
            })
            result = publish_resp.json()
            log.info(f"[Instagram] Published! Post ID: {result.get('id')}")
            return {"success": True, "post_id": result.get("id")}

        except Exception as e:
            log.error(f"[Instagram] Failed: {e}")
            return {"success": False, "error": str(e)}

    def post_instagram_image(self, image_url: str, caption: str, hashtags: list = None) -> dict:
        """Post a static image to Instagram."""
        if not self.instagram_token or not self.instagram_biz_id:
            return {"success": False, "error": "No Instagram credentials"}

        import requests
        full_caption = caption
        if hashtags:
            full_caption += "\n\n" + " ".join(f"#{h.strip('#')}" for h in hashtags[:30])

        base_url = f"https://graph.facebook.com/v19.0/{self.instagram_biz_id}"

        try:
            create_resp = requests.post(f"{base_url}/media", params={
                "image_url": image_url,
                "caption": full_caption,
                "access_token": self.instagram_token,
            }).json()

            container_id = create_resp.get("id")
            if not container_id:
                return {"success": False, "error": create_resp}

            publish_resp = requests.post(f"{base_url}/media_publish", params={
                "creation_id": container_id,
                "access_token": self.instagram_token,
            }).json()

            return {"success": True, "post_id": publish_resp.get("id")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── YOUTUBE ────────────────────────────────────────────────────────────────

    def upload_youtube_video(
        self,
        video_path: str,
        title: str,
        description: str,
        tags: list,
        channel_name: str = "Story With Aisha",
        privacy: str = "public",
    ) -> dict:
        """
        Upload a video to YouTube.
        Requires: YouTube Data API v3 credentials + OAuth token.

        NOTE: First-time use requires browser OAuth flow.
        Set YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET in .env
        """
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload

            creds_path = f"youtube_token_{channel_name.replace(' ', '_')}.json"

            if not os.path.exists(creds_path):
                log.warning(f"[YouTube] No OAuth token for '{channel_name}'. Run setup first.")
                return {"success": False, "error": f"No YouTube token. Run: python src/integrations/youtube_auth.py --channel '{channel_name}'"}

            creds = Credentials.from_authorized_user_file(creds_path)
            youtube = build("youtube", "v3", credentials=creds)

            body = {
                "snippet": {
                    "title": title[:100],
                    "description": description,
                    "tags": tags[:15],
                    "categoryId": "22",  # People & Blogs
                },
                "status": {
                    "privacyStatus": privacy,
                    "selfDeclaredMadeForKids": False,
                }
            }

            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            request = youtube.videos().insert(part=",".join(body.keys()), body=body, media_body=media)

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    log.info(f"[YouTube] Upload progress: {int(status.progress() * 100)}%")

            video_id = response.get("id")
            log.info(f"[YouTube] Uploaded! https://youtube.com/watch?v={video_id}")
            return {"success": True, "video_id": video_id, "url": f"https://youtube.com/watch?v={video_id}"}

        except ImportError:
            return {"success": False, "error": "Install: pip install google-api-python-client google-auth"}
        except Exception as e:
            log.error(f"[YouTube] Upload failed: {e}")
            return {"success": False, "error": str(e)}

    # ── CROSS-POST ─────────────────────────────────────────────────────────────

    def cross_post(self, content_package: dict) -> dict:
        """
        Post the same content across all platforms at once.
        content_package = {
            'video_path': '...', 'title': '...', 'description': '...',
            'tags': [...], 'caption': '...', 'video_url': '...', 'channel': '...'
        }
        """
        results = {}

        # YouTube
        if content_package.get("video_path"):
            results["youtube"] = self.upload_youtube_video(
                video_path=content_package["video_path"],
                title=content_package.get("title", "New Video"),
                description=content_package.get("description", ""),
                tags=content_package.get("tags", []),
                channel_name=content_package.get("channel", "Story With Aisha"),
            )

        # Instagram Reel
        if content_package.get("video_url"):
            results["instagram"] = self.post_instagram_reel(
                video_url=content_package["video_url"],
                caption=content_package.get("caption", ""),
                hashtags=content_package.get("tags", []),
            )

        return results

    # ── STATUS ─────────────────────────────────────────────────────────────────

    def status(self) -> str:
        """Return current integration status for Telegram /status command."""
        lines = ["=== Social Media Status ==="]
        lines.append(f"YouTube API   : {'Connected' if self.youtube_client_id else 'Not configured - Add YOUTUBE_CLIENT_ID to .env'}")
        lines.append(f"Instagram API : {'Connected' if self.instagram_token else 'Not configured - Add INSTAGRAM_ACCESS_TOKEN to .env'}")
        return "\n".join(lines)
