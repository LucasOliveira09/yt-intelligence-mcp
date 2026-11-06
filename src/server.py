from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from src.analytics.outliers import analyze_outliers
from src.auth import load_all_accounts
from src.config import DEFAULT_COMPETITOR_LIMIT, DEFAULT_OUTLIER_THRESHOLD
from src.services.competitor import fetch_channel_videos, search_youtube_videos
from src.services.owned import get_channel_overview
from src.services.transcripts import extract_transcript

mcp = FastMCP("yt-intelligence", dependencies=["yt-dlp", "google-api-python-client"])


@mcp.tool()
def yt_analyze_competitor(
    channel: str,
    limit: int = DEFAULT_COMPETITOR_LIMIT,
    threshold: float = DEFAULT_OUTLIER_THRESHOLD,
) -> Dict[str, Any]:
    """
    Analisa os vídeos recentes de um canal concorrente no YouTube.
    Calcula a mediana de visualizações do canal e identifica os vídeos que furaram a bolha (outliers).
    Zero consumo de cota da API oficial do Google.
    """
    channel_data = fetch_channel_videos(channel, limit=limit)
    if channel_data.get("error"):
        return {"error": channel_data["error"], "channel": channel}

    videos = channel_data.get("videos", [])
    analysis = analyze_outliers(videos, threshold=threshold)

    return {
        "channel_title": channel_data.get("channel_title"),
        "channel_url": channel_data.get("channel_url"),
        "followers_count": channel_data.get("followers_count"),
        "sample_size": analysis["sample_size"],
        "median_views": analysis["median_views"],
        "mean_views": analysis["mean_views"],
        "outliers_count": analysis["outliers_count"],
        "outliers": analysis["outliers"],
    }


@mcp.tool()
def yt_detect_outliers(
    channel: str,
    limit: int = 30,
    threshold: float = 2.0,
) -> List[Dict[str, Any]]:
    """
    Retorna apenas a lista filtrada de vídeos outliers de um canal (vídeos com performance >= threshold da mediana).
    Ideal para engenharia reversa de títulos e pautas que performaram acima da média.
    """
    channel_data = fetch_channel_videos(channel, limit=limit)
    videos = channel_data.get("videos", [])
    analysis = analyze_outliers(videos, threshold=threshold)
    return analysis.get("outliers", [])


@mcp.tool()
def yt_compare_competitors(
    channels: List[str],
    limit_per_channel: int = 20,
) -> List[Dict[str, Any]]:
    """
    Compara múltiplos canais concorrentes lado a lado.
    Retorna inscritos, mediana de views e o maior outlier de cada canal.
    """
    comparison = []
    for ch in channels:
        ch_data = fetch_channel_videos(ch, limit=limit_per_channel)
        if ch_data.get("error"):
            comparison.append({"channel": ch, "error": ch_data["error"]})
            continue

        analysis = analyze_outliers(ch_data.get("videos", []))
        top_outlier = analysis["outliers"][0] if analysis["outliers"] else None

        comparison.append({
            "channel": ch_data.get("channel_title") or ch,
            "followers": ch_data.get("followers_count"),
            "median_views": analysis["median_views"],
            "sample_size": analysis["sample_size"],
            "top_outlier": {
                "title": top_outlier["title"],
                "views": top_outlier["view_count"],
                "multiplier": top_outlier["multiplier"],
                "url": top_outlier["url"],
            } if top_outlier else None,
        })
    return comparison


@mcp.tool()
def yt_search_trends(
    query: str,
    limit: int = 15,
) -> List[Dict[str, Any]]:
    """
    Busca vídeos no YouTube sobre um nicho ou pauta sem gastar cota de API.
    """
    return search_youtube_videos(query, limit=limit)


@mcp.tool()
def yt_get_video_transcript(
    video_url_or_id: str,
    lang: str = "pt",
) -> Dict[str, Any]:
    """
    Tenta extrair transcrição / legendas de um vídeo do YouTube.
    """
    return extract_transcript(video_url_or_id, lang=lang)


@mcp.tool()
def yt_list_my_channels() -> List[Dict[str, Any]]:
    """
    Lista as contas próprias do YouTube cadastradas e autenticadas via OAuth2.
    """
    accounts = load_all_accounts()
    return [
        {
            "alias": alias,
            "channel_title": data.get("channel_title"),
            "channel_id": data.get("channel_id"),
        }
        for alias, data in accounts.items()
    ]


@mcp.tool()
def yt_my_channel_overview(account_alias: str) -> Dict[str, Any]:
    """
    Puxa visão geral de métricas de uma conta própria autenticada (inscritos, views totais, vídeos recentes).
    """
    return get_channel_overview(account_alias)


if __name__ == "__main__":
    mcp.run()
