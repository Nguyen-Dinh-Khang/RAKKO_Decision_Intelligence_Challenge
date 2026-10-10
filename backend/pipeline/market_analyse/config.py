"""
config.py - Bảng tham số cấu hình hệ thống phân tích thị trường (Market Analyse Config)
Được chuẩn hóa theo tài liệu đặc tả: Word/Function_md/market_analyse_engine.md
"""

# 1. Bán kính phân tích thị trường vi mô
ANALYSIS_RADIUS_METERS = 1000.0  # Chuẩn: 1.000m (1km)

# 2. Trọng số tính Điểm đe dọa Đối thủ (Competitor Threat Score - CTS)
WEIGHT_DISTANCE = 0.25      # 25% - Khoảng cách thực tế
WEIGHT_OVERLAP = 0.30       # 30% - Trùng lặp mô hình & danh mục món (Quan trọng nhất)
WEIGHT_WEAKNESS = 0.20      # 20% - Tử huyệt / Điểm yếu bị khách phàn nàn
WEIGHT_REPUTATION = 0.15    # 15% - Uy tín & Thị phần tương đối (Rating & Reviews)
WEIGHT_DEMOGRAPHIC = 0.10   # 10% - Mức độ hợp thị hiếu tệp khách địa phương

# 3. Ngưỡng phân loại đối thủ trực tiếp
DIRECT_COMPETITOR_CTS_THRESHOLD = 65.0  # Điểm CTS >= 65.0 là đối thủ trực tiếp

# 4. Ngưỡng gom cụm Vector Điểm yếu hệ thống (BGE-M3 Clustering)
WEAKNESS_SIMILARITY_THRESHOLD = 0.70    # Cosine Similarity >= 0.70 xem là cùng điểm yếu
MIN_CLUSTER_SIZE_SYSTEMIC = 2           # Ít nhất 2 quán cùng mắc phải mới tính là điểm yếu hệ thống

# 5. Ngưỡng phân tích vốn & kích hoạt Kịch bản kép (Dual Strategies)
CAPITAL_PREMIUM_HIGH_THRESHOLD = 300_000_000.0  # Vốn >= 300 triệu: Kích hoạt Premium
CAPITAL_PREMIUM_MID_THRESHOLD = 200_000_000.0   # Vốn >= 200 triệu: Kích hoạt Premium nếu thị trường thiếu
LUXURY_LACKING_RATIO_THRESHOLD = 0.15           # Thiếu phân khúc sang nếu tỷ lệ quán giá cao < 15%

# 6. Ngưỡng phân tầng giá & Đánh giá phân khúc cao cấp (Average Price Jump Threshold & Premium Determination)
PRICE_JUMP_ABSOLUTE_MIN = 15_000.0  # Bước nhảy giá tối thiểu để chia tách tầng giá mới (15.000đ)
PRICE_JUMP_RELATIVE_RATIO = 0.35    # Hoặc bước giá nhảy vọt >= 35% so với trung bình tích lũy của tầng trước đó
PREMIUM_CUSTOMER_PRICE_MULTIPLIER = 1.15  # Hệ số nhân với customer_price_max để xác định tầng giá cao cấp (> 15% trần chi trả)

# 7. Tỷ lệ điều chỉnh mức giá đề xuất (Recommended Price Multipliers)
PREMIUM_PRICE_MIN_RATIO = 1.25      # Giá sàn Premium = Giá trần DB5 * 1.25 (+25%)
PREMIUM_PRICE_MAX_RATIO = 1.40      # Giá trần Premium = Giá trần DB5 * 1.40 (+40%)
INCOME_RATIO_LOW = 0.90             # Tỷ lệ chi trả cho phân khúc thu nhập thấp
INCOME_RATIO_MEDIUM = 1.00          # Tỷ lệ chi trả cho phân khúc thu nhập trung bình
INCOME_RATIO_HIGH = 1.20            # Tỷ lệ chi trả cho phân khúc thu nhập cao

# 8. Khung giờ vàng mở quán (Golden Operating Windows)
EARLY_OPENING_MINUTES = 45          # Mở sớm trước giờ cao điểm DB5 45 phút để đón khách vội
PREPARATION_BUFFER_MINUTES = 15     # Kỷ luật sơ chế xong trước giờ mở cửa 15 phút

# 9. Ngưỡng tương đồng Semantic Search DB4
DB4_MATCH_SIMILARITY_THRESHOLD = 0.55  # Cosine >= 0.55 thì lấy bài học DB4, thấp hơn thì làm ngược lại
