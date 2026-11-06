from typing import Any, Dict, List, Optional
from mcp.server.fastmcp import FastMCP
from src.analytics.outliers import analyze_outliers
from src.auth import load_all_accounts
from src.config import DEFAULT_COMPETITOR_LIMIT, DEFAULT_OUTLIER_THRESHOLD
from src.services.competitor import fetch_channel_videos, search_youtube_videos
from src.services.niche_radar import scan_niche_radar
from src.services.owned import get_channel_overview
from src.services.owned_analytics import fetch_channel_health_report
from src.services.transcripts import extract_transcript
from src.services.video_deep_dive import get_video_deep_dive
from src.services.video_vision import inspect_video_visuals

mcp = FastMCP("yt-intelligence", dependencies=["yt-dlp", "google-api-python-client"])


# ==========================================
# 1. GESTÃO E AUDITORIA DE CANAIS PRÓPRIOS
# ==========================================

@mcp.tool()
def yt_list_my_channels() -> List[Dict[str, Any]]:
    """
    Lista todas as contas próprias do YouTube autenticadas via OAuth2 no servidor.
    Exibe alias (ex: canal_dev, galuzera), nome do canal e channel_id.
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
    Retorna métricas em tempo real de um canal próprio autenticado: total de inscritos,
    visualizações acumuladas, total de vídeos e últimos uploads.
    """
    return get_channel_overview(account_alias)


@mcp.tool()
def yt_channel_audit_report(account_alias: str, days: int = 30) -> Dict[str, Any]:
    """
    Gera um relatório de auditoria e diagnóstico estratégico do canal próprio nos últimos N dias.
    Avalia retenção média, conversão de inscritos, fontes de tráfego (Busca vs Sugeridos/Home)
    e prescreve um plano de ação para melhorar as próximas publicações.
    """
    return fetch_channel_health_report(account_alias, days=days)


# ==========================================
# 2. RAIO-X PROFUNDO DE VÍDEOS
# ==========================================

@mcp.tool()
def yt_video_deep_dive(video_url_or_id: str) -> Dict[str, Any]:
    """
    Executa um Raio-X completo em qualquer vídeo do YouTube (próprio ou concorrente).
    Extrai:
    - Tags reais ocultas cadastradas pelo criador.
    - Taxa de like e taxa de comentários (nível real de engajamento).
    - Tópicos classificados pelo algoritmo do YouTube.
    - Mineração de dúvidas da audiência nos comentários (ideias de conteúdo que o concorrente deixou passar).
    """
    return get_video_deep_dive(video_url_or_id)


@mcp.tool()
def yt_get_video_transcript(video_url_or_id: str, lang: str = "pt") -> Dict[str, Any]:
    """
    Extrai a transcrição/legendas de um vídeo do YouTube para dissecação de roteiro e estrutura de gancho.
    """
    return extract_transcript(video_url_or_id, lang=lang)


@mcp.tool()
def yt_inspect_video_visuals(
    video_source: str,
    interval_seconds: int = 45,
    max_frames: int = 12,
) -> Dict[str, Any]:
    """
    Inspeciona visualmente o que aparece na tela do vídeo (slides, código no editor, gráficos, telas).
    Extrai frames-chave com FFmpeg, roda OCR com Tesseract para ler o texto da tela,
    e disponibiliza os frames para análise visual detalhada da IA.
    Suporta arquivo local na VPS ou URL do YouTube (requer cookies.txt na VPS para streams do YouTube).
    """
    return inspect_video_visuals(video_source, interval_seconds=interval_seconds, max_frames=max_frames)


# ==========================================
# 3. INTELIGÊNCIA DE CONCORRÊNCIA & OUTLIERS (ZERO COTA)
# ==========================================

@mcp.tool()
def yt_analyze_competitor(
    channel: str,
    limit: int = DEFAULT_COMPETITOR_LIMIT,
    threshold: float = DEFAULT_OUTLIER_THRESHOLD,
) -> Dict[str, Any]:
    """
    Analisa os vídeos recentes de um canal concorrente no YouTube.
    Calcula a mediana de visualizações e identifica os vídeos que furaram a bolha (outliers).
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
    Retorna apenas a lista filtrada de vídeos outliers de um canal (performance >= threshold da mediana).
    Essencial para modelagem de títulos, ganchos e temas com tração comprovada.
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
    Compara base de inscritos, mediana de views e o principal vídeo outlier de cada criador.
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


# ==========================================
# 4. RADAR DE NICHOS E TENDÊNCIAS
# ==========================================

@mcp.tool()
def yt_niche_radar(topic: str, sample_size: int = 25) -> Dict[str, Any]:
    """
    Escaneia um nicho ou termo de busca no YouTube.
    Identifica:
    - Canais dominantes no topo das buscas.
    - Termos-chave e palavras mais repetidas nos títulos com alta performance.
    - Duração média ideal dos vídeos para reter o público desse nicho.
    - Padrão de formato recomendado (rápido, médio ou long-form).
    """
    return scan_niche_radar(topic, sample_size=sample_size)


@mcp.tool()
def yt_search_trends(query: str, limit: int = 15) -> List[Dict[str, Any]]:
    """
    Busca rápida de vídeos recentes no YouTube sobre um tópico sem gastar cota de API.
    """
    return search_youtube_videos(query, limit=limit)


if __name__ == "__main__":
    mcp.run()
