"""
config.py - Bảng tham số cấu hình bộ thử tải sinh tồn (Stress Test Config)
Được chuẩn hóa theo tài liệu đặc tả: Word/Function_md/stress_test_engine.md (Mục 2)
"""

# 1. Tỷ lệ Tiền đề phòng phát sinh hàng tháng so với tổng vốn
CONTINGENCY_RATIO_NORMAL = 0.015    # 1.5% tổng vốn / tháng (Bản Normal)
CONTINGENCY_RATIO_PREMIUM = 0.025   # 2.5% tổng vốn / tháng (Bản Premium)

# 2. Hệ số nhân chuyển đổi sang Kịch bản Premium (Khi has_dual_strategies = True)
PREMIUM_AOV_MULTIPLIER = 1.35           # Giỏ hàng AOV tăng 35%
PREMIUM_CAPEX_MULTIPLIER = 1.40         # Sàn và Trần Capex tăng 40%
PREMIUM_CAPEX_RATIO_ADDON = 0.05        # Tăng tỷ trọng vốn đầu tư ban đầu thêm 5%
PREMIUM_SALARY_MULTIPLIER = 1.25        # Lương mỗi người tăng 25%
PREMIUM_STAFF_ADDON = 1                 # Bổ sung thêm 1 nhân sự
PREMIUM_UTILITIES_MULTIPLIER = 1.30     # Điện nước tăng 30%

# 3. Giá thuê mặt bằng mặc định dự phòng (Fallback khi người dùng để trống)
DEFAULT_RENT_BY_MODEL = {
    101: 10_000_000,    # Quán ăn sáng
    102: 12_000_000,    # Quán nước / Cà phê
    103: 15_000_000,    # Quán cơm / Nhà hàng nhỏ
    104: 16_000_000,    # Quán nhậu / Ăn vặt
    105: 1_500_000,     # Kiosk / Xe đẩy mang đi
    106: 8_000_000,     # Cửa hàng tạp hóa / Đại lý
    107: 12_000_000,    # Cửa hàng chuyên doanh bán lẻ
    108: 14_000_000,    # Tiệm làm đẹp / Spa
    109: 9_000_000,     # Tiệm dịch vụ dân sinh
    110: 18_000_000     # Siêu thị mini / Tiện lợi
}
