"""
strategy_matcher.py - Trích xuất Điểm yếu thị trường & So khớp Bài học DB4 / Đảo ngược điểm yếu
Được chuẩn hóa theo tài liệu đặc tả: Word/Function_md/market_analyse_engine.md (Mục 3.10 & 3.11)
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
from ...database import get_db
from ..semantic_search import get_embedding_model
from .config import DB4_MATCH_SIMILARITY_THRESHOLD

logger = logging.getLogger(__name__)


INVALID_WEAKNESS_VALUES = {"", "n/a", "none", "null", "chưa có", "không có", "không có thông tin", "chưa rõ"}


def _is_valid_weakness(text: Any) -> bool:
    if not text:
        return False
    s = str(text).strip()
    return bool(s and s.lower() not in INVALID_WEAKNESS_VALUES)


def extract_market_weakness(
    max_threat_comp: Optional[Dict[str, Any]],
    clusters: List[Dict[str, Any]],
    competitors: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Trích xuất 3 điểm yếu thị trường tiêu biểu:
    1. important_weakness: Điểm yếu của đối thủ có điểm đe dọa (CTS) lớn nhất.
    2. normal_weakness:
       - Ưu tiên các điểm yếu lặp lại >= 2 lần từ thuật toán gom cụm (Điểm yếu hệ thống).
       - Nếu không có cái nào lặp lại >= 2 lần (hoặc chưa đủ 2 điểm yếu phụ),
         lấy điểm yếu của đối thủ có điểm đe dọa (CTS) cao thứ 2 và thứ 3 trong khu vực.
    3. count: Số lần lặp tương ứng.
    """
    sorted_comps: List[Dict[str, Any]] = []
    if competitors:
        sorted_comps = sorted(competitors, key=lambda c: float(c.get("cts_score", 0.0) or 0.0), reverse=True)

    important_w = ""
    used_comp_ids = set()

    if max_threat_comp:
        raw_w = str(max_threat_comp.get("weakness", "")).strip()
        if _is_valid_weakness(raw_w):
            important_w = raw_w
            comp_id = str(max_threat_comp.get("id") or max_threat_comp.get("_id") or "")
            if comp_id:
                used_comp_ids.add(comp_id)

    # Nếu đối thủ top 1 không có điểm yếu hợp lệ, lấy từ đối thủ có CTS cao nhất có điểm yếu
    if not important_w and sorted_comps:
        for c in sorted_comps:
            c_w = str(c.get("weakness", "")).strip()
            if _is_valid_weakness(c_w):
                important_w = c_w
                c_id = str(c.get("id") or c.get("_id") or "")
                if c_id:
                    used_comp_ids.add(c_id)
                break

    normal_w_list: List[str] = []
    normal_cnt_list: List[int] = []

    # 1. Ưu tiên lấy từ các cụm điểm yếu hệ thống (count >= 2)
    for cluster in clusters:
        rep_text = str(cluster.get("representative_weakness", "")).strip()
        cnt = int(cluster.get("count", 2) or 2)
        if rep_text and rep_text != important_w and rep_text not in normal_w_list and len(normal_w_list) < 2:
            normal_w_list.append(rep_text)
            normal_cnt_list.append(cnt)

    # 2. Nếu không có cụm nào >= 2 lần hoặc chưa đủ 2 điểm yếu phụ:
    # Lấy điểm yếu của đối thủ có điểm đe dọa cao thứ 2 và thứ 3
    if len(normal_w_list) < 2 and sorted_comps:
        for c in sorted_comps:
            c_id = str(c.get("id") or c.get("_id") or "")
            if c_id and c_id in used_comp_ids:
                continue
            c_w = str(c.get("weakness", "")).strip()
            if _is_valid_weakness(c_w) and c_w != important_w and c_w not in normal_w_list:
                normal_w_list.append(c_w)
                normal_cnt_list.append(1)  # Quán riêng lẻ: count = 1
                if c_id:
                    used_comp_ids.add(c_id)
                if len(normal_w_list) >= 2:
                    break

    important_cnt = 1 if important_w else 0
    return {
        "important_weakness": important_w,
        "normal_weakness": normal_w_list[:2],
        "count": ([important_cnt] if important_w else []) + normal_cnt_list[:2]
    }


def _apply_weakness_inversion(weakness_text: str) -> str:
    """
    Cơ chế Làm ngược lại (Weakness Inversion) khi không tìm thấy bài học DB4 có Cosine >= 0.55.
    """
    w_lower = weakness_text.lower()

    if any(k in w_lower for k in ["chờ lâu", "chậm", "> 5 phút", "> 7 phút", "đợi", "lâu"]):
        if any(f in w_lower for f in ["món", "ăn", "uống", "nấu", "bếp", "bàn", "thức ăn"]):
            return "Cam kết ra món siêu tốc dưới 60 giây, sơ chế sẵn đón dòng khách vội."
        return "Tối ưu hóa quy trình phục vụ và quầy thanh toán, hạn chế tối đa thời gian chờ đợi lúc cao điểm."

    if any(k in w_lower for k in ["bao bì", "nilon", "đổ vỡ", "tràn", "treo xe", "rách"]):
        return "Sử dụng bao bì giấy kraft giữ nhiệt, thiết kế nắp chống tràn chuyên dụng cho xe máy."

    if any(k in w_lower for k in ["không có cà phê", "ít nước", "đơn điệu", "cà phê", "nước giải khát"]):
        return "Tích hợp quầy cà phê pha máy chuyên nghiệp, bán combo kèm bữa ăn tiện lợi."

    return f"Khắc phục triệt để và làm tốt hơn tồn đọng của đối thủ: {weakness_text.rstrip('.')}."


def match_against_weakness(
    market_weakness_data: Dict[str, Any],
    model_id: int,
    product_ids: List[int],
    db=None
) -> List[Dict[str, str]]:
    """
    So khớp điểm yếu thị trường với CSDL DB4 (Kinh nghiệm) qua ma trận vector S = W @ D.T.
    Tự động chèn Tag 0 vào câu query CSDL DB4 theo quy tắc nghiệp vụ cốt lõi.
    """
    if db is None:
        db = get_db()

    w_queries = [market_weakness_data.get("important_weakness", "")]
    w_queries.extend(market_weakness_data.get("normal_weakness", []))
    w_queries = [w for w in w_queries if w][:3]

    if not w_queries:
        return []

    # Bước 1: Truy vấn DB4 kèm Tag 0
    clean_prods = [int(p) for p in product_ids]
    query_tags = [0, int(model_id)] + clean_prods

    db4_docs = []
    if db is not None:
        try:
            cursor = db["experiences"].find({"tag_ids": {"$in": query_tags}})
            db4_docs = [doc for doc in cursor if "embedding" in doc and len(doc["embedding"]) == 1024]
        except Exception as e:
            logger.warning(f"[!] Lỗi truy vấn DB4 trong strategy_matcher: {e}")

    # Nếu DB4 không có bản ghi hoặc không nạp được embedding, kích hoạt Inversion toàn bộ
    if not db4_docs:
        return [{"lesson": _apply_weakness_inversion(w), "experience_id": None} for w in w_queries]

    # Bước 2: Mã hóa Vector Runtime ma trận W (3 x 1024) bằng BGE-M3
    model = get_embedding_model()
    if model is None:
        return [{"lesson": _apply_weakness_inversion(w), "experience_id": None} for w in w_queries]

    w_embeddings = model.encode(w_queries, normalize_embeddings=True)
    matrix_w = np.array(w_embeddings, dtype=np.float32)

    # Bước 3: Lấy ma trận D (K x 1024) từ DB4
    d_embeddings = [doc["embedding"] for doc in db4_docs]
    matrix_d = np.array(d_embeddings, dtype=np.float32)

    # Bước 4: Nhân ma trận Cosine: S_db4 = W @ D.T (kích thước len(w_queries) x K)
    sim_scores = matrix_w @ matrix_d.T

    # Bước 5: So sánh ngưỡng DB4_MATCH_SIMILARITY_THRESHOLD (0.55)
    lessons: List[Dict[str, Any]] = []
    for i, w_text in enumerate(w_queries):
        best_j = int(np.argmax(sim_scores[i]))
        best_score = float(sim_scores[i, best_j])

        if best_score >= DB4_MATCH_SIMILARITY_THRESHOLD:
            doc = db4_docs[best_j]
            lesson_text = doc.get("key_takeaway") or doc.get("story") or _apply_weakness_inversion(w_text)
            lessons.append({
                "lesson": lesson_text,
                "experience_id": str(doc.get("_id", doc.get("id", ""))),
                "cosine_score": round(best_score, 3)
            })
        else:
            # Dưới ngưỡng 0.55: Kích hoạt Weakness Inversion
            lessons.append({
                "lesson": _apply_weakness_inversion(w_text),
                "experience_id": None
            })

    return lessons
