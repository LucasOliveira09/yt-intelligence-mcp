import logging
from typing import Any, Dict, List, Optional
from googleapiclient.discovery import build
from src.auth import get_credentials

logger = logging.getLogger("yt_intelligence.owned")


def get_channel_overview(alias: str) -> Dict[str, Any]:
    """
    Fetches real-time channel statistics for an authenticated channel.
    Uses YouTube Data API v3 (1 unit of quota).
    """
    creds = get_credentials(alias)
    if not creds:
        return {
            "error": "ACCOUNT_NOT_AUTHENTICATED",
            "message": f"Conta '{alias}' não encontrada ou não autenticada. Use a CLI para conectar.",
        }

    try:
        service = build("youtube", "v3", credentials=creds)
        res = service.channels().list(
            part="snippet,statistics,contentDetails",
            mine=True,
        ).execute()

        items = res.get("items", [])
        if not items:
            return {"error": "NO_CHANNEL_FOUND", "message": "Nenhum canal associado a esta conta Google."}

        item = items[0]
        snippet = item.get("snippet", {})
        stats = item.get("statistics", {})
        uploads_playlist = item.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")

        # Fetch recent 10 videos from uploads playlist (1 quota unit)
        recent_videos = []
        if uploads_playlist:
            p_res = service.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist,
                maxResults=10,
            ).execute()
            for p_item in p_res.get("items", []):
                p_snippet = p_item.get("snippet", {})
                vid_id = p_snippet.get("resourceId", {}).get("videoId")
                recent_videos.append({
                    "id": vid_id,
                    "title": p_snippet.get("title"),
                    "published_at": p_snippet.get("publishedAt"),
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                })

        return {
            "alias": alias,
            "title": snippet.get("title"),
            "custom_url": snippet.get("customUrl"),
            "subscriber_count": int(stats.get("subscriberCount", 0)),
            "view_count": int(stats.get("viewCount", 0)),
            "video_count": int(stats.get("videoCount", 0)),
            "recent_videos": recent_videos,
        }
    except Exception as e:
        logger.error(f"Error fetching channel overview for {alias}: {e}")
        return {"error": str(e)}
