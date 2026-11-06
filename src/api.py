import os
from typing import Any, Dict, List, Optional
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from src.analytics.outliers import analyze_outliers
from src.services.competitor import fetch_channel_videos
from src.services.content_arbitrage import find_viral_gringo_arbitrage
from src.services.flexible_search import search_youtube_flexible
from src.services.niche_radar import scan_niche_radar
from src.services.owned import get_channel_overview
from src.services.owned_analytics import fetch_channel_health_report
from src.services.video_deep_dive import get_video_deep_dive

# Initialize FastAPI with metadata tailored for ChatGPT Actions
app = FastAPI(
    title="YouTube Intelligence API",
    description="Zero-quota YouTube research, viral outlier detection, and channel management engine for AI agents.",
    version="1.0.0",
    servers=[
        {"url": os.getenv("API_PUBLIC_URL", "https://yt.yourdomain.com"), "description": "Production VPS Server"}
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chat.openai.com", "https://chatgpt.com", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()
API_SECRET_TOKEN = os.getenv("YT_INTEL_API_KEY", "")


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    if not API_SECRET_TOKEN:
        # If no key set in environment, allow local development
        return True
    if credentials.credentials != API_SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API Token")
    return True


# ==========================================
# SCHEMAS
# ==========================================

class SearchRequest(BaseModel):
    query: str = Field(..., description="Termo de pesquisa no YouTube")
    sort_by: str = Field("relevance", description="relevance, upload_date, view_count, rating")
    upload_period: Optional[str] = Field(None, description="hour, today, this_week, this_month, this_year")
    duration: Optional[str] = Field(None, description="short, medium, long")
    min_views: Optional[int] = Field(None, description="Filtro de views mínimas")
    max_views: Optional[int] = Field(None, description="Filtro de views máximas")
    exclude_shorts: bool = Field(False, description="Ignorar YouTube Shorts (<60s)")
    limit: int = Field(15, description="Quantidade de resultados")


class ArbitrageRequest(BaseModel):
    topic: str = Field("GTA 6", description="Tópico a minerar no exterior")
    min_multiplier: float = Field(2.5, description="Multiplicador mínimo sobre a mediana do canal")
    min_views: int = Field(50000, description="Visualizações mínimas")


class CompetitorRequest(BaseModel):
    channel: str = Field(..., description="Handle (@canal) ou URL do canal")
    limit: int = Field(20, description="Quantidade de vídeos recentes a analisar")
    threshold: float = Field(2.0, description="Multiplicador para ser considerado outlier")


# ==========================================
# ENDPOINTS (ChatGTP Actions)
# ==========================================

@app.post("/api/search", summary="Busca flexível no YouTube", dependencies=[Depends(verify_token)])
def api_search(req: SearchRequest):
    """Busca vídeos com filtros de data, visualizações, duração e relevância."""
    return search_youtube_flexible(
        query=req.query,
        sort_by=req.sort_by,
        upload_period=req.upload_period,
        duration=req.duration,
        min_views=req.min_views,
        max_views=req.max_views,
        exclude_shorts=req.exclude_shorts,
        limit=req.limit,
    )


@app.post("/api/arbitrage", summary="Mineração de conteúdo gringo viral", dependencies=[Depends(verify_token)])
def api_arbitrage(req: ArbitrageRequest):
    """Localiza vídeos virais no exterior e gera sugestões adaptadas para o Brasil."""
    return find_viral_gringo_arbitrage(
        topic=req.topic,
        min_multiplier=req.min_multiplier,
        min_views=req.min_views,
    )


@app.post("/api/outliers", summary="Análise de outliers de um canal", dependencies=[Depends(verify_token)])
def api_outliers(req: CompetitorRequest):
    """Calcula a mediana de views e extrai apenas os vídeos que furaram a bolha."""
    data = fetch_channel_videos(req.channel, limit=req.limit)
    if data.get("error"):
        raise HTTPException(status_code=400, detail=data["error"])
    return analyze_outliers(data.get("videos", []), threshold=req.threshold)


@app.get("/api/video-deep-dive", summary="Raio-X de um vídeo", dependencies=[Depends(verify_token)])
def api_deep_dive(video_url: str):
    """Extrai tags ocultas, métricas de engajamento e dúvidas do público nos comentários."""
    return get_video_deep_dive(video_url)


@app.get("/api/niche-radar", summary="Radar de nicho", dependencies=[Depends(verify_token)])
def api_niche_radar(topic: str, sample_size: int = 20):
    """Mapeia criadores líderes, palavras-chave em alta e duração ideal de um nicho."""
    return scan_niche_radar(topic, sample_size=sample_size)


@app.get("/api/audit-channel", summary="Auditoria do canal próprio", dependencies=[Depends(verify_token)])
def api_audit(alias: str = "canal_dev", days: int = 30):
    """Puxa relatório analítico de retenção, fontes de tráfego e diagnóstico de saúde."""
    return fetch_channel_health_report(alias, days=days)


@app.get("/health")
def health():
    return {"status": "ok", "service": "yt-intelligence"}
