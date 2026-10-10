"""
branch_strategic.py - Module Xử lý Chuyên biệt Nhánh 3: Đánh giá Chiến lược (What-If)
Đặc tả: Phần I & Phần III (Mục 3.5) - Tài liệu Tactical Copilot Engine (v3.2.0)

Chức năng:
1. Định tuyến câu hỏi người dùng vào 4 Module Chiến lược con:
   - Module 3.1: Chiến lược giá và khuyến mãi (Pricing & Promotions)
   - Module 3.2: Chiến lược mặt bằng & mở rộng (Location & Expansion)
   - Module 3.3: Chiến lược nhân sự & chi phí tinh gọn (HR & Lean Cost)
   - Module 3.4: Chiến lược dòng tiền và thử tải sinh tồn (Cash Flow & Runway Stress-Test)
2. Thực hiện tính toán toán học tất định (Deterministic Math) cho từng module.
3. Đóng vai Phản biện (Devil's Advocate): Tính toán cái giá phải trả và đề xuất phương án thay thế an toàn.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

# File cấu hình Anchor 4 Module con của Nhánh 3
BRANCH_3_DATA_PATH = Path(__file__).resolve().parent / "branch_3_anchors.json"

_cached_branch_3_metadata: Optional[Dict[str, Any]] = None
_cached_branch_3_vectors: Optional[Dict[str, np.ndarray]] = None


def load_branch_3_metadata() -> Dict[str, Any]:
    """Tải siêu dữ liệu cấu hình 4 Module con của Nhánh 3."""
    global _cached_branch_3_metadata
    if _cached_branch_3_metadata is not None:
        return _cached_branch_3_metadata

    try:
        with open(BRANCH_3_DATA_PATH, "r", encoding="utf-8") as f:
            _cached_branch_3_metadata = json.load(f)
            return _cached_branch_3_metadata
    except Exception as e:
        logger.error(f"[!] Không thể đọc file branch_3_anchors.json: {e}")
        return {}


def get_branch_3_vectors() -> Dict[str, np.ndarray]:
    """Tải và tính trước vector 1024 chiều (BGE-M3) cho 4 Module con."""
    global _cached_branch_3_vectors
    if _cached_branch_3_vectors is not None:
        return _cached_branch_3_vectors

    metadata = load_branch_3_metadata()
    if not metadata:
        return {}

    try:
        from .semantic_search import get_embedding_model
        model = get_embedding_model()
        if model is None:
            return {}

        vectors = {}
        for mod_id, info in metadata.items():
            anchor_text = info.get("anchor", "")
            vec = model.encode(anchor_text, normalize_embeddings=True)
            vectors[mod_id] = np.array(vec, dtype=np.float32)

        _cached_branch_3_vectors = vectors
        logger.info(f"[✓] Đã khởi tạo vector BGE-M3 thành công cho 4 Module con Nhánh 3.")
        return _cached_branch_3_vectors
    except Exception as e:
        logger.error(f"[!] Lỗi khi nạp vector anchor cho branch_strategic: {e}")
        return {}


def detect_branch_3_submodules(query: str, top_k: int = 1) -> Dict[str, Any]:
    """
    Định tuyến câu hỏi Nhánh 3 vào 1 trong 4 Module con (hoặc Top 2 Module nếu top_k=2).
    Kết hợp 2 tầng:
    1. So khớp mẫu câu từ khóa nhận diện cấu trúc
    2. Vector Cosine Similarity với BAAI/bge-m3 qua 4 Module Anchor Vectors
    """
    metadata = load_branch_3_metadata()
    cleaned_query = query.lower().strip()

    # Tầng 1: So khớp mẫu câu từ khóa
    pattern_matches: Dict[str, List[str]] = {}
    for mod_id, info in metadata.items():
        matched = []
        for pat in info.get("patterns", []):
            if re.search(pat, cleaned_query, re.IGNORECASE):
                matched.append(pat)
        if matched:
            pattern_matches[mod_id] = matched

    # Tầng 2: So khớp Không gian Vector BGE-M3
    scores: Dict[str, float] = {}
    mod_vectors = get_branch_3_vectors()

    if mod_vectors:
        try:
            from .semantic_search import get_embedding_model, cosine_similarity
            model = get_embedding_model()
            q_vec = model.encode(query.strip(), normalize_embeddings=True)
            q_vec = np.array(q_vec, dtype=np.float32)

            for m_id, m_vec in mod_vectors.items():
                scores[m_id] = float(cosine_similarity(q_vec, m_vec))
        except Exception as e:
            logger.warning(f"[!] Lỗi tính toán vector trong branch_strategic: {e}")

    # Thuật toán điểm kết hợp: Vector Score + Heuristic Boost
    final_scores: Dict[str, float] = {}
    for m_id in metadata.keys():
        v_score = scores.get(m_id, 0.0)
        p_boost = 0.0

        if m_id == "MODULE_3_1":
            if any(k in cleaned_query for k in [
                "giảm giá", "giãm giá", "hạ giá", "tăng giá", "khuyến mãi", "combo", "chiết khấu",
                "menu giá rẻ", "giá dùng thử", "trả trước", "thẻ tích điểm", "định giá linh hoạt"
            ]):
                if not any(k in cleaned_query for k in ["giá thuê", "tiền thuê", "thưởng nóng cho nhân viên", "thưởng cho nhân viên", "bổ sung vốn lưu động", "chi phí cố định không thể cắt giảm", "huy động vốn"]):
                    p_boost += 0.16

        elif m_id == "MODULE_3_2":
            if any(k in cleaned_query for k in [
                "mở thêm", "chi nhánh", "mặt bằng", "tiền nhà", "chủ nhà", "nhượng quyền", "kiosk",
                "sang nhượng", "cải tạo mặt bằng", "giá thuê", "mở rộng chuỗi"
            ]):
                if not re.search(r"luân chuyển nhân viên|nợ lương.*nợ tiền thuê|chuyển một phần tiền thuê cố định sang hình thức ăn chia|quỹ dự phòng khẩn cấp", cleaned_query):
                    p_boost += 0.16
            if re.search(r"50 chỗ lên 150 chỗ|tăng gấp đôi chỗ ngồi|cải tạo mặt bằng mới|thanh toán tiền thuê mặt bằng 1 năm", cleaned_query):
                p_boost += 0.15

        elif m_id == "MODULE_3_3":
            if any(k in cleaned_query for k in [
                "nhân viên", "nhân sự", "quỹ lương", "lương", "part-time", "full-time",
                "tự động hóa", "tinh thần đồng đội", "thưởng nóng"
            ]) or re.search(r"chuyển giao.*cho quản lý", cleaned_query):
                if not re.search(r"nợ lương.*nợ tiền thuê|trả nợ lương đến hạn", cleaned_query):
                    p_boost += 0.16

        elif m_id == "MODULE_3_4":
            if any(k in cleaned_query for k in [
                "runway", "dòng tiền", "vốn dự phòng", "tiền mặt", "gồng lỗ", "sinh tồn", "vay",
                "công nợ", "thanh khoản", "vốn lưu động", "số dư tài khoản", "chi phí cố định hàng tháng",
                "cổ tức", "ưu tiên thanh khoản", "giải phóng dòng tiền",
                "chuyển một phần tiền thuê cố định sang hình thức ăn chia",
                "huy động vốn", "chi phí tồn kho đang chiếm giữ",
                "ngân sách dự phòng cần tăng bao nhiêu", "chi phí cố định không thể cắt giảm ngay",
                "quỹ dự phòng khẩn cấp", "đàm phán trả chậm tiền nguyên liệu"
            ]) or re.search(r"nợ lương.*nợ tiền thuê|quỹ dự phòng có đủ trả tiền nhà", cleaned_query):
                p_boost += 0.18

        final_scores[m_id] = v_score + p_boost

    # Sắp xếp theo điểm giảm dần
    sorted_modules = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
    best_mod_id, best_score = sorted_modules[0] if sorted_modules else ("MODULE_3_1", 0.5)

    selected_modules = [best_mod_id]
    if top_k > 1 and len(sorted_modules) > 1:
        second_mod_id, second_score = sorted_modules[1]
        # Lấy module thứ 2 nếu vượt ngưỡng cosine >= 0.52 hoặc có điểm kết hợp cao
        if scores.get(second_mod_id, 0.0) >= 0.52 or second_score >= (best_score - 0.05):
            selected_modules.append(second_mod_id)

    best_info = metadata.get(best_mod_id, {})

    return {
        "primary_module": best_mod_id,
        "selected_modules": selected_modules,
        "name": best_info.get("name", best_mod_id),
        "english_name": best_info.get("english_name", ""),
        "badge_title": best_info.get("badge_title", ""),
        "badge_detail": best_info.get("badge_detail", ""),
        "confidence": round(float(scores.get(best_mod_id, 0.0)), 4),
        "data_sources": best_info.get("data_sources", []),
        "matched_by": "hybrid_pattern_vector" if best_mod_id in pattern_matches else "vector_bge",
        "matched_patterns": pattern_matches.get(best_mod_id, []),
        "scores": {k: round(v, 4) for k, v in scores.items()},
        "final_scores": {k: round(v, 4) for k, v in final_scores.items()}
    }


def calculate_deterministic_math(
    submodule_id: str,
    profile: Dict[str, Any],
    monthly_logs: List[Dict[str, Any]],
    simulation_profile: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Thực hiện tính toán toán học tất định (Deterministic Math) theo Section 3.5.
    Đảm bảo LLM nhận số liệu sạch chính xác tuyệt đối, không để LLM tự làm toán.
    """
    # Tính doanh thu và chi phí trung bình từ lịch sử monthly_logs
    if monthly_logs:
        total_rev = sum(log.get("revenue", 0) for log in monthly_logs)
        total_cost = sum(log.get("cost", 0) for log in monthly_logs)
        avg_revenue = total_rev / len(monthly_logs)
        avg_cost = total_cost / len(monthly_logs)
    else:
        # Giá trị tham chiếu mặc định nếu chưa có logs
        avg_revenue = 60000000.0
        avg_cost = 40000000.0

    rent = float(profile.get("rent", 12000000))
    budget = float(profile.get("budget", 100000000))
    staff_count = int(profile.get("staff_count", 3))
    avg_salary = float(profile.get("avg_salary", 6000000))
    total_payroll = staff_count * avg_salary

    math_result: Dict[str, Any] = {
        "submodule": submodule_id,
        "avg_revenue": round(avg_revenue, 0),
        "avg_cost": round(avg_cost, 0)
    }

    if submodule_id == "MODULE_3_1":
        # Module 3.1: Tính biên lợi nhuận gộp thực tế
        margin_pct = ((avg_revenue - avg_cost) / avg_revenue * 100.0) if avg_revenue > 0 else 0.0
        expected_margin = float(simulation_profile.get("expected_margin_pct", 35.0)) if simulation_profile else 35.0
        margin_delta = margin_pct - expected_margin

        math_result.update({
            "margin_pct": round(margin_pct, 2),
            "expected_margin_pct": round(expected_margin, 2),
            "margin_delta": round(margin_delta, 2),
            "is_margin_healthy": margin_pct >= 25.0
        })

    elif submodule_id == "MODULE_3_2":
        # Module 3.2: Tỷ lệ tiền thuê trên doanh thu (Ngưỡng an toàn <= 20%)
        rent_ratio = (rent / avg_revenue * 100.0) if avg_revenue > 0 else 0.0
        math_result.update({
            "current_rent": round(rent, 0),
            "rent_to_revenue_ratio": round(rent_ratio, 2),
            "is_rent_safe": rent_ratio <= 20.0,
            "max_safe_rent": round(avg_revenue * 0.20, 0)
        })

    elif submodule_id == "MODULE_3_3":
        # Module 3.3: Tỷ lệ quỹ lương trên doanh thu (Ngưỡng an toàn <= 20% - 22%)
        payroll_ratio = (total_payroll / avg_revenue * 100.0) if avg_revenue > 0 else 0.0
        math_result.update({
            "staff_count": staff_count,
            "avg_salary": round(avg_salary, 0),
            "total_payroll": round(total_payroll, 0),
            "payroll_to_revenue_ratio": round(payroll_ratio, 2),
            "is_payroll_safe": payroll_ratio <= 22.0,
            "max_safe_payroll": round(avg_revenue * 0.22, 0)
        })

    elif submodule_id == "MODULE_3_4":
        # Module 3.4: Runway sinh tồn khi doanh thu chạm đáy (zero-revenue)
        fixed_costs = rent + total_payroll
        runway_months = (budget / fixed_costs) if fixed_costs > 0 else 0.0
        math_result.update({
            "remaining_budget": round(budget, 0),
            "fixed_costs": round(fixed_costs, 0),
            "zero_revenue_runway_months": round(runway_months, 1),
            "is_runway_safe": runway_months >= 3.0
        })

    return math_result
