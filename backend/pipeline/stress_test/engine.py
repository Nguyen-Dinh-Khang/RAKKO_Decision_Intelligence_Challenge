"""
engine.py - Cỗ máy điều phối Giả lập Thử tải Rủi ro Sinh tồn (Stress Test Engine)
Được chuẩn hóa theo tài liệu đặc tả: Word/Function_md/stress_test_engine.md (Mục 1, 3.4, 4 & 5)
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from .config import (
    CONTINGENCY_RATIO_NORMAL,
    CONTINGENCY_RATIO_PREMIUM,
    PREMIUM_AOV_MULTIPLIER,
    PREMIUM_CAPEX_MULTIPLIER,
    PREMIUM_CAPEX_RATIO_ADDON,
    PREMIUM_SALARY_MULTIPLIER,
    PREMIUM_STAFF_ADDON,
    PREMIUM_UTILITIES_MULTIPLIER,
    DEFAULT_RENT_BY_MODEL
)
from .simulator import simulate_single_scenario

logger = logging.getLogger(__name__)

_cached_financial_profiles: Optional[Dict[str, Any]] = None


def load_financial_profiles() -> Dict[str, Any]:
    """Tải cấu hình tài chính từ file financial_profiles.json (Cached)."""
    global _cached_financial_profiles
    if _cached_financial_profiles is not None:
        return _cached_financial_profiles

    # Tìm file financial_profiles.json tại client_app/backend/financial_profiles.json
    current_dir = Path(__file__).resolve().parent
    potential_paths = [
        current_dir.parent.parent / "financial_profiles.json",
        current_dir.parent.parent.parent / "client_app" / "backend" / "financial_profiles.json",
        Path.cwd() / "client_app" / "backend" / "financial_profiles.json"
    ]

    for p in potential_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    _cached_financial_profiles = json.load(f)
                    return _cached_financial_profiles
            except Exception as e:
                logger.error(f"[!] Không thể đọc file {p}: {e}")

    logger.warning("[!] Không tìm thấy financial_profiles.json, sử dụng cấu hình dự phòng mặc định.")
    return {}


def run_stress_test(
    budget: float,
    monthly_rent: Optional[float] = None,
    business_model_id: int = 101,
    product_ids: Optional[List[int]] = None,
    has_dual_strategies: bool = False,
    **kwargs
) -> List[Dict[str, Any]]:
    """
    Hàm thực thi bài toán thử tải tài chính cực đoan (Zero Revenue).
    Hỗ trợ cả has_dual_strategies và bí danh has_dual_plans.
    Trả về mảng gồm 1 phần tử (Normal) hoặc 2 phần tử (Normal & Premium).
    """
    # Hỗ trợ bí danh has_dual_plans từ các caller cũ
    if "has_dual_plans" in kwargs:
        has_dual_strategies = kwargs["has_dual_plans"]

    profiles_data = load_financial_profiles()
    model_profiles = profiles_data.get("business_model_profiles", {})
    product_profiles = profiles_data.get("product_economics_profiles", {})

    b_model_key = str(int(business_model_id))
    bm = model_profiles.get(b_model_key, {})

    # Trích xuất thông số mô hình chuẩn
    capex_ratio = float(bm.get("capex_ratio", 0.45))
    min_capex = float(bm.get("min_capex", 35_000_000))
    max_capex = float(bm.get("max_capex", 90_000_000))
    staff_salary = float(bm.get("staff_salary_per_person", 6_000_000))
    staff_count = int(bm.get("staff_count", 2))
    utilities_cost = float(bm.get("utilities_cost", 3_000_000))
    utilities_note = str(bm.get("utilities_note", "Điện, nước, gas vận hành cơ bản"))

    # Xác định giá trị tiền thuê mặt bằng (cho phép 0đ nếu có sẵn mặt bằng hoặc bán online)
    if monthly_rent is not None and float(monthly_rent) >= 0:
        actual_rent = float(monthly_rent)
    else:
        actual_rent = float(DEFAULT_RENT_BY_MODEL.get(int(business_model_id), 10_000_000))

    # Tính toán AOV từ danh mục sản phẩm
    clean_prods = [str(p) for p in (product_ids or [201])]
    aov_list = []
    for p_id in clean_prods:
        if p_id in product_profiles:
            aov_list.append(float(product_profiles[p_id].get("aov", 32000)))
    base_aov = sum(aov_list) / len(aov_list) if aov_list else 32000.0

    # 1. Kịch bản Thông thường (Normal Scenario - LUÔN CÓ)
    normal_res = simulate_single_scenario(
        scenario_name="normal",
        budget=budget,
        rent=actual_rent,
        capex_ratio=capex_ratio,
        min_capex=min_capex,
        max_capex=max_capex,
        staff_salary_per_person=staff_salary,
        staff_count=staff_count,
        utilities_cost=utilities_cost,
        utilities_note=utilities_note,
        aov=base_aov,
        contingency_ratio=CONTINGENCY_RATIO_NORMAL
    )

    if not has_dual_strategies:
        return [normal_res]

    # 2. Kịch bản Cao cấp (Premium Scenario - KHI has_dual_strategies == True)
    premium_aov = base_aov * PREMIUM_AOV_MULTIPLIER
    premium_min_capex = min_capex * PREMIUM_CAPEX_MULTIPLIER
    premium_max_capex = max_capex * PREMIUM_CAPEX_MULTIPLIER
    premium_capex_ratio = min(capex_ratio + PREMIUM_CAPEX_RATIO_ADDON, 0.60)
    premium_salary = staff_salary * PREMIUM_SALARY_MULTIPLIER
    premium_staff_count = staff_count + PREMIUM_STAFF_ADDON
    premium_utilities = utilities_cost * PREMIUM_UTILITIES_MULTIPLIER

    premium_res = simulate_single_scenario(
        scenario_name="premium",
        budget=budget,
        rent=actual_rent,
        capex_ratio=premium_capex_ratio,
        min_capex=premium_min_capex,
        max_capex=premium_max_capex,
        staff_salary_per_person=premium_salary,
        staff_count=premium_staff_count,
        utilities_cost=premium_utilities,
        utilities_note=utilities_note,
        aov=premium_aov,
        contingency_ratio=CONTINGENCY_RATIO_PREMIUM
    )

    return [normal_res, premium_res]


class StressTestEngine:
    """
    Class giao diện của bộ máy Stress Test Engine.
    """
    def __init__(self, profiles_path: Optional[str] = None):
        self.profiles = load_financial_profiles()

    def run_stress_test(
        self,
        budget: float,
        monthly_rent: Optional[float] = None,
        business_model_id: int = 101,
        product_ids: Optional[List[int]] = None,
        has_dual_strategies: bool = False,
        **kwargs
    ) -> List[Dict[str, Any]]:
        return run_stress_test(
            budget=budget,
            monthly_rent=monthly_rent,
            business_model_id=business_model_id,
            product_ids=product_ids,
            has_dual_strategies=has_dual_strategies,
            **kwargs
        )
