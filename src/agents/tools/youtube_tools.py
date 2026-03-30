import os
import requests
from crewai.tools import tool

@tool("Search YouTube Trends")
def search_youtube_trends(query: str, max_results: int = 5) -> str:
    """Uses the YouTube Data API to search for currently trending topics and videos related to a specific query. Requires YOUTUBE_API_KEY in .env."""
    api_key = os.getenv("YOUTUBE_API_KEY")
    if not api_key:
        return "Error: YOUTUBE_API_KEY not configured in .env."

    try:
        url = "https://www.googleapis.com/youtube/v3/search"
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",
            "order": "viewCount", # Find what's getting views right now
            "maxResults": max_results,
            "key": api_key,
            "regionCode": "IN" # Default to India for Ajay
        }

        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        trends = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            title = snippet.get("title", "No Title")
            channel = snippet.get("channelTitle", "Unknown Channel")
            desc = snippet.get("description", "")
            trends.append(f"- **{title}** (by {channel}): {desc[:100]}...")

        return "Trending YouTube Videos:\n" + "\n".join(trends) if trends else "No trending videos found."

    except Exception as e:
        return f"Error fetching YouTube trends: {e}"

@tool("Upload Video to YouTube")
def upload_to_youtube(video_path: str, title: str, description: str, tags: str) -> str:
    """
    Uploads a local .mp4 video file to YouTube.
    Requires OAuth 2.0 credentials (`client_secrets.json`) configured for the YouTube Data API v3.
    Provide the path to the video, title, description, and comma-separated tags.
    """
    import google.oauth2.credentials
    import google_auth_oauthlib.flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    if not os.path.exists(video_path):
        return f"Error: Video file '{video_path}' not found."

    # The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
    # the OAuth 2.0 information for this application.
    CLIENT_SECRETS_FILE = "client_secrets.json"
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return "Error: YouTube OAuth `client_secrets.json` not found in the root directory. You must download it from the Google Cloud Console."

    # This OAuth 2.0 access scope allows for full read/write access to the authenticated user's account and requires requests to use an SSL connection.
    SCOPES = ['https://www.googleapis.com/auth/youtube.upload']
    API_SERVICE_NAME = 'youtube'
    API_VERSION = 'v3'

    try:
        # Get credentials and create an API client
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
        # Note: In a headless environment like Render, run_console is needed, or we must use a refresh token mechanism.
        # For this tool, we assume the user has pre-authenticated and saved the token, or we are running locally.
        credentials = flow.run_local_server(port=0)
        youtube = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)

        tags_list = [tag.strip() for tag in tags.split(",") if tag.strip()]

        body=dict(
            snippet=dict(
                title=title,
                description=description,
                tags=tags_list,
                categoryId="22" # 22 = People & Blogs
            ),
            status=dict(
                privacyStatus="unlisted" # Always unlisted first so Ajay can review it before publishing
            )
        )

        insert_request = youtube.videos().insert(
            part=",".join(body.keys()),
            body=body,
            media_body=MediaFileUpload(video_path, chunksize=-1, resumable=True)
        )

        response = insert_request.execute()
        return f"Video successfully uploaded to YouTube! Unlisted URL: https://youtu.be/{response['id']}"

    except HttpError as e:
        return f"YouTube API Error: {e}"
    except Exception as e:
        return f"Unexpected Error uploading to YouTube: {e}"
