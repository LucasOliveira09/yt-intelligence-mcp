import logging
from pathlib import Path
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List
from src.config import COOKIES_FILE, DATA_DIR

logger = logging.getLogger("yt_intelligence.video_vision")


def _format_timestamp(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _run_tesseract(image_path: Path) -> str:
    """Runs local Tesseract OCR on extracted frame to capture on-screen text/code."""
    try:
        res = subprocess.run(
            ["/usr/bin/tesseract", str(image_path), "stdout", "--psm", "11", "-l", "por+eng"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return res.stdout.strip()
    except Exception as e:
        logger.warning(f"OCR failed for {image_path}: {e}")
        return ""


def inspect_video_visuals(
    video_source: str,
    interval_seconds: int = 45,
    max_frames: int = 12,
) -> Dict[str, Any]:
    """
    Downloads low-res video stream, extracts key visual frames at regular intervals,
    runs OCR on each frame, and prepares the visual timeline for AI inspection.
    Enforces immediate deletion of temporary video files to protect VPS disk space.
    """
    is_url = video_source.startswith("http://") or video_source.startswith("https://")
    scratch_dir = Path(tempfile.mkdtemp(prefix="yt_vision_"))

    video_file_path = None
    try:
        if is_url:
            if not COOKIES_FILE.exists():
                return {
                    "error": "COOKIES_REQUIRED_FOR_VIDEO_STREAM",
                    "message": (
                        "O YouTube bloqueia download direto de vídeo em IPs de datacenter (Oracle Cloud). "
                        "Para permitir que eu enxergue a tela de vídeos do YouTube, salve seus cookies em "
                        f"{COOKIES_FILE}. Vídeos locais na VPS funcionam normalmente sem cookies."
                    ),
                }

            video_file_path = scratch_dir / "stream_temp.mp4"
            # Download lowest viable resolution (360p/480p) to minimize bandwidth and disk
            cmd = [
                "/home/ubuntu/yt-intelligence-mcp/.venv/bin/yt-dlp",
                "--cookiefile", str(COOKIES_FILE),
                "-f", "worst[ext=mp4]/worst",
                "--no-playlist",
                "-o", str(video_file_path),
                video_source,
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if res.returncode != 0 or not video_file_path.exists():
                return {
                    "error": "DOWNLOAD_FAILED",
                    "message": f"Falha ao baixar stream para análise visual: {res.stderr[:300]}",
                }
        else:
            video_file_path = Path(video_source)
            if not video_file_path.exists():
                return {"error": "FILE_NOT_FOUND", "message": f"Arquivo local não encontrado: {video_source}"}

        # Extract frames with FFmpeg
        frames_dir = scratch_dir / "frames"
        frames_dir.mkdir(exist_ok=True)

        ffmpeg_cmd = [
            "/usr/bin/ffmpeg",
            "-y",
            "-i", str(video_file_path),
            "-vf", f"fps=1/{interval_seconds}",
            "-vframes", str(max_frames),
            "-q:v", "3",
            str(frames_dir / "frame_%03d.jpg"),
        ]
        f_res = subprocess.run(ffmpeg_cmd, capture_output=True, text=True, timeout=90)
        if f_res.returncode != 0:
            return {"error": "FFMPEG_FAILED", "message": f"Erro na extração de frames: {f_res.stderr[:300]}"}

        # Delete the video file immediately after frame extraction (VPS hygiene)
        if is_url and video_file_path.exists():
            video_file_path.unlink()

        # Process extracted frames
        frame_files = sorted(frames_dir.glob("frame_*.jpg"))
        timeline = []

        for i, frame_p in enumerate(frame_files):
            t_sec = i * interval_seconds
            ocr_text = _run_tesseract(frame_p)
            timeline.append({
                "frame_index": i + 1,
                "timestamp_seconds": t_sec,
                "timestamp_formatted": _format_timestamp(t_sec),
                "frame_path": str(frame_p),
                "texto_na_tela_ocr": ocr_text[:500] if ocr_text else "(Nenhum texto detectado)",
            })

        return {
            "source": video_source,
            "intervalo_segundos": interval_seconds,
            "total_frames_analisados": len(timeline),
            "timeline_visual": timeline,
            "nota": "Os frames foram salvos temporariamente na VPS com OCR extraído para análise visual do agente.",
        }

    except Exception as e:
        logger.error(f"Error inspecting video visuals: {e}")
        return {"error": str(e), "source": video_source}
