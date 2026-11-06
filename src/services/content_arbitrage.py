import logging
import re
from typing import Any, Dict, List, Optional
from src.analytics.outliers import analyze_outliers
from src.services.competitor import fetch_channel_videos, search_youtube_videos

logger = logging.getLogger("yt_intelligence.content_arbitrage")

# Corporate channels to exclude
CORPORATE_EXCLUSIONS = {
    "netflix", "ign", "playstation", "xbox", "gamespot", "rockstargames",
    "warnerbros", "marvel", "paramount", "universal", "bbc", "cnn"
}

# High-yield benchmark creators by niche
KNOWN_SEEDS = {
    "gta": ["@Misteri_GTA", "@YTGrid", "@TGG_", "@JetroYT", "@MrDalekJD", "@T5G2"],
    "dev": ["@BeroODev", "@LucasMontano", "@ThePrimeTimeagen", "@Fireship"],
}


def _generate_brazilian_angles(title: str, topic: str) -> Dict[str, Any]:
    """Generates localized Portuguese title angles and hook frameworks based on the viral gringo structure."""
    clean_title = re.sub(rf"(?i){re.escape(topic)}", "", title).strip(" -:|")

    pt_titles = [
        f"Isso em {topic} Muda TUDO (E Quase Ninguém Notou)",
        f"Analisei os Segredos de {topic} e Achei Isso...",
        f"O Detalhe Escondido em {topic} Que Explica Toda a História",
        f"A Teoria Sobre {topic} Que a Comunidade Gringa Descobriu",
    ]

    hook_framework = (
        "Nos primeiros 15 segundos: NÃO dê boas-vindas. Comece mostrando o detalhe/leak exato na tela: "
        f"'A maioria das pessoas passou batido por esse detalhe em {topic}, mas quando você repara nisso aqui, "
        "fica claro o que a desenvolvedora escondeu...' "
        "Corte direto para a imagem/cena comprovando a tese."
    )

    return {
        "titulos_adaptados_ptbr": pt_titles,
        "estrutura_de_gancho_30s": hook_framework,
    }


def find_viral_gringo_arbitrage(
    topic: str = "GTA 6",
    search_queries: Optional[List[str]] = None,
    seed_channels: Optional[List[str]] = None,
    min_multiplier: float = 2.0,
    min_views: int = 50000,
) -> Dict[str, Any]:
    """
    Scans the international YouTube market for high-multiplier outlier videos.
    Identifies topics that broke the algorithm for medium/small channels abroad,
    and provides localized angles to adapt the content for Brazilian audiences.
    """
    channels_to_scan = list(seed_channels or [])

    # If no channels provided, use known seeds or discover via search
    if not channels_to_scan:
        topic_lower = topic.lower()
        if "gta" in topic_lower:
            channels_to_scan.extend(KNOWN_SEEDS["gta"])
        elif any(k in topic_lower for k in ["dev", "program", "code", "ia", "ai"]):
            channels_to_scan.extend(KNOWN_SEEDS["dev"])

        queries = search_queries or [
            f"{topic} secrets you missed",
            f"{topic} gameplay details analysis",
        ]
        for q in queries:
            results = search_youtube_videos(q, limit=5)
            for r in results:
                uploader = r.get("uploader") or ""
                if uploader:
                    handle = f"@{uploader.replace(' ', '')}"
                    if handle not in channels_to_scan and not any(c in handle.lower() for c in CORPORATE_EXCLUSIONS):
                        channels_to_scan.append(handle)

    arbitrage_opportunities = []

    for ch in channels_to_scan[:8]:
        data = fetch_channel_videos(ch, limit=15)
        if data.get("error") or not data.get("videos"):
            continue

        ch_title = data.get("channel_title") or ch
        if any(corp in ch_title.lower() for corp in CORPORATE_EXCLUSIONS):
            continue

        analysis = analyze_outliers(data.get("videos", []), threshold=min_multiplier)
        subs = data.get("followers_count") or 0

        for o in analysis.get("outliers", []):
            views = o.get("view_count") or 0
            multiplier = o.get("multiplier", 0.0)

            if views >= min_views and multiplier >= min_multiplier:
                angles = _generate_brazilian_angles(o["title"], topic)
                arbitrage_opportunities.append({
                    "titulo_gringo": o["title"],
                    "canal_gringo": ch_title,
                    "canal_handle": ch,
                    "inscritos_canal": subs,
                    "views_obtidas": views,
                    "multiplicador_de_performance": f"{multiplier}x da média do canal",
                    "classificacao": o.get("tier"),
                    "url_original": o.get("url"),
                    "adaptacao_brasil": angles,
                })

    # Sort descending by multiplier
    arbitrage_opportunities.sort(
        key=lambda x: float(x["multiplicador_de_performance"].split("x")[0]),
        reverse=True,
    )

    return {
        "tema_pesquisado": topic,
        "canais_gringos_minerados": len(channels_to_scan),
        "oportunidades_encontradas": len(arbitrage_opportunities),
        "ranking_de_arbitragem": arbitrage_opportunities[:10],
    }
