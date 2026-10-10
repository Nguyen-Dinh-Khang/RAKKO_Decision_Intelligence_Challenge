"""
pricing_engine.py - Phân tầng giá thị trường & Đề xuất định giá theo kịch bản vốn
Được chuẩn hóa theo tài liệu đặc tả: Word/Function_md/market_analyse_engine.md (Mục 3.5, 3.7 & 3.8)
"""

import re
from typing import Dict, Any, List, Tuple, Optional
from .config import (
    PRICE_JUMP_ABSOLUTE_MIN,
    PRICE_JUMP_RELATIVE_RATIO,
    CAPITAL_PREMIUM_HIGH_THRESHOLD,
    CAPITAL_PREMIUM_MID_THRESHOLD,
    LUXURY_LACKING_RATIO_THRESHOLD,
    PREMIUM_PRICE_MIN_RATIO,
    PREMIUM_PRICE_MAX_RATIO,
    PREMIUM_CUSTOMER_PRICE_MULTIPLIER
)


def _parse_price_range(val: Any) -> Optional[float]:
    """
    Bóc tách trường price_range dạng chuỗi từ CSDL DB2
    Ví dụ: '50.000 - 90.000 VND', '1.500.000 - 4.000.000 VND', '30.000đ', '20k - 50k'.
    Trả về giá trị trung bình dạng float.
    """
    if not val or not isinstance(val, str):
        return None

    text = val.lower().replace("vnd", "").replace("đ", "").strip()
    text = re.sub(r'(\d+)\s*k\b', r'\g<1>000', text)

    raw_matches = re.findall(r'\b\d+(?:[\.,]\d{3})*\b|\b\d+\b', text)
    clean_nums = []
    for m in raw_matches:
        num_str = m.replace(".", "").replace(",", "").strip()
        if num_str.isdigit():
            val_num = float(num_str)
            if val_num > 0:
                clean_nums.append(val_num)

    if len(clean_nums) >= 2:
        return (clean_nums[0] + clean_nums[1]) / 2.0
    elif len(clean_nums) == 1:
        return clean_nums[0]

    return None


def _get_competitor_avg_price(comp: Dict[str, Any]) -> float:
    """Trích xuất giá trung bình của một đối thủ (ưu tiên price_range, sau đó min/max, avg)."""
    # 1. Thử bóc tách price_range (chuẩn lưu trữ DB2 competitors)
    pr = comp.get("price_range")
    parsed_pr = _parse_price_range(pr)
    if parsed_pr is not None:
        return parsed_pr

    # 2. Thử min_price / max_price
    min_p = comp.get("min_price") or comp.get("price_min")
    max_p = comp.get("max_price") or comp.get("price_max")
    if min_p is not None and max_p is not None:
        try:
            return (float(min_p) + float(max_p)) / 2.0
        except (ValueError, TypeError):
            pass

    # 3. Thử avg_price / price
    avg_p = comp.get("avg_price") or comp.get("price")
    if avg_p is not None:
        try:
            return float(avg_p)
        except (ValueError, TypeError):
            pass

    return 30000.0  # Fallback phổ biến F&B


def analyze_average_price(
    competitors: List[Dict[str, Any]],
    customer_price_max: float
) -> Tuple[List[Dict[str, Any]], List[float]]:
    """
    Phân tầng giá trung bình thị trường dựa trên điểm nhảy vọt (Jump Threshold).
    So sánh giá quán mới với trung bình tích lũy của cụm giá trước đó (running average of current tier):
    - Tách tầng khi: giá quán > (1 + 35%) * trung bình cụm trước VÀ chênh lệch tuyệt đối >= 15.000đ.
    Output: Mảng các object [{"price": "22.000đ", "count": 6, "raw_avg": 22000.0}, ...] và danh sách giá thô.
    """
    if not competitors:
        default_price = f"{int(customer_price_max):,}đ".replace(",", ".")
        return [{"price": default_price, "count": 0, "raw_avg": float(customer_price_max)}], []

    prices = [_get_competitor_avg_price(c) for c in competitors]
    prices.sort()

    tiers: List[List[float]] = []
    current_tier = [prices[0]]

    for p in prices[1:]:
        current_tier_avg = sum(current_tier) / len(current_tier)
        ratio_jump = p > (1.0 + PRICE_JUMP_RELATIVE_RATIO) * current_tier_avg
        diff_jump = (p - current_tier_avg) >= PRICE_JUMP_ABSOLUTE_MIN

        if ratio_jump and diff_jump:
            tiers.append(current_tier)
            current_tier = [p]
        else:
            current_tier.append(p)

    if current_tier:
        tiers.append(current_tier)

    result = []
    for tier in tiers:
        tier_avg = sum(tier) / len(tier)
        result.append({
            "price": f"{int(round(tier_avg, -3)):,}đ".replace(",", "."),
            "count": len(tier),
            "raw_avg": tier_avg
        })

    return result, prices


def evaluate_dual_strategy(
    budget: float,
    competitor_prices: List[float],
    customer_price_max: float,
    avg_price_data: Optional[List[Dict[str, Any]]] = None
) -> bool:
    """
    Xác định cờ kích hoạt Kịch bản kép (has_dual_strategies).
    - Vốn >= 300 triệu -> True
    - Vốn >= 200 triệu VÀ tỷ lệ quán giá cao (premium) < 15% -> True
      (Quán cao cấp được xác định dựa trên các tầng giá có mức giá trung bình vượt trần chi trả nhân hệ số:
       raw_avg > customer_price_max * PREMIUM_CUSTOMER_PRICE_MULTIPLIER)
    - Còn lại -> False
    """
    if budget >= CAPITAL_PREMIUM_HIGH_THRESHOLD:
        return True

    if budget >= CAPITAL_PREMIUM_MID_THRESHOLD:
        if not competitor_prices:
            return True

        premium_threshold = customer_price_max * PREMIUM_CUSTOMER_PRICE_MULTIPLIER

        if avg_price_data:
            # Đếm số lượng quán thuộc các tầng giá có mức giá trung bình vượt ngưỡng cao cấp
            luxury_count = sum(
                tier.get("count", 0)
                for tier in avg_price_data
                if tier.get("raw_avg", 0.0) > premium_threshold
            )
        else:
            # Fallback nếu không truyền avg_price_data
            luxury_count = sum(1 for p in competitor_prices if p > premium_threshold)

        luxury_ratio = luxury_count / len(competitor_prices)
        if luxury_ratio < LUXURY_LACKING_RATIO_THRESHOLD:
            return True

    return False


def calculate_recommended_price(
    has_dual_strategies: bool,
    customer_price_min: float,
    customer_price_max: float
) -> List[Dict[str, str]]:
    """
    Đề xuất mức giá bán theo chiến lược vốn (Normal hoặc Normal + Premium).
    """
    normal_str = f"{int(customer_price_min):,}đ - {int(customer_price_max):,}đ".replace(",", ".")

    if not has_dual_strategies:
        return [{"type": "normal", "price": normal_str}]

    prem_min = customer_price_max * PREMIUM_PRICE_MIN_RATIO
    prem_max = customer_price_max * PREMIUM_PRICE_MAX_RATIO
    premium_str = f"{int(prem_min):,}đ - {int(prem_max):,}đ".replace(",", ".")

    return [
        {"type": "normal", "price": normal_str},
        {"type": "premium", "price": premium_str}
    ]
