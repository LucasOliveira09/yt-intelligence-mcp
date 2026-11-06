import logging
from typing import Any, Dict, List, Optional
import urllib.parse
import yt_dlp
from src.config import COOKIES_FILE

logger = logging.getLogger("yt_intelligence.flexible_search")

# YouTube SP parameter lookup table
# Sort options
SORT_CODES = {
    "relevance": "",
    "upload_date": "CAISAhAB",
    "view_count": "CAMSAhAB",
    "rating": "CAESAhAB",
}

# Upload period options (when sort is relevance)
PERIOD_CODES = {
    "hour": "EgIIAQ%3D%3D",
    "today": "EgIIAg%3D%3D",
    "this_week": "EgIIAw%3D%3D",
    "this_month": "EgIIBA%3D%3D",
    "this_year": "EgIIBQ%3D%3D",
}

# Duration options
DURATION_CODES = {
    "short": "EgIYAQ%3D%3D",   # < 4 min
    "medium": "EgIYAw%3D%3D",  # 4 - 20 min
    "long": "EgIYAg%3D%3D",    # > 20 min
}

# Content type options
TYPE_CODES = {
    "video": "EgIQAQ%3D%3D",
    "channel": "EgIQAg%3D%3D",
    "playlist": "EgIQAw%3D%3D",
}


def _build_search_url(
    query: str,
    sort_by: str = "relevance",
    upload_period: Optional[str] = None,
    duration: Optional[str] = None,
    content_type: str = "video",
) -> str:
    encoded_query = urllib.parse.quote_plus(query)
    base_url = f"https://www.youtube.com/results?search_query={encoded_query}"

    # Determine SP parameter
    sp = ""
    # Combined Sort by View Count + Upload Period
    if sort_by == "view_count" and upload_period:
        if upload_period == "this_week":
            sp = "CAMSAhABEgIIAw%3D%3D"
        elif upload_period == "this_month":
            sp = "CAMSAhABEgIIBA%3D%3D"
        elif upload_period == "this_year":
            sp = "CAMSAhABEgIIBQ%3D%3D"
        elif upload_period == "today":
            sp = "CAMSAhABEgIIAg%3D%3D"
        else:
            sp = SORT_CODES.get("view_count", "")
    elif sort_by in SORT_CODES and SORT_CODES[sort_by]:
        sp = SORT_CODES[sort_by]
    elif upload_period in PERIOD_CODES:
        sp = PERIOD_CODES[upload_period]
    elif duration in DURATION_CODES:
        sp = DURATION_CODES[duration]
    elif content_type in TYPE_CODES and content_type != "video":
        sp = TYPE_CODES[content_type]

    if sp:
        return f"{base_url}&sp={sp}"
    return base_url


def _format_duration(seconds: Optional[int]) -> str:
    if not seconds:
        return "N/A"
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def search_youtube_flexible(
    query: str,
    sort_by: str = "relevance",
    upload_period: Optional[str] = None,
    duration: Optional[str] = None,
    content_type: str = "video",
    min_views: Optional[int] = None,
    max_views: Optional[int] = None,
    exclude_shorts: bool = False,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Versatile, filter-rich YouTube search engine without API quota limitations.
    Allows searching by recency, view count, length, channel vs video, and audience size.
    """
    url = _build_search_url(
        query=query,
        sort_by=sort_by,
        upload_period=upload_period,
        duration=duration,
        content_type=content_type,
    )

    fetch_limit = limit * 2 if (min_views or max_views or exclude_shorts) else limit

    ydl_opts: Any = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "playlistend": fetch_limit,
    }
    if COOKIES_FILE.exists():
        ydl_opts["cookiefile"] = str(COOKIES_FILE)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            logger.error(f"Search failed for '{query}' at {url}: {e}")
            return {"error": str(e), "query": query, "url": url, "results": []}

    raw_entries = (info.get("entries") if info else []) or []
    cleaned_results = []

    for entry in raw_entries:
        if not entry:
            continue

        v_id = entry.get("id")
        title = entry.get("title")
        views = entry.get("view_count")
        dur = entry.get("duration")

        # Exclude shorts (duration <= 60 seconds)
        if exclude_shorts and dur and dur <= 60:
            continue

        # View count thresholds
        if min_views is not None and (views is None or views < min_views):
            continue
        if max_views is not None and (views is not None and views > max_views):
            continue

        thumbnails = entry.get("thumbnails") or []
        thumb_url = thumbnails[-1]["url"] if thumbnails else None

        cleaned_results.append({
            "id": v_id,
            "title": title,
            "url": entry.get("url") or (f"https://www.youtube.com/watch?v={v_id}" if v_id else None),
            "uploader": entry.get("uploader") or entry.get("channel"),
            "uploader_url": entry.get("uploader_url"),
            "view_count": views,
            "views_formatted": f"{views:,}" if views is not None else "N/A",
            "duration_seconds": dur,
            "duration_formatted": _format_duration(dur),
            "thumbnail": thumb_url,
        })

        if len(cleaned_results) >= limit:
            break

    return {
        "query": query,
        "filtros_aplicados": {
            "ordenacao": sort_by,
            "periodo": upload_period or "todos",
            "duracao": duration or "qualquer",
            "tipo": content_type,
            "min_views": min_views,
            "max_views": max_views,
            "excluir_shorts": exclude_shorts,
        },
        "url_da_busca": url,
        "total_encontrado": len(cleaned_results),
        "resultados": cleaned_results,
    }
