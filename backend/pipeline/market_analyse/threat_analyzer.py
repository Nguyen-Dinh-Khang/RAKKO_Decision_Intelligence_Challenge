"""
threat_analyzer.py - Đánh giá Điểm đe dọa Đối thủ (Competitor Threat Score - CTS)
Được chuẩn hóa theo tài liệu đặc tả: Word/Function_md/market_analyse_engine.md (Mục 3.1 & 3.4)
"""

from typing import Dict, Any, List, Set, Tuple, Optional
from .config import (
    ANALYSIS_RADIUS_METERS,
    WEIGHT_DISTANCE,
    WEIGHT_OVERLAP,
    WEIGHT_WEAKNESS,
    WEIGHT_REPUTATION,
    WEIGHT_DEMOGRAPHIC,
    DIRECT_COMPETITOR_CTS_THRESHOLD
)

INVALID_WEAKNESS_VALUES = {"", "n/a", "none", "null", "chưa có", "không có", "không có thông tin", "chưa rõ"}


def calculate_cts(
    competitor: Dict[str, Any],
    user_model_id: int,
    user_product_ids: List[int],
    max_reviews_area: int,
    systemic_comp_ids: Set[str],
    target_segment_interest: float = 0.5
) -> float:
    """
    Tính điểm đe dọa (Competitor Threat Score - CTS) cho 1 quán đối thủ.
    Thang điểm 0 - 100.
    """
    # 1. S_dist (Cự ly khoảng cách - 25%)
    dist = float(competitor.get("distance_m", competitor.get("distance", 500.0)))
    if dist <= ANALYSIS_RADIUS_METERS:
        s_dist = max(0.0, 100.0 * (1.0 - (dist / ANALYSIS_RADIUS_METERS)))
    else:
        s_dist = 0.0

    # 2. S_overlap (Trùng lặp Mô hình & Món - 30%)
    comp_model = competitor.get("model_id") or competitor.get("business_model_id")
    comp_products = competitor.get("product_ids") or competitor.get("category_ids") or []
    
    same_model = (comp_model is not None and int(comp_model) == int(user_model_id))
    user_prod_set = set(int(p) for p in user_product_ids)
    comp_prod_set = set(int(p) for p in comp_products)
    overlap_count = len(user_prod_set & comp_prod_set)

    if same_model and overlap_count >= 1:
        s_overlap = 100.0
    elif (not same_model) and overlap_count >= 1:
        s_overlap = min(100.0, 70.0 + (10.0 * overlap_count))
    elif same_model and overlap_count == 0:
        s_overlap = 50.0
    else:
        s_overlap = 0.0

    # 3. S_weakness (Tử huyệt / Điểm yếu - 20%)
    comp_id = str(competitor.get("id") or competitor.get("_id") or "")
    raw_weakness = str(competitor.get("weakness", "")).strip().lower()
    
    if comp_id in systemic_comp_ids:
        s_weakness = 100.0
    elif raw_weakness and raw_weakness not in INVALID_WEAKNESS_VALUES:
        s_weakness = 40.0
    else:
        s_weakness = 0.0

    # 4. S_rep (Uy tín & Quy mô tương đối - 15%)
    rating = float(competitor.get("rating", 0.0) or 0.0)
    star_score = min(50.0, max(0.0, (rating / 5.0) * 50.0))
    
    review_count = int(competitor.get("review_count", competitor.get("reviews", 0)) or 0)
    if max_reviews_area <= 0:
        share_score = 25.0
    else:
        share_score = min(50.0, (review_count / max(max_reviews_area, 1)) * 50.0)
    s_rep = star_score + share_score

    # 5. S_demo (Hợp thị hiếu tệp khách địa phương - 10%)
    if overlap_count >= 1:
        s_demo = max(50.0, target_segment_interest * 100.0)
    else:
        s_demo = 50.0

    # Tổng hợp CTS
    cts = (
        WEIGHT_DISTANCE * s_dist +
        WEIGHT_OVERLAP * s_overlap +
        WEIGHT_WEAKNESS * s_weakness +
        WEIGHT_REPUTATION * s_rep +
        WEIGHT_DEMOGRAPHIC * s_demo
    )
    return round(float(cts), 1)


def analyze_direct_competitors(
    competitors: List[Dict[str, Any]],
    user_model_id: int,
    user_product_ids: List[int],
    systemic_comp_ids: Set[str],
    target_segment_interest: float = 0.5
) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
    """
    Tính CTS cho danh sách đối thủ, xác định đối thủ trực tiếp (CTS >= 65.0)
    và tìm đối thủ có mối đe dọa lớn nhất (Max CTS).
    """
    if not competitors:
        return {"count": 0, "ids": []}, None

    max_reviews = max(
        [int(c.get("review_count", c.get("reviews", 0)) or 0) for c in competitors],
        default=0
    )

    direct_ids: List[str] = []
    max_threat_comp: Optional[Dict[str, Any]] = None
    max_threat_score = -1.0

    for c in competitors:
        comp_id = str(c.get("id") or c.get("_id") or "")
        score = calculate_cts(
            competitor=c,
            user_model_id=user_model_id,
            user_product_ids=user_product_ids,
            max_reviews_area=max_reviews,
            systemic_comp_ids=systemic_comp_ids,
            target_segment_interest=target_segment_interest
        )
        c["cts_score"] = score

        is_direct = (score >= DIRECT_COMPETITOR_CTS_THRESHOLD)
        c["is_direct"] = is_direct

        if is_direct:
            direct_ids.append(comp_id)

        if score > max_threat_score:
            max_threat_score = score
            max_threat_comp = c

    return {"count": len(direct_ids), "ids": direct_ids}, max_threat_comp
