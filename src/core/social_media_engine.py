"""
social_media_engine.py
======================
Aisha's Social Media Command Center.
One-account-first compatible, then scalable to multi-account.
"""

import os
import logging

log = logging.getLogger("Aisha.SocialMedia")


class SocialMediaEngine:
    """
    Unified social media manager.
    Supports channel-specific credentials and a generic single-account fallback.
    """

    CHANNEL_TO_ENV = {
        "Story With Aisha": {
            "instagram_token": "INSTAGRAM_TOKEN_STORY_WITH_AISHA",
            "instagram_biz": "INSTAGRAM_BIZ_ID_STORY_WITH_AISHA",
            "youtube_token": "youtube_token_Story_With_Aisha.json",
        },
        "Riya's Dark Whisper": {
            "instagram_token": "INSTAGRAM_TOKEN_RIYAS_DARK_WHISPER",
            "instagram_biz": "INSTAGRAM_BIZ_ID_RIYAS_DARK_WHISPER",
            "youtube_token": "youtube_token_Riyas_Dark_Whisper.json",
        },
        "Riya's Dark Romance Library": {
            "instagram_token": "INSTAGRAM_TOKEN_RIYAS_DARK_LIBRARY",
            "instagram_biz": "INSTAGRAM_BIZ_ID_RIYAS_DARK_LIBRARY",
            "youtube_token": "youtube_token_Riyas_Dark_Romance_Library.json",
        },
        "Aisha & Him": {
            "instagram_token": "INSTAGRAM_TOKEN_AISHA_AND_HIM",
            "instagram_biz": "INSTAGRAM_BIZ_ID_AISHA_AND_HIM",
            "youtube_token": "youtube_token_Aisha_Him.json",
        },
    }

    def __init__(self):
        self.youtube_client_id = os.getenv("YOUTUBE_CLIENT_ID")
        self.youtube_client_secret = os.getenv("YOUTUBE_CLIENT_SECRET")

    def _get_instagram_creds(self, channel: str) -> tuple[str, str]:
        mapping = self.CHANNEL_TO_ENV.get(channel, {})
        token = os.getenv(mapping.get("instagram_token", ""), "")
        biz_id = os.getenv(mapping.get("instagram_biz", ""), "")

        # One-account fallback
        if not token:
            token = os.getenv("INSTAGRAM_ACCESS_TOKEN", "")
        if not biz_id:
            biz_id = os.getenv("INSTAGRAM_BUSINESS_ID", "")

        return token, biz_id

    def _get_youtube_token_file(self, channel: str) -> str:
        mapping = self.CHANNEL_TO_ENV.get(channel, {})
        preferred = mapping.get("youtube_token", "")
        if preferred and os.path.exists(preferred):
            return preferred

        # One-account fallback token names
        for candidate in ["youtube_token_default.json", "youtube_token.json"]:
            if os.path.exists(candidate):
                return candidate

        return preferred or "youtube_token_default.json"

    def post_instagram_reel(self, video_url: str, caption: str, hashtags: list | None = None, channel: str = "Story With Aisha") -> dict:
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

            return {"success": True, "post_id": publish_resp.get("id")}
        except Exception as e:
            log.error(f"[Instagram] Reel post failed: {e}")
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
    ) -> dict:
        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build
            from googleapiclient.http import MediaFileUpload

            creds_path = self._get_youtube_token_file(channel_name)
            if not os.path.exists(creds_path):
                return {
                    "success": False,
                    "error": f"No YouTube OAuth token found for '{channel_name}'. Expected: {creds_path}",
                }

            creds = Credentials.from_authorized_user_file(creds_path)
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
            return {"success": True, "video_id": video_id, "url": f"https://youtube.com/watch?v={video_id}"}

        except ImportError:
            return {"success": False, "error": "Install: pip install google-api-python-client google-auth"}
        except Exception as e:
            log.error(f"[YouTube] Upload failed: {e}")
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
        yt_token_file = self._get_youtube_token_file(channel)

        lines = ["=== Social Media Status ==="]
        lines.append(f"Channel       : {channel}")
        lines.append(f"YouTube API   : {'Connected' if self.youtube_client_id else 'Missing YOUTUBE_CLIENT_ID'}")
        lines.append(f"YouTube OAuth : {'Found' if os.path.exists(yt_token_file) else f'Missing token file ({yt_token_file})'}")
        lines.append(f"Instagram API : {'Connected' if (ig_token and ig_biz) else 'Missing INSTAGRAM_ACCESS_TOKEN / INSTAGRAM_BUSINESS_ID'}")
        return "\n".join(lines)
