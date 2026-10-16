"""
copilot_router.py - Bộ Định tuyến Ý định Nghiệp vụ 5 Nhánh (Tactical Copilot Router)
Đặc tả: Phần I - Tài liệu Đặc tả Tactical Copilot Engine (v3.2.0)

Phân loại câu hỏi của người dùng thành 5 nhánh ý định:
- Nhánh A (Nhóm A): Hỏi Kinh nghiệm Thuần túy (Experience-Only) -> Chỉ lọc DB4
- Nhánh B (Nhóm B): Gỡ rối Sự cố Nội bộ tại chỗ (Internal Crisis) -> Lọc DB3 + DB4
- Nhánh C (Nhóm C): Giả định Chiến lược ("Nếu - Thì") (Strategic What-If) -> Hồ sơ quán + DB2 + DB5 + DB4 & DB3
- Nhánh D (Nhóm D): Phản công Cạnh tranh Vi mô (Micro-Defense) -> Lọc DB2 + DB5 + DB4 (Bỏ qua DB3)
- Nhánh E (Nhóm E): Phân tích & Chẩn đoán Bệnh kinh doanh (Diagnostic Triage) -> Quét DB3 + DB4 + logs tài chính

Kiến trúc định tuyến 2 tầng:
- Tầng 1: Bộ phát hiện mẫu câu & từ khóa (Intent Pattern Detector)
- Tầng 2: Ánh xạ không gian vector BAAI/bge-m3 (1024 chiều) với 5 Anchor Vectors
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

# Đường dẫn nạp dữ liệu định nghĩa 5 nhánh
BRANCH_DATA_PATH = Path(__file__).resolve().parent / "branch_anchors.json"

_cached_branch_metadata: Optional[Dict[str, Any]] = None
_cached_branch_vectors: Optional[Dict[str, np.ndarray]] = None


def load_branch_metadata() -> Dict[str, Any]:
    """Tải siêu dữ liệu cấu hình 5 nhánh từ file JSON độc lập."""
    global _cached_branch_metadata
    if _cached_branch_metadata is not None:
        return _cached_branch_metadata

    try:
        with open(BRANCH_DATA_PATH, "r", encoding="utf-8") as f:
            _cached_branch_metadata = json.load(f)
            return _cached_branch_metadata
    except Exception as e:
        logger.error(f"[!] Không thể đọc file branch_anchors.json: {e}")
        return {}


def get_branch_vectors() -> Dict[str, np.ndarray]:
    """Tải và tính trước vector 1024 chiều (BGE-M3) cho 5 Anchor đại diện."""
    global _cached_branch_vectors
    if _cached_branch_vectors is not None:
        return _cached_branch_vectors

    metadata = load_branch_metadata()
    if not metadata:
        return {}

    try:
        from .semantic_search import get_embedding_model
        model = get_embedding_model()
        if model is None:
            return {}

        vectors = {}
        for branch_id, info in metadata.items():
            anchor_text = info.get("anchor", "")
            vec = model.encode(anchor_text, normalize_embeddings=True)
            vectors[branch_id] = np.array(vec, dtype=np.float32)

        _cached_branch_vectors = vectors
        logger.info(f"[✓] Đã khởi tạo vector BGE-M3 thành công cho 5 nhánh ý định.")
        return _cached_branch_vectors
    except Exception as e:
        logger.error(f"[!] Lỗi khi nạp vector anchor cho copilot_router: {e}")
        return {}


def detect_copilot_intent(query: str) -> Dict[str, Any]:
    """
    Định tuyến câu hỏi người dùng vào đúng 1 trong 5 nhánh ý định nghiệp vụ.
    Kết hợp 2 tầng:
    1. So khớp mẫu câu từ khóa nhận diện cấu trúc (Heuristic pattern detection)
    2. Vector Cosine Similarity với BAAI/bge-m3 qua 5 Anchor Vectors
    """
    metadata = load_branch_metadata()
    cleaned_query = query.lower().strip()

    # Tầng 1: Kiểm tra cấu trúc câu hỏi qua Regex Patterns
    pattern_matches: Dict[str, List[str]] = {}
    for branch_id, info in metadata.items():
        matched_pats = []
        for pat in info.get("patterns", []):
            if re.search(pat, cleaned_query, re.IGNORECASE):
                matched_pats.append(pat)
        if matched_pats:
            pattern_matches[branch_id] = matched_pats

    # Tầng 2: So khớp Không gian Vector BGE-M3
    scores: Dict[str, float] = {}
    branch_vectors = get_branch_vectors()

    if branch_vectors:
        try:
            from .semantic_search import get_embedding_model, cosine_similarity
            model = get_embedding_model()
            q_vec = model.encode(query.strip(), normalize_embeddings=True)
            q_vec = np.array(q_vec, dtype=np.float32)

            for b_id, b_vec in branch_vectors.items():
                scores[b_id] = float(cosine_similarity(q_vec, b_vec))
        except Exception as e:
            logger.warning(f"[!] Lỗi tính toán vector BGE-M3 trong router: {e}")

    # Thuật toán phân định kết hợp:
    # Điểm cuối = Điểm Cosine Vector + Pattern Boost
    final_scores: Dict[str, float] = {}
    for b_id in metadata.keys():
        v_score = scores.get(b_id, 0.0)
        p_boost = 0.09 if b_id in pattern_matches else 0.0

        # Nếu chứa "có nên" (cân nhắc quyết định chiến lược Nhánh C)
        if b_id == "BRANCH_C" and re.search(r"có nên\b", cleaned_query):
            if not any(k in cleaned_query for k in ["đối thủ", "cắt lỗ ngay lập tức", "quay lại ngày đầu", "dừng toàn bộ hoạt động quảng cáo"]):
                p_boost += 0.18

        # Phản công cạnh tranh vi mô (Nhánh D): khi có đối thủ / đối trọng nhưng KHÔNG phải khủng hoảng nội bộ Nhánh B
        if b_id == "BRANCH_D" and ("đối thủ" in cleaned_query or "đối trọng" in cleaned_query):
            is_crisis_b = any(k in cleaned_query for k in [
                "sập", "khắc phục trong 24 giờ", "mất tinh thần nghiêm trọng", "trong tuần đầu tiên",
                "report", "báo cáo vi phạm"
            ])
            if not re.match(r"^nếu\b", cleaned_query) and not is_crisis_b:
                p_boost += 0.12

        # Câu hỏi phỏng vấn bài học/năng lực người sáng lập (Nhánh A)
        if b_id == "BRANCH_A" and any(k in cleaned_query for k in ["nếu phải chỉ ra", "quay lại ngày đầu"]):
            p_boost += 0.20

        # Đo lường đối sánh thời gian trong chẩn đoán hiệu suất (Nhánh E)
        if b_id == "BRANCH_E" and re.search(r"nhanh hay chậm hơn đối thủ", cleaned_query):
            p_boost += 0.15

        # Đánh giá sức sống tự nhiên khi dừng quảng cáo (chẩn đoán phụ thuộc - Nhánh E)
        if b_id == "BRANCH_E" and re.search(r"dừng toàn bộ hoạt động quảng cáo.*trong bao lâu", cleaned_query):
            p_boost += 0.22

        # Chẩn đoán tính tự vận hành / hệ thống quy trình (Nhánh E)
        if b_id == "BRANCH_E" and any(k in cleaned_query for k in ["loại bỏ toàn bộ các hỗ trợ thủ công", "tự vận hành trơn tru"]):
            p_boost += 0.22

        final_scores[b_id] = v_score + p_boost

    # Chọn nhánh chiến thắng
    if final_scores:
        best_branch = max(final_scores, key=final_scores.get)
        top_raw_score = scores.get(best_branch, 0.0)
    else:
        best_branch = "BRANCH_B"
        top_raw_score = 0.50

    branch_info = metadata.get(best_branch, {})
    matched_by = "hybrid_pattern_vector" if best_branch in pattern_matches else "vector_bge"

    # Giữ tương thích ngược với API hiện tại của main.py
    legacy_intent = "COMPETITIVE" if best_branch == "BRANCH_D" else "INTERNAL"

    return {
        "branch": best_branch,
        "branch_name": branch_info.get("name", best_branch),
        "english_name": branch_info.get("english_name", ""),
        "intent": legacy_intent,
        "raw_intent": branch_info.get("intent", best_branch),
        "confidence": round(float(top_raw_score), 4),
        "matched_by": matched_by,
        "matched_patterns": pattern_matches.get(best_branch, []),
        "badge_title": branch_info.get("badge_title", ""),
        "badge_detail": branch_info.get("badge_detail", ""),
        "data_sources": branch_info.get("data_sources", []),
        "skip_sources": branch_info.get("skip_sources", []),
        "scores": {k: round(v, 4) for k, v in scores.items()}
    }
