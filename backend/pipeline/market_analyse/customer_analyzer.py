"""
customer_analyzer.py - Phân tích Khách hàng Mục tiêu, Mức độ Cạnh tranh & Giờ vàng
Được chuẩn hóa theo tài liệu đặc tả: Word/Function_md/market_analyse_engine.md (Mục 3.3, 3.6 & 3.9)
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from ...database import get_db
from .config import (
    INCOME_RATIO_LOW,
    INCOME_RATIO_MEDIUM,
    INCOME_RATIO_HIGH,
    EARLY_OPENING_MINUTES
)

logger = logging.getLogger(__name__)

# Mã tag nhóm tuổi DB5
AGE_TAG_MAP = {
    "18-24": 301,
    "25-34": 302,
    "35-50": 303,
    ">50": 304,
    "50+": 304,
    "> 50": 304
}

# Thứ tự ưu tiên nhóm trẻ nhất khi tỉ lệ bằng nhau
AGE_PRIORITY = ["18-24", "25-34", "35-50", ">50"]


def calculate_competition_level(
    competitors: List[Dict[str, Any]],
    user_model_id: int,
    demographics: Dict[str, Any]
) -> str:
    """
    Tính mức độ cạnh tranh trên thang 10 dựa trên số quán cùng mô hình trên 1.000 dân cư.
    Format output: "{score}/10" (VD: "5/10")
    """
    pop_density = float(
        demographics.get("density") or
        demographics.get("population_density") or
        demographics.get("population", 5000.0) or
        5000.0
    )

    n_model = sum(
        1 for c in competitors
        if c.get("model_id") is not None and int(c.get("model_id")) == int(user_model_id)
    )

    norm_density = max(pop_density / 1000.0, 1.0)
    ratio = n_model / norm_density

    # Quy đổi ra thang 10
    if ratio < 0.3:
        if ratio <= 0.1:
            score = 1
        elif ratio <= 0.2:
            score = 2
        else:
            score = 3
    elif ratio <= 0.8:
        if ratio <= 0.45:
            score = 4
        elif ratio <= 0.65:
            score = 5
        else:
            score = 6
    elif ratio <= 1.5:
        if ratio <= 1.15:
            score = 7
        else:
            score = 8
    else:
        if ratio <= 2.2:
            score = 9
        else:
            score = 10

    return f"{score}/10"


def _extract_primary_age_tag(demographics: Dict[str, Any]) -> Tuple[str, int]:
    """
    Trích xuất nhóm tuổi chủ lực theo quy tắc:
    Lấy lứa tuổi có tỉ lệ lớn nhất, nếu có nhiều lứa tuổi bằng nhau thì lấy nhóm trẻ nhất.
    """
    age_dist = demographics.get("age_distribution", {})
    if not isinstance(age_dist, dict) or not age_dist:
        return "18-24", 301

    best_age = "18-24"
    best_rate = -1.0

    for age in AGE_PRIORITY:
        rate = float(age_dist.get(age, 0.0))
        if rate > best_rate:
            best_rate = rate
            best_age = age

    tag = AGE_TAG_MAP.get(best_age, 301)
    return best_age, tag


def analyze_target_customer(
    demographics: Dict[str, Any],
    product_ids: List[int],
    db=None
) -> Dict[str, Any]:
    """
    Truy vấn DB5 (market_segments) kết hợp nhóm tuổi và danh mục món do client gửi.
    Tính dải giá khả thi đã nhân hệ số thu nhập DB1.
    """
    if db is None:
        db = get_db()

    primary_age, age_tag = _extract_primary_age_tag(demographics)
    clean_prods = [int(p) for p in product_ids]

    segment_doc = None
    if db is not None:
        try:
            # Query DB5: {"tag_ids": {"$all": [age_tag], "$in": clean_prods}}
            cursor = db["market_segments"].find({
                "tag_ids": {
                    "$all": [age_tag],
                    "$in": clean_prods
                }
            })
            docs = list(cursor)
            if docs:
                # Ưu tiên bản ghi có interest cao nhất
                segment_doc = max(docs, key=lambda d: float(d.get("interest", 0.0) or 0.0))
            else:
                # Fallback: tìm theo age_tag
                fallback_cursor = db["market_segments"].find({"tag_ids": age_tag})
                f_docs = list(fallback_cursor)
                if f_docs:
                    segment_doc = f_docs[0]
        except Exception as e:
            logger.warning(f"[!] Lỗi truy vấn DB5 trong customer_analyzer: {e}")

    # Giá trị mặc định nếu CSDL không có
    raw_time = "06:30 - 08:30"
    raw_interest = 0.80
    raw_behavior = "Mua mang đi vội giờ sáng, ưu tiên thanh toán tiện lợi"
    raw_min_price = 25000.0
    raw_max_price = 35000.0

    if segment_doc:
        raw_time_data = segment_doc.get("peak_hours") or segment_doc.get("time")
        if isinstance(raw_time_data, list):
            time_parts = [
                f"{item.get('start', '')} - {item.get('end', '')}"
                for item in raw_time_data
                if isinstance(item, dict) and "start" in item and "end" in item
            ]
            if time_parts:
                raw_time = " & ".join(time_parts)
        elif isinstance(raw_time_data, str) and raw_time_data.strip():
            raw_time = raw_time_data.strip()

        raw_interest = float(segment_doc.get("interest", raw_interest) or raw_interest)
        raw_behavior = (
            segment_doc.get("behavior") or
            segment_doc.get("demand") or
            segment_doc.get("description") or
            raw_behavior
        )
        
        pr = segment_doc.get("price_range")
        if isinstance(pr, list) and len(pr) >= 2:
            raw_min_price = float(pr[0])
            raw_max_price = float(pr[1])
        elif isinstance(pr, dict):
            raw_min_price = float(pr.get("min", raw_min_price))
            raw_max_price = float(pr.get("max", raw_max_price))

    # Áp dụng hệ số thu nhập từ DB1
    income_level = str(demographics.get("income_level") or demographics.get("income", "MEDIUM")).upper()
    if "LOW" in income_level or "THẤP" in income_level:
        factor = INCOME_RATIO_LOW
    elif "HIGH" in income_level or "CAO" in income_level:
        factor = INCOME_RATIO_HIGH
    else:
        factor = INCOME_RATIO_MEDIUM

    adj_min_price = raw_min_price * factor
    adj_max_price = raw_max_price * factor

    price_str = f"{int(adj_min_price):,}đ - {int(adj_max_price):,}đ".replace(",", ".")

    return {
        "time": raw_time,
        "price": price_str,
        "price_min": adj_min_price,
        "price_max": adj_max_price,
        "interest": round(raw_interest, 2),
        "behavior": raw_behavior,
        "primary_age": primary_age,
        "age_tag": age_tag,
        "segment_id": str(segment_doc["_id"]) if (segment_doc and "_id" in segment_doc) else None
    }


def calculate_recommended_time(peak_hours_str: str) -> str:
    """
    Tính thời gian mở quán đề xuất:
    Mở sớm hơn giờ bắt đầu cao điểm 45 phút (EARLY_OPENING_MINUTES = 45) để đón dòng khách vội.
    """
    if not peak_hours_str or not isinstance(peak_hours_str, str):
        return "06:30 - 08:30"

    parts = peak_hours_str.split("&")
    shifted_parts = []

    for part in parts:
        part = part.strip()
        # Tìm cụm giờ mở và kết thúc: HH:MM - HH:MM
        times = re.findall(r"(\d{1,2}:\d{2})", part)
        if len(times) >= 2:
            start_str, end_str = times[0], times[1]
            try:
                dt_start = datetime.strptime(start_str, "%H:%M")
                dt_shifted = dt_start - timedelta(minutes=EARLY_OPENING_MINUTES)
                new_start_str = dt_shifted.strftime("%H:%M")
                # Giữ nguyên phần đuôi giờ kết thúc
                shifted_part = part.replace(start_str, new_start_str, 1)
                shifted_parts.append(shifted_part)
            except Exception:
                shifted_parts.append(part)
        else:
            shifted_parts.append(part)

    return " & ".join(shifted_parts)
