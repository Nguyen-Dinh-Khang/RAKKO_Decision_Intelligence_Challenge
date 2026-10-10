"""
config.py - Bảng tham số cấu hình bộ sách lược chiến thuật (Tactical Playbook Config)
Được chuẩn hóa theo tài liệu đặc tả: Word/Function_md/tactical_playbook_engine.md (Mục 2)
"""

# 1. Ngưỡng Cosine Similarity xác định "đồng bọn" (cùng một cụm chủ đề/na ná nhau)
SIMILARITY_THRESHOLD = 0.65         # Cosine >= 0.65 được xem là cùng một cụm vấn đề/kinh nghiệm

# 2. Số lượng mục tối đa cần lấy ra cho mỗi nhánh (Phòng thủ / Tấn công)
TOP_K_ITEMS = 4                     # Chuẩn đầu ra: tối đa 4 vấn đề và 4 kinh nghiệm

# 3. Kích thước vector embedding chuẩn của mô hình BAAI/bge-m3
EMBEDDING_DIM = 1024                # Vector 1024 chiều chuẩn hóa L2

# 4. Ngưỡng Cosine Similarity tối thiểu để xem là kinh nghiệm liên quan giải quyết bài học
RELATED_SIMILARITY_THRESHOLD = 0.30   # Cosine(exp, prob) >= 0.30 xem như kinh nghiệm liên quan

# 5. Prompt Neo Khái Niệm chuẩn xác định bản chất Vấn đề (Dễ/Tác nghiệp vs Khó/Chiến lược)
ANCHOR_SIMPLE_ISSUE = (
    "Lỗi sơ suất vận hành thường nhật, checklist chuẩn bị tác nghiệp cơ bản, biển hiệu cửa hàng bị cây che khuất "
    "hoặc thiếu đèn chiếu sáng ban đêm, thiếu chỗ đỗ xe máy hoặc lối gửi xe bất tiện, giờ giấc mở cửa chưa khớp với thói quen sinh hoạt "
    "của khu dân cư lân cận, thiếu sót thủ tục hành chính đăng ký kinh doanh và giấy phép an toàn vệ sinh thực phẩm cơ bản, "
    "nhân viên quên kiểm tra hạn sử dụng nguyên vật liệu tồn đầu ca, định lượng pha chế bị sai lệch nhẹ do thiếu cân tiểu ly hoặc muỗng đong tiêu chuẩn, "
    "thao tác phần mềm bán hàng POS bị chậm trong ngày khai trương, thiếu dù che nắng cho khách ngồi ngoài trời, âm nhạc quán quá to hoặc không phù hợp gu khách, "
    "đồng phục nhân viên chưa đồng bộ, quên ghim địa chỉ vị trí trên Google Maps hoặc định vị sai bản đồ, thiếu thùng rác tại bàn. "
    "Đây là các vấn đề vận hành vi mô, chỉ cần lập danh sách kiểm tra (checklist), đôn đốc quy trình, người mở quán đọc qua là biết để phòng tránh và điều chỉnh ngay tức thì."
)

ANCHOR_COMPLEX_RISK = (
    "Rủi ro chiến lược kinh doanh sống còn, cạn kiệt dòng tiền mặt và đứt gãy vốn lưu động, áp lực chi phí cố định tiền thuê mặt bằng quá cao "
    "chiếm tỷ trọng lớn đè bẹp biên lợi nhuận, bẫy dòng tiền do thanh toán tiền nhà trước nhiều tháng, mô hình định giá sai lầm dẫn đến biên lợi nhuận gộp "
    "mỏng dưới ngưỡng hòa vốn dù đông khách, đối thủ cạnh tranh trực diện mạnh vốn tung khuyến mãi phá giá giành giật thị phần lân cận, "
    "tỷ lệ khách hàng quay lại cực thấp do định vị sai phân khúc nhu cầu và định giá lệch năng lực chi trả của dân cư, "
    "xung đột quyền lợi và phân chia tỷ lệ cổ phần tranh chấp quyền điều hành giữa các cổ đông sáng lập, quỹ lương nhân sự phình to vượt quá năng suất lao động, "
    "bẫy công nợ nhà cung cấp và tồn đọng vốn vào hàng hóa tồn kho khó thanh lý, tranh chấp pháp lý hợp đồng thuê đất dài hạn bị chủ nhà đòi lại mặt bằng đột ngột, "
    "khủng hoảng truyền thông chất lượng dịch vụ. Đây là các vấn đề nghiêm trọng đe dọa sinh mệnh cửa hàng, bắt buộc phải có bài học xương máu, "
    "chiến lược tái cấu trúc và kinh nghiệm thực chiến từ người từng vấp ngã mới có thể vượt qua."
)
