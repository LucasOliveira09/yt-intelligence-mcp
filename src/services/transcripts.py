import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional
import yt_dlp
from src.config import COOKIES_FILE, DATA_DIR

logger = logging.getLogger("yt_intelligence.transcripts")


def extract_transcript(video_url_or_id: str, lang: str = "pt") -> Dict[str, Any]:
    """
    Extracts transcript / subtitles from a YouTube video.
    Uses cookies.txt if available to bypass datacenter IP restrictions.
    """
    video_id = video_url_or_id.split("v=")[-1].split("&")[0].split("/")[-1]
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts: Any = {
        "skip_download": True,
        "writeautomaticsub": True,
        "writesubtitles": True,
        "subtitleslangs": [lang, "en", "pt-BR"],
        "quiet": True,
        "no_warnings": True,
    }

    if COOKIES_FILE.exists():
        ydl_opts["cookiefile"] = str(COOKIES_FILE)

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(video_url, download=False)
        except Exception as e:
            err_msg = str(e)
            if "Sign in to confirm" in err_msg or "bot" in err_msg.lower():
                return {
                    "video_id": video_id,
                    "error": "IP_BOT_RESTRICTION",
                    "message": (
                        "O YouTube bloqueou download de legendas/vídeo por IP de datacenter. "
                        "Para liberar transcrições sem cota, exporte seus cookies do YouTube e salve em data/cookies.txt."
                    ),
                    "transcript": "",
                }
            return {
                "video_id": video_id,
                "error": err_msg,
                "transcript": "",
            }

    subtitles = info.get("subtitles") or {}
    auto_subtitles = info.get("automatic_captions") or {}

    available_subs = subtitles or auto_subtitles
    if not available_subs:
        return {
            "video_id": video_id,
            "title": info.get("title"),
            "error": "NO_CAPTIONS_AVAILABLE",
            "message": "Nenhuma legenda ou transcrição automática encontrada para este vídeo.",
            "transcript": "",
        }

    return {
        "video_id": video_id,
        "title": info.get("title"),
        "available_languages": list(available_subs.keys()),
        "message": "Legendas identificadas com sucesso.",
    }
