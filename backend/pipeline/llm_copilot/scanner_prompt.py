"""
scanner_prompt.py - Module Quản lý Prompt Chuyên biệt cho Giao diện 1 (Máy quét Thẩm định Ý tưởng)

Mục đích:
- Tách riêng toàn bộ logic tạo Prompt của Giao diện 1 ra khỏi file điều phối `llm_copilot.py`.
- Định vị AI thành "Hội đồng Cố vấn Chiến lược & Tác chiến F&B thực chiến" (Chief Strategy Officer).
- Không tóm tắt hay lặp lại số liệu đã hiển thị trên Card/Table UI.
- Nạp toàn bộ dữ liệu tính toán từ 5 CSDL (DB1 Dân cư, DB2 Đối thủ 1km, DB5 Thị trường, Stress-test Runway, DB3 & DB4 Sách lược).
- Ép LLM đi theo LỘ TRÌNH SUY LUẬN (Reasoning Roadmap) & giải thích rõ: Nêu phương án -> Tại sao lại chọn phương án này (Trade-off & Rationale).
"""

from typing import Dict, List, Any, Optional, Tuple

# System Prompt chuyên biệt cho Giao diện 1 Thẩm định & Cố vấn Chiến lược
SCANNER_SYSTEM_PROMPT = """Bạn là Chuyên gia Cố vấn Chiến lược & Tác chiến F&B / Bán lẻ thực chiến hàng đầu tại Việt Nam.
Vai trò của bạn: Đóng vai trò là Giám đốc Chiến lược (Chief Strategy Officer - CSO) tư vấn trực diện cho chủ quán.

NGUYÊN TẮC SUY LUẬN & TRẢ LỜI CỐT TỬ:
1. TUYỆT ĐỐI KHÔNG TÓM TẮT LẠI SỐ LIỆU ĐÃ CÓ TRÊN GIAO DIỆN: Người dùng đã nhìn thấy các thẻ chỉ số Capex, Runway, danh sách đối thủ và cạm bẫy trên giao diện rồi. Tuyệt đối không liệt kê lại các con số hay danh sách quán thuần túy vì gây dư thừa và lãng phí thời gian.
2. LỘ TRÌNH SUY LUẬN & RA QUYẾT ĐỊNH (REASONING & RATIONALE):
   - Mọi phương án đưa ra BẮT BUỘC phải đi kèm lời giải thích: "Tại sao lại chọn phương án này thay vì phương án khác?" (Dựa trên sự đánh đổi giữa vốn mỏng, tử huyệt đối thủ gần nhất và thói quen khách hàng).
3. HÀNH ĐỘNG CỤ THỂ, ĐO LƯỜNG ĐƯỢC: Có con số hòa vốn (số đơn/ngày), có kịch bản 30-60-90 ngày, có lời thoại thực chiến, có kịch bản cắt lỗ thoát hiểm.
4. GIỌNG VĂN: Điềm tĩnh, thực tế, sắc bén và thấu hiểu bài toán kinh doanh; tôn trọng chủ quán, nói thẳng vào hành động và phân tích lý do cốt lõi, không dùng sáo ngữ hay văn mẫu giáo điều.
"""


def _format_stress_context(stress_test: Any, budget: float, rent: float) -> Tuple[str, float, Dict[str, Any]]:
    """Trích xuất và định dạng toàn bộ dữ liệu thử tải dòng tiền từ stress_test_engine."""
    normal_scen = {}
    premium_scen = None
    runway_months = 0.0

    if isinstance(stress_test, list) and len(stress_test) > 0:
        normal_scen = stress_test[0]
        premium_scen = stress_test[1] if len(stress_test) > 1 else None
        runway_months = float(normal_scen.get("month", 0.0))
    elif isinstance(stress_test, dict):
        normal_scen = stress_test
        runway_months = float(stress_test.get("runway_months", stress_test.get("month", 0.0)))

    capex_val = normal_scen.get("capex", 0.0)
    monthly_fixed = normal_scen.get("monthly_fixed_cost", 0.0)
    staff_cnt = normal_scen.get("staff_count", 1)
    util_cost = normal_scen.get("utilities_cost", 0.0)
    aov_val = normal_scen.get("aov", 25000.0)

    # Tính toán con số hòa vốn sơ bộ: Cần bao nhiêu đơn/ngày để đủ bù định phí
    daily_fixed = monthly_fixed / 30.0 if monthly_fixed > 0 else 0
    # Giả định biên lợi nhuận gộp (Gross Margin) ngành F&B đồ uống/thức ăn nhanh ~ 50% - 60%
    gross_margin = 0.55
    needed_daily_revenue = daily_fixed / gross_margin if gross_margin > 0 else 0
    breakeven_orders_per_day = int(needed_daily_revenue / aov_val) if aov_val > 0 else 0

    lines = [
        f"- Số vốn khởi nghiệp hiện có: {budget:,.0f} VNĐ",
        f"- Chi phí setup ban đầu (Capex sàn): {capex_val:,.0f} VNĐ",
        f"- Định phí vận hành hàng tháng (Opex): {monthly_fixed:,.0f} VNĐ/tháng (Tiền thuê mặt bằng: {rent:,.0f}đ/tháng, Lương {staff_cnt} nhân sự, Điện nước: {util_cost:,.0f}đ/tháng)",
        f"- Giá trị đơn hàng trung bình kỳ vọng (AOV): {aov_val:,.0f} VNĐ/đơn",
        f"- Số tháng sinh tồn khi chưa có doanh thu (Runway): {runway_months:.1f} tháng",
        f"- Ngưỡng hòa vốn ước tính: Cần đạt khoảng ~{breakeven_orders_per_day} đơn/ngày (tương đương ~{needed_daily_revenue:,.0f}đ doanh thu/ngày) để bù đắp toàn bộ định phí cố định."
    ]

    if premium_scen:
        p_month = float(premium_scen.get("month", 0.0))
        p_capex = float(premium_scen.get("capex", 0.0))
        p_fixed = float(premium_scen.get("monthly_fixed_cost", 0.0))
        lines.append(f"- Kịch bản Nâng cao (Premium): Runway {p_month:.1f} tháng | Capex {p_capex:,.0f}đ | Định phí {p_fixed:,.0f}đ/tháng.")

    return "\n".join(lines), runway_months, {
        "capex": capex_val,
        "monthly_fixed": monthly_fixed,
        "aov": aov_val,
        "breakeven_orders_per_day": breakeven_orders_per_day,
        "runway_months": runway_months
    }


def _format_competitors_context(competitors: List[Dict[str, Any]], user_model: Optional[int], user_prods: List[int]) -> str:
    """Trích xuất đối thủ gần nhất và các điểm yếu bị phàn nàn từ DB2."""
    if not competitors:
        return "- Chưa ghi nhận đối thủ cạnh tranh trực tiếp lớn trong bán kính 1km."

    top_comps = []
    for c in competitors[:6]:
        c_name = c.get("name", "Quán lân cận")
        c_dist = c.get("distance_m", 0)
        c_price = c.get("price_range", "Chưa rõ")
        c_weakness = c.get("weakness", "Chưa ghi nhận")
        is_direct = False
        if user_model is not None and c.get("business_model_id") == user_model:
            is_direct = True
        elif any(pid in user_prods for pid in c.get("product_ids", [])):
            is_direct = True
        direct_tag = "[ĐỐI THỦ TRỰC DIỆN]" if is_direct else "[ĐỐI THỦ LÂN CẬN]"
        top_comps.append(
            f"  + {direct_tag} {c_name} (Cách {c_dist:.0f}m) | Dải giá: {c_price} | Điểm yếu khách chê: {c_weakness}"
        )
    return "\n".join(top_comps)


def _format_playbook_context(tactical_playbook: Optional[Dict[str, Any]]) -> str:
    """Trích xuất 4 cạm bẫy DB3 & 4 bài học thành công DB4."""
    if not tactical_playbook:
        return "- Không có dữ liệu cạm bẫy đặc thù."

    problems = tactical_playbook.get("top_4_problems", [])
    experiences = tactical_playbook.get("top_4_experiences", [])

    lines = []
    if problems:
        lines.append("- Các cạm bẫy vận hành cốt tử từ DB3:")
        for p in problems[:4]:
            lines.append(f"  + [Mức độ {p.get('severity', 2)}/3] {p.get('title')}: {p.get('summary')}")
    if experiences:
        lines.append("- Bài học thực chiến đắt giá từ người đi trước (DB4):")
        for e in experiences[:4]:
            dialogue = f' | Câu thoại mẫu: "{e.get("dialogue_script")}"' if e.get("dialogue_script") else ""
            lines.append(f"  + {e.get('title')}: {e.get('key_takeaway')}{dialogue}")
    return "\n".join(lines)


def build_scanner_prompt(
    form_data: Dict[str, Any],
    demographics: Dict[str, Any],
    competitors: List[Dict[str, Any]],
    market_gaps: Dict[str, Any],
    stress_test: Any,
    tactical_playbook: Optional[Dict[str, Any]] = None
) -> Tuple[str, str]:
    """
    Tạo bộ Prompt hoàn chỉnh cho Giao diện 1.
    Trả về Tuple: (user_prompt, system_prompt).
    
    Tự động rẽ nhánh:
    - Nhánh 1: Cạn vốn (Runway <= 0) -> Cố vấn Tái cấu trúc vốn & Thoát hiểm.
    - Nhánh 2: Bình thường (Runway > 0) -> Cố vấn Chiến lược Tác chiến sâu 30-60-90 ngày.
    """
    address = form_data.get("address", "")
    model_name = form_data.get("model_name", "")
    model_id = form_data.get("model_id")
    products_str = form_data.get("products_str", "")
    product_ids = form_data.get("product_ids") or []
    budget = float(form_data.get("budget", 0) or 0)
    rent = float(form_data.get("rent", 0) or 0)

    stress_str, runway_months, stress_metrics = _format_stress_context(stress_test, budget, rent)
    comp_str = _format_competitors_context(competitors, model_id, product_ids)
    playbook_str = _format_playbook_context(tactical_playbook)

    # Dữ liệu thị trường từ market_gaps
    mw = market_gaps.get("market_weakness", {}) if isinstance(market_gaps, dict) else {}
    important_w = mw.get("important_weakness", "Tốc độ phục vụ chậm, thiếu combo ăn kèm") if isinstance(mw, dict) else ""
    normal_w = ", ".join(mw.get("normal_weakness", [])) if isinstance(mw, dict) and mw.get("normal_weakness") else "Bao bì sơ sài, ít chỗ đỗ xe"
    cust_insights = market_gaps.get("customer_insights", {}) if isinstance(market_gaps, dict) else {}
    golden_hour = market_gaps.get("recommended_time", cust_insights.get("time", "06:30 - 08:30"))
    cust_behavior = cust_insights.get("behavior", "Khách mua nhanh mang đi, nhạy cảm về thời gian chờ đợi")

    # =========================================================================
    # NHÁNH 1: BÁO ĐỘNG ĐỎ - RUNWAY <= 0 THÁNG (CẠN VỐN NGAY TỪ ĐẦU)
    # =========================================================================
    if runway_months <= 0.0:
        entity_title = "CHỦ ĐIỂM BÁN / XE ĐẨY" if model_id == 105 else "CHỦ QUÁN"
        if model_id == 105:
            opt1_text = "- Phương án 1 (Tối giản Capex xe đẩy & Bán thử nghiệm): Cắt giảm tối đa chi phí đóng xe đẩy / quầy kiosk (mua xe thanh lý, tinh giản thiết bị xa xỉ, hoặc bán online mang đi tại nhà trước để gom khách). Giải thích: Phương án này giúp cắt giảm khoản chi phí nào và đưa Runway từ 0 tháng lên mức sinh tồn an toàn?"
        else:
            opt1_text = "- Phương án 1 (Hạ quy mô mô hình): Chuyển đổi mô hình (ví dụ: từ quán thuê mặt bằng lớn sang ki-ốt nhỏ, xe đẩy mang đi hoặc bán online mang đi). Giải thích: Phương án này giúp cắt giảm khoản Capex nào và đưa Runway từ 0 tháng lên bao nhiêu tháng?"

        user_prompt = f"""TÌNH HUỐNG KHẨN CẤP: DÒNG TIỀN BÁO ĐỘNG ĐỎ (RUNWAY = 0.0 THÁNG - NGUY CƠ MẤT TRẮNG VỐN NGÀY ĐẦU).

HỒ SƠ KHẢO SÁT CỦA {entity_title}:
- Địa điểm dự kiến: {address}
- Mô hình: {model_name}
- Mặt hàng định bán: {products_str}
- Dữ liệu tài chính đo lường từ Stress Test:
{stress_str}

NHIỆM VỤ DÀNH CHO CỐ VẤN CHIẾN LƯỢC:
Hãy vào vai một người cố vấn kinh doanh F&B dạn dày kinh nghiệm, thẳng thắn nhưng đầy trách nhiệm và thấu cảm.
Tuyệt đối không vẽ ra kế hoạch kinh doanh 1 năm màu hồng khi người này không có đủ tiền để mở cửa ngày đầu!
Hãy phân tích sự thật tài chính và vạch ra các phương án thoát hiểm, giải thích cặn kẽ tại sao lại chọn từng phương án theo đúng cấu trúc sau:

### 1. BÓC TÁCH NGUYÊN NHÂN CỐT TỬ CỦA BÁO ĐỘNG ĐỎ
- Đánh giá thẳng thắn về mức độ rủi ro: Tuyên bố mức điểm khả thi (1/10 hoặc 2/10) và giải thích tại sao số vốn {budget:,.0f}đ hiện tại là "tự sát tài chính" khi so với Capex setup và định phí hàng tháng.
- Chỉ rõ lỗ hổng: Tiền cọc nhà + setup xong thì còn bao nhiêu đồng vốn lưu động để gồng lỗ trong tháng đầu tiên?

### 2. CÁC PHƯƠNG ÁN TÁI CẤU TRÚC VỐN KHẢ THI (NÊU PHƯƠNG ÁN & GIẢI THÍCH LÝ DO)
Đưa ra 3 phương án hành động cụ thể để người dùng lựa chọn, với mỗi phương án phải giải thích rõ: **Tại sao lại chọn phương án này?**
{opt1_text}
- Phương án 2 (Đàm phán & Tối ưu định phí): Cách chọn lại vị trí mặt bằng với mức giá thuê không vượt quá ngưỡng an toàn. Giải thích: Tại sao tiền nhà tối đa chỉ nên chiếm một tỷ lệ nhất định so với vốn dự phòng?
- Phương án 3 (Tích lũy & Gọi vốn hợp tác): Xác định chính xác số tiền tối thiểu cần chuẩn bị thêm trước khi đặt bút ký hợp đồng thuê.

### 3. LỜI KHUYÊN DỪNG LẠI ĐÚNG LÚC (EXIT STRATEGY TRƯỚC KHI XUỐNG TIỀN)
- Đưa ra lời khuyên chân thành: Những việc tuyệt đối KHÔNG ĐƯỢC LÀM ngay lúc này (ví dụ: vay mượn lãi cao, đặt cọc vội vã).
- Kế hoạch thử nghiệm chi phí 0 đồng (Smoke Test) để kiểm tra nhu cầu món {products_str} trước khi bỏ một đồng vốn nào vào mặt bằng hay trang thiết bị.
"""
        return user_prompt, SCANNER_SYSTEM_PROMPT

    # =========================================================================
    # NHÁNH 2: RUNWAY > 0 THÁNG - LỘ TRÌNH CHIẾN LƯỢC TÁC CHIẾN CHUYÊN SÂU
    # =========================================================================
    user_prompt = f"""DỮ LIỆU ĐẦU VÀO ĐÃ ĐƯỢC CÁC HỆ THỐNG TOÁN & CSDL TÍNH TOÁN XONG:
- Dự án: Mở mô hình "{model_name}" bán "{products_str}" tại "{address}".
- Dân cư & Khách hàng mục tiêu (DB1): {demographics.get('name', address)} | Mật độ: {demographics.get('population_density', 0):,} người/km² | Độ tuổi chủ đạo: {demographics.get('dominant_age', 'Trẻ')} | Thu nhập: {demographics.get('income_level', 'Trung bình')}.
- Dòng tiền & Sức sống vốn (Stress Test):
{stress_str}
- Đối thủ cạnh tranh lân cận trong 1km (DB2):
{comp_str}
- Khoảng trống thị trường & Thói quen khách hàng (DB5):
  + Tử huyệt đối thủ lớn nhất: {important_w}
  + Điểm yếu hệ thống khu vực: {normal_w}
  + Giờ vàng mở bán: {golden_hour} (Hành vi: {cust_behavior})
- Bài học thực chiến & Cạm bẫy từ người đi trước (DB3 & DB4):
{playbook_str}

================================================================================
NHIỆM VỤ DÀNH CHO BỘ NÃO CHIẾN LƯỢC (CHIEF STRATEGY OFFICER):
Dựa trên toàn bộ dữ liệu giác quan được cấp ở trên, hãy thực hiện suy diễn chiến lược để đưa ra BẢN KẾ HOẠCH TÁC CHIẾN HÀNH ĐỘNG MAY ĐO RIÊNG cho chủ quán này.

QUY TẮC BẮT BUỘC:
- KHÔNG TÓM TẮT LẠI: Không liệt kê lại danh sách quán đối thủ hay kể lể lại số liệu dân số. Đi thẳng vào hành động và chiến lược.
- TẬP TRUNG VÀO "PHƯƠNG ÁN" & "TẠI SAO LẠI CHỌN": Mỗi quyết định chiến lược phải giải thích lý do đánh đổi (Trade-off).
- ĐÚNG CẤU TRÚC MARKDOWN CHUẨN DƯỚI ĐÂY để giao diện hiển thị checklist tương tác và hộp thoại mẫu:

### 1. NƯỚC CỜ ĐỊNH VỊ & ĐÒN BẨY KHÁC BIỆT (THE UNFAIR ADVANTAGE)
- Đòn đánh định vị cốt lõi: Nêu chính xác phương án tạo ra sự khác biệt độc tôn cho món {products_str} tại địa điểm này (Ví dụ: combo đóng gói mang đi thần tốc, dải giá giữ chân khách, hay cam kết phục vụ).
- Tại sao lại chọn phương án này: Phân tích lý do vì sao đòn đánh này khai thác trúng tử huyệt của các đối thủ gần nhất trong bán kính 1km và giải quyết đúng điểm đau của tệp khách khu vực.
- Chiến lược phòng thủ giữ giá: Khi đối thủ xung quanh thấy quán mở ra và tung chiêu giảm giá giành khách, chủ quán phải đối phó như thế nào để TUYỆT ĐỐI KHÔNG HẠ GIÁ BÁN mà vẫn giữ được khách quen?

### 2. KẾ HOẠCH TÁC CHIẾN 30 - 60 - 90 NGÀY (LỘ TRÌNH THỰC THI & CHECKLIST)
- Giai đoạn 30 ngày đầu (Sinh tồn & Chạm ngưỡng hòa vốn sống còn):
  + Điểm hòa vốn mục tiêu: Nhắc lại con số mục tiêu cần bán khoảng ~{stress_metrics['breakeven_orders_per_day']} đơn/ngày với AOV ~{stress_metrics['aov']:,.0f}đ để bảo toàn vốn và không bị âm định phí.
  + Tại sao cần ưu tiên mục tiêu này đầu tiên: Giải thích ngắn gọn về bảo toàn Runway ({stress_metrics['runway_months']:.1f} tháng).
  + Checklist hành động tuần 1 (Sử dụng đúng format '- [ ]' cho từng đầu việc):
    - [ ] Chuẩn bị quy trình ra món chuẩn dưới 60 - 90 giây trước giờ cao điểm ({golden_hour}).
    - [ ] Áp dụng bài học thực chiến chống cạm bẫy vận hành (chọn 1 cạm bẫy DB3 phù hợp nhất để phòng ngừa).
    - [ ] Thiết lập combo mồi câu khách dùng thử trong tuần khai trương.
  + Lời thoại mẫu thực chiến (Sử dụng đúng format '> Lời thoại: "..."'):
    Viết nguyên văn câu thoại ngắn gọn, lịch sự, đắt giá để chủ quán hoặc nhân viên nói với khách hàng ghé mua lần đầu để họ ấn tượng và muốn quay lại.

- Giai đoạn 60 - 90 ngày (Tích lũy & Tối ưu hóa tệp khách quen):
  + Phương án hành động: Chiến lược kéo khách quay lại (Retention) và nâng giá trị đơn hàng (AOV).
  + Tại sao lại chọn phương án này: Lý do tập trung vào khách quen thay vì tốn tiền quảng cáo ngoài đường.
  + Checklist hành động:
    - [ ] Triển khai chương trình khách hàng thân thiết siêu đơn giản (thẻ tích điểm vật lý / Zalo OA).
    - [ ] Tinh chỉnh menu loại bỏ món bán chậm, đẩy mạnh nhóm món có biên lợi nhuận cao nhất.

### 3. KỊCH BẢN DỰ PHÒNG & ĐIỂM CẮT LỖ AN TOÀN (PLAN B & EXIT STRATEGY)
- Điểm kích hoạt báo động đỏ (Trigger point): Nếu sau 45 ngày đầu tiên mà lượng đơn bán ra không đạt tối thiểu 50% ngưỡng hòa vốn (dưới {int(stress_metrics['breakeven_orders_per_day'] * 0.5)} đơn/ngày), chủ quán BẮT BUỘC phải thực hiện hành động khẩn cấp gì ngay lập tức?
- Kế hoạch điều chỉnh Plan B: Cắt giảm định phí nào đầu tiên? Điều chỉnh khung giờ mở bán hay đổi menu ra sao?
- Ngưỡng cắt lỗ an toàn (Stop-loss threshold): Chỉ rõ mốc thời gian hoặc số vốn tối đa được phép gồng lỗ (dựa trên Runway còn lại) để nếu xấu nhất phải thanh lý sang nhượng quán mà vẫn giữ lại được ít nhất 40-50% vốn, tuyệt đối không lún sâu vào nợ nần.
"""
    # Lắp ghép Mục 4 từ module lean_capital_rules (phân nhánh if-else độc lập)
    from .lean_capital_rules import build_section_4_lean_capital
    section_4 = build_section_4_lean_capital(form_data, stress_metrics, rent)
    user_prompt = f"{user_prompt}\n\n{section_4}\n"

    return user_prompt, SCANNER_SYSTEM_PROMPT
