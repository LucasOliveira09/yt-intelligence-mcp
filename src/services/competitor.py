import logging
from typing import Any, Dict, List, Optional
import yt_dlp
from src.config import COOKIES_FILE

logger = logging.getLogger("yt_intelligence.competitor")


def normalize_channel_url(target: str) -> str:
    """Normalizes handles, custom URLs, and direct links to YouTube channel /videos URL."""
    target = target.strip()
    if target.startswith("http://") or target.startswith("https://"):
        url = target.rstrip("/")
        if not (url.endswith("/videos") or url.endswith("/shorts") or url.endswith("/streams")):
            url += "/videos"
        return url
    
    if not target.startswith("@"):
        target = f"@{target}"
    return f"https://www.youtube.com/{target}/videos"


def fetch_channel_videos(
    channel_target: str,
    limit: int = 30,
) -> Dict[str, Any]:
    """
    Fetches channel metadata and recent videos using yt-dlp flat-playlist extraction.
    Consumes ZERO Google Cloud API quota.
    """
    url = normalize_channel_url(channel_target)

    ydl_opts: Any = {
        "extract_flat": "in_playlist",
        "playlistend": limit,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }

    if COOKIES_FILE.exists():
        ydl_opts["cookiefile"] = str(COOKIES_FILE)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            logger.error(f"Failed to extract info from {url}: {e}")
            return {
                "error": str(e),
                "channel": channel_target,
                "url": url,
                "videos": [],
            }

    if not info:
        return {
            "error": "No data returned for channel",
            "channel": channel_target,
            "url": url,
            "videos": [],
        }

    raw_entries = info.get("entries") or []
    cleaned_videos = []

    for entry in raw_entries:
        if not entry:
            continue
        video_id = entry.get("id")
        title = entry.get("title")
        view_count = entry.get("view_count")
        duration = entry.get("duration")

        # Pick best thumbnail
        thumbnails = entry.get("thumbnails") or []
        thumb_url = thumbnails[-1]["url"] if thumbnails else None

        cleaned_videos.append({
            "id": video_id,
            "title": title,
            "url": f"https://www.youtube.com/watch?v={video_id}" if video_id else None,
            "view_count": view_count,
            "duration": duration,
            "thumbnail": thumb_url,
            "channel": info.get("channel") or info.get("uploader"),
            "channel_id": info.get("channel_id"),
        })

    return {
        "channel_title": info.get("channel") or info.get("uploader") or channel_target,
        "channel_id": info.get("channel_id"),
        "channel_url": info.get("channel_url") or url,
        "followers_count": info.get("channel_follower_count"),
        "total_channel_videos": info.get("playlist_count"),
        "fetched_count": len(cleaned_videos),
        "videos": cleaned_videos,
    }


def search_youtube_videos(
    query: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Searches YouTube videos by query (Zero Quota).
    """
    ydl_opts: Any = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
    }

    if COOKIES_FILE.exists():
        ydl_opts["cookiefile"] = str(COOKIES_FILE)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
        except Exception as e:
            logger.error(f"Failed to search YouTube for '{query}': {e}")
            return []

    entries = (info.get("entries") if info else []) or []
    results = []
    for entry in entries:
        if not entry:
            continue
        results.append({
            "id": entry.get("id"),
            "title": entry.get("title"),
            "url": entry.get("url") or (f"https://www.youtube.com/watch?v={entry.get('id')}" if entry.get("id") else None),
            "uploader": entry.get("uploader"),
            "channel": entry.get("channel"),
            "view_count": entry.get("view_count"),
            "duration": entry.get("duration"),
        })

    return results
