# HƯỚNG DẪN VẬN HÀNH: NỀN TẢNG RA QUYẾT ĐỊNH & TRỢ LÝ KINH DOANH THỰC CHIẾN F&B

> **Hệ thống Song Trụ (Dual-Engine Architecture v3.2)**:
> 1. **Giao diện 1 (Day 0 - Trước khi mở quán)**: Máy quét Thẩm định Ý tưởng (Feasibility Scanner).
> 2. **Giao diện 2 (Day 1 - 365 - Trong khi vận hành)**: Trợ lý Tác chiến Đồng hành 5 Nhánh (Tactical Copilot Router).

---

## 1. YÊU CẦU HỆ THỐNG (PREREQUISITES)

Trước khi khởi chạy, máy chủ hoặc máy phát triển cần đáp ứng các điều kiện sau:

- **Hệ điều hành**: Windows 10/11, macOS, hoặc Linux (Ubuntu 20.04+).
- **Python**: Phiên bản **3.10 trở lên** (khuyên dùng Python **3.11** - **3.13**).
- **Node.js**: Phiên bản **18.x trở lên** (chỉ cần thiết nếu bạn muốn biên dịch lại mã nguồn React Frontend).
- **Ollama**: Máy chủ suy luận AI cục bộ đã được cài đặt và đang chạy ngầm trên máy.
- **Phần cứng**:
  - RAM: Tối thiểu 8GB (khuyên dùng 16GB trở lên).
  - GPU (Tùy chọn): GPU NVIDIA hỗ trợ CUDA để tăng tốc mô hình nhúng `BAAI/bge-m3` và `Qwen3.5 4B` (hệ thống tự động chuyển về CPU nếu không có GPU rời).
- **Kết nối Mạng**: Có kết nối Internet để tải trọng số mô hình `BAAI/bge-m3` từ Hugging Face trong lần chạy đầu tiên và kết nối tới CSDL MongoDB Atlas.

---

## 2. HƯỚNG DẪN THIẾT LẬP MÔI TRƯỜNG CHẠY (STEP-BY-STEP SETUP)

Dự án được cấu trúc hoàn toàn **độc lập và tự chủ (self-contained)**. Bạn có thể đặt tên thư mục dự án tùy ý khi tải về (ví dụ: `fnb_ai_platform`, `decision_copilot`...) mà không ảnh hưởng tới bất kỳ thành phần nào của hệ thống. Mọi thao tác dưới đây đều được thực hiện **trực tiếp tại thư mục gốc của dự án**.

### Bước 1: Chuẩn bị file cấu hình `.env`
Đảm bảo file `.env` đã có mặt tại thư mục gốc của dự án với đầy đủ các tham số cấu hình:

```env
# Cổng chạy ứng dụng FastAPI
PORT=5000
HOST=0.0.0.0

# Kết nối Cơ sở dữ liệu MongoDB Atlas (chứa 5 CSDL: DB1, DB2, DB3, DB4, DB5)
MONGO_URI=mongodb+srv://<username>:<password>@<cluster-url>/?retryWrites=true&w=majority
DB_NAME=MLAI_Hackathon_2026

# Cấu hình máy chủ LLM Ollama cục bộ
OLLAMA_BASE_URL=http://127.0.0.1:11434
LLM_MODEL=qwen3.5:4b

# Cấu hình mô hình Vector Embedding cục bộ (BAAI/bge-m3)
EMBEDDING_MODEL=BAAI/bge-m3
DEVICE=cuda
```

*(Lưu ý: Nếu máy không có card đồ họa NVIDIA CUDA, bạn đổi `DEVICE=cpu`)*.

---

### Bước 2: Tạo và kích hoạt môi trường ảo Python (`venv`)

Mở Terminal trực tiếp tại thư mục gốc của dự án và khởi tạo môi trường ảo:

#### Trên Windows (PowerShell):
```powershell
# 1. Tạo môi trường ảo riêng biệt tên là .venv
python -m venv .venv

# 2. Kích hoạt môi trường ảo
.\.venv\Scripts\Activate.ps1
```
*(Nếu gặp lỗi Policy trên PowerShell, chạy lệnh: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` rồi kích hoạt lại).*

#### Trên Windows (Command Prompt - CMD):
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

#### Trên Linux / macOS:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Sau khi kích hoạt thành công, dấu nhắc lệnh terminal sẽ có tiền tố `(.venv)`.

---

### Bước 3: Cài đặt toàn bộ thư viện cần thiết

Nâng cấp công cụ `pip` và cài đặt danh sách phụ thuộc từ `requirements.txt`:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

> **Danh mục thư viện được cài đặt tự động:**
> - `fastapi`, `uvicorn[standard]`: Máy chủ Web REST API và hỗ trợ Server-Sent Events (SSE) streaming.
> - `pydantic`: Rào chắn kiểm tra tính hợp lệ của dữ liệu đầu vào.
> - `python-dotenv`: Nạp biến môi trường tự động từ file `.env`.
> - `requests`, `httpx`: Kết nối HTTP API đồng bộ và bất đồng bộ tới Ollama và chạy kiểm thử.
> - `pymongo[srv]`, `dnspython`: Trình điều khiển kết nối MongoDB Atlas bảo mật qua giao thức DNS SRV.
> - `geopy`: Thư viện chuyển đổi địa chỉ thành tọa độ địa lý (Geocoding).
> - `torch`, `sentence-transformers`, `numpy`: Động cơ tính toán ma trận tương đồng vector 1024 chiều của `BAAI/bge-m3`.

---

### Bước 4: Thiết lập và khởi chạy máy chủ AI Ollama

1. **Khởi động ứng dụng Ollama** trên máy của bạn (kiểm tra biểu tượng Ollama đã xuất hiện ở khay hệ thống).
2. **Tải và chạy mô hình `qwen3.5:4b`**:
   ```bash
   ollama run qwen3.5:4b
   ```
3. Sau khi mô hình tải xong và xuất hiện màn hình chat của Ollama, gõ `/bye` để thoát ra. Ollama sẽ tiếp tục chạy nền phục vụ tại cổng mặc định `http://127.0.0.1:11434`.

---

### Bước 5: (Tùy chọn) Biên dịch lại Frontend React

Thư mục `frontend/dist` đã được biên dịch sẵn bản production hoàn chỉnh và được FastAPI tự động phân phối. Tuy nhiên, nếu bạn có chỉnh sửa mã nguồn giao diện trong `frontend/src`, hãy chạy:

```bash
cd frontend
npm install
npm run build
cd ..
```

---

### Bước 6: Khởi chạy Nền tảng Ứng dụng

Chạy lệnh sau trực tiếp tại thư mục gốc của dự án (khi môi trường `.venv` đang được kích hoạt):

```bash
python run.py
```

---

## 3. KIỂM TRA TRUY CẬP HỆ THỐNG

Sau khi khởi chạy thành công, mở trình duyệt web:

| Dịch vụ | Đường dẫn | Mục đích |
| :--- | :--- | :--- |
| **Giao diện Ứng dụng Web** | [http://localhost:5000](http://localhost:5000) | Trải nghiệm trực quan cả 2 chế độ (Scanner & Copilot) |
| **Tài liệu API Tương tác** | [http://localhost:5000/docs](http://localhost:5000/docs) | Kiểm tra và gửi request thử nghiệm trực tiếp qua Swagger UI |
| **Kiểm tra Sức khỏe Hệ thống** | [http://localhost:5000/api/health](http://localhost:5000/api/health) | Kiểm tra trạng thái kết nối MongoDB, LLM và Vector Database |

---

## 4. CẤU TRÚC THƯ MỤC CHUẨN HÓA

```
./ (Thư mục gốc dự án)
├── .env                              # Biến môi trường hệ thống (Port, Mongo, Ollama, Device)
├── .gitignore                         # Danh mục loại trừ Git (Loại bỏ file test, cache, nháp)
├── requirements.txt                  # Danh mục đầy đủ 100% thư viện phụ thuộc Python
├── run.py                            # Entrypoint chính để khởi động máy chủ ứng dụng
├── README.md                         # Tài liệu hướng dẫn vận hành hệ thống
│
├── backend/                          # MÃ NGUỒN MÁY CHỦ BACKEND (FASTAPI)
│   ├── config.py                     # Quản lý cấu hình tập trung từ .env
│   ├── database.py                   # Quản lý kết nối MongoDB Atlas (5 Collections)
│   ├── tag_manager.py                # Quản lý danh mục 10 Mô hình (101-110) & 20 Sản phẩm (201-220)
│   ├── tag_map.json                  # Siêu dữ liệu danh mục Tag chuẩn hóa
│   ├── financial_profiles.json       # Bảng hằng số tài chính mặc định cho giả lập dòng tiền
│   ├── main.py                       # API Router FastAPI, phân phối SSE streaming và static frontend
│   │
│   └── pipeline/                     # CÁC MẮT XÍCH XỬ LÝ NGHIỆP VỤ & TÍNH TOÁN
│       ├── spatial_engine.py         # Quét Geocoding tọa độ, dân cư DB1 & đối thủ DB2 trong bán kính 1km
│       ├── semantic_search.py        # Tìm kiếm ngữ nghĩa lai (Hybrid Search) qua BAAI/bge-m3
│       ├── copilot_router.py         # Bộ định tuyến ý định 5 Nhánh chiến thuật qua Anchor Vectors
│       ├── branch_anchors.json       # Cấu hình vector neo và từ khóa cho 5 Nhánh A, B, C, D, E
│       ├── branch_strategic.py       # Module con Nhánh C: Tính toán toán học tất định What-If
│       ├── branch_competitive.py     # Module con Nhánh D: Thuật toán chấm điểm phản công vi mô
│       ├── branch_diagnostic.py      # Module con Nhánh E: Chẩn đoán nguyên nhân và checklist bệnh quán
│       │
│       ├── market_analyse/           # Phân tích khoảng trống thị trường & túi tiền khách hàng (DB5)
│       ├── stress_test/              # Giả lập dòng tiền đa kịch bản, tính tháng sinh tồn Runway
│       ├── tactical_playbook/        # Trích xuất rủi ro (DB3) & bài học thực chiến đa dạng (DB4)
│       └── llm_copilot/              # Động cơ tạo Prompt & Giao tiếp mô hình Qwen3.5 4B qua Ollama
│           ├── engine.py             # Client gửi request đồng bộ / streaming token-by-token
│           ├── scanner_prompt.py     # Prompt chuyên biệt cho Giao diện 1 (Thẩm định ý tưởng)
│           ├── lean_capital_rules.py # Phân nhánh lời răn quy mô & kiểm soát dòng tiền mặt Mục 4
│           └── copilot_prompts.py    # Bộ System Prompt & Cấu trúc Markdown riêng cho 5 nhánh
│
└── frontend/                         # MÃ NGUỒN GIAO DIỆN CLIENT REACT
    ├── package.json                  # Dependencies React, TailwindCSS, Lucide Icons
    ├── vite.config.js                # Cấu hình Vite build
    ├── dist/                         # Bản build tĩnh production (FastAPI tự động nạp)
    └── src/                          # Mã nguồn giao diện người dùng
        ├── App.jsx                   # Component gốc điều phối trạng thái và chuyển đổi Tab
        ├── components/
        │   ├── Navbar.jsx            # Thanh điều hướng và hiển thị trạng thái kết nối
        │   ├── FeasibilityScanner.jsx# Giao diện 1: Thẩm định ý tưởng & Báo cáo 4 khối
        │   └── TacticalCopilot.jsx   # Giao diện 2: Trợ lý tác chiến thời gian thực SSE
        └── ...
```

---

## 5. TỔNG QUAN LUỒNG HOẠT ĐỘNG NGHIỆP VỤ

### Giao diện 1: Máy quét Thẩm định Ý tưởng (Day 0)
1. **Tiếp nhận Form thẩm định**: Địa chỉ mở quán, mã mô hình (101 - 110), mã nhóm món (201 - 220), số vốn ban đầu và tiền thuê nhà dự kiến.
2. **Khảo sát không gian vi mô**: Geocoding địa chỉ qua `spatial_engine`, quét mật độ dân cư DB1 (bán kính 3km) và tìm kiếm đối thủ trực diện DB2 (bán kính 1km).
3. **Phân tích khoảng trống & Thử tải dòng tiền**:
   - `market_analyse`: Khai thác dữ liệu DB5 chỉ ra điểm yếu phổ biến của đối thủ và khung giờ vàng phục vụ khách.
   - `stress_test`: Tính toán chi phí đầu tư ban đầu (Capex), định phí hàng tháng (Opex) và số tháng sinh tồn (Runway). Nếu cạn vốn (`Runway <= 0`), hệ thống kích hoạt kịch bản Báo động đỏ tái cấu trúc vốn.
4. **Suy diễn chiến lược Qwen3.5 4B**: Xuất bản báo cáo 4 mục hành động rõ ràng kèm điểm hòa vốn, lộ trình tác chiến 30-60-90 ngày, kịch bản cắt lỗ an toàn và nguyên tắc sống còn giữ dòng tiền mặt dương.

### Giao diện 2: Trợ lý Tác chiến Đồng hành (Day 1 - 365)
1. **Bộ định tuyến Agentic Router (5 Nhánh)**: Dựa trên phân tích từ khóa và vector ngữ nghĩa `BAAI/bge-m3` để tự động kích hoạt 1 trong 5 nhánh chuyên biệt:
   - **Nhánh A (Hỏi kinh nghiệm thuần túy)**: Chỉ truy vấn DB4 (Kinh nghiệm thực chiến).
   - **Nhánh B (Gỡ rối sự cố nội bộ tại chỗ)**: Truy vấn DB3 (Sự cố) + DB4 (Bài học) để dập lửa trong 5 phút.
   - **Nhánh C (Giả định chiến lược Nếu - Thì)**: Kích hoạt bài toán tài chính What-If định lượng và so khớp tiền lệ.
   - **Nhánh D (Phản công cạnh tranh vi mô)**: Quét đối thủ DB2 + túi tiền DB5 + chiến thuật DB4 để xuất đòn combo giữ giá, bảo vệ thị phần.
   - **Nhánh E (Chẩn đoán bệnh kinh doanh)**: Khoanh vùng triệu chứng qua DB3 và xuất Checklist tự rà soát tại quán.
2. **Streaming Real-time (SSE)**: Phản hồi từng token từ mô hình `Qwen3.5 4B` qua giao thức Server-Sent Events, hiển thị kết quả ngay tức thì cho người dùng.
