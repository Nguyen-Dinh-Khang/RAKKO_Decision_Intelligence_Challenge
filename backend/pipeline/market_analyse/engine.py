"""
engine.py - Cỗ máy điều phối Phân tích Thị trường Vi mô (Market Analyse Engine)
Được chuẩn hóa theo tài liệu đặc tả: Word/Function_md/market_analyse_engine.md (Mục 1, 4 & 5)
"""

import logging
from typing import Dict, Any, List, Optional
from ...database import get_db
from .threat_analyzer import analyze_direct_competitors
from .clustering_engine import cluster_systemic_weaknesses
from .customer_analyzer import (
    calculate_competition_level,
    analyze_target_customer,
    calculate_recommended_time
)
from .pricing_engine import (
    analyze_average_price,
    evaluate_dual_strategy,
    calculate_recommended_price
)
from .strategy_matcher import (
    extract_market_weakness,
    match_against_weakness
)

logger = logging.getLogger(__name__)


def analyse_market(
    competitors: List[Dict[str, Any]],
    model_id: int,
    product_ids: List[int],
    budget: float,
    demographics: Optional[Dict[str, Any]] = None,
    db=None
) -> Dict[str, Any]:
    """
    Hàm phân tích thị trường vi mô chuẩn 1km (Pure Analytical Function).
    Không tự query competitors, nhận dữ liệu đã được SpatialEngine lọc sẵn.
    """
    if db is None:
        db = get_db()
    if demographics is None:
        demographics = {}

    clean_prods = [int(p) for p in product_ids]
    model_id = int(model_id)
    budget = float(budget)

    # 1. Gom cụm điểm yếu hệ thống BGE-M3 (Chạy trước để cung cấp systemic_comp_ids cho CTS)
    cluster_res = cluster_systemic_weaknesses(competitors)
    systemic_ids = cluster_res.get("systemic_comp_ids", set())
    clusters = cluster_res.get("clusters", [])

    # 2. Phân tích chân dung khách hàng chủ lực (DB5 kết hợp nhóm tuổi và món)
    cust_insights = analyze_target_customer(demographics, clean_prods, db=db)

    # 3. Tính điểm đe dọa CTS & Xác định đối thủ trực tiếp
    direct_comps, max_threat_comp = analyze_direct_competitors(
        competitors=competitors,
        user_model_id=model_id,
        user_product_ids=clean_prods,
        systemic_comp_ids=systemic_ids,
        target_segment_interest=cust_insights.get("interest", 0.5)
    )

    # 4. Tính mức độ cạnh tranh
    comp_level = calculate_competition_level(competitors, model_id, demographics)

    # 5. Phân tầng giá thị trường & Đánh giá kịch bản kép
    cust_price_max = cust_insights.get("price_max", 35000.0)
    cust_price_min = cust_insights.get("price_min", 25000.0)
    avg_price_data, comp_prices = analyze_average_price(competitors, cust_price_max)
    has_dual = evaluate_dual_strategy(budget, comp_prices, cust_price_max, avg_price_data=avg_price_data)

    # 6. Đề xuất dải giá bán (Normal / Premium)
    rec_price = calculate_recommended_price(has_dual, cust_price_min, cust_price_max)

    # 7. Đề xuất khung giờ mở quán đón đầu cao điểm
    rec_time = calculate_recommended_time(cust_insights.get("time", "06:30 - 08:30"))

    # 8. Trích xuất điểm yếu thị trường tiêu biểu (Important + 2 Normal)
    market_weakness_data = extract_market_weakness(max_threat_comp, clusters, competitors=competitors)

    # 9. So khớp bài học DB4 (tự động gắn tag 0) hoặc cơ chế Weakness Inversion
    lessons = match_against_weakness(market_weakness_data, model_id, clean_prods, db=db)

    # Đóng gói dữ liệu đầu ra chuẩn theo Bảng đặc tả Mục 4
    output = {
        "competition_level": comp_level,
        "direct_competitors": direct_comps,
        "has_dual_strategies": has_dual,
        "customer_insights": {
            "time": cust_insights.get("time", "06:30 - 08:30"),
            "price": cust_insights.get("price", "25.000đ - 35.000đ"),
            "price_min": cust_insights.get("price_min", 25000.0),
            "price_max": cust_insights.get("price_max", 35000.0),
            "interest": cust_insights.get("interest", 0.8),
            "behavior": cust_insights.get("behavior", ""),
            "primary_product_id": cust_insights.get("primary_product_id"),
            "secondary_insights": cust_insights.get("secondary_insights")
        },
        "average_price": avg_price_data,
        "recommended_price": rec_price,
        "recommended_time": rec_time,
        "market_weakness": market_weakness_data,
        "against_weakness": lessons
    }

    return output


class MarketAnalyseEngine:
    """
    Class giao diện của bộ máy Market Analyse Engine.
    Hỗ trợ đồng thời analyse_market (chuẩn mới) và find_market_gaps (tương thích ngược).
    """
    def __init__(self, db=None):
        self.db = db

    def analyse_market(
        self,
        competitors: List[Dict[str, Any]],
        model_id: int,
        product_ids: List[int],
        budget: float,
        demographics: Optional[Dict[str, Any]] = None,
        db=None
    ) -> Dict[str, Any]:
        return analyse_market(
            competitors=competitors,
            model_id=model_id,
            product_ids=product_ids,
            budget=budget,
            demographics=demographics,
            db=db or self.db
        )

    def find_market_gaps(
        self,
        competitors: List[Dict[str, Any]],
        model_id: int,
        product_ids: List[int],
        budget: float,
        demographics: Optional[Dict[str, Any]] = None,
        db=None
    ) -> Dict[str, Any]:
        """Bí danh tương thích ngược cho các mắt xích pipeline hiện có."""
        return self.analyse_market(
            competitors=competitors,
            model_id=model_id,
            product_ids=product_ids,
            budget=budget,
            demographics=demographics,
            db=db
        )
