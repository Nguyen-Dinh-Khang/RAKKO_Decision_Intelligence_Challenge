"""
branch_competitive.py - Module Xử lý Chuyên biệt Nhánh 4: Phản công Cạnh tranh Vi mô (Micro-Defense)
Đặc tả: Phần I & Phần III (Mục 3.6), Phần IV (Mục 4.2) - Tactical Copilot Engine (v3.2.0)

Chức năng:
1. Chấm điểm 6 Module Chiến lược phản công cạnh tranh:
   - Module 4.1: Hạ giá món đơn có kiểm soát (Controlled Unit Price Defense)
   - Module 4.2: Combo bù trừ & Món mới (Bundle & Cross-Sell)
   - Module 4.3: Khắc chế điểm yếu đối thủ (Weakness Exploitation & Inversion)
   - Module 4.4: Khai phá tệp khách hàng mới (Flank Segment Pivot)
   - Module 4.5: Nâng cấp Tiện ích & Trải nghiệm (Frictionless In-store Experience)
   - Module 4.6: Khóa chân, giữ khách quen & Marketing (Retention & Loyalty)
2. Công thức tính điểm tổng hợp chuẩn hóa:
   Total_Score_k = 0.35 * S_Intent^(k) + 0.65 * S_Feasibility^(k)
3. Chọn Top 3 Chiến lược tối ưu nhất và đóng gói Markdown Checklist (- [ ]).
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

# File cấu hình Anchor 6 Module con của Nhánh 4
BRANCH_4_DATA_PATH = Path(__file__).resolve().parent / "branch_4_anchors.json"

_cached_branch_4_metadata: Optional[Dict[str, Any]] = None
_cached_branch_4_vectors: Optional[Dict[str, np.ndarray]] = None


def load_branch_4_metadata() -> Dict[str, Any]:
    """Tải siêu dữ liệu cấu hình 6 Module con của Nhánh 4."""
    global _cached_branch_4_metadata
    if _cached_branch_4_metadata is not None:
        return _cached_branch_4_metadata

    try:
        with open(BRANCH_4_DATA_PATH, "r", encoding="utf-8") as f:
            _cached_branch_4_metadata = json.load(f)
            return _cached_branch_4_metadata
    except Exception as e:
        logger.error(f"[!] Không thể đọc file branch_4_anchors.json: {e}")
        return {}


def get_branch_4_vectors() -> Dict[str, np.ndarray]:
    """Tải và tính trước vector 1024 chiều (BGE-M3) cho 6 Module con."""
    global _cached_branch_4_vectors
    if _cached_branch_4_vectors is not None:
        return _cached_branch_4_vectors

    metadata = load_branch_4_metadata()
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

        _cached_branch_4_vectors = vectors
        logger.info(f"[✓] Đã khởi tạo vector BGE-M3 thành công cho 6 Module con Nhánh 4.")
        return _cached_branch_4_vectors
    except Exception as e:
        logger.error(f"[!] Lỗi khi nạp vector anchor cho branch_competitive: {e}")
        return {}


def calculate_intent_scores(query: str) -> Dict[str, float]:
    """
    Tính điểm ý định S_Intent^(k) trong thang điểm [0, 100] cho 6 Module con.
    Kết hợp Vector Cosine BGE-M3 chuẩn hóa + Heuristic Pattern Matching.
    """
    metadata = load_branch_4_metadata()
    cleaned_query = query.lower().strip()
    mod_vectors = get_branch_4_vectors()

    raw_cosines: Dict[str, float] = {}
    if mod_vectors:
        try:
            from .semantic_search import get_embedding_model, cosine_similarity
            model = get_embedding_model()
            q_vec = model.encode(cleaned_query, normalize_embeddings=True)
            q_vec = np.array(q_vec, dtype=np.float32)

            for m_id, m_vec in mod_vectors.items():
                sim = float(cosine_similarity(q_vec, m_vec))
                raw_cosines[m_id] = max(0.0, sim)
        except Exception as e:
            logger.warning(f"[!] Lỗi tính toán vector trong calculate_intent_scores: {e}")

    # Chuyển đổi điểm Cosine về thang [0, 100] và cộng điểm Heuristic
    intent_scores: Dict[str, float] = {}

    # Nhận diện tín hiệu ngữ nghĩa chuyên sâu cho từng Module
    # 1. Tín hiệu hạ giá món đơn (Module 4.1):
    is_price_action = bool(
        re.search(r"(hạ giá theo|giảm giá theo|tôi hạ giá|tôi giảm giá|giảm giá.*xuống để|hạ giá.*xuống|hạ giá món \d+k|hạ giá an toàn|d_max|margin floor|biên sàn|ngưỡng trần giảm giá|chiến tranh giảm giá|chiến tranh giá|tự sát tài chính|mức giá sàn|dư địa giảm giá|phương án hạ giá món phễu|gồng lỗ.*giảm giá|tính toán chi phí.*hạ giá|hạ giá riêng cho khách|lượng bán ra.*bù đắp|khoảng giảm giá an toàn|đại hạ giá)", cleaned_query)
        or (re.search(r"(bán rẻ hơn|phá giá)", cleaned_query) and re.search(r"(hạ giá|giảm giá|bán lẻ|món chính)", cleaned_query) and not re.search(r"combo|bán kèm", cleaned_query))
    )

    # 2. Tín hiệu combo / bán chéo (Module 4.2):
    is_bundle_action = bool(
        re.search(r"(tạo combo|thiết kế combo|ra mắt combo|combo bù trừ|bán kèm|bán chéo|cross-sell|upsell|gói sản phẩm|combo 3 món|combo đồ ăn trưa|combo tiết kiệm|mua 2.*tặng 1|dùng thử cho 2 người|ready-to-eat|đóng gói sẵn.*quầy|quẩy và trứng chần|combo món đôi|luân phiên thay đổi.*combo|chi phí nguyên liệu.*combo|bán kèm trà sữa|combo bữa sáng|combo gia đình|combo dùng thử)", cleaned_query)
        or (re.search(r"combo", cleaned_query) and not is_price_action)
        or (re.search(r"món mới", cleaned_query) and not re.search(r"khách hàng thân thiết|khách quen|hội viên", cleaned_query))
    )

    # 3. Tín hiệu điểm yếu đối thủ (Module 4.3):
    is_competitor_weakness = bool(
        re.search(r"(đối thủ|quán bên|quán đối diện|quán khác|quán xung quanh).*(bị chê|chê|phàn nàn|than phiền|phục vụ chậm|ra món lâu|chậm|chất lượng|nguội|vệ sinh|bẩn|bí bách|nóng nực|chật|không có|không cho|không nhận|chỉ nhận tiền mặt|thiếu|ly nhựa|đá viên|nhạc.*ồn|cũ|dở|mặn ngọt|nhầm|bảo hành|hết món|phốt|lạnh nhạt|đóng cửa|thất vọng|xếp hàng|chờ hơn|chờ lâu|chờ đợi)", cleaned_query)
        or re.search(r"(khách chê|khách than|khách phàn nàn|tử huyệt|điểm yếu.*đối thủ|khắc chế.*đối thủ|lật ngược tình thế|phản đòn truyền thông|biến việc đối thủ|đối thủ.*chê|đối thủ dùng đá|bàn ghế của đối thủ)", cleaned_query)
    )

    # 4. Tín hiệu khách quen / loyalty / retention (Module 4.6):
    is_loyalty = bool(
        re.search(r"(thẻ vip|thẻ thành viên|thẻ trả trước|tích điểm|tích dấu|đổi quà|switching costs|rào cản chuyển đổi|khách hàng ruột|khách ruột|khách thân thiết|khách hàng thân thiết|khách hàng trung thành|lòng trung thành|đại sứ thương hiệu|tri ân|voucher cá nhân|sở thích cá nhân.*khách|kỷ niệm.*gắn bó|retention rate|tỷ lệ.*quay lại|vật phẩm độc quyền|referral|giới thiệu bạn bè|top 20 khách|vinh danh|kích hoạt lại.*khách|ngừng ghé quán|cộng đồng người yêu thích|cộng đồng khách hàng thân thiết|bảo vệ thương hiệu trước sự công kích|khóa chân|hội viên|hội viên thân thiết|quyền lợi độc quyền|không thể sao chép)", cleaned_query)
        or (re.search(r"khách quen", cleaned_query) and not re.search(r"(thu hút.*vãng lai|du lịch|đối thủ.*khách quen)", cleaned_query))
    )

    # 5. Tín hiệu bọc sườn / tệp khách mới (Module 4.4):
    is_flank_segment = bool(
        re.search(r"(tệp khách mới|tệp khách|phân khúc|bọc sườn|flanking|thị trường ngách|dân văn phòng|cơm văn phòng|công sở|gia đình|trẻ em|kids menu|ăn kiêng|eat-clean|tập gym|phòng gym|cú đêm|du lịch|vãng lai|freelancer|phụ huynh|học sinh|người lớn tuổi|thảo mộc|tài xế công nghệ|meal plan|bữa ăn theo tuần|chung cư|cư dân|chạy bộ|đi một mình|quầy bar đơn|tiệc trà|tea-break|ăn chay|ngày rằm|hẹn hò|lãng mạn|giới trẻ|khách nước ngoài|menu song ngữ|mảng đồ ăn vặt|lấn sân sang|doanh nghiệp)", cleaned_query)
    )
    is_flank_action = bool(
        re.search(r"(thu hút tệp|khai phá|bọc sườn|flanking|tiếp cận tệp|du lịch vãng lai|vãng lai)", cleaned_query)
    )

    # 6. Tín hiệu tiện ích & trải nghiệm tại quán (Module 4.5):
    is_instore_exp = bool(
        re.search(r"(thái độ phục vụ.*niềm nở|cúi chào|dưới 60 giây|ra món dưới|tối ưu.*quy trình pha chế|máy lạnh mát|phun sương|cây xanh|ổ cắm điện|wifi tốc độ cao|sạc điện thoại không dây|khoảng cách giữa các bàn|quẹt thẻ.*tại bàn|thanh toán tại bàn|túi quai giấy|mùi thức ăn bám|châm thêm nước|ghế bọc nệm|gương soi|góc chụp ảnh|check-in|nhiệt độ phòng|dù che mưa|xử lý phàn nàn.*3 phút|bàn ghế.*laptop|mùi hương tinh dầu|giữ xe ô tô|quầy tự phục vụ|chuông gọi phục vụ|nhà vệ sinh.*khô ráo|khu vực ngồi ngoài trời|trang phục đồng bộ|bảng tên|dọn bàn.*dưới 30 giây|đầu tư nâng cấp trải nghiệm|tiện ích miễn phí)", cleaned_query)
    )

    for m_id, info in metadata.items():
        base_cos = raw_cosines.get(m_id, 0.40)
        # Chuẩn hóa cosine [0.35, 0.65] thành thang [40, 90] điểm
        norm_score = np.clip((base_cos - 0.35) / 0.30 * 50.0 + 40.0, 30.0, 95.0)

        # Kiểm tra mẫu từ khóa đặc thù của từng module trong metadata
        pats = info.get("patterns", [])
        matched = any(re.search(p, cleaned_query, re.IGNORECASE) for p in pats)
        if matched:
            norm_score += 10.0

        # Áp dụng heuristic ưu tiên chuẩn xác theo thứ tự quyết định nghiệp vụ
        if is_price_action and m_id == "MODULE_4_1":
            norm_score += 35.0
        elif is_bundle_action and m_id == "MODULE_4_2":
            norm_score += 35.0
        elif is_competitor_weakness and not is_price_action and m_id == "MODULE_4_3":
            norm_score += 35.0
        elif is_flank_action and m_id == "MODULE_4_4":
            norm_score += 35.0
        elif is_loyalty and not is_competitor_weakness and "cúi chào" not in cleaned_query and m_id == "MODULE_4_6":
            norm_score += 35.0
        elif is_flank_segment and not is_competitor_weakness and not is_price_action and not is_loyalty and m_id == "MODULE_4_4":
            norm_score += 35.0
        elif (is_instore_exp or "cúi chào" in cleaned_query) and not is_competitor_weakness and m_id == "MODULE_4_5":
            norm_score += 35.0

        intent_scores[m_id] = round(float(np.clip(norm_score, 10.0, 100.0)), 2)

    return intent_scores


def calculate_feasibility_scores(
    profile: Dict[str, Any],
    monthly_logs: List[Dict[str, Any]],
    competitors: Optional[List[Dict[str, Any]]] = None,
    simulation_profile: Optional[Dict[str, Any]] = None,
    model_id: int = 105
) -> Dict[str, float]:
    """
    Tính điểm khả thi thực tế S_Feasibility^(k) trong thang [0, 100] cho 6 Module theo Mục 3.6.
    Đảm bảo tính toán toán học tất định (Deterministic Math).
    """
    feas_scores: Dict[str, float] = {}

    # Dữ liệu tài chính cơ sở
    if monthly_logs:
        avg_revenue = sum(log.get("revenue", 0) for log in monthly_logs) / len(monthly_logs)
        avg_cost = sum(log.get("cost", 0) for log in monthly_logs) / len(monthly_logs)
    else:
        avg_revenue = 60000000.0
        avg_cost = 40000000.0

    expected_margin_pct = float(simulation_profile.get("expected_margin_pct", 35.0)) if simulation_profile else 35.0
    staff_count = int(profile.get("staff_count", 2))

    # -------------------------------------------------------------
    # 1. Module 4.1: Hạ giá món đơn có kiểm soát
    # Công thức:
    # margin_floor = max(0.15, expected_margin_pct / 100 * 0.5)
    # d_max = 1 - (avg_cost / (avg_revenue * (1 - margin_floor)))
    # -------------------------------------------------------------
    margin_floor = max(0.15, (expected_margin_pct / 100.0) * 0.5)
    if avg_revenue > 0 and (1.0 - margin_floor) > 0:
        d_max = 1.0 - (avg_cost / (avg_revenue * (1.0 - margin_floor)))
    else:
        d_max = 0.0

    if d_max <= 0.0:
        score_4_1 = 0.0  # Hard Veto: Biên lãi quá mỏng, cấm hạ giá
    elif d_max <= 0.05:
        score_4_1 = 40.0
    elif d_max <= 0.15:
        score_4_1 = 85.0
    else:
        score_4_1 = 100.0
    feas_scores["MODULE_4_1"] = score_4_1

    # -------------------------------------------------------------
    # 2. Module 4.2: Combo bù trừ & Món mới
    # Phân tầng Tier mô hình:
    # Tier S (85-100đ): Cafe (102), Trà sữa (101), Ăn vặt (106), Quán nhậu (104)
    # Tier A (65-80đ): Bánh mì (105), Quán sáng (103), Cơm văn phòng (107)
    # Tier B (25-40đ): Bán lẻ / Tạp hóa (108)
    # Tier C (0-10đ): Sửa xe, Thuốc tây (109, 110)
    # -------------------------------------------------------------
    tier_s_models = [101, 102, 104, 106]
    tier_a_models = [103, 105, 107]
    tier_b_models = [108]

    if model_id in tier_s_models:
        score_4_2 = 94.0
    elif model_id in tier_a_models:
        score_4_2 = 78.0
    elif model_id in tier_b_models:
        score_4_2 = 35.0
    else:
        score_4_2 = 10.0
    feas_scores["MODULE_4_2"] = score_4_2

    # -------------------------------------------------------------
    # 3. Module 4.3: Khắc chế điểm yếu đối thủ
    # Quét dữ liệu đối thủ DB2 trong bán kính 1km:
    # Nếu có >= 2 quán bị khách chê cùng 1 vấn đề -> S_Feas = 95 - 100đ
    # Nếu có 1 quán bị chê -> 75đ
    # Mặc định: 45đ
    # -------------------------------------------------------------
    comp_list = competitors or []
    complaints_count = 0
    for comp in comp_list:
        weaknesses = comp.get("market_weakness", []) or comp.get("weaknesses", [])
        if weaknesses:
            complaints_count += len(weaknesses)

    if complaints_count >= 2:
        score_4_3 = 95.0
    elif complaints_count == 1:
        score_4_3 = 75.0
    else:
        score_4_3 = 60.0  # Mặc định cơ hội trung bình
    feas_scores["MODULE_4_3"] = score_4_3

    # -------------------------------------------------------------
    # 4. Module 4.4: Khai phá tệp khách hàng mới (Flank Segment Pivot)
    # Điểm tiềm năng tệp khách mới: Mặc định 85-90đ nếu ở khu vực đông đúc
    # -------------------------------------------------------------
    score_4_4 = 88.0
    feas_scores["MODULE_4_4"] = score_4_4

    # -------------------------------------------------------------
    # 5. Module 4.5: Nâng cấp Tiện ích & Trải nghiệm
    # Cơ sở 50đ + 25đ (nếu đối thủ bị chê tốc độ/không gian) + 20đ (nếu đủ >= 2 nhân sự)
    # -------------------------------------------------------------
    score_4_5 = 50.0
    if complaints_count >= 1:
        score_4_5 += 25.0
    if staff_count >= 2:
        score_4_5 += 20.0
    feas_scores["MODULE_4_5"] = min(100.0, score_4_5)

    # -------------------------------------------------------------
    # 6. Module 4.6: Khóa chân, giữ khách quen & Marketing
    # 85đ cho ngành hàng Daily Habit (Cafe 102, Trà sữa 101, Bánh mì 105)
    # 45đ cho các ngành hàng ăn chơi cuối tuần
    # -------------------------------------------------------------
    daily_habit_models = [101, 102, 105, 103]
    if model_id in daily_habit_models:
        score_4_6 = 85.0
    else:
        score_4_6 = 50.0
    feas_scores["MODULE_4_6"] = score_4_6

    return feas_scores


def evaluate_branch_4_competitive(
    query: str,
    profile: Optional[Dict[str, Any]] = None,
    monthly_logs: Optional[List[Dict[str, Any]]] = None,
    competitors: Optional[List[Dict[str, Any]]] = None,
    simulation_profile: Optional[Dict[str, Any]] = None,
    model_id: int = 105,
    top_k: int = 3
) -> Dict[str, Any]:
    """
    Đánh giá toàn diện 6 Module Chiến lược Phản công Cạnh tranh Vi mô (Nhánh 4).
    Quy tắc chuẩn hóa:
    Total_Score_k = 0.35 * S_Intent^(k) + 0.65 * S_Feasibility^(k)
    Dùng np.argsort() chọn ra Top 3 Module có điểm cao nhất.
    """
    prof = profile or {}
    logs = monthly_logs or []
    comps = competitors or []
    sim_prof = simulation_profile or {}

    metadata = load_branch_4_metadata()

    # Bước 1: Tính điểm Ý định (S_Intent) và Khả thi (S_Feasibility)
    intent_scores = calculate_intent_scores(query)
    feas_scores = calculate_feasibility_scores(
        profile=prof,
        monthly_logs=logs,
        competitors=comps,
        simulation_profile=sim_prof,
        model_id=model_id
    )

    # Bước 2: Chấm điểm tổng hợp chuẩn hóa
    total_scores: Dict[str, float] = {}
    for m_id in metadata.keys():
        s_intent = intent_scores.get(m_id, 50.0)
        s_feas = feas_scores.get(m_id, 50.0)
        total = 0.35 * s_intent + 0.65 * s_feas
        total_scores[m_id] = round(float(total), 2)

    # Bước 3: Sắp xếp lấy Top Module
    sorted_modules = sorted(total_scores.items(), key=lambda x: x[1], reverse=True)
    top_modules = [m_id for m_id, _ in sorted_modules[:top_k]]
    primary_module = top_modules[0] if top_modules else "MODULE_4_2"

    detailed_results = []
    for rank, (m_id, tot_score) in enumerate(sorted_modules, start=1):
        info = metadata.get(m_id, {})
        detailed_results.append({
            "rank": rank,
            "module_id": m_id,
            "name": info.get("name", m_id),
            "badge_title": info.get("badge_title", ""),
            "badge_detail": info.get("badge_detail", ""),
            "intent_score": intent_scores.get(m_id, 0.0),
            "feasibility_score": feas_scores.get(m_id, 0.0),
            "total_score": tot_score,
            "is_top_selected": m_id in top_modules
        })

    primary_info = metadata.get(primary_module, {})

    return {
        "primary_module": primary_module,
        "primary_name": primary_info.get("name", ""),
        "primary_badge": primary_info.get("badge_title", ""),
        "top_modules": top_modules,
        "intent_scores": intent_scores,
        "feasibility_scores": feas_scores,
        "total_scores": total_scores,
        "detailed_rankings": detailed_results
    }
