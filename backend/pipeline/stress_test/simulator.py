"""
simulator.py - Hàm tính toán toán học cho từng kịch bản thử tải tài chính
Được chuẩn hóa theo tài liệu đặc tả: Word/Function_md/stress_test_engine.md (Mục 3.1, 3.2, 3.3)
"""

import math
from typing import Dict, Any


def simulate_single_scenario(
    scenario_name: str,
    budget: float,
    rent: float,
    capex_ratio: float,
    min_capex: float,
    max_capex: float,
    staff_salary_per_person: float,
    staff_count: int,
    utilities_cost: float,
    utilities_note: str,
    aov: float,
    contingency_ratio: float
) -> Dict[str, Any]:
    """
    Giả lập tình huống tài chính cực đoan (Zero Revenue - 0đ doanh thu) cho 1 kịch bản.
    Bỏ qua hoàn toàn tiền cọc theo quy chuẩn điều chỉnh.
    """
    budget = float(budget)
    rent = float(rent)
    capex_ratio = float(capex_ratio)
    min_capex = float(min_capex)
    max_capex = float(max_capex)
    staff_salary_per_person = float(staff_salary_per_person)
    staff_count = int(staff_count)
    utilities_cost = float(utilities_cost)
    contingency_ratio = float(contingency_ratio)

    # 1. Tính toán Capex dự kiến & Kiểm tra điều kiện sàn
    raw_capex = budget * capex_ratio

    # Kiểm tra sàn sinh tồn tối thiểu
    if raw_capex < min_capex or budget < min_capex:
        # Vốn không đủ chạm ngưỡng setup tối thiểu -> month = 0
        actual_capex = min(raw_capex, max_capex) if raw_capex > 0 else min_capex
        salary_total = staff_count * staff_salary_per_person
        contingency_fund = budget * contingency_ratio
        monthly_fixed_cost = rent + salary_total + utilities_cost + contingency_fund

        return {
            "scenario": scenario_name,
            "month": 0.0,
            "utilities_note": utilities_note,
            "staff_count": staff_count,
            "capex": round(actual_capex, 0),
            "utilities_cost": round(utilities_cost, 0),
            "aov": round(aov, 0),
            "monthly_fixed_cost": round(monthly_fixed_cost, 0)
        }

    # Kẹp trong khoảng Sàn và Trần
    actual_capex = min(raw_capex, max_capex)

    # 2. Tính toán Chi phí định phí mỗi tháng (Monthly Recurring Cost)
    salary_total = staff_count * staff_salary_per_person
    contingency_fund = budget * contingency_ratio
    monthly_fixed_cost = rent + salary_total + utilities_cost + contingency_fund

    # 3. Tính toán Tháng sinh tồn (month) - Làm tròn xuống, nếu < 1 tháng thì kích hoạt runway = 0
    remaining_cash = budget - actual_capex
    if remaining_cash <= 0 or monthly_fixed_cost <= 0:
        survival_months = 0.0
    else:
        raw_months = remaining_cash / monthly_fixed_cost
        if raw_months < 1.0:
            survival_months = 0.0
        else:
            survival_months = float(math.floor(raw_months))

    return {
        "scenario": scenario_name,
        "month": survival_months,
        "utilities_note": utilities_note,
        "staff_count": staff_count,
        "capex": round(actual_capex, 0),
        "utilities_cost": round(utilities_cost, 0),
        "aov": round(aov, 0),
        "monthly_fixed_cost": round(monthly_fixed_cost, 0)
    }
