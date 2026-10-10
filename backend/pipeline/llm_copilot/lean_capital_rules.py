"""
lean_capital_rules.py - Module Chuyên biệt Quản lý Lời răn Quy mô & Dòng tiền mặt (Mục 4)

Chức năng:
- Tách nhỏ các logic phân nhánh if-else độc lập cho 2 khía cạnh:
  1. Lời răn về Quy mô (Lean Validation): Bắt đầu nhỏ để gom khách quen vs Mở rộng lớn.
  2. Quản trị Dòng tiền mặt (Cash is King): Chống cạm bẫy doanh thu ảo, nợ đọng và thiếu tiền trả chi phí hàng tháng.
- Lắp ghép linh hoạt thành Mục 4 chuẩn Markdown cho Prompt Giao diện 1.
"""

from typing import Dict, Any


def build_scale_advice(form_data: Dict[str, Any], stress_metrics: Dict[str, Any]) -> str:
    """
    Cặp if-else 1: Lời răn về Quy mô kinh doanh (Lean Validation).
    Phân nhánh dựa trên: Quy mô mô hình đã chọn (model_id), Capex đầu tư, hoặc Vốn đăng ký.
    """
    model_id = form_data.get("model_id")
    capex = stress_metrics.get("capex", 0.0)
    budget = float(form_data.get("budget", 0) or 0)

    # Nếu đã là mô hình xe đẩy / kiosk (Mã 105)
    if model_id == 105:
        if budget >= 150000000:
            return (
                "Đánh giá cao việc chủ quán lựa chọn mô hình xe đẩy / kiosk mang đi tinh gọn để thăm dò thị trường. "
                "Tuy nhiên, với số vốn hiện có tương đối lớn, TUYỆT ĐỐI KHÔNG NÊN dồn hết tiền vào đóng xe đẩy thật hoành tráng hay mua sắm thiết bị đắt đỏ. "
                "Hãy giữ lại ít nhất 70% số vốn làm quỹ dự phòng sinh tồn, ưu tiên tối đa việc tinh gọn quy trình và gom đủ 30 - 50 khách quen ruột trước."
            )
        return (
            "Đánh giá cao và cổ vũ việc chủ quán đã biết bắt đầu từ quy mô nhỏ gọn (kiosk, xe đẩy mang đi) để thăm dò thị trường "
            "mà không phải chịu gánh nặng Capex lớn. Nhắc nhở nhiệm vụ sống còn lúc này là tập trung toàn lực để biến khách vãng lai "
            "thành 30 - 50 khách quen ruột đầu tiên, tuyệt đối không được nóng vội mở rộng quy mô khi chưa có lượng khách quen ổn định."
        )

    is_large_scale = (model_id in (101, 102, 103, 107)) or (capex >= 120000000) or (budget >= 200000000)

    if is_large_scale:
        return (
            "Nhắc nhở chủ quán một cách thẳng thắn: Nếu chưa có bất kỳ khách hàng nào, TUYỆT ĐỐI KHÔNG NÊN đổ hết số vốn lớn này ra "
            "mở quán quy mô lớn ngay từ đầu. Hãy lùi lại một bước: Mở với quy mô nhỏ (xe đẩy, quầy pop-up, kiosk hoặc bán online mang đi) "
            "để thăm dò nhu cầu thực tế và gom đủ tối thiểu 30 - 50 khách quen nhớ mặt trước, sau đó mới chính thức bỏ vốn ra mở lớn."
        )
    else:
        return (
            "Đánh giá cao và cổ vũ việc chủ quán đã biết bắt đầu từ quy mô nhỏ gọn (kiosk, xe đẩy mang đi) để thăm dò thị trường "
            "mà không phải chịu gánh nặng Capex lớn. Nhắc nhở nhiệm vụ sống còn lúc này là tập trung toàn lực để biến khách vãng lai "
            "thành 30 - 50 khách quen ruột đầu tiên, tuyệt đối không được nóng vội mở rộng quy mô khi chưa có lượng khách quen ổn định."
        )


def build_cashflow_advice(stress_metrics: Dict[str, Any], rent: float) -> str:
    """
    Cặp if-else 2: Lời răn về Dòng tiền mặt & Cạm bẫy doanh thu ảo (Cash is King).
    Phân nhánh dựa trên: Số tháng sinh tồn (Runway) và Gánh nặng tiền thuê nhà / Định phí.
    """
    runway = stress_metrics.get("runway_months", 0.0)
    monthly_fixed = stress_metrics.get("monthly_fixed", 1.0)
    rent_ratio = (rent / monthly_fixed) if monthly_fixed > 0 else 0.0

    is_tight_cashflow = (runway <= 3.0) or (rent_ratio >= 0.4)

    if is_tight_cashflow:
        return (
            "Với số vốn dự phòng mỏng, nếu đã có khách quen rồi thì PHẢI LUÔN CHÚ Ý DUY TRÌ DÒNG TIỀN MẶT DƯƠNG mỗi ngày. "
            "Tuyệt đối cảnh báo bẫy 'doanh thu nhìn thì to nhưng chỉ toàn là nợ, tiền bị app giam đối soát và không có sẵn tiền mặt "
            "để trả tiền thuê nhà và chi phí hàng tháng'. Cấm tuyệt đối bán chịu công nợ, phải thu tiền tươi ngay để bảo đảm đủ "
            "thanh khoản trả định phí đúng ngày đến hạn."
        )
    else:
        return (
            "Dù số vốn dự phòng còn tương đối an toàn, khi đã có khách quen thì vẫn phải luôn kiểm soát chặt chẽ dòng tiền mặt thực tế. "
            "Tránh ảo tưởng doanh thu nổ đơn nhưng lợi nhuận thực bị bào mòn bởi chiết khấu app, công nợ nguyên liệu và chi tiêu cá nhân "
            "lẹm vào vốn quán. Luôn tách bạch tài khoản quán riêng và duy trì dòng tiền mặt dương, bảo đảm lúc nào cũng có sẵn tiền mặt "
            "trả chi phí cố định."
        )


def build_section_4_lean_capital(form_data: Dict[str, Any], stress_metrics: Dict[str, Any], rent: float) -> str:
    """
    Lắp ghép Mục 4 hoàn chỉnh từ 2 cặp if-else độc lập.
    Được gọi từ scanner_prompt.py để bổ sung vào Prompt của AI.
    """
    scale_advice = build_scale_advice(form_data, stress_metrics)
    cashflow_advice = build_cashflow_advice(stress_metrics, rent)

    return (
        "### 4. NGUYÊN TẮC SỐNG CÒN: TỪ KHÁCH QUEN ĐẦU TIÊN ĐẾN DÒNG TIỀN DƯƠNG\n"
        f"- Lời răn về Quy mô (Thử nghiệm trước, Mở lớn sau):\n  {scale_advice}\n"
        f"- Cảnh báo Dòng tiền & Cạm bẫy Doanh thu ảo (Tiền mặt là vua):\n  {cashflow_advice}"
    )
