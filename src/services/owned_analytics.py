from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional
from googleapiclient.discovery import build
from src.auth import get_credentials

logger = logging.getLogger("yt_intelligence.owned_analytics")

# Traffic source mappings
TRAFFIC_SOURCE_NAMES = {
    "YT_SEARCH": "Busca do YouTube (SEO)",
    "RELATED_VIDEO": "Vídeos Sugeridos (Recomendação Lateral/Final)",
    "SUBSCRIBER": "Feed de Inscrições",
    "YT_OTHER_PAGE": "Outras Páginas do YouTube",
    "BROWSE_USERS": "Recursos de Navegação (Página Inicial/Home)",
    "EXT_URL": "Fontes Externas (Google, WhatsApp, Discord, etc.)",
    "PLAYLIST": "Playlists",
    "END_SCREEN": "Telas Finais",
    "CARD": "Cards Interativos",
    "SHORTS": "Feed do YouTube Shorts",
}


def _diagnose_channel_health(
    avg_retention_pct: float,
    traffic_sources: List[Dict[str, Any]],
    sub_conversion_rate: float,
) -> Dict[str, Any]:
    """Generates sharp, actionable diagnostic insights based on real analytics numbers."""
    strengths = []
    bottlenecks = []
    actions = []

    # Retention diagnosis
    if avg_retention_pct >= 50.0:
        strengths.append(f"Retenção média excelente ({avg_retention_pct:.1f}%). O conteúdo segura a audiência.")
    elif avg_retention_pct >= 35.0:
        strengths.append(f"Retenção sólida ({avg_retention_pct:.1f}%), dentro da média saudável para vídeos longos.")
    else:
        bottlenecks.append(f"Retenção média baixa ({avg_retention_pct:.1f}%). A audiência está abandonando cedo.")
        actions.append("Corte os primeiros 15s de enrolação nos próximos vídeos. Vá direto ao cerne da promessa do título.")

    # Traffic source distribution
    total_views = sum(s.get("views", 0) for s in traffic_sources) or 1
    browse_pct = sum(s.get("views", 0) for s in traffic_sources if s.get("raw_type") in ("BROWSE_USERS", "RELATED_VIDEO")) / total_views * 100
    search_pct = sum(s.get("views", 0) for s in traffic_sources if s.get("raw_type") == "YT_SEARCH") / total_views * 100

    if browse_pct >= 40.0:
        strengths.append(f"Boa tração algorítmica: {browse_pct:.1f}% das visualizações vêm da Home e Sugeridos.")
    elif search_pct >= 60.0:
        bottlenecks.append(f"Dependência excessiva de Busca ({search_pct:.1f}%). O algoritmo não está recomendando ativamente seu canal na Home dos usuários.")
        actions.append("Trabalhe temas com curiosidade e tensão narrativa em vez de apenas tutoriais utilitários (busca).")

    # Subscriber conversion
    if sub_conversion_rate >= 1.5:
        strengths.append(f"Alta taxa de conversão em inscritos ({sub_conversion_rate:.2f}% dos espectadores se inscrevem).")
    elif sub_conversion_rate < 0.5:
        bottlenecks.append(f"Baixa conversão em inscritos ({sub_conversion_rate:.2f}%). As pessoas assistem mas não fixam no canal.")
        actions.append("Insira um gancho de retenção no meio do vídeo apontando para um benefício futuro exclusivo para inscritos.")

    return {
        "pontos_fortes": strengths,
        "gargalos_atuais": bottlenecks,
        "plano_de_acao_imediato": actions,
    }


def fetch_channel_health_report(alias: str, days: int = 30) -> Dict[str, Any]:
    """
    Pulls complete analytics report for an authenticated channel using YouTube Analytics API.
    Evaluates retention, traffic source breakdowns, subscriber velocity, and growth bottlenecks.
    """
    creds = get_credentials(alias)
    if not creds:
        return {
            "error": "ACCOUNT_NOT_AUTHENTICATED",
            "message": f"Conta '{alias}' não conectada via OAuth. Use 'python -m src.cli add-account {alias}' na VPS.",
        }

    try:
        data_service = build("youtube", "v3", credentials=creds)
        analytics_service = build("youtubeAnalytics", "v2", credentials=creds)

        # 1. Channel identity
        ch_res = data_service.channels().list(part="snippet,statistics", mine=True).execute()
        items = ch_res.get("items", [])
        if not items:
            return {"error": "NO_CHANNEL_FOUND", "message": "Nenhum canal associado."}

        snippet = items[0]["snippet"]
        statistics = items[0]["statistics"]
        channel_title = snippet["title"]

        # Date calculations
        end_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")

        # 2. Macro performance report
        macro_res = analytics_service.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched,averageViewDuration,averageViewPercentage,subscribersGained,subscribersLost",
        ).execute()

        macro_rows = macro_res.get("rows") or [[]]
        macro_data = macro_rows[0] if macro_rows else []
        
        total_views = int(macro_data[0]) if len(macro_data) > 0 and macro_data[0] is not None else 0
        minutes_watched = int(macro_data[1]) if len(macro_data) > 1 and macro_data[1] is not None else 0
        avg_view_duration_sec = int(macro_data[2]) if len(macro_data) > 2 and macro_data[2] is not None else 0
        avg_retention_pct = round(float(macro_data[3]), 2) if len(macro_data) > 3 and macro_data[3] is not None else 0.0
        subs_gained = int(macro_data[4]) if len(macro_data) > 4 and macro_data[4] is not None else 0
        subs_lost = int(macro_data[5]) if len(macro_data) > 5 and macro_data[5] is not None else 0
        net_subs = subs_gained - subs_lost
        sub_conversion_rate = round((subs_gained / total_views * 100), 2) if total_views > 0 else 0.0

        # 3. Traffic sources breakdown
        traffic_sources = []
        try:
            ts_res = analytics_service.reports().query(
                ids="channel==MINE",
                startDate=start_date,
                endDate=end_date,
                dimensions="insightTrafficSourceType",
                metrics="views,estimatedMinutesWatched",
                sort="-views",
            ).execute()

            for row in ts_res.get("rows") or []:
                raw_type = row[0]
                ts_views = int(row[1])
                pct = round((ts_views / total_views * 100), 1) if total_views > 0 else 0.0
                traffic_sources.append({
                    "raw_type": raw_type,
                    "name": TRAFFIC_SOURCE_NAMES.get(raw_type, raw_type),
                    "views": ts_views,
                    "percentage": pct,
                })
        except Exception as e:
            logger.warning(f"Could not fetch traffic sources for {alias}: {e}")

        # 4. Top videos in period
        top_videos = []
        try:
            vid_res = analytics_service.reports().query(
                ids="channel==MINE",
                startDate=start_date,
                endDate=end_date,
                dimensions="video",
                metrics="views,estimatedMinutesWatched,averageViewPercentage,subscribersGained",
                sort="-views",
                maxResults=8,
            ).execute()

            video_ids = [r[0] for r in vid_res.get("rows") or []]
            title_map = {}
            if video_ids:
                v_data = data_service.videos().list(part="snippet", id=",".join(video_ids)).execute()
                for v_item in v_data.get("items", []):
                    title_map[v_item["id"]] = v_item["snippet"]["title"]

            for r in vid_res.get("rows") or []:
                v_id = r[0]
                top_videos.append({
                    "video_id": v_id,
                    "title": title_map.get(v_id, f"Video {v_id}"),
                    "url": f"https://www.youtube.com/watch?v={v_id}",
                    "views": int(r[1]),
                    "minutes_watched": int(r[2]),
                    "retention_pct": round(float(r[3]), 1) if r[3] is not None else 0.0,
                    "subs_gained": int(r[4]),
                })
        except Exception as e:
            logger.warning(f"Could not fetch top videos for {alias}: {e}")

        # 5. Diagnostic analysis
        diagnosis = _diagnose_channel_health(avg_retention_pct, traffic_sources, sub_conversion_rate)

        return {
            "channel_title": channel_title,
            "alias": alias,
            "periodo_dias": days,
            "data_inicio": start_date,
            "data_fim": end_date,
            "resumo_macro": {
                "total_views": total_views,
                "horas_assistidas": round(minutes_watched / 60, 1),
                "duracao_media_segundos": avg_view_duration_sec,
                "retencao_media_percentual": avg_retention_pct,
                "inscritos_ganhos": subs_gained,
                "inscritos_perdidos": subs_lost,
                "saldo_inscritos": net_subs,
                "taxa_conversao_inscritos": sub_conversion_rate,
            },
            "fontes_de_trafego": traffic_sources,
            "videos_mais_assistidos": top_videos,
            "diagnostico_estrategico": diagnosis,
        }

    except Exception as e:
        logger.error(f"Error fetching channel health for {alias}: {e}")
        return {"error": str(e), "alias": alias}
