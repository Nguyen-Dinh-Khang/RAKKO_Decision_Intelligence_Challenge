"""
insolvency_rules.py - Module Chuyên biệt Quản lý Kịch bản Tái cấu trúc vốn & Báo động đỏ khi Runway <= 0 tháng

Chức năng cốt lõi:
1. Chuẩn hóa danh xưng và thuật ngữ: Phân biệt rõ giữa "Chủ quán / Mặt bằng" và "Chủ điểm bán / Xe đẩy / Vị trí đặt xe" (Model 105).
2. Hạ cấp mô hình theo tầng (Tiered Downgrade):
   - Nhóm Đại mô hình / Quán lớn (101, 102, 104, 107...): Hạ xuống mặt bằng nhỏ, tinh giản decor hoặc Quick-service (TUYỆT ĐỐI không ép nhảy cóc xuống xe đẩy).
   - Nhóm Quán vừa & nhỏ: Chuyển sang Quầy Pop-up chia sẻ mặt bằng theo giờ, Kiosk nhỏ hoặc Bán Online / Cloud Kitchen.
   - Nhóm Xe đẩy / Kiosk (105): Đã là đáy chuỗi vật lý -> TUYỆT ĐỐI không nói hạ mô hình. Chuyển sang: Săn xe cũ thanh lý, Bán tại nhà 0đ, Gom đơn đặt trước (Pre-order).
3. Bóc tách nguyên nhân cạn vốn: Phân định rõ do Capex vượt ngưỡng, do Gánh nặng tiền cọc nhà, hay do vốn khởi điểm quá mỏng.
"""

from typing import Dict, Any, Optional


def resolve_entity_terms(model_id: Optional[int], rent: float) -> Dict[str, str]:
    """
    Chuẩn hóa danh xưng và thuật ngữ giao tiếp phù hợp với bản chất mô hình.
    Tránh lỗi gọi người bán xe đẩy là 'chủ quán' hoặc bắt người bán vỉa hè 'ký hợp đồng thuê nhà'.
    """
    is_pushcart = (model_id == 105)

    if is_pushcart:
        return {
            "entity_title": "CHỦ ĐIỂM BÁN / XE ĐẨY TINH GỌN",
            "location_term": "vị trí đặt xe / điểm bán vỉa hè",
            "commitment_action": "thỏa thuận thuê vị trí đặt xe hoặc đặt cọc mua sắm xe",
            "capex_term": "chi phí đóng xe đẩy và mua sắm dụng cụ chế biến",
            "rent_term": "tiền thuê chỗ đặt xe" if rent > 0 else "chi phí chỗ bán (0 đồng)",
        }
    else:
        return {
            "entity_title": "CHỦ QUÁN / CHỦ CƠ SỞ KINH DOANH",
            "location_term": "mặt bằng kinh doanh",
            "commitment_action": "đặt bút ký hợp đồng thuê mặt bằng",
            "capex_term": "chi phí thiết kế, sửa chữa, decor và sắm sửa máy móc (Capex)",
            "rent_term": f"tiền thuê mặt bằng ({rent:,.0f}đ/tháng)" if rent > 0 else "mặt bằng có sẵn (0 đồng)",
        }


def classify_model_tier(model_id: Optional[int], budget: float, capex: float) -> str:
    """
    Phân tầng quy mô mô hình để áp dụng chiến lược hạ cấp tương thích (Tiered Downgrade):
    - 'micro': Kiosk / Xe đẩy mang đi (Model 105).
    - 'large': Quán lớn, nhà hàng, quán cà phê không gian trải nghiệm (101, 102, 103, 104, 107) hoặc Capex/Vốn lớn.
    - 'mid': Quán vừa & nhỏ, cửa hàng dân sinh, tiệm đồ ăn nhanh gọn.
    """
    if model_id == 105:
        return "micro"

    is_large = (
        model_id in (101, 102, 103, 104, 107)
        or budget >= 200_000_000
        or capex >= 150_000_000
    )
    if is_large:
        return "large"

    return "mid"


def build_insolvency_root_cause(
    tier: str,
    terms: Dict[str, str],
    budget: float,
    capex: float,
    monthly_fixed: float,
    rent: float
) -> str:
    """
    Bóc tách nguyên nhân cốt tử khiến Runway = 0.
    Tự động phân tích điểm nghẽn nằm ở Capex setup, tiền cọc nhà hay vốn quá mỏng.
    """
    lines = [
        "- Đánh giá thẳng thắn về mức độ rủi ro: Tuyên bố mức điểm khả thi (1/10 hoặc 2/10) và giải thích tại sao số vốn "
        f"{budget:,.0f}đ hiện tại là 'tự sát tài chính' khi so với mức chi phí đầu tư ban đầu và định phí hàng tháng."
    ]

    if tier == "micro":
        if rent <= 0:
            lines.append(
                f"- Chỉ rõ lỗ hổng: Số vốn {budget:,.0f}đ hiện tại chỉ vừa đủ (hoặc thậm chí chưa đủ) để trang trải {terms['capex_term']} (~{capex:,.0f}đ). "
                "Sau khi đóng xe và sắm xong đồ nghề, bạn sẽ còn đúng 0 đồng trong túi để mua nguyên liệu cho những ngày đầu vắng khách."
            )
        else:
            lines.append(
                f"- Chỉ rõ lỗ hổng: Số vốn {budget:,.0f}đ bị phân tán vào {terms['capex_term']} (~{capex:,.0f}đ) và {terms['rent_term']}. "
                "Ngay khi đưa xe vào hoạt động, bạn hoàn toàn không còn vốn lưu động để xoay vòng nhập hàng và duy trì điểm bán qua 2 tuần đầu."
            )
    else:
        if rent <= 0:
            lines.append(
                f"- Chỉ rõ lỗ hổng: Dù có sẵn mặt bằng 0 đồng, nhưng {terms['capex_term']} ({capex:,.0f}đ) đã nuốt trọn hoặc vượt số vốn hiện có ({budget:,.0f}đ). "
                f"Quán sẽ mở cửa với tài khoản dự phòng bằng 0, không có khả năng chi trả định phí điện nước ({monthly_fixed:,.0f}đ/tháng) và bù lỗ tháng đầu."
            )
        else:
            deposit_est = rent * 2
            lines.append(
                f"- Chỉ rõ lỗ hổng: Tiền cọc nhà (ước tính tối thiểu 2 tháng ~{deposit_est:,.0f}đ) cộng với {terms['capex_term']} ({capex:,.0f}đ) "
                f"đã vượt quá số vốn {budget:,.0f}đ. Bạn rơi vào tình thế 'vừa ký hợp đồng xong là cạn sạch tiền', không còn một đồng vốn lưu động nào để vận hành."
            )

    return "\n".join(lines)


def build_restructuring_options(
    tier: str,
    terms: Dict[str, str],
    budget: float,
    capex: float,
    monthly_fixed: float,
    rent: float,
    products_str: str
) -> str:
    """
    Xây dựng 3 phương án tái cấu trúc vốn may đo theo tầng mô hình (Tiered Downgrade):
    - micro (Xe đẩy): TUYỆT ĐỐI không khuyên hạ cấp mô hình. Hướng dẫn săn đồ cũ thanh lý, bán tại nhà 0đ, gom order trước.
    - large (Quán lớn/Nhà hàng): Hạ cấp diện tích sàn, tối giản decor, tinh gọn sang Quick-service (không nhảy cóc xuống xe đẩy).
    - mid (Quán vừa/nhỏ): Chuyển sang Quầy Pop-up chia sẻ mặt bằng, Kiosk nhỏ, hoặc Bán online / Cloud Kitchen.
    """
    intro = (
        "Đưa ra 3 phương án hành động cụ thể để người dùng lựa chọn, với mỗi phương án phải giải thích rõ: "
        "**Tại sao lại chọn phương án này?**"
    )

    if tier == "micro":
        # TẦNG XE ĐẨY / KIOSK TINH GỌN (MODEL 105)
        opt1 = (
            "- Phương án 1 (Săn xe cũ thanh lý & Tối giản công cụ - Asset-light): "
            "TUYỆT ĐỐI KHÔNG chi tiền đóng xe đẩy mới đắt đỏ hay sắm máy móc đắt tiền. "
            "Hãy tìm mua xe đẩy cũ thanh lý từ các hội nhóm F&B (tiết kiệm 60 - 70% Capex, chỉ còn 2 - 4 triệu đồng), "
            "tận dụng tối đa nồi niêu, bếp và dụng cụ sẵn có của gia đình. "
            "Giải thích: Phương án này giúp cắt giảm khoản chi phí nào để đưa Runway từ 0 tháng lên mức sinh tồn an toàn?"
        )
        opt2 = (
            "- Phương án 2 (Tận dụng điểm bán 0 đồng hoặc thuê vỉa hè theo khung giờ vàng): "
            "Thay vì thuê vị trí cố định cả ngày tốn kém, hãy tìm điểm đặt xe chi phí 0đ (trước cửa nhà người quen, góc sân vắng giờ sáng) "
            "hoặc chỉ thuê vỉa hè đúng khung giờ cao điểm (sáng 6h-9h hoặc chiều 16h-19h) với giá dưới 1 - 1.5 triệu/tháng. "
            "Giải thích: Tại sao việc giảm định phí mặt bằng về mức tối thiểu là điều kiện sống còn của người bán xe đẩy?"
        )
        opt3 = (
            f"- Phương án 3 (Bán thử nghiệm đặt trước tại nhà - Pre-order Smoke Test): "
            f"Chưa vội xuống tiền sắm xe. Hãy nấu thử món {products_str} tại bếp nhà, chụp ảnh thật và gom đơn đặt trước (Pre-order) "
            "từ bạn bè, đồng nghiệp hoặc các hội nhóm cư dân lân cận. "
            "Giải thích: Tại sao cần gom đủ 30 - 50 khách quen và kiểm chứng khẩu vị trước khi bỏ tiền mua xe ra đường?"
        )
    elif tier == "large":
        # TẦNG ĐẠI MÔ HÌNH / NHÀ HÀNG / QUÁN LỚN
        opt1 = (
            "- Phương án 1 (Thu hẹp diện tích mặt bằng & Tinh giản Decor): "
            "Thay vì thuê mặt bằng lớn 100 - 150m² với chi phí decor dàn trải hàng trăm triệu, hãy hạ xuống mặt bằng vừa 30 - 45m² "
            "hoặc mô hình Tiệm bán nhanh (Quick Service / Casual Dining). Cắt bỏ 70% các hạng mục trang trí cầu kỳ, "
            "tập trung 100% vào chất lượng món ăn và tốc độ ra món. "
            "Giải thích: Phương án này giúp cắt giảm khoản Capex nào và giải phóng bao nhiêu vốn lưu động?"
        )
        opt2 = (
            "- Phương án 2 (Đổi tiêu chí mặt bằng & Tái đàm phán hợp đồng thuê): "
            "Chuyển hướng tìm mặt bằng trong hẻm lớn hoặc trục phụ có chỗ để xe máy thuận tiện thay vì cố bám mặt tiền đắt đỏ; "
            "đàm phán chỉ cọc 1 tháng (thay vì 3 tháng) và xin miễn phí 30 ngày thi công sửa chữa. "
            "Giải thích: Tại sao tiền thuê nhà tối đa chỉ nên chiếm tỷ lệ an toàn dưới 20% so với vốn thực tế?"
        )
        opt3 = (
            "- Phương án 3 (Kêu gọi đối tác đồng hành hoặc tích lũy thêm vốn): "
            "Xác định chính xác số tiền tối thiểu cần chuẩn bị thêm (đủ trả Capex setup và giữ lại quỹ dự phòng tối thiểu 3 - 6 tháng định phí) "
            f"trước khi {terms['commitment_action']}."
        )
    else:
        # TẦNG QUÁN VỪA & NHỎ (MID-TIER)
        opt1 = (
            "- Phương án 1 (Chuyển sang Quầy Pop-up chia sẻ mặt bằng hoặc Bán Online / Cloud Kitchen): "
            "Thay vì thuê nguyên căn chịu gánh nặng cọc nhà, hãy thuê lại mặt tiền của cửa hàng khác vào khung giờ cao điểm, "
            "hoặc mở điểm bán mang đi kết hợp giao hàng trực tuyến (Delivery). "
            "Giải thích: Phương án này giúp triệt tiêu chi phí bàn ghế, máy lạnh và đưa Runway lên bao nhiêu tháng?"
        )
        opt2 = (
            "- Phương án 2 (Tinh gọn định phí & Tự vận hành trong giai đoạn đầu): "
            "Loại bỏ chi phí thuê nhân viên ngoài trong 1 - 2 tháng đầu, tự tay đứng bếp/pha chế; "
            "chọn mặt bằng có mức giá thuê thấp hơn 30 - 40% so với dự tính ban đầu. "
            "Giải thích: Lý do việc kiểm soát chặt định phí hàng tháng giúp kéo dài số tháng sinh tồn."
        )
        opt3 = (
            "- Phương án 3 (Xác định ngưỡng vốn an toàn trước khi xuống tiền): "
            "Tính toán chính xác số vốn cần có thêm để đảm bảo sau khi setup quán vẫn còn đủ quỹ dự phòng cho ít nhất 3 tháng vận hành "
            f"trước khi {terms['commitment_action']}."
        )

    return f"{intro}\n{opt1}\n{opt2}\n{opt3}"


def build_exit_advice(
    tier: str,
    terms: Dict[str, str],
    products_str: str
) -> str:
    """
    Xây dựng Mục 3: Lời khuyên dừng lại đúng lúc (Exit Strategy) trước khi xuống tiền.
    """
    lines = [
        "- Đưa ra lời khuyên chân thành: Những việc tuyệt đối KHÔNG ĐƯỢC LÀM ngay lúc này (ví dụ: vay nóng, vay app, vay lãi suất cao để cố đấm ăn xôi bù vào vốn thiếu)."
    ]

    if tier == "micro":
        lines.append(
            f"- Kế hoạch thử nghiệm chi phí 0 đồng (Smoke Test): Các bước cụ thể để kiểm tra xem khách hàng khu vực có thực sự chuộng vị món {products_str} "
            f"và sẵn sàng trả tiền hay không, trước khi bỏ tiền mua sắm xe hay công cụ chế biến."
        )
    else:
        lines.append(
            f"- Điểm dừng an toàn (Pause & Validate): Tuyên bố rõ ràng chủ cơ sở cần tạm hoãn việc {terms['commitment_action']}; "
            f"thay vào đó thực hiện bài test nhỏ về công thức món {products_str} và đo lường nhu cầu thực tế trước khi bỏ một đồng vốn nào vào mặt bằng."
        )

    return "\n".join(lines)


def build_insolvency_prompt(
    form_data: Dict[str, Any],
    stress_metrics: Dict[str, Any],
    stress_str: str,
    budget: float,
    rent: float,
    address: str,
    model_name: str,
    products_str: str
) -> str:
    """
    Lắp ráp toàn bộ Prompt hoàn chỉnh cho tình huống Cạn vốn / Báo động đỏ (Runway <= 0.0 tháng).
    Được gọi từ scanner_prompt.py.
    """
    model_id = form_data.get("model_id")
    capex = stress_metrics.get("capex", 0.0)
    monthly_fixed = stress_metrics.get("monthly_fixed", 0.0)

    # 1. Chuẩn hóa thuật ngữ & danh xưng
    terms = resolve_entity_terms(model_id, rent)

    # 2. Phân tầng quy mô mô hình (Tiered Classification)
    tier = classify_model_tier(model_id, budget, capex)

    # 3. Lắp ráp 3 khối nội dung cốt lõi
    section_1 = build_insolvency_root_cause(tier, terms, budget, capex, monthly_fixed, rent)
    section_2 = build_restructuring_options(tier, terms, budget, capex, monthly_fixed, rent, products_str)
    section_3 = build_exit_advice(tier, terms, products_str)

    user_prompt = f"""TÌNH HUỐNG KHẨN CẤP: DÒNG TIỀN BÁO ĐỘNG ĐỎ (RUNWAY = 0.0 THÁNG - NGUY CƠ MẤT TRẮNG VỐN NGÀY ĐẦU).

HỒ SƠ KHẢO SÁT CỦA {terms['entity_title']}:
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
{section_1}

### 2. CÁC PHƯƠNG ÁN TÁI CẤU TRÚC VỐN KHẢ THI (NÊU PHƯƠNG ÁN & GIẢI THÍCH LÝ DO)
{section_2}

### 3. LỜI KHUYÊN DỪNG LẠI ĐÚNG LÚC (EXIT STRATEGY TRƯỚC KHI XUỐNG TIỀN)
{section_3}
"""
    return user_prompt
