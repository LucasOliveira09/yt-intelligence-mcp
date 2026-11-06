import statistics
from typing import Any, Dict, List, Optional
from src.config import DEFAULT_OUTLIER_THRESHOLD, MEGA_VIRAL_THRESHOLD


def classify_performance(multiplier: float, threshold: float) -> str:
    if multiplier >= MEGA_VIRAL_THRESHOLD:
        return "MEGA_VIRAL"
    if multiplier >= threshold:
        return "OUTLIER"
    if multiplier >= 1.3:
        return "ABOVE_AVERAGE"
    if multiplier >= 0.7:
        return "NORMAL"
    return "UNDERPERFORMING"


def analyze_outliers(
    videos: List[Dict[str, Any]],
    threshold: float = DEFAULT_OUTLIER_THRESHOLD,
) -> Dict[str, Any]:
    """
    Analyzes view counts relative to the channel's baseline median.
    Identifies true breakout videos (outliers) that broke through algorithmic thresholds.
    """
    # Filter out videos without view count (e.g., scheduled, members-only)
    valid_videos = [v for v in videos if v.get("view_count") is not None and isinstance(v["view_count"], (int, float))]

    if not valid_videos:
        return {
            "sample_size": 0,
            "median_views": 0,
            "mean_views": 0,
            "outliers_count": 0,
            "outliers": [],
            "all_analyzed": [],
        }

    views_list = [v["view_count"] for v in valid_videos]
    median_views = statistics.median(views_list)
    mean_views = round(statistics.mean(views_list), 1)

    baseline = max(median_views, 1.0)

    analyzed_videos = []
    outliers = []

    for v in valid_videos:
        views = v["view_count"]
        multiplier = round(views / baseline, 2)
        perf_tier = classify_performance(multiplier, threshold)

        item = {
            "id": v.get("id"),
            "title": v.get("title"),
            "url": v.get("url") or f"https://www.youtube.com/watch?v={v.get('id')}",
            "view_count": views,
            "duration_seconds": v.get("duration"),
            "multiplier": multiplier,
            "tier": perf_tier,
            "is_outlier": multiplier >= threshold,
            "thumbnail": v.get("thumbnail"),
        }

        analyzed_videos.append(item)
        if item["is_outlier"]:
            outliers.append(item)

    # Sort outliers descending by multiplier
    outliers.sort(key=lambda x: x["multiplier"], reverse=True)

    return {
        "sample_size": len(valid_videos),
        "median_views": int(median_views),
        "mean_views": int(mean_views),
        "outliers_count": len(outliers),
        "outliers": outliers,
        "all_analyzed": analyzed_videos,
    }
