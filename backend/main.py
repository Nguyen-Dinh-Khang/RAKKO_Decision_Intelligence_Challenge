"""
main.py - Máy chủ FastAPI phục vụ Nền Tảng Ra Quyết Định Kinh Doanh (Client App)
Hỗ trợ:
- Giao diện 1: Máy quét Thẩm định Ý tưởng (Day 0) -> POST /api/scanner/evaluate
- Giao diện 2: Trợ lý Chiến thuật Đồng hành (Day 1 - 365) -> POST /api/copilot/chat
- Danh mục 10 Mô hình & 20 Sản phẩm chuẩn hóa -> GET /api/metadata
- Kiểm tra sức khỏe hệ thống -> GET /api/health
"""

import sys
import re
import json
import logging
import hashlib
import secrets
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

# Đảm bảo console Windows in tiếng Việt chuẩn UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("MLAI_ClientApp")

# Import các module nội bộ
from .config import PORT, HOST, LLM_MODEL, EMBEDDING_MODEL
from .database import check_mongo_health, get_db
from .tag_manager import tag_manager
from .pipeline.spatial_engine import SpatialEngine, geocode_address
from .pipeline.market_analyse import MarketAnalyseEngine, analyse_market
from .pipeline.stress_test import StressTestEngine, run_stress_test, load_financial_profiles
from .pipeline.stress_test.config import DEFAULT_RENT_BY_MODEL
from .pipeline.tactical_playbook import TacticalPlaybookEngine, run_tactical_playbook
from .pipeline.semantic_search import SemanticSearchEngine
from .pipeline.llm_copilot import LLMCopilot
from .pipeline.copilot_router import detect_copilot_intent, get_branch_vectors
from .pipeline.branch_strategic import get_branch_3_vectors
from .pipeline.branch_competitive import get_branch_4_vectors
from .pipeline.branch_diagnostic import get_branch_5_vectors

# Khởi tạo FastAPI app
app = FastAPI(
    title="MLAI Business Decision Co-pilot Platform",
    description="Nền tảng Ra quyết định & Trợ lý Kinh doanh thực chiến Hộ Bán lẻ & Dịch vụ Đời sống",
    version="3.0.0"
)

# Cho phép gọi chéo CORS từ Frontend React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo các mắt xích pipeline
spatial_engine = SpatialEngine()
market_analyse_engine = MarketAnalyseEngine()
market_gap_engine = market_analyse_engine
stress_test_engine = StressTestEngine()
tactical_playbook_engine = TacticalPlaybookEngine()
semantic_search_engine = SemanticSearchEngine()
llm_copilot = LLMCopilot()


@app.on_event("startup")
async def preload_embedding_cache():
    """
    Tối ưu hiệu năng Embedding Text mẫu:
    Nạp toàn bộ BGE-M3 model và 4 bộ Anchor Vectors (Nhánh A-E, C, D, E) vào RAM Cache
    ngay khi khởi động máy chủ để xóa bỏ hoàn toàn độ trễ cold-start cho người dùng.
    """
    logger.info("[*] [STARTUP] Bắt đầu nạp trước Anchor Vectors và BGE-M3 vào RAM...")
    try:
        vecs_main = get_branch_vectors()
        logger.info(f"[+] [STARTUP] Đã nạp {len(vecs_main)} Anchor vectors cho 5 Nhánh chính (A-E).")
        vecs_b3 = get_branch_3_vectors()
        logger.info(f"[+] [STARTUP] Đã nạp {len(vecs_b3)} Anchor vectors cho Nhánh C (What-If).")
        vecs_b4 = get_branch_4_vectors()
        logger.info(f"[+] [STARTUP] Đã nạp {len(vecs_b4)} Anchor vectors cho Nhánh D (Cạnh tranh vi mô).")
        vecs_b5 = get_branch_5_vectors()
        logger.info(f"[+] [STARTUP] Đã nạp {len(vecs_b5)} Anchor vectors cho Nhánh E (Chẩn đoán).")
        logger.info("[✓] [STARTUP] Hoàn tất nạp RAM cache Embedding thành công!")
    except Exception as e:
        logger.warning(f"[!] [STARTUP] Lỗi khi nạp trước cache embedding (sẽ nạp on-demand khi có request): {e}")


# =====================================================================
# PYDANTIC SCHEMAS (ĐẶC TẢ DỮ LIỆU ĐẦU VÀO)
# =====================================================================

class LLMConfigPayload(BaseModel):
    """Cấu hình chuyển luồng LLM (Local Ollama hoặc Cloud API Key cá nhân)"""
    mode: Optional[str] = Field("local", description="Chế độ chạy LLM: 'local' hoặc 'cloud'")
    provider: Optional[str] = Field("gemini", description="Nhà cung cấp Cloud: 'gemini', 'openai', 'groq', 'deepseek', 'openrouter'")
    api_key: Optional[str] = Field(None, description="API Key cá nhân của người dùng")
    model: Optional[str] = Field(None, description="Tên model tùy chọn")


class FeasibilityRequest(BaseModel):
    """Dữ liệu Form thẩm định ý tưởng (Giao diện 1)"""
    address: str = Field(..., description="Địa chỉ dự kiến mở quán")
    model_id: int = Field(..., description="Mã mô hình kinh doanh (101 - 110)")
    product_ids: List[int] = Field(..., description="Danh sách mã nhóm sản phẩm (201 - 220)")
    budget: float = Field(..., description="Số vốn hiện có (VNĐ)")
    rent: Optional[float] = Field(None, description="Tiền thuê mặt bằng dự kiến (VNĐ/tháng)")
    llm_config: Optional[LLMConfigPayload] = Field(None, description="Cấu hình nguồn LLM tùy chọn")


class CopilotChatRequest(BaseModel):
    """Dữ liệu Chat sự cố thực tế (Giao diện 2)"""
    query: str = Field(..., description="Câu hỏi hoặc sự cố thực tế cần tư vấn")
    model_id: Optional[int] = Field(None, description="Mã mô hình quán đang kinh doanh (tùy chọn)")
    address: Optional[str] = Field(None, description="Địa chỉ quán kinh doanh (tùy chọn để quét đối thủ vi mô)")
    coordinates: Optional[Dict[str, float]] = Field(None, description="Tọa độ {'lng': float, 'lat': float} (tùy chọn)")
    product_ids: Optional[List[int]] = Field(None, description="Danh sách mã sản phẩm bán (tùy chọn)")
    customer_segment_ids: Optional[List[int]] = Field(None, description="Danh sách mã phân khúc khách hàng chủ đạo (301 - 304)")
    conversation_history: Optional[List[Dict[str, str]]] = Field(None, description="Lịch sử đối thoại trước đó")
    mode: Optional[str] = Field(None, description="Chế độ kiểm thử: 'part_1' (định tuyến 5 nhánh) hoặc 'full'")
    llm_config: Optional[LLMConfigPayload] = Field(None, description="Cấu hình nguồn LLM tùy chọn")



class RegisterRequest(BaseModel):
    """Dữ liệu đăng ký tài khoản"""
    username: str = Field(..., min_length=3, max_length=50, description="Tên đăng nhập")
    password: str = Field(..., min_length=4, description="Mật khẩu")
    full_name: Optional[str] = Field(None, description="Họ tên hoặc Tên quán")


class LoginRequest(BaseModel):
    """Dữ liệu đăng nhập"""
    username: str = Field(..., description="Tên đăng nhập")
    password: str = Field(..., description="Mật khẩu")


class SaveStrategyRequest(BaseModel):
    """Dữ liệu lưu kế sách chiến lược kèm thông số vốn, tiền thuê, nhân sự và tệp khách hàng"""
    address: str = Field(..., description="Địa chỉ kinh doanh")
    coordinates: Dict[str, float] = Field(..., description="Tọa độ chuẩn xác {'lng': float, 'lat': float}")
    model_id: int = Field(..., description="Mã mô hình (101 - 110)")
    product_ids: List[int] = Field(..., description="Danh sách mã sản phẩm (201 - 220)")
    report_result: Dict[str, Any] = Field(..., description="Bản báo cáo kế sách 4 khối từ Giao diện 1")
    budget: Optional[float] = Field(None, description="Số vốn ban đầu (VNĐ)")
    rent: Optional[float] = Field(None, description="Tiền thuê mặt bằng dự kiến (VNĐ/tháng)")
    staff_count: Optional[int] = Field(None, description="Số lượng nhân viên")
    avg_salary: Optional[int] = Field(None, description="Lương trung bình mỗi nhân viên (VNĐ/tháng)")
    customer_segment_ids: Optional[List[int]] = Field(None, description="Danh sách mã phân khúc khách hàng chủ đạo (301 - 304)")
    selected_scenario: Optional[str] = Field("normal", description="Kịch bản được chọn để lưu: 'normal' hoặc 'premium'")



class UpdateProfileRequest(BaseModel):
    """Dữ liệu cập nhật hồ sơ quán thực tế (profile)"""
    budget: int = Field(..., description="Vốn thực tế còn lại (VNĐ)")
    rent: int = Field(..., description="Tiền thuê mặt bằng hiện tại (VNĐ/tháng)")
    staff_count: Optional[int] = Field(0, description="Số lượng nhân viên hiện tại")
    avg_salary: Optional[int] = Field(0, description="Tiền lương trung bình mỗi nhân viên (VNĐ/tháng)")
    customer_segment_ids: Optional[List[int]] = Field(default_factory=list, description="Danh sách mã phân khúc khách hàng chủ đạo (301 - 304)")
    month_set: str = Field(..., description="Tháng ghi nhận (YYYY-MM)")



class MonthlyLogRequest(BaseModel):
    """Dữ liệu nhật ký tài chính từng tháng (monthly_logs)"""
    month: str = Field(..., description="Tháng ghi nhận YYYY-MM (Ví dụ: 2026-07)")
    revenue: int = Field(..., description="Doanh thu thực tế (VNĐ)")
    cost: int = Field(..., description="Tổng chi phí thực tế đã bao gồm tiền nhà (VNĐ)")
    note: Optional[str] = Field("", description="Ghi chú sự kiện thực tế trong tháng")


class SavePlaybookRequest(BaseModel):
    """Dữ liệu lưu kế sách tác chiến (Tactical Playbook) theo mô hình Embedded"""
    query: str = Field(..., description="Câu hỏi hoặc tình huống người dùng gặp phải")
    branch_id: Optional[str] = Field("BRANCH_UNKNOWN", description="Mã nhánh tư duy (BRANCH_A -> E)")
    branch_name: Optional[str] = Field("Tác chiến vận hành", description="Tên nhánh tư duy")
    model_name: Optional[str] = Field("", description="Tên mô hình kinh doanh của quán")
    strategy_id: Optional[str] = Field(None, description="Mã kế sách quán nếu có")
    answer_markdown: str = Field(..., description="Nội dung giải pháp tác chiến định dạng Markdown từ Copilot")
    title: Optional[str] = Field(None, description="Tiêu đề tóm tắt tình huống (nếu muốn đặt riêng)")
    dialogue_script: Optional[str] = Field(None, description="Lời thoại mẫu thực chiến nếu có")
    tasks: Optional[List[Dict[str, Any]]] = Field(None, description="Danh sách checklist đầu việc nếu đã có")


class ToggleTaskRequest(BaseModel):
    """Dữ liệu cập nhật trạng thái tick hoàn thành cho 1 task"""
    is_completed: Optional[bool] = Field(None, description="Trạng thái hoàn thành mới (None để đảo ngược)")


# =====================================================================
# XÁC THỰC NGƯỜI DÙNG & BẢO MẬT (AUTH HELPERS)
# =====================================================================

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Băm mật khẩu kết hợp Salt bảo mật bằng SHA-256."""
    if not salt:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    return pwd_hash, salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Xác thực mật khẩu người dùng nhập với hash đã lưu trong DB."""
    pwd_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(pwd_hash, expected_hash)


def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    """Trích xuất và kiểm tra session người dùng từ Authorization Header."""
    if not authorization or not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        return None
    token = authorization.split("Bearer ", 1)[1].strip()
    if not token:
        return None
    try:
        db = get_db()
        session = db["user_sessions"].find_one({"token": token})
        if not session:
            return None
        user = db["users"].find_one({"username": session["username"]})
        return user
    except Exception as e:
        logger.error(f"Lỗi xác thực người dùng: {e}")
        return None


# =====================================================================
# REST API ENDPOINTS
# =====================================================================

@app.post("/api/auth/register")
def register_user(req: RegisterRequest):
    """Đăng ký tài khoản người dùng mới."""
    db = get_db()
    clean_username = req.username.strip().lower()
    if not clean_username:
        raise HTTPException(status_code=400, detail="Tên đăng nhập không được để trống!")
    
    existing = db["users"].find_one({"username": clean_username})
    if existing:
        raise HTTPException(status_code=400, detail="Tên đăng nhập này đã được sử dụng!")
    
    pwd_hash, salt = hash_password(req.password)
    user_doc = {
        "username": clean_username,
        "password_hash": pwd_hash,
        "salt": salt,
        "full_name": req.full_name.strip() if req.full_name else clean_username,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    db["users"].insert_one(user_doc)
    
    # Tự động tạo token session sau khi đăng ký thành công
    token = secrets.token_hex(32)
    db["user_sessions"].insert_one({
        "token": token,
        "username": clean_username,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    logger.info(f"[✓] Đăng ký thành công tài khoản: {clean_username}")
    return {
        "status": "success",
        "message": "Đăng ký tài khoản thành công!",
        "token": token,
        "user": {
            "username": clean_username,
            "full_name": user_doc["full_name"]
        }
    }


@app.post("/api/auth/login")
def login_user(req: LoginRequest):
    """Đăng nhập tài khoản người dùng."""
    db = get_db()
    clean_username = req.username.strip().lower()
    user = db["users"].find_one({"username": clean_username})
    if not user:
        raise HTTPException(status_code=401, detail="Tài khoản hoặc mật khẩu không chính xác!")
    
    if not verify_password(req.password, user["salt"], user["password_hash"]):
        raise HTTPException(status_code=401, detail="Tài khoản hoặc mật khẩu không chính xác!")
    
    # Tạo token phiên đăng nhập
    token = secrets.token_hex(32)
    db["user_sessions"].insert_one({
        "token": token,
        "username": clean_username,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    logger.info(f"[✓] Đăng nhập thành công: {clean_username}")
    return {
        "status": "success",
        "message": "Đăng nhập thành công!",
        "token": token,
        "user": {
            "username": clean_username,
            "full_name": user.get("full_name", clean_username)
        }
    }


@app.get("/api/auth/me")
def get_user_profile(authorization: Optional[str] = Header(None)):
    """Lấy thông tin tài khoản hiện tại từ session token."""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Phiên đăng nhập hết hạn hoặc không hợp lệ!")
    
    return {
        "username": user["username"],
        "full_name": user.get("full_name", user["username"])
    }


@app.post("/api/auth/logout")
def logout_user(authorization: Optional[str] = Header(None)):
    """Đăng xuất tài khoản, hủy session token."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        db = get_db()
        db["user_sessions"].delete_many({"token": token})
    return {"status": "success", "message": "Đã đăng xuất thành công!"}


@app.post("/api/user/strategy/save")
def save_user_strategy(req: SaveStrategyRequest, authorization: Optional[str] = Header(None)):
    """
    Lưu trữ cấu hình mô hình (1xx), món định bán (2xx), địa chỉ, tọa độ [lng, lat]
    và toàn bộ Kế sách chiến lược (báo cáo 4 khối) của người dùng vào MongoDB.
    Tự động khởi tạo 3 khối thời gian:
    - profile: Vốn hiện tại, tiền thuê, tháng ghi nhận
    - simulation_profile: Doanh thu mục tiêu, biên lợi nhuận kỳ vọng, runway cạn vốn ban đầu
    - monthly_logs: Giữ nguyên lịch sử sổ sách nếu đã có
    """
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để lưu kế sách chiến lược!")
    
    db = get_db()
    
    # Tra cứu tên mô hình và nhóm sản phẩm từ tag_manager
    business_models = {m["id"]: m["name"] for m in tag_manager.get_business_models()}
    products_map = {p["id"]: p["name"] for p in tag_manager.get_products()}
    
    model_name = business_models.get(req.model_id, f"Mô hình {req.model_id}")
    product_names = [products_map.get(pid, f"Sản phẩm {pid}") for pid in req.product_ids]
    
    # Lấy tài liệu hiện tại nếu đã có để không ghi đè mất monthly_logs
    existing_doc = db["user_strategies"].find_one({"username": user["username"]})
    current_month_str = datetime.now().strftime("%Y-%m")

    # 1. Khởi tạo / cập nhật Khối profile hiện tại
    init_budget = int(req.budget) if req.budget is not None and req.budget > 0 else (
        existing_doc.get("profile", {}).get("budget", 0) if (existing_doc and isinstance(existing_doc.get("profile"), dict)) else 0
    )
    init_rent = int(req.rent) if req.rent is not None and req.rent >= 0 else (
        existing_doc.get("profile", {}).get("rent", 0) if (existing_doc and isinstance(existing_doc.get("profile"), dict)) else 0
    )

    target_scenario = (req.selected_scenario or "normal").lower().strip()
    if target_scenario not in ["normal", "premium"]:
        target_scenario = "normal"

    # TỰ ĐỘNG LẤY DỮ LIỆU TỪ BỘ GIẢ LẬP (SIMULATION DATA) ĐỂ THIẾT LẬP PROFILE:
    # A. Nhân sự & Lương: Lấy tự động theo mô hình kinh doanh từ cấu hình giả lập (financial_profiles.json / stress_test)
    fin_profiles = load_financial_profiles().get("business_model_profiles", {})
    bm_profile = fin_profiles.get(str(int(req.model_id)), {})
    sim_staff_count = int(bm_profile.get("staff_count", 2))
    sim_avg_salary = int(bm_profile.get("staff_salary_per_person", 6_000_000))

    # Nếu stress_test trong kết quả thẩm định có ghi nhận số nhân sự:
    stress_data = req.report_result.get("stress_test") if isinstance(req.report_result, dict) else []
    chosen_scen = None
    if isinstance(stress_data, list) and len(stress_data) > 0:
        chosen_scen = next((s for s in stress_data if isinstance(s, dict) and s.get("scenario") == target_scenario), None)
        if not chosen_scen:
            chosen_scen = stress_data[0]
    elif isinstance(stress_data, dict):
        chosen_scen = stress_data

    if chosen_scen and isinstance(chosen_scen, dict):
        raw_staff = chosen_scen.get("staff_count")
        if raw_staff is not None:
            try:
                sim_staff_count = int(raw_staff)
            except (ValueError, TypeError):
                pass

        # Nếu chọn kịch bản Premium: Lương nhân viên tăng 25% theo PREMIUM_SALARY_MULTIPLIER
        if target_scenario == "premium" and sim_avg_salary > 0:
            sim_avg_salary = int(sim_avg_salary * 1.25)

    # Bỏ 1 chủ quán ra khi lưu vào profile: Hồ sơ quán và công thức lương chỉ tính nhân viên làm cùng, không tính chủ quán
    sim_staff_count = max(0, sim_staff_count - 1)

    # B. Tệp khách hàng mục tiêu: Lấy tự động từ phân bổ độ tuổi dân cư khu vực 3km (demographics.age_distribution)
    # Quy tắc: Chỉ lưu đúng duy nhất 1 tệp khách hàng chủ lực (dominant segment)
    demographics = req.report_result.get("demographics", {}) if isinstance(req.report_result, dict) else {}
    age_dist = demographics.get("age_distribution", {}) if isinstance(demographics, dict) else {}

    AGE_KEY_TO_TAG = {
        "18_24": 301, "18-24": 301,
        "25_34": 302, "25-34": 302,
        "35_50": 303, "35-50": 303,
        "over_50": 304, ">50": 304, "50+": 304, "> 50": 304
    }

    def safe_float(val):
        try:
            return float(val)
        except (ValueError, TypeError):
            return 0.0

    if age_dist and isinstance(age_dist, dict):
        sorted_ages = sorted(
            [(k, safe_float(v)) for k, v in age_dist.items() if k in AGE_KEY_TO_TAG],
            key=lambda x: x[1],
            reverse=True
        )
        sim_seg_ids = [AGE_KEY_TO_TAG[k] for k, _ in sorted_ages[:1]] if sorted_ages else [301]
    elif req.customer_segment_ids is not None and len(req.customer_segment_ids) > 0:
        sim_seg_ids = [int(sid) for sid in req.customer_segment_ids[:1]]
    else:
        sim_seg_ids = [301]

    if not sim_seg_ids:
        sim_seg_ids = [301]

    segment_map = {seg["id"]: seg["name"] for seg in tag_manager.get_customer_segments()}
    sim_seg_names = [segment_map.get(sid, f"Phân khúc {sid}") for sid in sim_seg_ids]

    profile_data = {
        "budget": init_budget,
        "rent": init_rent,
        "staff_count": sim_staff_count,
        "avg_salary": sim_avg_salary,
        "customer_segment_ids": sim_seg_ids,
        "customer_segments": sim_seg_names,
        "selected_scenario": target_scenario,
        "month_set": current_month_str
    }


    # 2. Khởi tạo Khối simulation_profile từ kết quả Thẩm định Day 0
    # Lấy runway_months từ kịch bản được chọn
    runway_val = 5
    try:
        if chosen_scen and isinstance(chosen_scen, dict):
            raw_month = chosen_scen.get("month") if chosen_scen.get("month") is not None else chosen_scen.get("runway_months", 5.0)
            runway_val = int(float(raw_month or 5.0))
    except Exception:
        runway_val = 5
    runway_val = max(0, runway_val)

    # Biên lợi nhuận chuẩn theo mô hình kinh doanh
    margin_benchmarks = {
        101: 40.0, 102: 55.0, 103: 30.0, 104: 35.0, 105: 35.0,
        106: 20.0, 107: 40.0, 108: 60.0, 109: 50.0, 110: 25.0
    }
    expected_margin = float(margin_benchmarks.get(int(req.model_id), 35.0))

    # Doanh thu mục tiêu ước tính (Target Monthly Revenue)
    # Ước lượng dựa trên tiền thuê và biên lãi
    model_base_opex = 3_000_000 if int(req.model_id) == 105 else 15_000_000
    base_fixed_costs = init_rent + model_base_opex
    target_rev = int((base_fixed_costs * 1.5) / (expected_margin / 100.0))
    min_target_rev = 15_000_000 if int(req.model_id) == 105 else 40_000_000
    target_rev = max(min_target_rev, round(target_rev / 1_000_000) * 1_000_000)

    simulation_data = {
        "target_monthly_revenue": target_rev,
        "expected_margin_pct": expected_margin,
        "zero_revenue_runway_months": runway_val
    }

    # 3. Bảo toàn Khối monthly_logs đã có
    monthly_logs = existing_doc.get("monthly_logs", []) if existing_doc else []

    strategy_doc = {
        "username": user["username"],
        "address": req.address.strip(),
        "coordinates": {
            "lng": float(req.coordinates.get("lng") or 0.0),
            "lat": float(req.coordinates.get("lat") or 0.0)
        },
        "model_id": req.model_id,
        "model_name": model_name,
        "product_ids": req.product_ids,
        "product_names": product_names,
        "customer_segment_ids": sim_seg_ids,
        "customer_segments": sim_seg_names,
        "selected_scenario": target_scenario,
        "report_result": req.report_result,
        "profile": profile_data,
        "simulation_profile": simulation_data,
        "monthly_logs": monthly_logs,
        "is_active": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    db["user_strategies"].update_one(
        {"username": user["username"]},
        {"$set": strategy_doc},
        upsert=True
    )
    
    scen_label = "Nâng cao (Premium)" if target_scenario == "premium" else "Thông thường (Normal)"
    logger.info(f"[✓] Đã lưu kế sách ({scen_label}) cho user '{user['username']}' tại '{strategy_doc['address']}'.")
    return {
        "status": "success",
        "message": f"Đã lưu kế sách chiến lược ({scen_label}) thành công vào hồ sơ cá nhân của bạn!",
        "strategy": {
            "address": strategy_doc["address"],
            "coordinates": strategy_doc["coordinates"],
            "model_id": strategy_doc["model_id"],
            "model_name": strategy_doc["model_name"],
            "product_ids": strategy_doc["product_ids"],
            "product_names": strategy_doc["product_names"],
            "customer_segment_ids": strategy_doc["customer_segment_ids"],
            "customer_segments": strategy_doc["customer_segments"],
            "selected_scenario": strategy_doc["selected_scenario"],
            "profile": strategy_doc["profile"],
            "simulation_profile": strategy_doc["simulation_profile"],
            "monthly_logs": strategy_doc["monthly_logs"],
            "updated_at": strategy_doc["updated_at"]
        }
    }


@app.post("/api/user/strategy/profile")
def update_user_profile(req: UpdateProfileRequest, authorization: Optional[str] = Header(None)):
    """
    Cập nhật thông tin thực tế hồ sơ quán (profile):
    - budget: Vốn thực tế còn lại
    - rent: Tiền thuê mặt bằng hiện tại
    - staff_count: Số lượng nhân sự hiện tại
    - avg_salary: Lương bình quân mỗi nhân sự
    - customer_segment_ids: Danh sách phân khúc khách hàng mục tiêu
    - month_set: Tháng chốt số liệu (YYYY-MM)
    """
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để cập nhật hồ sơ quán!")
    
    db = get_db()
    strat = db["user_strategies"].find_one({"username": user["username"]})
    if not strat:
        raise HTTPException(status_code=404, detail="Chưa có hồ sơ kế sách của người dùng!")
    
    clean_seg_ids = [int(sid) for sid in (req.customer_segment_ids or [])][:1]
    if not clean_seg_ids:
        clean_seg_ids = [301]
    segment_map = {seg["id"]: seg["name"] for seg in tag_manager.get_customer_segments()}
    clean_seg_names = [segment_map.get(sid, f"Phân khúc {sid}") for sid in clean_seg_ids]

    profile_data = {
        "budget": int(req.budget),
        "rent": int(req.rent),
        "staff_count": int(req.staff_count or 0),
        "avg_salary": int(req.avg_salary or 0),
        "customer_segment_ids": clean_seg_ids,
        "customer_segments": clean_seg_names,
        "month_set": req.month_set.strip()
    }

    db["user_strategies"].update_one(
        {"username": user["username"]},
        {"$set": {
            "profile": profile_data,
            "customer_segment_ids": clean_seg_ids,
            "customer_segments": clean_seg_names,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    logger.info(f"[✓] User '{user['username']}' đã cập nhật profile: Vốn {req.budget:,.0f}đ, Thuê {req.rent:,.0f}đ, NV {req.staff_count or 0} (Lương {req.avg_salary or 0:,.0f}đ), Tệp KH: {clean_seg_names} ({req.month_set})")
    return {
        "status": "success",
        "message": "Đã cập nhật hồ sơ quán thành công!",
        "profile": profile_data,
        "customer_segment_ids": clean_seg_ids,
        "customer_segments": clean_seg_names
    }


@app.post("/api/user/strategy/monthly_log")
def upsert_monthly_log(req: MonthlyLogRequest, authorization: Optional[str] = Header(None)):
    """
    Ghi nhận hoặc cập nhật nhật ký tài chính một tháng (monthly_logs).
    Backend Python tự động tính toán:
    - profit = revenue - cost
    - margin_pct = (profit / revenue) * 100%
    """
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để ghi chép sổ sách tháng!")
    
    clean_month = req.month.strip()
    if not re.match(r"^\d{4}-\d{2}$", clean_month):
        raise HTTPException(status_code=400, detail="Định dạng tháng phải là YYYY-MM (Ví dụ: 2026-07)")
    
    db = get_db()
    strat = db["user_strategies"].find_one({"username": user["username"]})
    if not strat:
        raise HTTPException(status_code=404, detail="Chưa tìm thấy hồ sơ kế sách để lưu sổ sách tháng!")
    
    # Tính toán tự động chuẩn xác bằng Python (Deterministic Math)
    profit = int(req.revenue) - int(req.cost)
    margin_pct = round((profit / float(req.revenue)) * 100.0, 1) if req.revenue > 0 else 0.0

    monthly_logs = strat.get("monthly_logs", [])
    updated = False

    for log in monthly_logs:
        if log.get("month") == clean_month:
            log["revenue"] = int(req.revenue)
            log["cost"] = int(req.cost)
            log["profit"] = profit
            log["margin_pct"] = margin_pct
            log["note"] = req.note.strip() if req.note else ""
            updated = True
            break
    
    if not updated:
        monthly_logs.append({
            "month": clean_month,
            "revenue": int(req.revenue),
            "cost": int(req.cost),
            "profit": profit,
            "margin_pct": margin_pct,
            "note": req.note.strip() if req.note else ""
        })
    
    # Sắp xếp các tháng theo thứ tự tăng dần (cũ đến mới)
    monthly_logs.sort(key=lambda x: x.get("month", ""))

    db["user_strategies"].update_one(
        {"username": user["username"]},
        {"$set": {
            "monthly_logs": monthly_logs,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )

    logger.info(f"[✓] User '{user['username']}' ghi sổ tháng {clean_month}: Doanh thu {req.revenue:,.0f}đ, Lãi {profit:,.0f}đ")
    return {
        "status": "success",
        "message": f"Đã lưu sổ sách tháng {clean_month} thành công!",
        "entry": {
            "month": clean_month,
            "revenue": int(req.revenue),
            "cost": int(req.cost),
            "profit": profit,
            "margin_pct": margin_pct,
            "note": req.note.strip() if req.note else ""
        },
        "monthly_logs": monthly_logs
    }


@app.delete("/api/user/strategy/monthly_log/{month}")
def delete_monthly_log(month: str, authorization: Optional[str] = Header(None)):
    """Xóa nhật ký tài chính của một tháng cụ thể."""
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập!")
    
    db = get_db()
    strat = db["user_strategies"].find_one({"username": user["username"]})
    if not strat:
        raise HTTPException(status_code=404, detail="Không tìm thấy hồ sơ quán!")
    
    monthly_logs = [log for log in strat.get("monthly_logs", []) if log.get("month") != month]
    db["user_strategies"].update_one(
        {"username": user["username"]},
        {"$set": {
            "monthly_logs": monthly_logs,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    return {"status": "success", "message": f"Đã xóa sổ sách tháng {month}!", "monthly_logs": monthly_logs}


@app.get("/api/user/strategy/active")
def get_active_strategy(authorization: Optional[str] = Header(None)):
    """
    Truy xuất kế sách chiến lược đang áp dụng của người dùng đã đăng nhập.
    Bao gồm cả 3 khối: profile, simulation_profile, monthly_logs.
    """
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để xem kế sách!")
    
    db = get_db()
    doc = db["user_strategies"].find_one({"username": user["username"]})
    if not doc:
        return {"has_strategy": False, "strategy": None}
    
    current_month_str = datetime.now().strftime("%Y-%m")
    strat_profile = doc.get("profile", {}) if isinstance(doc.get("profile"), dict) else {}
    seg_ids = (doc.get("customer_segment_ids") or strat_profile.get("customer_segment_ids", []))[:1]
    seg_names = (doc.get("customer_segments") or strat_profile.get("customer_segments", []))[:1]

    prod_ids = doc.get("product_ids") or strat_profile.get("product_ids", [])
    prod_names = doc.get("product_names") or strat_profile.get("product_names", [])
    if (not prod_names or len(prod_names) == 0) and prod_ids:
        products_map = {p["id"]: p["name"] for p in tag_manager.get_products()}
        prod_names = [products_map.get(pid, f"Sản phẩm {pid}") for pid in prod_ids]

    return {
        "has_strategy": True,
        "strategy": {
            "address": doc.get("address", ""),
            "coordinates": doc.get("coordinates", {}),
            "model_id": doc.get("model_id"),
            "model_name": doc.get("model_name", ""),
            "product_ids": prod_ids,
            "product_names": prod_names,
            "customer_segment_ids": seg_ids,
            "customer_segments": seg_names,
            "report_result": doc.get("report_result", {}),
            "profile": {
                "budget": strat_profile.get("budget", 0),
                "rent": strat_profile.get("rent", 0),
                "staff_count": strat_profile.get("staff_count", 0),
                "avg_salary": strat_profile.get("avg_salary", 0),
                "customer_segment_ids": seg_ids,
                "customer_segments": seg_names,
                "product_ids": prod_ids,
                "product_names": prod_names,
                "month_set": strat_profile.get("month_set", current_month_str)
            },
            "simulation_profile": doc.get("simulation_profile", {
                "target_monthly_revenue": 60_000_000,
                "expected_margin_pct": 35.0,
                "zero_revenue_runway_months": 5
            }),
            "monthly_logs": doc.get("monthly_logs", []),
            "updated_at": doc.get("updated_at", "")
        }
    }


@app.get("/api/health")
def health_check():
    """Kiểm tra trạng thái kết nối MongoDB, Ollama và mô hình Embedding."""
    mongo_status = check_mongo_health()
    return {
        "status": "online",
        "mongo": mongo_status,
        "llm_model": LLM_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "port": PORT
    }


@app.post("/api/llm/verify")
def verify_llm_config(req: LLMConfigPayload):
    """Kiểm tra nhanh kết nối API Key và Model của người dùng."""
    from .pipeline.llm_copilot.cloud_provider import verify_cloud_api_key
    is_valid, resolved_model, msg = verify_cloud_api_key(
        provider=req.provider or "gemini",
        api_key=req.api_key or "",
        model=req.model
    )
    if not is_valid:
        raise HTTPException(status_code=400, detail=msg)
    return {
        "status": "success",
        "provider": req.provider or "gemini",
        "model": resolved_model,
        "message": msg
    }


@app.get("/api/metadata")
def get_metadata():
    """
    Trả về danh mục:
    - 10 Mô hình kinh doanh
    - 20 Nhóm sản phẩm chuẩn hóa
    - 4 Phân khúc khách hàng mục tiêu
    - Danh sách gợi ý các địa chỉ phổ biến tại TP.HCM
    """
    suggested_locations = [
        "Cổng ĐH Bách Khoa, Tô Hiến Thành, Quận 10",
        "Gần Chợ Bến Thành, Quận 1",
        "Khu Phố Tây Thảo Điền, Quận 2",
        "Đường Tú Xương / Hồ Con Rùa, Quận 3",
        "Phố ẩm thực Tôn Đản / Vĩnh Khánh, Quận 4"
    ]
    return {
        "business_models": tag_manager.get_business_models(),
        "products": tag_manager.get_products(),
        "customer_segments": tag_manager.get_customer_segments(),
        "suggested_locations": suggested_locations
    }


@app.post("/api/scanner/evaluate")
def evaluate_business_feasibility(req: FeasibilityRequest):
    """
    GIAO DIỆN 1: MÁY QUÉT THẨM ĐỊNH Ý TƯỞNG (DAY 0)
    Chạy trọn vẹn quy trình các mắt xích:
    1. Geocoding -> Tọa độ & Dân cư 3km (DB1)
    2. Quét Đối thủ 1km (DB2)
    3. Phân tích Thị trường Vi mô (market_analyse_engine: CTS, Gom cụm BGE-M3, Giá, Giờ vàng)
    4. Thử tải sinh tồn (stress_test_engine: Zero-revenue Runway simulator)
    5. Sách lược Chiến thuật (tactical_playbook_engine: 4 Vấn đề DB3 & 4 Kinh nghiệm DB4)
    6. LLM Qwen3.5 4B tổng hợp ra bản báo cáo thẩm định thực chiến.
    """
    try:
        logger.info(f"[*] Bắt đầu thẩm định cho địa chỉ: {req.address} | Vốn: {req.budget:,.0f}đ")
        
        if req.budget <= 0:
            raise HTTPException(status_code=400, detail="Số vốn đầu tư phải lớn hơn 0 VNĐ!")
        if not req.product_ids:
            raise HTTPException(status_code=400, detail="Vui lòng chọn ít nhất 1 sản phẩm kinh doanh!")

        # Mắt xích 1: Geocoding & Dân cư (DB1)
        lng, lat, display_addr = geocode_address(req.address)
        if lng == 0 and lat == 0:
            raise HTTPException(status_code=400, detail="Không thể định vị được địa chỉ này trên bản đồ. Vui lòng nhập địa chỉ rõ ràng hơn (VD: Tên đường, Phường/Xã, Quận/Huyện)!")
        demographics = spatial_engine.get_area_demographics(lng, lat)

        # Mắt xích 1b: Quét Đối thủ trong 1km (DB2)
        competitors = spatial_engine.get_competitors_within_radius(
            lng, lat, radius_m=1000.0,
            model_id=req.model_id,
            product_ids=req.product_ids
        )

        # Mắt xích 2: Phân tích Thị trường Vi mô (DB2 x DB5 x DB4)
        market_analysis = market_analyse_engine.analyse_market(
            competitors=competitors,
            model_id=req.model_id,
            product_ids=req.product_ids,
            demographics=demographics,
            budget=req.budget
        )

        # Bổ sung danh sách thẻ market_gaps để bảo đảm tương thích ngược với Frontend
        gap_cards = []
        mw = market_analysis.get("market_weakness", {})
        if isinstance(mw, dict) and mw.get("important_weakness"):
            gap_cards.append({
                "title": "Tử huyệt đối thủ lớn nhất",
                "detail": mw["important_weakness"]
            })
        for nw in (mw.get("normal_weakness", []) if isinstance(mw, dict) else []):
            gap_cards.append({
                "title": "Điểm yếu hệ thống khu vực",
                "detail": nw
            })
        for ag in market_analysis.get("against_weakness", []):
            gap_cards.append({
                "title": "Đòn đánh hóa giải đề xuất",
                "detail": ag.get("lesson", "") if isinstance(ag, dict) else str(ag)
            })
        market_analysis["market_gaps"] = gap_cards

        # Mắt xích 3: Bộ Thử tải Rủi ro & Đo Sức sống Vốn (Zero-Revenue Runway)
        has_dual = market_analysis.get("has_dual_strategies", False)
        stress_test = stress_test_engine.run_stress_test(
            budget=req.budget,
            monthly_rent=req.rent,
            business_model_id=req.model_id,
            product_ids=req.product_ids,
            has_dual_strategies=has_dual
        )

        # Mắt xích 4: Sách lược Chiến thuật Đa dạng (DB3 x DB4 qua Tag 0 & Greedy Diversity Pruning)
        tactical_playbook = tactical_playbook_engine.run_tactical_playbook(
            model_id=req.model_id,
            product_ids=req.product_ids
        )

        # Mắt xích 6: LLM Reasoning (Qwen3.5 4B qua Ollama)
        model_name = tag_manager.get_tag_name(req.model_id)
        product_names = [tag_manager.get_tag_name(pid) for pid in req.product_ids]
        products_str = ", ".join(product_names)

        rent_val = float(req.rent) if (req.rent is not None and float(req.rent) >= 0) else float(DEFAULT_RENT_BY_MODEL.get(int(req.model_id), 10_000_000))


        form_summary = {
            "address": display_addr,
            "model_name": model_name,
            "model_id": req.model_id,
            "products_str": products_str,
            "product_ids": req.product_ids,
            "budget": req.budget,
            "rent": rent_val
        }

        ai_report = llm_copilot.evaluate_feasibility(
            form_data=form_summary,
            demographics=demographics,
            competitors=competitors,
            market_gaps=market_analysis,
            stress_test=stress_test,
            tactical_playbook=tactical_playbook,
            llm_config=req.llm_config.model_dump() if req.llm_config else None
        )

        # Kiểm tra sức sống vốn (Runway): Nếu cạn vốn ngay ngày đầu (<= 0), không gửi thông tin đối thủ, tấn công 3 mảng & playbook
        runway_val = 0.0
        if isinstance(stress_test, list) and len(stress_test) > 0:
            runway_val = float(stress_test[0].get("month", stress_test[0].get("runway_months", 0.0)))
        elif isinstance(stress_test, dict):
            runway_val = float(stress_test.get("month", stress_test.get("runway_months", 0.0)))
        is_red_alert = (runway_val <= 0.0)

        # Thu thập toàn bộ ID và thông tin tóm tắt của các Object thực tế được sử dụng
        all_competitors_processed = competitors if competitors else []
        used_problems = (tactical_playbook.get("top_4_problems", []) if tactical_playbook else [])
        used_exps = (tactical_playbook.get("top_4_experiences", []) if tactical_playbook else [])
        market_weakness_lessons = (market_analysis.get("against_weakness", []) if market_analysis else [])
        cust_insights = market_analysis.get("customer_insights", {}) if market_analysis else {}

        all_competitor_ids = [str(c.get("_id", c.get("id", ""))) for c in all_competitors_processed if (c.get("_id") or c.get("id"))]

        all_used_ids = {
            "db1_demographics_id": demographics.get("id") or str(demographics.get("_id", "")),
            "db2_competitor_ids": all_competitor_ids,
            "db3_problem_ids": [p.get("id") for p in used_problems if p.get("id")],
            "db4_experience_ids": list(dict.fromkeys(filter(None, [
                *[exp.get("id") for exp in used_exps],
                *[m.get("experience_id") for m in market_weakness_lessons if m.get("experience_id")]
            ]))),
            "db5_market_segment_id": cust_insights.get("segment_id")
        }

        used_objects = {
            "all_used_ids": all_used_ids,
            "total_competitors_analyzed": len(all_competitors_processed),
            "demographics": {
                "id": demographics.get("id") or str(demographics.get("_id", "")),
                "name": demographics.get("name", ""),
                "ward_name": demographics.get("ward_name", ""),
                "population_density": demographics.get("population_density", 0)
            },
            "competitors": [
                {
                    "id": str(c.get("_id", c.get("id", ""))),
                    "name": c.get("name", ""),
                    "business_model_id": c.get("business_model_id"),
                    "product_ids": c.get("product_ids", []),
                    "distance_m": c.get("distance_m"),
                    "weakness": c.get("weakness", "")
                }
                for c in all_competitors_processed
            ],
            "market_segment": {
                "id": cust_insights.get("segment_id"),
                "time": cust_insights.get("time"),
                "price": cust_insights.get("price"),
                "behavior": cust_insights.get("behavior"),
                "primary_product_id": cust_insights.get("primary_product_id"),
                "secondary_insights": cust_insights.get("secondary_insights")
            } if cust_insights.get("segment_id") else None,
            "market_lessons": [
                {
                    "experience_id": m.get("experience_id"),
                    "lesson": m.get("lesson"),
                    "cosine_score": m.get("cosine_score")
                }
                for m in market_weakness_lessons
                if m.get("experience_id")
            ],
            "tactical_problems": used_problems,
            "tactical_experiences": used_exps
        }

        return {
            "success": True,
            "location_info": {
                "input_address": req.address,
                "recognized_area": display_addr,
                "coordinates": [lng, lat]
            },
            "demographics": demographics,
            "competitors_summary": None if is_red_alert else {
                "total_nearby": len(competitors),
                "list": competitors[:8]  # Trả về 8 đối thủ tiêu biểu
            },
            "market_analysis": None if is_red_alert else market_analysis,
            "market_gaps": None if is_red_alert else market_analysis,          # Giữ alias cho frontend cũ
            "stress_test": stress_test,              # Mảng kịch bản [normal, premium] chuẩn đặc tả
            "tactical_playbook": None if is_red_alert else tactical_playbook,  # Top 4 vấn đề & Top 4 kinh nghiệm
            "ai_report": ai_report,
            "used_objects": used_objects,
            "used_object_ids": all_used_ids
        }

    except Exception as e:
        logger.error(f"[!] Lỗi trong quá trình thẩm định: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi phân tích pipeline: {str(e)}")


@app.post("/api/scanner/evaluate/stream")
def evaluate_business_feasibility_stream(req: FeasibilityRequest):
    """
    GIAO DIỆN 1: MÁY QUÉT THẨM ĐỊNH Ý TƯỞNG (STREAMING 2 PHA)
    - Pha 1: Trả về NGAY LẬP TỨC toàn bộ kết quả tính toán logic (Bản đồ, Dân cư DB1,
      Đối thủ 1km DB2, Phân tích thị trường vi mô DB5, Thử tải sinh tồn Runway,
      4 Vấn đề cốt tử DB3 & 4 Bài học DB4) cho Frontend hiển thị tức thì.
    - Pha 2: Streaming từng chữ / token từ LLM Qwen3.5 4B qua Server-Sent Events (SSE)
      để điền dần vào Bản Kế Hoạch Tác Chiến Chiến Lược.
    """
    try:
        logger.info(f"[*] Bắt đầu thẩm định Streaming cho địa chỉ: {req.address} | Vốn: {req.budget:,.0f}đ")
        
        if req.budget <= 0:
            raise HTTPException(status_code=400, detail="Số vốn đầu tư phải lớn hơn 0 VNĐ!")
        if not req.product_ids:
            raise HTTPException(status_code=400, detail="Vui lòng chọn ít nhất 1 sản phẩm kinh doanh!")

        # Mắt xích 1: Geocoding & Dân cư (DB1)
        lng, lat, display_addr = geocode_address(req.address)
        if lng == 0 and lat == 0:
            raise HTTPException(status_code=400, detail="Không thể định vị được địa chỉ này trên bản đồ. Vui lòng nhập địa chỉ rõ ràng hơn (VD: Tên đường, Phường/Xã, Quận/Huyện)!")
        demographics = spatial_engine.get_area_demographics(lng, lat)

        # Mắt xích 1b: Quét Đối thủ trong 1km (DB2)
        competitors = spatial_engine.get_competitors_within_radius(
            lng, lat, radius_m=1000.0,
            model_id=req.model_id,
            product_ids=req.product_ids
        )

        # Mắt xích 2: Phân tích Thị trường Vi mô (DB2 x DB5 x DB4)
        market_analysis = market_analyse_engine.analyse_market(
            competitors=competitors,
            model_id=req.model_id,
            product_ids=req.product_ids,
            demographics=demographics,
            budget=req.budget
        )

        gap_cards = []
        mw = market_analysis.get("market_weakness", {})
        if isinstance(mw, dict) and mw.get("important_weakness"):
            gap_cards.append({
                "title": "Tử huyệt đối thủ lớn nhất",
                "detail": mw["important_weakness"]
            })
        for nw in (mw.get("normal_weakness", []) if isinstance(mw, dict) else []):
            gap_cards.append({
                "title": "Điểm yếu hệ thống khu vực",
                "detail": nw
            })
        for ag in market_analysis.get("against_weakness", []):
            gap_cards.append({
                "title": "Đòn đánh hóa giải đề xuất",
                "detail": ag.get("lesson", "") if isinstance(ag, dict) else str(ag)
            })
        market_analysis["market_gaps"] = gap_cards

        # Mắt xích 3: Bộ Thử tải Rủi ro & Đo Sức sống Vốn (Zero-Revenue Runway)
        has_dual = market_analysis.get("has_dual_strategies", False)
        stress_test = stress_test_engine.run_stress_test(
            budget=req.budget,
            monthly_rent=req.rent,
            business_model_id=req.model_id,
            product_ids=req.product_ids,
            has_dual_strategies=has_dual
        )

        # Mắt xích 4: Sách lược Chiến thuật Đa dạng (DB3 x DB4 qua Tag 0 & Greedy Diversity Pruning)
        tactical_playbook = tactical_playbook_engine.run_tactical_playbook(
            model_id=req.model_id,
            product_ids=req.product_ids
        )

        # Kiểm tra sức sống vốn (Runway)
        runway_val = 0.0
        if isinstance(stress_test, list) and len(stress_test) > 0:
            runway_val = float(stress_test[0].get("month", stress_test[0].get("runway_months", 0.0)))
        elif isinstance(stress_test, dict):
            runway_val = float(stress_test.get("month", stress_test.get("runway_months", 0.0)))
        is_red_alert = (runway_val <= 0.0)

        # Thu thập ID & Object thực tế
        all_competitors_processed = competitors if competitors else []
        used_problems = (tactical_playbook.get("top_4_problems", []) if tactical_playbook else [])
        used_exps = (tactical_playbook.get("top_4_experiences", []) if tactical_playbook else [])
        market_weakness_lessons = (market_analysis.get("against_weakness", []) if market_analysis else [])
        cust_insights = market_analysis.get("customer_insights", {}) if market_analysis else {}

        all_competitor_ids = [str(c.get("_id", c.get("id", ""))) for c in all_competitors_processed if (c.get("_id") or c.get("id"))]

        all_used_ids = {
            "db1_demographics_id": demographics.get("id") or str(demographics.get("_id", "")),
            "db2_competitor_ids": all_competitor_ids,
            "db3_problem_ids": [p.get("id") for p in used_problems if p.get("id")],
            "db4_experience_ids": list(dict.fromkeys(filter(None, [
                *[exp.get("id") for exp in used_exps],
                *[m.get("experience_id") for m in market_weakness_lessons if m.get("experience_id")]
            ]))),
            "db5_market_segment_id": cust_insights.get("segment_id")
        }

        used_objects = {
            "all_used_ids": all_used_ids,
            "total_competitors_analyzed": len(all_competitors_processed),
            "demographics": {
                "id": demographics.get("id") or str(demographics.get("_id", "")),
                "name": demographics.get("name", ""),
                "ward_name": demographics.get("ward_name", ""),
                "population_density": demographics.get("population_density", 0)
            },
            "competitors": [
                {
                    "id": str(c.get("_id", c.get("id", ""))),
                    "name": c.get("name", ""),
                    "business_model_id": c.get("business_model_id"),
                    "product_ids": c.get("product_ids", []),
                    "distance_m": c.get("distance_m"),
                    "weakness": c.get("weakness", "")
                }
                for c in all_competitors_processed
            ],
            "market_segment": {
                "id": cust_insights.get("segment_id"),
                "time": cust_insights.get("time"),
                "price": cust_insights.get("price"),
                "behavior": cust_insights.get("behavior")
            } if cust_insights.get("segment_id") else None,
            "market_lessons": [
                {
                    "experience_id": m.get("experience_id"),
                    "lesson": m.get("lesson"),
                    "cosine_score": m.get("cosine_score")
                }
                for m in market_weakness_lessons
                if m.get("experience_id")
            ],
            "tactical_problems": used_problems,
            "tactical_experiences": used_exps
        }

        model_name = tag_manager.get_tag_name(req.model_id)
        product_names = [tag_manager.get_tag_name(pid) for pid in req.product_ids]
        products_str = ", ".join(product_names)
        rent_val = float(req.rent) if (req.rent is not None and float(req.rent) >= 0) else float(DEFAULT_RENT_BY_MODEL.get(int(req.model_id), 10_000_000))


        form_summary = {
            "address": display_addr,
            "model_name": model_name,
            "model_id": req.model_id,
            "products_str": products_str,
            "product_ids": req.product_ids,
            "budget": req.budget,
            "rent": rent_val
        }

        # Dữ liệu logic gửi TRƯỚC ngay lập tức
        logic_results_event = {
            "type": "logic_results",
            "data": {
                "success": True,
                "location_info": {
                    "input_address": req.address,
                    "recognized_area": display_addr,
                    "coordinates": [lng, lat]
                },
                "demographics": demographics,
                "competitors_summary": None if is_red_alert else {
                    "total_nearby": len(competitors),
                    "list": competitors[:8]
                },
                "market_analysis": None if is_red_alert else market_analysis,
                "market_gaps": None if is_red_alert else market_analysis,
                "stress_test": stress_test,
                "tactical_playbook": None if is_red_alert else tactical_playbook,
                "used_objects": used_objects,
                "used_object_ids": all_used_ids,
                "is_red_alert": is_red_alert,
                "business_model": {
                    "model_id": req.model_id,
                    "model_name": model_name,
                    "product_ids": req.product_ids,
                    "products_str": products_str,
                    "budget": req.budget,
                    "rent": rent_val
                }
            }
        }

        def event_stream():
            # Pha 1: Bắn ngay lập tức toàn bộ số liệu logic tính toán ra Frontend
            yield f"data: {json.dumps(logic_results_event, ensure_ascii=False)}\n\n"

            # Pha 2: Streaming từng chữ / token từ LLM Qwen3.5 4B qua Ollama (hoặc Cloud API Key)
            try:
                for token in llm_copilot.stream_evaluate_feasibility(
                    form_data=form_summary,
                    demographics=demographics,
                    competitors=competitors,
                    market_gaps=market_analysis,
                    stress_test=stress_test,
                    tactical_playbook=tactical_playbook,
                    llm_config=req.llm_config.model_dump() if req.llm_config else None
                ):
                    yield f"data: {json.dumps({'type': 'chunk', 'text': token}, ensure_ascii=False)}\n\n"
            except Exception as stream_err:
                logger.error(f"[!] Lỗi stream LLM evaluate: {stream_err}")
                err_msg = f"\n\n[!] Lỗi sinh báo cáo AI: {str(stream_err)}"
                err_payload = json.dumps({"type": "chunk", "text": err_msg}, ensure_ascii=False)
                yield f"data: {err_payload}\n\n"


            # Kết thúc dòng SSE
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        logger.error(f"[!] Lỗi trong quá trình thẩm định stream: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi phân tích pipeline: {str(e)}")


def _format_copilot_context_and_insights(
    competitors: List[Dict[str, Any]],
    problems: List[Dict[str, Any]],
    experiences: List[Dict[str, Any]],
    market_segments: List[Dict[str, Any]],
    customer_segments: Optional[List[str]] = None,
    customer_segment_ids: Optional[List[int]] = None
) -> Tuple[str, Dict[str, int]]:
    """
    Chắt lọc và định dạng dữ liệu trực tiếp theo nhu cầu từng nhánh,
    không phụ thuộc vào distillation engine cũ.
    Tận dụng sâu tệp khách hàng chủ lực từ Day 0 / Hồ sơ quán.
    """
    lines = []

    # 0. Tệp khách hàng mục tiêu cốt lõi (Day 0 / Hồ sơ quán)
    resolved_seg_names = list(customer_segments or [])
    if not resolved_seg_names and customer_segment_ids:
        resolved_seg_names = [tag_manager.get_tag_name(sid) for sid in customer_segment_ids if tag_manager.get_tag_name(sid)]

    if resolved_seg_names:
        seg_str = ", ".join(resolved_seg_names)
        lines.append(f"### TỆP KHÁCH HÀNG MỤC TIÊU CHỦ LỰC (DAY 0 / HỒ SƠ QUÁN): {seg_str.upper()}")
        lines.append(
            f"- Nhóm khách hàng chủ lực: **{seg_str}**. Mọi đề xuất về giá bán, thiết kế combo món mồi, "
            "khung giờ phục vụ và phong cách tư vấn phải phục vụ đúng nhu cầu và túi tiền của tệp khách này."
        )
        lines.append("")

    # 1. Đối thủ cạnh tranh DB2 (nếu có)
    if competitors:
        lines.append("### ĐỐI THỦ CẠNH TRANH THỰC TẾ TRONG BÁN KÍNH 1KM (DB2):")
        for c in competitors[:5]:
            name = c.get("name", "Quán lân cận")
            dist = round(c.get("distance_m", 0))
            price = c.get("price_range", "Chưa rõ")
            weakness = c.get("weakness", "Chưa có thông tin")
            lines.append(f"- Quán '{name}' (Cách {dist}m, Giá: {price}) => Điểm yếu: \"{weakness}\"")
        lines.append("")

    # 2. Sự cố & Rủi ro DB3
    if problems:
        lines.append("### DỮ LIỆU SỰ CỐ & RỦI RO THỰC TẾ LIÊN QUAN (DB3):")
        sev_map = {3: "HIGH", 2: "MEDIUM", 1: "LOW", "3": "HIGH", "2": "MEDIUM", "1": "LOW"}
        seen_p_titles = set()
        for p in problems:
            title = p.get("title", "").strip()
            title_key = title.lower()
            if title_key in seen_p_titles:
                continue
            seen_p_titles.add(title_key)
            summary = p.get("summary", "")
            if len(summary) > 140:
                summary = summary[:140].strip() + "..."
            sev_label = sev_map.get(p.get("severity", 2), "MEDIUM")
            lines.append(f"- [{sev_label}] {title}: {summary}")
        lines.append("")

    # 3. Bài học kinh nghiệm & Lời thoại DB4
    if experiences:
        lines.append("### BÀI HỌC KINH NGHIỆM ĐÃ KIỂM CHỨNG & LỜI THOẠI ĐÀM PHÁN (DB4):")
        seen_exp_titles = set()
        for exp in experiences:
            title = exp.get("title", "").strip()
            title_key = title.lower()
            if title_key in seen_exp_titles:
                continue
            seen_exp_titles.add(title_key)
            takeaway = exp.get("key_takeaway") or exp.get("story", "")
            if len(takeaway) > 160:
                takeaway = takeaway[:160].strip() + "..."
            dialogue = exp.get("dialogue_script", "").strip()
            script_part = f" => Lời thoại mẫu: \"{dialogue}\"" if dialogue else ""
            lines.append(f"- {title}: {takeaway}{script_part}")
        lines.append("")

    # 4. Hành vi & Sức mua khách hàng DB5
    if market_segments:
        lines.append("### HÀNH VI & SỨC MUA KHÁCH HÀNG (DB5):")
        for m in market_segments:
            behavior = m.get("demand") or m.get("behavior_notes", "")
            if len(behavior) > 140:
                behavior = behavior[:140].strip() + "..."
            segment_name = m.get("segment")
            if not segment_name:
                for tid in m.get("tag_ids", []):
                    if 301 <= tid <= 304:
                        segment_name = tag_manager.get_tag_name(tid)
                        break
            if not segment_name:
                segment_name = "Khách hàng mục tiêu"

            budget_str = m.get("price_tolerance")
            if not budget_str:
                pr = m.get("price_range")
                if isinstance(pr, dict) and "min" in pr and "max" in pr:
                    budget_str = f"{pr['min']:,}đ - {pr['max']:,}đ"
                else:
                    budget_str = "Chưa rõ"

            peak_str = m.get("peak_traffic")
            if not peak_str:
                ph = m.get("peak_hours")
                if isinstance(ph, list) and ph:
                    peak_str = ", ".join(
                        f"{p.get('start', '')} - {p.get('end', '')}"
                        for p in ph if isinstance(p, dict) and p.get("start")
                    )
                else:
                    peak_str = "Chưa rõ"

            lines.append(f"- Tệp {segment_name} (Túi tiền: {budget_str}, Giờ cao điểm: {peak_str}): {behavior}")
        lines.append("")

    context_md = "\n".join(lines).strip()
    if not context_md:
        context_md = "- Không có dữ liệu đặc thù bổ sung."

    matched_insights = {
        "problems_found": len(problems),
        "lessons_found": len(experiences),
        "market_found": len(market_segments),
        "competitors_found": len(competitors)
    }

    return context_md, matched_insights


@app.post("/api/copilot/chat")
def copilot_chat(req: CopilotChatRequest, authorization: Optional[str] = Header(None)):
    """
    GIAO DIỆN 2: TRỢ LÝ CHIẾN THUẬT ĐỒNG HÀNH (DAY 1 - 365)
    Bộ định tuyến Agentic Router:
    1. Phân loại ý định: CẠNH TRANH (COMPETITIVE) vs NỘI BỘ (INTERNAL).
    2. Nếu CẠNH TRANH:
       - Lấy vị trí quán (từ user_strategies hoặc input người dùng).
       - Quét DB2 (Đối thủ 1km) + DB3 (Rủi ro) + DB4 (Kinh nghiệm) + DB5 (Sức mua thị trường).
       - LLM xuất đòn phản công combo, giữ giá và khai thác điểm yếu đối thủ.
    3. Nếu NỘI BỘ:
       - Quét DB3 (Rủi ro & sự cố) + DB4 (Bài học xương máu & lời thoại).
       - LLM xuất checklist SOP quy trình & đàm phán nội bộ.
    """
    try:
        query_text = req.query.strip()
        if not query_text:
            raise HTTPException(status_code=400, detail="Câu hỏi không được để trống")

        logger.info(f"[*] Nhận câu hỏi Co-pilot: '{query_text}' | Model ID: {req.model_id}")

        # Lấy thông tin kế sách đã lưu của người dùng (nếu có đăng nhập)
        user = get_current_user(authorization) if authorization else None
        saved_strategy = None
        if user:
            db = get_db()
            saved_strategy = db["user_strategies"].find_one({"username": user["username"]})

        # Ưu tiên dữ liệu người dùng truyền từ giao diện, sau đó đến hồ sơ đã lưu
        model_id = req.model_id or (saved_strategy.get("model_id") if saved_strategy else None) or 105
        product_ids = req.product_ids or (saved_strategy.get("product_ids") if saved_strategy else None) or []
        address = req.address or (saved_strategy.get("address") if saved_strategy else "")
        req_coords = req.coordinates or (saved_strategy.get("coordinates") if saved_strategy else None)

        # Lấy thông tin Phân khúc khách hàng mục tiêu từ Day 0 / Hồ sơ quán
        customer_segment_ids = (
            req.customer_segment_ids
            or (saved_strategy.get("customer_segment_ids") if saved_strategy else None)
            or (saved_strategy.get("profile", {}).get("customer_segment_ids") if saved_strategy else None)
            or []
        )
        customer_segments = (
            (saved_strategy.get("customer_segments") if saved_strategy else None)
            or (saved_strategy.get("profile", {}).get("customer_segments") if saved_strategy else None)
            or []
        )
        if not customer_segments and customer_segment_ids:
            customer_segments = [tag_manager.get_tag_name(sid) for sid in customer_segment_ids if tag_manager.get_tag_name(sid)]

        # Xác định tọa độ quán phục vụ việc quét đối thủ 1km
        lng, lat = 106.6578, 10.7725  # Tọa độ mặc định: Cổng ĐH Bách Khoa, Q10
        if req_coords and "lng" in req_coords and "lat" in req_coords and float(req_coords.get("lng", 0)) != 0:
            lng = float(req_coords["lng"])
            lat = float(req_coords["lat"])
        elif address:
            try:
                calc_lng, calc_lat, _ = geocode_address(address)
                if calc_lng != 0:
                    lng, lat = calc_lng, calc_lat
            except Exception as geo_err:
                logger.warning(f"Lỗi geocoding địa chỉ copilot: {geo_err}")

        # Mắt xích Định tuyến Ý định (Agentic Intent Router - 5 Nhánh BGE-M3)
        intent_info = detect_copilot_intent(query_text)
        intent = intent_info.get("intent", "INTERNAL")
        model_name = tag_manager.get_tag_name(model_id) if model_id else "Chung các mô hình"
        if product_ids:
            prod_names = [tag_manager.get_tag_name(pid) for pid in product_ids if tag_manager.get_tag_name(pid)]
            if prod_names:
                model_name = f"{model_name} (Sản phẩm: {', '.join(prod_names)})"

        branch_id = intent_info.get("branch", "BRANCH_B")
        submodule_info = None
        branch_4_info = None
        branch_5_info = None

        if branch_id == "BRANCH_C":
            from .pipeline.branch_strategic import detect_branch_3_submodules, calculate_deterministic_math
            submodule_info = detect_branch_3_submodules(query_text, top_k=2)
            profile_data = saved_strategy.get("profile", {}) if saved_strategy else {}
            monthly_logs_data = saved_strategy.get("monthly_logs", []) if saved_strategy else []
            sim_profile_data = saved_strategy.get("simulation_profile", {}) if saved_strategy else {}
            math_calc = calculate_deterministic_math(
                submodule_info["primary_module"],
                profile_data,
                monthly_logs_data,
                sim_profile_data
            )
            submodule_info["math_result"] = math_calc

        elif branch_id == "BRANCH_D":
            from .pipeline.branch_competitive import evaluate_branch_4_competitive
            profile_data = saved_strategy.get("profile", {}) if saved_strategy else {}
            monthly_logs_data = saved_strategy.get("monthly_logs", []) if saved_strategy else []
            sim_profile_data = saved_strategy.get("simulation_profile", {}) if saved_strategy else {}

            competitors_b4 = []
            try:
                competitors_b4 = spatial_engine.get_competitors_within_radius(
                    lng=lng,
                    lat=lat,
                    radius_m=1000.0,
                    model_id=model_id,
                    product_ids=product_ids
                )
            except Exception as comp_err:
                logger.warning(f"[!] Lỗi quét đối thủ cho Nhánh 4: {comp_err}")

            branch_4_info = evaluate_branch_4_competitive(
                query=query_text,
                profile=profile_data,
                monthly_logs=monthly_logs_data,
                competitors=competitors_b4,
                simulation_profile=sim_profile_data,
                model_id=model_id,
                top_k=3
            )

        elif branch_id == "BRANCH_E":
            from .pipeline.branch_diagnostic import diagnose_business_issues
            branch_5_info = diagnose_business_issues(
                query=query_text,
                model_id=model_id,
                top_limit=3
            )

        # Nếu đang ở chế độ kiểm thử Phần I (Router Only)
        if req.mode == "part_1":
            ai_resp_lines = [
                f"### {intent_info.get('badge_title')}",
                "",
                f"• **Nhánh BGE xác định:** `{intent_info.get('branch')}` — **{intent_info.get('branch_name')}** ({intent_info.get('english_name')})",
                f"• **Độ tương đồng Cosine:** `{intent_info.get('confidence', 0):.4f}` (Cơ chế: `{intent_info.get('matched_by')}`)",
                f"• **Nguồn dữ liệu BẮT BUỘC:** `{', '.join(intent_info.get('data_sources', []))}`",
                f"• **Nguồn dữ liệu BỎ QUA:** `{', '.join(intent_info.get('skip_sources', [])) if intent_info.get('skip_sources') else 'Không'}`"
            ]

            if submodule_info:
                ai_resp_lines.extend([
                    "",
                    "---",
                    f"### {submodule_info.get('badge_title')}",
                    f"• **Module con chiến lược:** `{submodule_info.get('primary_module')}` — **{submodule_info.get('name')}**",
                    f"• **Độ tương đồng Module:** `{submodule_info.get('confidence', 0):.4f}`",
                    f"• **Mô tả chuyên sâu:** {submodule_info.get('badge_detail')}",
                    f"• **Số liệu tính toán mẫu (Deterministic Math):** `{json.dumps(submodule_info.get('math_result', {}), ensure_ascii=False)}`"
                ])

            if branch_4_info:
                primary_id = branch_4_info.get('primary_module')
                ai_resp_lines.extend([
                    "",
                    "---",
                    f"### 🛡️ CHIẾN LƯỢC PHẢN CÔNG CẠNH TRANH VI MÔ (NHÁNH 4)",
                    f"• **Module dẫn đầu:** `{primary_id}` — **{branch_4_info.get('primary_name')}**",
                    f"• **Định dạng giải thuật:** Chấm điểm 6 Module đồng thời (35% Intent + 65% Feasibility) → Chọn Top 3",
                    "",
                    "• **🏆 TOP 3 CHIẾN LƯỢC TÁC CHIẾN ĐƯỢC CHỌN:**"
                ])
                for rank_item in branch_4_info.get("detailed_rankings", [])[:3]:
                    ai_resp_lines.append(
                        f"  {rank_item['rank']}. {rank_item['badge_title']} → **{rank_item['total_score']}đ** "
                        f"(Ý định: {rank_item['intent_score']}đ | Khả thi: {rank_item['feasibility_score']}đ)"
                    )

            if branch_5_info:
                ai_resp_lines.extend([
                    "",
                    "---",
                    f"### 🩺 BÁO CÁO CHẨN ĐOÁN & KỊCH BẢN KHẢ NGHI (NHÁNH 5 - DIAGNOSTIC TRIAGE)",
                    f"• **Bệnh lý nghi vấn số 1:** `{branch_5_info.get('primary_tag')}` — **{branch_5_info.get('primary_name')}**",
                    f"• **Điểm tương đồng triệu chứng:** `{branch_5_info.get('scores', {}).get(branch_5_info.get('primary_tag'), 0)}đ`",
                    f"• **Các kịch bản khả nghi đã khoanh vùng:** `{', '.join(branch_5_info.get('suspected_tags', []))}`",
                    "",
                    "• **📋 KỊCH BẢN & CHECKLIST TỰ KIỂM TRA TẠI QUÁN TRONG 24H:**"
                ])
                for sc in branch_5_info.get("scenarios", []):
                    ai_resp_lines.extend([
                        f"\n**🔍 Kịch bản {sc['rank']}: {sc['scenario_title']}**",
                        f"  - *Dấu hiệu:* {sc['symptom_description']}",
                        f"  - *Lỗ rò rỉ tiềm ẩn:* {sc['potential_leak']}"
                    ])
                    for st in sc["checklist"]:
                        ai_resp_lines.append(f"  - [ ] **Bước {st['step_num']} ({st['title']}):** {st['action']}")

            ai_resp_lines.extend([
                "",
                "*(Hệ thống đã định tuyến và chẩn đoán chính xác theo tiêu chí Phần I, Nhánh 3, Nhánh 4 & Nhánh 5)*"
            ])

            return {
                "success": True,
                "query": query_text,
                "model_name": model_name,
                "intent": intent,
                "branch": branch_id,
                "branch_name": intent_info.get("branch_name", ""),
                "english_name": intent_info.get("english_name", ""),
                "intent_badge": intent_info.get("badge_title", ""),
                "intent_detail": intent_info.get("badge_detail", ""),
                "data_sources": intent_info.get("data_sources", []),
                "skip_sources": intent_info.get("skip_sources", []),
                "confidence": intent_info.get("confidence", 0.0),
                "scores": intent_info.get("scores", {}),
                "matched_by": intent_info.get("matched_by", "vector_bge"),
                "matched_patterns": intent_info.get("matched_patterns", []),
                "router_info": intent_info,
                "submodule_info": submodule_info,
                "branch_4_info": branch_4_info,
                "branch_5_info": branch_5_info,
                "ai_response": "\n".join(ai_resp_lines)
            }

        # Quét đúng các CSDL theo yêu cầu của nhánh (loại bỏ distillation trung gian)
        data_sources = intent_info.get("data_sources") or (["DB2", "DB5", "DB4"] if intent == "COMPETITIVE" else ["DB3", "DB4"])

        competitors = []
        if "DB2" in data_sources or intent == "COMPETITIVE":
            try:
                competitors = spatial_engine.get_competitors_within_radius(
                    lng=lng,
                    lat=lat,
                    radius_m=1000.0,
                    model_id=model_id,
                    product_ids=product_ids
                )
            except Exception as comp_err:
                logger.warning(f"[!] Lỗi quét đối thủ DB2: {comp_err}")
                competitors = []

        problems = []
        if "DB3" in data_sources:
            problems = semantic_search_engine.search_collection(
                "problems", query=query_text, top_k=3, tag_filter=model_id, product_ids=product_ids
            )

        experiences = []
        if "DB4" in data_sources:
            experiences = semantic_search_engine.search_collection(
                "experiences", query=query_text, top_k=3, tag_filter=model_id, product_ids=product_ids
            )

        market_segments = []
        if "DB5" in data_sources:
            market_segments = semantic_search_engine.search_market_segments(
                product_ids=product_ids,
                tag_filter=model_id,
                customer_segment_ids=customer_segment_ids,
                top_k=2
            )

        context_md, matched_insights = _format_copilot_context_and_insights(
            competitors=competitors,
            problems=problems,
            experiences=experiences,
            market_segments=market_segments,
            customer_segments=customer_segments,
            customer_segment_ids=customer_segment_ids
        )

        # Bổ sung dữ liệu nhánh chuyên sâu vào context LLM
        if submodule_info and submodule_info.get("math_result"):
            context_md += f"\n\n### ĐÁNH GIÁ TOÁN HỌC TẤT ĐỊNH (WHAT-IF):\n{json.dumps(submodule_info['math_result'], ensure_ascii=False, indent=2)}"
        if branch_4_info and branch_4_info.get("detailed_rankings"):
            top3_txt = "\n".join([f"- Hạng {r.get('rank', idx+1)}: {r.get('badge_title', r.get('name', ''))} ({r.get('total_score', 0)}đ): {r.get('badge_detail', r.get('detail', ''))}" for idx, r in enumerate(branch_4_info["detailed_rankings"][:3])])
            context_md += f"\n\n### TOP 3 CHIẾN LƯỢC TÁC CHIẾN ĐỀ XUẤT:\n{top3_txt}"
        if branch_5_info and branch_5_info.get("scenarios"):
            sc_txt = "\n".join([f"- Kịch bản {s.get('rank', idx+1)} ({s.get('scenario_title', '')}): {s.get('symptom_description', '')} | Lỗ rò rỉ: {s.get('potential_leak', '')}" for idx, s in enumerate(branch_5_info["scenarios"])])
            context_md += f"\n\n### KỊCH BẢN CHẨN ĐOÁN KHẢ NGHI:\n{sc_txt}"

        # Mắt xích 6: LLM Reasoning (kèm lịch sử đa lượt theo 5 nhánh chuyên biệt)
        ai_advice = llm_copilot.answer_tactical_copilot(
            user_query=query_text,
            model_name=model_name,
            context_markdown=context_md,
            intent=intent,
            branch=branch_id,
            conversation_history=req.conversation_history,
            llm_config=req.llm_config.model_dump() if req.llm_config else None
        )

        return {
            "success": True,
            "query": query_text,
            "model_name": model_name,
            "intent": intent,
            "branch": intent_info.get("branch", "BRANCH_B"),
            "branch_name": intent_info.get("branch_name", ""),
            "english_name": intent_info.get("english_name", ""),
            "intent_badge": intent_info.get("badge_title", "⚙️ Chế độ: Tối ưu Vận hành Nội bộ"),
            "intent_detail": intent_info.get("badge_detail", ""),
            "data_sources": intent_info.get("data_sources", ["DB3", "DB4"]),
            "skip_sources": intent_info.get("skip_sources", []),
            "confidence": intent_info.get("confidence", 0.0),
            "scores": intent_info.get("scores", {}),
            "matched_by": intent_info.get("matched_by", "vector_bge"),
            "router_info": intent_info,
            "competitors_count": len(competitors),
            "matched_insights": matched_insights,
            "distilled_context": context_md,
            "submodule_info": submodule_info,
            "branch_4_info": branch_4_info,
            "branch_5_info": branch_5_info,
            "ai_response": ai_advice
        }

    except Exception as e:
        logger.error(f"[!] Lỗi trong quá trình tư vấn Co-pilot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý trợ lý: {str(e)}")


@app.post("/api/copilot/chat/stream")
def copilot_chat_stream(req: CopilotChatRequest, authorization: Optional[str] = Header(None)):
    """
    GIAO DIỆN 2: TRỢ LÝ STREAMING REAL-TIME (SERVER-SENT EVENTS - SSE)
    Truyền tải token-by-token giúp người dùng thấy kết quả ngay sau 1-2 giây.
    Hỗ trợ Lọc phân cấp 3 tầng, Ma trận Vector và Bộ nhớ hội thoại đa lượt.
    """
    try:
        query_text = req.query.strip()
        if not query_text:
            raise HTTPException(status_code=400, detail="Câu hỏi không được để trống")

        logger.info(f"[*] Nhận câu hỏi Co-pilot Streaming: '{query_text}' | Model ID: {req.model_id}")

        # Lấy thông tin kế sách đã lưu của người dùng (nếu có đăng nhập)
        user = get_current_user(authorization) if authorization else None
        saved_strategy = None
        if user:
            db = get_db()
            saved_strategy = db["user_strategies"].find_one({"username": user["username"]})

        # Ưu tiên dữ liệu người dùng truyền từ giao diện, sau đó đến hồ sơ đã lưu
        model_id = req.model_id or (saved_strategy.get("model_id") if saved_strategy else None) or 105
        product_ids = req.product_ids or (saved_strategy.get("product_ids") if saved_strategy else None) or []
        address = req.address or (saved_strategy.get("address") if saved_strategy else "")
        req_coords = req.coordinates or (saved_strategy.get("coordinates") if saved_strategy else None)

        # Lấy thông tin Phân khúc khách hàng mục tiêu từ Day 0 / Hồ sơ quán
        customer_segment_ids = (
            req.customer_segment_ids
            or (saved_strategy.get("customer_segment_ids") if saved_strategy else None)
            or (saved_strategy.get("profile", {}).get("customer_segment_ids") if saved_strategy else None)
            or []
        )
        customer_segments = (
            (saved_strategy.get("customer_segments") if saved_strategy else None)
            or (saved_strategy.get("profile", {}).get("customer_segments") if saved_strategy else None)
            or []
        )
        if not customer_segments and customer_segment_ids:
            customer_segments = [tag_manager.get_tag_name(sid) for sid in customer_segment_ids if tag_manager.get_tag_name(sid)]

        # Xác định tọa độ quán phục vụ việc quét đối thủ 1km
        lng, lat = 106.6578, 10.7725
        if req_coords and "lng" in req_coords and "lat" in req_coords and float(req_coords.get("lng", 0)) != 0:
            lng = float(req_coords["lng"])
            lat = float(req_coords["lat"])
        elif address:
            try:
                calc_lng, calc_lat, _ = geocode_address(address)
                if calc_lng != 0:
                    lng, lat = calc_lng, calc_lat
            except Exception as geo_err:
                logger.warning(f"Lỗi geocoding địa chỉ copilot stream: {geo_err}")

        # Mắt xích Định tuyến Ý định (Agentic Intent Router)
        intent_info = detect_copilot_intent(query_text)
        intent = intent_info.get("intent", "INTERNAL")
        branch_id = intent_info.get("branch", "BRANCH_B")
        submodule_info = None
        branch_4_info = None
        branch_5_info = None

        if branch_id == "BRANCH_C":
            from .pipeline.branch_strategic import detect_branch_3_submodules, calculate_deterministic_math
            submodule_info = detect_branch_3_submodules(query_text, top_k=2)
            profile_data = saved_strategy.get("profile", {}) if saved_strategy else {}
            monthly_logs_data = saved_strategy.get("monthly_logs", []) if saved_strategy else []
            sim_profile_data = saved_strategy.get("simulation_profile", {}) if saved_strategy else {}
            math_calc = calculate_deterministic_math(
                submodule_info["primary_module"],
                profile_data,
                monthly_logs_data,
                sim_profile_data
            )
            submodule_info["math_result"] = math_calc

        elif branch_id == "BRANCH_D":
            from .pipeline.branch_competitive import evaluate_branch_4_competitive
            profile_data = saved_strategy.get("profile", {}) if saved_strategy else {}
            monthly_logs_data = saved_strategy.get("monthly_logs", []) if saved_strategy else []
            sim_profile_data = saved_strategy.get("simulation_profile", {}) if saved_strategy else {}

            competitors_b4 = []
            try:
                competitors_b4 = spatial_engine.get_competitors_within_radius(
                    lng=lng,
                    lat=lat,
                    radius_m=1000.0,
                    model_id=model_id,
                    product_ids=product_ids
                )
            except Exception as comp_err:
                logger.warning(f"[!] Lỗi quét đối thủ cho Nhánh 4 stream: {comp_err}")

            branch_4_info = evaluate_branch_4_competitive(
                query=query_text,
                profile=profile_data,
                monthly_logs=monthly_logs_data,
                competitors=competitors_b4,
                simulation_profile=sim_profile_data,
                model_id=model_id,
                top_k=3
            )

        elif branch_id == "BRANCH_E":
            from .pipeline.branch_diagnostic import diagnose_business_issues
            branch_5_info = diagnose_business_issues(
                query=query_text,
                model_id=model_id,
                top_limit=3
            )

        # Quét đúng các CSDL theo yêu cầu của nhánh (loại bỏ distillation trung gian)
        data_sources = intent_info.get("data_sources") or (["DB2", "DB5", "DB4"] if intent == "COMPETITIVE" else ["DB3", "DB4"])

        competitors = []
        if "DB2" in data_sources or intent == "COMPETITIVE":
            try:
                competitors = spatial_engine.get_competitors_within_radius(
                    lng=lng,
                    lat=lat,
                    radius_m=1000.0,
                    model_id=model_id,
                    product_ids=product_ids
                )
            except Exception as comp_err:
                logger.warning(f"[!] Lỗi quét đối thủ DB2: {comp_err}")
                competitors = []

        problems = []
        if "DB3" in data_sources:
            problems = semantic_search_engine.search_collection(
                "problems", query=query_text, top_k=3, tag_filter=model_id, product_ids=product_ids
            )

        experiences = []
        if "DB4" in data_sources:
            experiences = semantic_search_engine.search_collection(
                "experiences", query=query_text, top_k=3, tag_filter=model_id, product_ids=product_ids
            )

        market_segments = []
        if "DB5" in data_sources:
            market_segments = semantic_search_engine.search_market_segments(
                product_ids=product_ids,
                tag_filter=model_id,
                customer_segment_ids=customer_segment_ids,
                top_k=2
            )

        context_md, matched_insights = _format_copilot_context_and_insights(
            competitors=competitors,
            problems=problems,
            experiences=experiences,
            market_segments=market_segments,
            customer_segments=customer_segments,
            customer_segment_ids=customer_segment_ids
        )

        # Bổ sung dữ liệu nhánh chuyên sâu vào context LLM
        if submodule_info and submodule_info.get("math_result"):
            context_md += f"\n\n### ĐÁNH GIÁ TOÁN HỌC TẤT ĐỊNH (WHAT-IF):\n{json.dumps(submodule_info['math_result'], ensure_ascii=False, indent=2)}"
        if branch_4_info and branch_4_info.get("detailed_rankings"):
            top3_txt = "\n".join([f"- Hạng {r.get('rank', idx+1)}: {r.get('badge_title', r.get('name', ''))} ({r.get('total_score', 0)}đ): {r.get('badge_detail', r.get('detail', ''))}" for idx, r in enumerate(branch_4_info["detailed_rankings"][:3])])
            context_md += f"\n\n### TOP 3 CHIẾN LƯỢC TÁC CHIẾN ĐỀ XUẤT:\n{top3_txt}"
        if branch_5_info and branch_5_info.get("scenarios"):
            sc_txt = "\n".join([f"- Kịch bản {s.get('rank', idx+1)} ({s.get('scenario_title', '')}): {s.get('symptom_description', '')} | Lỗ rò rỉ: {s.get('potential_leak', '')}" for idx, s in enumerate(branch_5_info["scenarios"])])
            context_md += f"\n\n### KỊCH BẢN CHẨN ĐOÁN KHẢ NGHI:\n{sc_txt}"

        model_name = tag_manager.get_tag_name(model_id) if model_id else "Chung các mô hình"
        if product_ids:
            prod_names = [tag_manager.get_tag_name(pid) for pid in product_ids if tag_manager.get_tag_name(pid)]
            if prod_names:
                model_name = f"{model_name} (Sản phẩm: {', '.join(prod_names)})"

        def sse_event_stream():
            # 1. Gửi event metadata đầu tiên chứa các thông tin trạng thái & 5 nhánh
            meta_event = {
                "type": "metadata",
                "query": query_text,
                "model_name": model_name,
                "intent": intent,
                "branch": branch_id,
                "branch_name": intent_info.get("branch_name", ""),
                "english_name": intent_info.get("english_name", ""),
                "intent_badge": intent_info.get("badge_title", "⚙️ Chế độ: Tối ưu Vận hành Nội bộ"),
                "intent_detail": intent_info.get("badge_detail", ""),
                "data_sources": intent_info.get("data_sources", ["DB3", "DB4"]),
                "skip_sources": intent_info.get("skip_sources", []),
                "confidence": intent_info.get("confidence", 0.0),
                "scores": intent_info.get("scores", {}),
                "matched_by": intent_info.get("matched_by", "vector_bge"),
                "competitors_count": len(competitors),
                "matched_insights": matched_insights,
                "submodule_info": submodule_info,
                "branch_4_info": branch_4_info,
                "branch_5_info": branch_5_info
            }
            yield f"data: {json.dumps(meta_event, ensure_ascii=False)}\n\n"

            # 2. Streaming từng token từ LLM Qwen3.5 4B qua Ollama (hoặc Cloud API Key) theo 5 nhánh chuyên biệt
            for token in llm_copilot.stream_tactical_copilot(
                user_query=query_text,
                model_name=model_name,
                context_markdown=context_md,
                intent=intent,
                branch=branch_id,
                conversation_history=req.conversation_history,
                llm_config=req.llm_config.model_dump() if req.llm_config else None
            ):
                yield f"data: {json.dumps({'type': 'chunk', 'text': token}, ensure_ascii=False)}\n\n"

            # 3. Gửi event kết thúc
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        return StreamingResponse(
            sse_event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )

    except Exception as e:
        logger.error(f"[!] Lỗi trong quá trình stream Co-pilot: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Lỗi xử lý trợ lý: {str(e)}")


# =====================================================================
# SỔ TAY TÁC CHIẾN (TACTICAL PLAYBOOK - EMBEDDED DOCUMENT MODEL)
# =====================================================================

@app.post("/api/copilot/playbook/save")
def save_playbook(req: SavePlaybookRequest, authorization: Optional[str] = Header(None)):
    """
    Lưu câu trả lời chiến thuật từ Copilot vào Sổ tay tác chiến (copilot_playbooks).
    Tự động bóc tách các đầu việc Checklist thành mảng tasks có task_id độc lập.
    """
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để lưu vào Sổ tay tác chiến!")

    db = get_db()
    from .pipeline.llm_copilot.playbook_service import save_playbook_entry
    result = save_playbook_entry(db, user["username"], req.model_dump())
    return {
        "status": "success",
        "message": f"Đã lưu kế sách vào Sổ tay tác chiến thành công ({result['task_count']} nhiệm vụ)!",
        "playbook": result
    }


@app.get("/api/copilot/playbook/entries")
def get_playbooks(authorization: Optional[str] = Header(None)):
    """
    Lấy toàn bộ danh sách các kế sách và mảng checklist tasks của người dùng.
    """
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để xem Sổ tay tác chiến!")

    db = get_db()
    from .pipeline.llm_copilot.playbook_service import get_user_playbooks
    entries = get_user_playbooks(db, user["username"])
    total_tasks = sum(e.get("task_count", 0) for e in entries)
    total_completed = sum(e.get("completed_task_count", 0) for e in entries)

    return {
        "status": "success",
        "entries": entries,
        "total_playbooks": len(entries),
        "total_tasks": total_tasks,
        "total_completed": total_completed
    }


@app.patch("/api/copilot/playbook/tasks/{task_id}/toggle")
def toggle_task(task_id: str, req: Optional[ToggleTaskRequest] = None, authorization: Optional[str] = Header(None)):
    """
    Cập nhật trạng thái tick/untick của 1 task checklist cụ thể trong mảng nhúng.
    """
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để cập nhật nhiệm vụ!")

    db = get_db()
    from .pipeline.llm_copilot.playbook_service import toggle_playbook_task
    is_comp = req.is_completed if req else None
    result = toggle_playbook_task(db, user["username"], task_id, is_comp)

    if not result:
        raise HTTPException(status_code=404, detail="Không tìm thấy nhiệm vụ hoặc không có quyền thao tác!")

    return {
        "status": "success",
        "message": "Đã cập nhật trạng thái nhiệm vụ!",
        "task": result
    }


@app.delete("/api/copilot/playbook/entries/{playbook_id}")
def delete_playbook(playbook_id: str, authorization: Optional[str] = Header(None)):
    """
    Xóa 1 kế sách khỏi Sổ tay tác chiến (các tasks nhúng tự động xóa theo).
    """
    user = get_current_user(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Vui lòng đăng nhập để xóa kế sách!")

    db = get_db()
    from .pipeline.llm_copilot.playbook_service import delete_playbook_entry
    ok = delete_playbook_entry(db, user["username"], playbook_id)

    if not ok:
        raise HTTPException(status_code=404, detail="Không tìm thấy kế sách cần xóa!")

    return {
        "status": "success",
        "message": "Đã xóa kế sách khỏi Sổ tay tác chiến thành công!"
    }


# =====================================================================
# PHỤC VỤ GIAO DIỆN REACT (KHI ĐÃ BUILD)
# =====================================================================

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="static_assets")

    @app.get("/{full_path:path}")
    async def serve_react_app(full_path: str):
        # Trả về các file tĩnh nếu tồn tại, ngược lại trả về index.html (SPA routing)
        file_candidate = FRONTEND_DIST / full_path
        if file_candidate.is_file():
            return FileResponse(file_candidate)
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    @app.get("/")
    def root_dev():
        return {
            "message": "MLAI Business Co-pilot Backend đang chạy!",
            "port": PORT,
            "frontend_status": "Vui lòng build React frontend hoặc chạy Vite dev server ở port 3000/5173",
            "api_docs": f"http://localhost:{PORT}/docs"
        }


if __name__ == "__main__":
    import uvicorn
    print("\n" + "=" * 70)
    print(f"🚀 KHỞI ĐỘNG MÁY CHỦ FASTAPI TẠI: http://localhost:{PORT}")
    print(f"👉 API Docs (Swagger UI): http://localhost:{PORT}/docs")
    print(f"👉 CSDL: MongoDB Atlas (5 collections) | LLM: {LLM_MODEL}")
    print("=" * 70 + "\n")
    uvicorn.run(app, host=HOST, port=PORT)
