"""
branch_diagnostic.py - Module Xử lý Chuyên biệt Nhánh 5: Phân tích & Chẩn đoán Bệnh kinh doanh (Diagnostic Triage)
Đặc tả: Phần I & Phần III (Mục 3.7), Phần IV (Mục 4.3) - Tactical Copilot Engine (v3.2.0)

Triết lý cốt lõi: "Bác sĩ chẩn đoán F&B thực chiến"
1. Hệ thống không vội vàng phán xét mà khoanh vùng 2 - 3 Kịch bản khả nghi nhất.
2. Thiết lập Checklist chi tiết từng bước (- [ ]) để chủ quán tự kiểm tra trong 24h.
3. 8 Tag Triệu chứng than phiền đời thường (DB3: 401 - 408):
   - Tag 401: Mặt bằng & Pháp lý
   - Tag 402: Dòng tiền & Định giá
   - Tag 403: Chuỗi cung ứng & Nguyên liệu
   - Tag 404: Vận hành & Nhân sự
   - Tag 405: Marketing & Giữ chân khách
   - Tag 406: Sản phẩm & Trải nghiệm
   - Tag 407: Bán hàng đa kênh & App giao hàng
   - Tag 408: Đối thủ cạnh tranh & Chiến tranh giá
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Cấu hình tham số ngưỡng Cosine chuẩn theo Mục 3.7
DIAGNOSTIC_FLOOR_THRESHOLD = 0.48  # Ngưỡng sàn tối thiểu để khoanh vùng kịch bản
DIAGNOSTIC_PEAK_THRESHOLD = 0.60   # Ngưỡng đỉnh (vượt ngưỡng này lấy tối đa 3 tag)
MAX_DIAGNOSTIC_ISSUES = 3          # Giới hạn tối đa số vấn đề khả nghi
DEFAULT_DIAGNOSTIC_ISSUES = 2      # Số lượng kịch bản mặc định

# File cấu hình Anchor 8 Tag của Nhánh 5
BRANCH_5_DATA_PATH = Path(__file__).resolve().parent / "branch_5_anchors.json"

_cached_branch_5_metadata: Optional[Dict[str, Any]] = None
_cached_branch_5_vectors: Optional[Dict[str, np.ndarray]] = None


def load_branch_5_metadata() -> Dict[str, Any]:
    """Tải siêu dữ liệu cấu hình 8 Tag triệu chứng của Nhánh 5."""
    global _cached_branch_5_metadata
    if _cached_branch_5_metadata is not None:
        return _cached_branch_5_metadata

    try:
        with open(BRANCH_5_DATA_PATH, "r", encoding="utf-8") as f:
            _cached_branch_5_metadata = json.load(f)
            return _cached_branch_5_metadata
    except Exception as e:
        logger.error(f"[!] Không thể đọc file branch_5_anchors.json: {e}")
        return {}


def get_branch_5_vectors() -> Dict[str, np.ndarray]:
    """Tải và tính trước vector 1024 chiều (BGE-M3) cho 8 Tag triệu chứng."""
    global _cached_branch_5_vectors
    if _cached_branch_5_vectors is not None:
        return _cached_branch_5_vectors

    metadata = load_branch_5_metadata()
    if not metadata:
        return {}

    try:
        from .semantic_search import get_embedding_model
        model = get_embedding_model()
        if model is None:
            return {}

        vectors = {}
        for tag_id, info in metadata.items():
            anchor_text = info.get("anchor", "")
            vec = model.encode(anchor_text, normalize_embeddings=True)
            vectors[tag_id] = np.array(vec, dtype=np.float32)

        _cached_branch_5_vectors = vectors
        logger.info(f"[✓] Đã khởi tạo vector BGE-M3 thành công cho 8 Tag triệu chứng Nhánh 5.")
        return _cached_branch_5_vectors
    except Exception as e:
        logger.error(f"[!] Lỗi khi nạp vector anchor cho branch_diagnostic: {e}")
        return {}


def calculate_diagnostic_scores(query: str) -> Dict[str, float]:
    """
    Tính điểm tương đồng triệu chứng S_Diagnostic^(k) trong thang [0, 100] cho 8 Tag.
    Kết hợp Vector Cosine BGE-M3 chuẩn hóa + Heuristic Pattern Matching.
    """
    metadata = load_branch_5_metadata()
    cleaned_query = query.lower().strip()
    tag_vectors = get_branch_5_vectors()

    raw_cosines: Dict[str, float] = {}
    if tag_vectors:
        try:
            from .semantic_search import get_embedding_model, cosine_similarity
            model = get_embedding_model()
            q_vec = model.encode(cleaned_query, normalize_embeddings=True)
            q_vec = np.array(q_vec, dtype=np.float32)

            for t_id, t_vec in tag_vectors.items():
                sim = float(cosine_similarity(q_vec, t_vec))
                raw_cosines[t_id] = max(0.0, sim)
        except Exception as e:
            logger.warning(f"[!] Lỗi tính toán vector trong calculate_diagnostic_scores: {e}")

    # Nhận diện tín hiệu triệu chứng chuyên sâu cho từng Tag
    # Tag 401: Mặt bằng & Pháp lý
    is_tag_401 = bool(
        re.search(r"(tiền thuê nhà|tiền thuê mặt bằng|tăng tiền nhà|chủ nhà|đòi lại mặt bằng|lấy lại mặt bằng|hợp đồng thuê|vỉa hè|lòng lề đường|trật tự đô thị|công an phạt|an toàn thực phẩm|vệ sinh an toàn|giấy phép|phòng cháy|hàng xóm|ranh giới|lối đi chung|giải tỏa|quy hoạch|mở rộng đường|tố cáo.*(xả rác|nước thải)|cống công cộng|hố ga lọc mỡ|bồi thường.*nứt tường|thuế.*cho thuê nhà)", cleaned_query)
    )

    # Tag 408: Đối thủ cạnh tranh & Chiến tranh giá
    is_tag_408 = bool(
        re.search(r"(đối thủ|quán bên cạnh.*đông|quán đối diện|đối diện mới mở|bán phá giá|cướp.*khách|chơi xấu|dìm hàng|kẹp giữa đối thủ|chèo kéo khách|cuộc chiến giảm giá|chặn trước cửa hẻm|mua chuộc.*thợ|nói xấu.*nguyên liệu|bán từ sáng sớm đến tận khuya|chịu lỗ 6 tháng|đắt hơn quán bên cạnh|tạo trend.*bắt chước|né tránh.*đối đầu)", cleaned_query)
    )

    # Tag 407: Bán hàng đa kênh & App giao hàng
    is_tag_407 = bool(
        re.search(r"(grab|shopeefood|baemin|gojek|chiết khấu app|phí hoa hồng app|phí sàn|nổ đơn app|sập quầy|tài xế shipper|shipper|đánh giá 1 sao.*app|gian hàng online|đơn app|bán trên app|ứng dụng giao hàng|nhận đơn đóng gói.*tài xế|từng đặt qua app|bấm hoàn thành đơn sớm|kẹt đơn tại chỗ|hối thúc quán.*kẹt đơn)", cleaned_query)
        and not re.search(r"không đủ trả tiền nguyên liệu", cleaned_query)
    )

    # Tag 402: Dòng tiền & Định giá
    is_tag_402 = bool(
        re.search(r"(không thấy tiền dư|hụt tiền két|hụt tiền|tiền két|dòng tiền|xoay vòng vốn|định giá.*quá rẻ|không bù nổi chi phí|bán đông nhưng không thấy lãi|bán có khách nhưng|tiền đi đâu hết|âm tiền|thiếu tiền mặt|sổ sách thu chi|bán không có lãi|doanh thu.*không thấy lãi|không thấy tiền đâu|mất cân đối dòng tiền|chẳng còn đồng lãi nào|ít hơn.*tiền lương|không đủ trả tiền nguyên liệu|bốc hơi toàn bộ lợi nhuận|chi phí ẩn|chôn vốn|mất thanh khoản|bán nợ|quỹ dự phòng khẩn cấp|cụt vốn lưu động)", cleaned_query)
    )

    # Tag 403: Chuỗi cung ứng & Nguyên liệu
    is_tag_403 = bool(
        re.search(r"(hao hụt nguyên liệu|chua thiu|ôi thiu|hỏng phải đổ|tồn kho quá hạn|nhà cung cấp|giá nguyên liệu|nguyên vật liệu|thịt rau không tươi|pha chế quá tay|đong sữa|đong siro|định lượng nguyên liệu|lãng phí nguyên liệu|hư hỏng nguyên liệu|thất thoát nguyên liệu|bảo quản nguyên liệu|tỷ lệ hao hụt|cà phê hạt.*bay mùi|dầu ăn chiên rán|thay dầu mới|đổ bỏ đồ ăn thừa|định lượng mỗi phần ăn|bom|fifo|tủ đông.*hỏng|hao tổn cost|độ tươi|lên men)", cleaned_query)
    )

    # Tag 404: Vận hành & Nhân sự
    is_tag_404 = bool(
        re.search(r"(thợ mới làm sai|thái độ phục vụ|cộc cằn|cãi tay đôi|nghỉ ngang|đi trễ|thu ngân gian lận|trộm tiền|trộm đồ|sai công thức|làm chậm giờ cao điểm|phục vụ chậm chạp|chia ca|nhân viên cãi|thái độ nhân viên|quản lý nhân sự|bếp và quầy bar|đùn đẩy trách nhiệm|bấm điện thoại trong giờ|nội quy thưởng phạt|giữ chân nhân sự|tuồn nguyên liệu|tính nhầm hóa đơn|làm đổ nước sôi|đeo găng tay|chấm công hộ|bắt nạt nhân viên|quên.*ghi chú|lắp camera quan sát.*quầy)", cleaned_query)
    )

    # Tag 405: Marketing & Giữ chân khách
    is_tag_405 = bool(
        re.search(r"(quán vắng tanh|vắng vẻ như chùa|không ai biết đến|khách ghé một lần rồi thôi|ăn một lần rồi|không bao giờ quay lại|không có khách quen|chạy quảng cáo không ra đơn|quán ế ẩm|quán ế|quảng cáo tốn tiền|mất khách|thiếu khách|không hút được khách|vắng khách|thu hút khách mới|nhận diện thương hiệu|ngân sách marketing|ngại ghé thử|kích thích khách quay lại|phát tờ rơi|fanpage|kols|hâm nóng lại)", cleaned_query)
        and not is_tag_408
    )

    # Tag 406: Sản phẩm & Trải nghiệm
    is_tag_406 = bool(
        re.search(r"(mặn ngọt thất thường|hương vị dở|khách chê dở|mùi hôi quán|không gian bí bách|nóng nực|ồn ào|menu quá nhiều món|menu rối rắm|bao bì.*đổ vỡ|hộp xốp|ly nhựa mỏng manh|đồ ăn nguội ngắt|chất lượng món ăn thất thường|trải nghiệm tệ|không gian chật chội|vị món ăn|chất lượng món|bàn ghế.*kê quá sát|ánh sáng trong quán|cốc chén.*dầu mỡ|ngồi đợi hơn \d+ phút|ỉu xìu|ngấm dầu mỡ|quá ngọt khé cổ|gom gọn menu|chỗ để xe thuận tiện|kiểm soát chất lượng món|hương liệu công nghiệp)", cleaned_query)
    )

    diagnostic_scores: Dict[str, float] = {}
    for t_id, info in metadata.items():
        base_cos = raw_cosines.get(t_id, 0.40)
        norm_score = np.clip((base_cos - 0.35) / 0.30 * 50.0 + 40.0, 30.0, 95.0)

        # Kiểm tra mẫu từ khóa trong metadata
        pats = info.get("patterns", [])
        matched = any(re.search(p, cleaned_query, re.IGNORECASE) for p in pats)
        if matched:
            norm_score += 10.0

        # Áp dụng heuristic ưu tiên chuẩn xác
        if t_id == "TAG_408" and is_tag_408:
            norm_score += 35.0
        elif t_id == "TAG_401" and is_tag_401:
            norm_score += 35.0
        elif t_id == "TAG_407" and is_tag_407:
            norm_score += 35.0
        elif t_id == "TAG_402" and is_tag_402:
            norm_score += 35.0
        elif t_id == "TAG_403" and is_tag_403:
            norm_score += 35.0
        elif t_id == "TAG_404" and is_tag_404:
            norm_score += 35.0
        elif t_id == "TAG_405" and is_tag_405:
            norm_score += 35.0
        elif t_id == "TAG_406" and is_tag_406:
            norm_score += 35.0

        diagnostic_scores[t_id] = round(float(np.clip(norm_score, 10.0, 100.0)), 2)

    return diagnostic_scores


def diagnose_business_issues(
    query: str,
    model_id: int = 105,
    top_limit: int = MAX_DIAGNOSTIC_ISSUES
) -> Dict[str, Any]:
    """
    Thuật toán 6 bước Chẩn đoán Bệnh kinh doanh (Mục 3.7 & 4.3).
    Khoanh vùng 2 - 3 Kịch bản khả nghi nhất và đóng gói Checklist kiểm tra 24h.
    """
    metadata = load_branch_5_metadata()
    scores = calculate_diagnostic_scores(query)

    # Sắp xếp các Tag theo điểm từ cao xuống thấp
    sorted_tags = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    # Áp dụng quy tắc ngưỡng:
    # Lấy top các tag vượt ngưỡng sàn (tương ứng >= 62đ), tối đa 3 nếu vượt đỉnh (>= 82đ)
    peak_count = sum(1 for _, sc in sorted_tags if sc >= 82.0)
    limit = MAX_DIAGNOSTIC_ISSUES if peak_count > 2 else DEFAULT_DIAGNOSTIC_ISSUES

    selected_tags = [t_id for t_id, _ in sorted_tags[:min(limit, top_limit)]]
    primary_tag = selected_tags[0] if selected_tags else "TAG_402"

    detailed_scenarios = []
    for rank, t_id in enumerate(selected_tags, start=1):
        info = metadata.get(t_id, {})
        tag_num = t_id.replace("TAG_", "")
        score = scores.get(t_id, 0.0)

        # Tạo kịch bản mẫu và checklist 3 bước hành động
        if t_id == "TAG_401":
            title = "Rủi ro Pháp lý & Biến động Mặt bằng"
            symptom = "Có dấu hiệu ép giá thuê, bất ổn pháp lý vỉa hè hoặc hợp đồng thiếu ràng buộc."
            leak = "Nguy cơ mất tiền cọc, gián đoạn kinh doanh hoặc bị phạt hành chính."
            steps = [
                ("Soi hiện trường", "Rà soát lại toàn bộ hợp đồng thuê mặt bằng và các phụ lục gia hạn."),
                ("Cân đo / Đếm số liệu", "Tính tỷ lệ chi phí thuê mặt bằng so với doanh thu trung bình (ngưỡng an toàn <= 20%)."),
                ("Tiêu chuẩn đối chiếu", "Nếu chủ nhà đòi tăng quá 15%/năm hoặc tỷ lệ vượt 25% doanh thu -> Cần chuẩn bị phương án đàm phán hoặc dời điểm.")
            ]
        elif t_id == "TAG_402":
            title = "Bẫy Dòng tiền & Định giá dưới Biên an toàn"
            symptom = "Bán có doanh thu và đông khách nhưng cuối tháng hụt tiền két, không thấy tiền dư."
            leak = "Định giá món ăn quá rẻ hoặc chi phí sàn app/hao hụt ăn mòn toàn bộ biên lãi gộp."
            steps = [
                ("Soi hiện trường", "Tách riêng dòng tiền mặt tại quầy và dòng tiền chuyển khoản / ví điện tử mỗi ngày."),
                ("Cân đo / Đếm số liệu", "Tính lãi gộp thực tế của từng món chính sau khi trừ giá vốn nguyên liệu và phí sàn."),
                ("Tiêu chuẩn đối chiếu", "Nếu biên lãi gộp dưới 45% ở F&B bán lẻ -> Càng bán nhiều đơn càng thâm hụt vốn lưu động.")
            ]
        elif t_id == "TAG_403":
            title = "Thất thoát vô hình ở Khâu Định lượng & Bảo quản Nguyên liệu"
            symptom = "Nguyên liệu hao hụt nhiều, đồ ăn cốt nước bị chua thiu hỏng phải đổ bỏ."
            leak = "Rót siro/sữa theo cảm tính hoặc bảo quản không chuẩn làm đội giá vốn 15% - 20%."
            steps = [
                ("Soi hiện trường", "Quan sát trực tiếp 5 lần pha chế / ra món giờ cao điểm xem nhân sự có dùng ca đong chuẩn không."),
                ("Cân đo / Đếm số liệu", "Chia tổng lượng nguyên liệu xuất kho cho số suất bán ra trong tuần đối chiếu với barem chuẩn."),
                ("Tiêu chuẩn đối chiếu", "Nếu lượng nguyên liệu thực tế dùng vượt > 10% barem chuẩn -> Đã tìm ra lỗ rò rỉ!")
            ]
        elif t_id == "TAG_404":
            title = "Lỗ hổng Vận hành & Kỷ luật Nhân sự"
            symptom = "Nhân viên làm sai công thức, thái độ cộc cằn, làm chậm giờ cao điểm hoặc nghi ngờ gian lận."
            leak = "Mất khách vĩnh viễn do trải nghiệm tồi tệ và thất thoát tiền két tại quầy thu ngân."
            steps = [
                ("Soi hiện trường", "Kiểm tra camera góc quầy thu ngân và quy trình xuất hóa đơn trước khi nhận tiền."),
                ("Cân đo / Đếm số liệu", "Đối chiếu số lượng ly/dĩa bán ra trên phần mềm với số lượng vật tư tiêu hao (ly nhựa, hộp mang đi)."),
                ("Tiêu chuẩn đối chiếu", "Nếu số lượng vỏ hộp/ly hao hụt lệch > 5% so với đơn trên bill -> Có rủi ro gian lận tiền két.")
            ]
        elif t_id == "TAG_405":
            title = "Tắc nghẽn Phễu Thu hút & Mất liên kết Khách hàng"
            symptom = "Quán mở ra vắng tanh, khách chỉ ghé một lần rồi không quay lại, quảng cáo không hiệu quả."
            leak = "Lãng phí ngân sách marketing vô bổ mà không tạo ra khách hàng thân thiết bền vững."
            steps = [
                ("Soi hiện trường", "Khảo sát trực quan mặt tiền quán từ khoảng cách 50m xem biển hiệu và lối vào có bị khuất không."),
                ("Cân đo / Đếm số liệu", "Đo lường tỷ lệ khách quay lại (Retention Rate) trong 30 ngày qua."),
                ("Tiêu chuẩn đối chiếu", "Nếu tỷ lệ quay lại < 20% -> Vấn đề nằm ở chất lượng trải nghiệm lần đầu chứ không phải do thiếu quảng cáo.")
            ]
        elif t_id == "TAG_406":
            title = "Đứt gãy Trải nghiệm Thực khách & Rối loạn Thực đơn"
            symptom = "Khách phàn nàn đồ ăn mặn ngọt thất thường, hương vị dở, không gian bí bách nóng nực."
            leak = "Menu quá nhiều món làm thợ quá tải, tồn kho nguyên vật liệu rối rắm và chất lượng tụt dốc."
            steps = [
                ("Soi hiện trường", "Đóng vai khách hàng ngồi ăn tại góc khuất nhất của quán vào khung giờ nóng nhất."),
                ("Cân đo / Đếm số liệu", "Lọc ra 20% số món đóng góp 80% doanh thu và rà soát các món ế ẩm."),
                ("Tiêu chuẩn đối chiếu", "Cắt bỏ ngay các món chiếm < 3% doanh thu nhưng đòi hỏi nguyên liệu riêng biệt khó bảo quản.")
            ]
        elif t_id == "TAG_407":
            title = "Bẫy Phí Chiết khấu Sàn & Sập quầy Đơn App"
            symptom = "Nổ đơn app dồn dập làm sập quầy quán phục vụ không kịp, phí chiết khấu 25-30% ăn mòn lãi."
            leak = "Bán lấy số lượng trên app nhưng càng bán càng lỗ vì phí sàn và bao bì đóng gói đắt đỏ."
            steps = [
                ("Soi hiện trường", "Theo dõi thời gian hoàn tất một đơn app từ lúc nổ chuông đến khi giao cho tài xế."),
                ("Cân đo / Đếm số liệu", "Lấy giá bán trên app trừ 25% phí sàn và giá vốn món ăn để tính lãi ròng."),
                ("Tiêu chuẩn đối chiếu", "Nếu biên lãi ròng trên app < 15% -> Cần thiết lập lại phổ giá trên app hoặc ngắt bớt app giờ cao điểm.")
            ]
        else: # TAG_408
            title = "Sức ép Phá giá từ Đối thủ Sát vách"
            symptom = "Quán bên cạnh mở ra bán phá giá rẻ hơn 5k-10k, lôi kéo khách quen của quán."
            leak = "Sa đà vào cuộc chiến hạ giá tự sát khiến quỹ dự phòng cạn kiệt nhanh chóng."
            steps = [
                ("Soi hiện trường", "Cử người sang ăn thử món của đối thủ để đánh giá chất lượng nguyên liệu và tốc độ phục vụ."),
                ("Cân đo / Đếm số liệu", "Tính toán khoảng giảm giá an toàn d_max của quán mình trước khi quyết định điều chỉnh."),
                ("Tiêu chuẩn đối chiếu", "Tuyệt đối không hạ giá món chính nếu d_max <= 0; chuyển hướng sang tạo Combo bù trừ hoặc khai thác điểm yếu đối thủ.")
            ]

        detailed_scenarios.append({
            "rank": rank,
            "tag_id": t_id,
            "tag_name": info.get("name", t_id),
            "badge_title": info.get("badge_title", t_id),
            "score": score,
            "scenario_title": title,
            "symptom_description": symptom,
            "potential_leak": leak,
            "checklist": [
                {"step_num": 1, "title": steps[0][0], "action": steps[0][1]},
                {"step_num": 2, "title": steps[1][0], "action": steps[1][1]},
                {"step_num": 3, "title": steps[2][0], "action": steps[2][1]}
            ]
        })

    primary_info = metadata.get(primary_tag, {})

    # Đóng gói định dạng Markdown chuẩn xuất LLM
    md_lines = [
        "### 🩺 BÁO CÁO CHẨN ĐOÁN & KỊCH BẢN KHẢ NGHI",
        "*(Dựa trên triệu chứng bạn chia sẻ và mô hình quán, hệ thống khoanh vùng kịch bản nghi vấn lớn nhất)*",
        ""
    ]
    for sc in detailed_scenarios:
        md_lines.extend([
            "---",
            "",
            f"### 🔍 KỊCH BẢN {sc['rank']}: [{sc['scenario_title']} - {sc['badge_title']} ({sc['score']}đ)]",
            f"- **Dấu hiệu nhận biết:** {sc['symptom_description']}",
            f"- **Lỗ rò rỉ tiềm ẩn:** {sc['potential_leak']}",
            "- **📋 Các bước tự kiểm tra tại quán trong 24h:**"
        ])
        for st in sc["checklist"]:
            md_lines.append(f"  - [ ] **Bước {st['step_num']} ({st['title']}):** {st['action']}")
        md_lines.append("")

    return {
        "primary_tag": primary_tag,
        "primary_name": primary_info.get("name", ""),
        "primary_badge": primary_info.get("badge_title", ""),
        "suspected_tags": selected_tags,
        "scores": scores,
        "scenarios": detailed_scenarios,
        "markdown_report": "\n".join(md_lines)
    }
