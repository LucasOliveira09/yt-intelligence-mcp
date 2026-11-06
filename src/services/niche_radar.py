from collections import Counter
import re
from typing import Any, Dict, List
from src.services.competitor import search_youtube_videos

STOP_WORDS = {
    "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é", "com", "nao", "não",
    "uma", "os", "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "foi", "ao",
    "ele", "das", "tem", "à", "seu", "sua", "ou", "ser", "quando", "muito", "nos", "já",
    "eu", "também", "só", "pelo", "pela", "até", "isso", "ela", "entre", "era", "depois",
    "sem", "mesmo", "aos", "ter", "seus", "quem", "nas", "me", "esse", "eles", "estão",
    "você", "tinha", "foram", "essa", "num", "nem", "suas", "meu", "às", "minha", "têm",
    "numa", "pelos", "elas", "havia", "seja", "qual", "será", "nós", "tenho", "lhe",
    "the", "and", "to", "of", "a", "in", "is", "for", "you", "that", "it", "on", "with",
    "as", "this", "are", "from", "at", "by", "an", "be", "how", "what", "why", "i", "my",
    "video", "vídeo", "completo", "2025", "2026", "2024",
}


def scan_niche_radar(topic: str, sample_size: int = 25) -> Dict[str, Any]:
    """
    Scans a niche or search query across YouTube to identify patterns, dominant players,
    winning title keywords, and content gaps. Zero API quota.
    """
    raw_results = search_youtube_videos(topic, limit=sample_size)
    if not raw_results:
        return {"error": "Nenhum resultado encontrado para o tópico informado.", "topic": topic}

    channels = []
    durations = []
    titles = []

    for item in raw_results:
        ch = item.get("channel") or item.get("uploader")
        if ch:
            channels.append(ch)
        d = item.get("duration")
        if d and isinstance(d, (int, float)):
            durations.append(d)
        t = item.get("title")
        if t:
            titles.append(t)

    # Dominant channels
    channel_counts = Counter(channels).most_common(5)
    dominant_creators = [{"canal": name, "videos_no_top": count} for name, count in channel_counts]

    # Winning keywords in titles
    all_words = []
    for title in titles:
        # Tokenize words
        words = re.findall(r"\b[a-zA-ZÀ-ÿ0-9_-]{3,}\b", title.lower())
        for w in words:
            if w not in STOP_WORDS:
                all_words.append(w)

    top_keywords = [{"palavra": word, "frequencia": count} for word, count in Counter(all_words).most_common(12)]

    # Duration analysis
    avg_duration_sec = int(sum(durations) / len(durations)) if durations else 0
    avg_duration_min = round(avg_duration_sec / 60, 1)

    # Recommendation
    if avg_duration_min >= 15.0:
        format_rec = "Formato Long-form (15-25 min): a audiência deste nicho busca profundidade técnica e explicações detalhadas."
    elif avg_duration_min >= 8.0:
        format_rec = "Formato Médio (8-14 min): ideal para retenção dinâmica, foco no problema e solução sem enrolação."
    else:
        format_rec = "Formato Rápido (< 8 min): audiência prefere tutoriais diretos ao ponto e respostas cirúrgicas."

    return {
        "nicho_pesquisado": topic,
        "amostra_analisada": len(raw_results),
        "duracao_media_recomendada_minutos": avg_duration_min,
        "padrao_de_formato": format_rec,
        "canais_dominantes": dominant_creators,
        "termos_chave_mais_repetidos": top_keywords,
        "amostra_titulos_topo": [r.get("title") for r in raw_results[:5]],
    }
