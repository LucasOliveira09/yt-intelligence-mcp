import logging
import re
from typing import Any, Dict, List, Optional
from googleapiclient.discovery import build
from src.auth import get_credentials, load_all_accounts

logger = logging.getLogger("yt_intelligence.video_deep_dive")


def _extract_video_id(video_url_or_id: str) -> str:
    cleaned = video_url_or_id.strip()
    if "v=" in cleaned:
        return cleaned.split("v=")[1].split("&")[0]
    if "youtu.be/" in cleaned:
        return cleaned.split("youtu.be/")[1].split("?")[0]
    if "shorts/" in cleaned:
        return cleaned.split("shorts/")[1].split("?")[0]
    return cleaned.split("/")[0]


def get_video_deep_dive(video_url_or_id: str) -> Dict[str, Any]:
    """
    Performs an exhaustive technical & strategic breakdown of any YouTube video.
    Extracts hidden tags, engagement rates, and mines audience questions from top comments.
    """
    video_id = _extract_video_id(video_url_or_id)
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    # Try to use any available authenticated credentials to get full API benefits
    accounts = load_all_accounts()
    service = None
    for alias in accounts:
        creds = get_credentials(alias)
        if creds:
            try:
                service = build("youtube", "v3", credentials=creds)
                break
            except Exception:
                continue

    if not service:
        # Fallback to pure public scraping via yt-dlp
        return _deep_dive_via_ytdlp(video_id, video_url)

    try:
        # 1. Video snippet & statistics
        v_res = service.videos().list(
            part="snippet,statistics,contentDetails,topicDetails",
            id=video_id,
        ).execute()

        items = v_res.get("items", [])
        if not items:
            return {"error": "VIDEO_NOT_FOUND", "video_id": video_id}

        v_data = items[0]
        snippet = v_data.get("snippet", {})
        statistics = v_data.get("statistics", {})
        topic_details = v_data.get("topicDetails", {})

        views = int(statistics.get("viewCount", 0))
        likes = int(statistics.get("likeCount", 0))
        comments_count = int(statistics.get("commentCount", 0))

        like_rate = round((likes / views * 100), 2) if views > 0 else 0.0
        comment_rate = round((comments_count / views * 100), 2) if views > 0 else 0.0

        # Tags and categories
        tags = snippet.get("tags") or []
        topics = [t.split("/")[-1].replace("_", " ") for t in topic_details.get("topicCategories", [])]

        # 2. Extract Top Comments and Audience Questions
        top_comments = []
        audience_questions = []

        try:
            c_res = service.commentThreads().list(
                part="snippet",
                videoId=video_id,
                order="relevance",
                maxResults=20,
            ).execute()

            for item in c_res.get("items", []):
                top_c = item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                author = top_c.get("authorDisplayName", "Anônimo")
                text = top_c.get("textDisplay", "").strip()
                like_count = int(top_c.get("likeCount", 0))

                top_comments.append({
                    "author": author,
                    "text": text,
                    "likes": like_count,
                })

                # Check if it's a question or unmet audience demand
                if "?" in text or any(k in text.lower() for k in ["como faz", "qual", "porque", "dúvida", "ensina"]):
                    audience_questions.append({
                        "author": author,
                        "question": text,
                        "likes": like_count,
                    })

        except Exception as e:
            logger.warning(f"Could not fetch comments for video {video_id}: {e}")

        # Sort audience questions by likes
        audience_questions.sort(key=lambda x: x["likes"], reverse=True)

        return {
            "video_id": video_id,
            "title": snippet.get("title"),
            "url": video_url,
            "channel_title": snippet.get("channelTitle"),
            "channel_id": snippet.get("channelId"),
            "published_at": snippet.get("publishedAt"),
            "duration": v_data.get("contentDetails", {}).get("duration"),
            "metricas_engajamento": {
                "views": views,
                "likes": likes,
                "comments": comments_count,
                "taxa_de_like_pct": like_rate,
                "taxa_de_comentarios_pct": comment_rate,
                "engajamento_geral": "ALTO" if like_rate >= 5.0 else ("MEDIO" if like_rate >= 2.5 else "BAIXO"),
            },
            "tags_reais_do_criador": tags,
            "topicos_do_algoritmo": topics,
            "duvidas_da_audiencia_para_novas_pautas": audience_questions[:8],
            "top_comentarios": top_comments[:10],
        }

    except Exception as e:
        logger.error(f"Error in deep dive for {video_id}: {e}")
        return _deep_dive_via_ytdlp(video_id, video_url)


def _deep_dive_via_ytdlp(video_id: str, video_url: str) -> Dict[str, Any]:
    """Fallback when no Google API token is available."""
    import yt_dlp
    from src.config import COOKIES_FILE

    ydl_opts: Any = {
        "extract_flat": True,
        "quiet": True,
        "no_warnings": True,
    }
    if COOKIES_FILE.exists():
        ydl_opts["cookiefile"] = str(COOKIES_FILE)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False)
            views = info.get("view_count") or 0
            likes = info.get("like_count") or 0
            return {
                "video_id": video_id,
                "title": info.get("title"),
                "url": video_url,
                "channel_title": info.get("channel") or info.get("uploader"),
                "published_at": info.get("upload_date"),
                "duration_seconds": info.get("duration"),
                "metricas_engajamento": {
                    "views": views,
                    "likes": likes,
                    "taxa_de_like_pct": round(likes / views * 100, 2) if views > 0 else 0.0,
                },
                "tags_reais_do_criador": info.get("tags") or [],
                "duvidas_da_audiencia_para_novas_pautas": [],
                "nota": "Para extração completa de dúvidas e comentários, conecte uma conta Google no MCP.",
            }
        except Exception as e:
            return {"error": str(e), "video_id": video_id}
