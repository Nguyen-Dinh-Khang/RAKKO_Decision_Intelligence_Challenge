"""
diversity_selector.py - Thuật toán chọn đại diện đa dạng (Greedy Diversity Pruning)
và Cơ chế Phân loại Vấn đề qua Vector Neo & Tuyển chọn Kinh nghiệm Kép DB4.
Được chuẩn hóa theo tài liệu đặc tả: Word/Function_md/tactical_playbook_engine.md (Mục 3)
"""

import logging
from typing import Dict, Any, List, Set, Optional, Tuple
import numpy as np

from .config import (
    SIMILARITY_THRESHOLD, 
    TOP_K_ITEMS, 
    EMBEDDING_DIM,
    RELATED_SIMILARITY_THRESHOLD,
    ANCHOR_SIMPLE_ISSUE,
    ANCHOR_COMPLEX_RISK
)

logger = logging.getLogger(__name__)

# Bộ nhớ đệm lưu vector 1024 chiều của 2 Prompt Neo
_cached_anchor_vectors: Optional[Dict[str, np.ndarray]] = None


def get_anchor_vectors() -> Dict[str, np.ndarray]:
    """
    Sinh và lưu đệm vector chuẩn hóa L2 của 2 Prompt Neo:
    - simple: Vector đại diện vấn đề Tác nghiệp / Bề nổi (Checklist - né là xong)
    - complex: Vector đại diện vấn đề Chiến lược / Sống còn (Khó - cần bài học xương máu)
    """
    global _cached_anchor_vectors
    if _cached_anchor_vectors is not None:
        return _cached_anchor_vectors

    try:
        from ..semantic_search import get_embedding_model
        model = get_embedding_model()
        if model is not None:
            vec_simple = model.encode(ANCHOR_SIMPLE_ISSUE, normalize_embeddings=True)
            vec_complex = model.encode(ANCHOR_COMPLEX_RISK, normalize_embeddings=True)
            _cached_anchor_vectors = {
                "simple": np.array(vec_simple, dtype=np.float32),
                "complex": np.array(vec_complex, dtype=np.float32)
            }
            logger.info("[✓] Đã khởi tạo thành công 2 Vector Neo (Anchor) cho Tactical Playbook.")
            return _cached_anchor_vectors
    except Exception as e:
        logger.warning(f"[!] Không thể sinh vector anchor từ mô hình: {e}")

    return {}


def extract_top_diverse_clusters(
    records: List[Dict[str, Any]],
    top_k: int = TOP_K_ITEMS,
    sim_threshold: float = SIMILARITY_THRESHOLD,
    keep_embedding: bool = False
) -> List[Dict[str, Any]]:
    """
    Rút trích các bản ghi có mật độ lặp lại cao nhất nhưng hoàn toàn đa dạng, không trùng lặp chủ đề.
    Sử dụng kỹ thuật Greedy Diversity Pruning trên ma trận tương đồng cosine.
    Bảo toàn ID đối tượng cho truy vết và hiển thị.
    """
    if not records:
        return []

    # Bước 1: Lọc các bản ghi có vector embedding hợp lệ
    valid_records = []
    vector_list = []

    for r in records:
        emb = r.get("embedding")
        if isinstance(emb, list) and len(emb) == EMBEDDING_DIM:
            valid_records.append(r)
            vector_list.append(emb)

    n = len(valid_records)
    if n == 0:
        return []

    # Nếu số lượng ứng viên nhỏ hơn hoặc bằng top_k, trả về toàn bộ
    if n <= top_k:
        results = []
        for r in valid_records:
            clean_r = dict(r) if keep_embedding else {k: v for k, v in r.items() if k != "embedding"}
            clean_r["id"] = str(r.get("_id", r.get("id", "")))
            results.append(clean_r)
        return results

    # Bước 2: Ma trận hóa & Chuẩn hóa L2-norm
    matrix_m = np.array(vector_list, dtype=np.float32)
    norms = np.linalg.norm(matrix_m, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    matrix_norm = matrix_m / norms

    # Nhân ma trận Cosine Similarity: S = M @ M.T (N x N)
    sim_matrix = matrix_norm @ matrix_norm.T

    # Bước 3: Đo mật độ lặp lại (Cluster Density)
    density_scores = np.sum(sim_matrix >= sim_threshold, axis=1)

    # Sắp xếp thứ tự ưu tiên Index giảm dần (bảo toàn Index gốc)
    sorted_indices = np.argsort(density_scores)[::-1]

    # Bước 4: Vòng lặp Greedy Diversity Pruning
    selected_indices: List[int] = []
    excluded_set: Set[int] = set()

    for idx in sorted_indices:
        idx_int = int(idx)
        if idx_int in excluded_set:
            continue

        selected_indices.append(idx_int)

        # Gạch tên toàn bộ đồng bọn của thủ lĩnh này
        buddies = np.where(sim_matrix[idx_int] >= sim_threshold)[0]
        excluded_set.update(buddies.tolist())

        if len(selected_indices) >= top_k:
            break

    # Bước 5: Ánh xạ ngược lại Object gốc theo Index
    final_items: List[Dict[str, Any]] = []
    for idx in selected_indices:
        orig = valid_records[idx]
        clean_item = dict(orig) if keep_embedding else {k: v for k, v in orig.items() if k != "embedding"}
        clean_item["id"] = str(orig.get("_id", orig.get("id", "")))
        final_items.append(clean_item)

    return final_items


def classify_problems_by_anchor(
    problems: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Phân loại các vấn đề DB3 thành:
    - "complex" (Phức tạp / Chiến lược sống còn): Cần tìm bài học DB4 cứu cánh.
    - "simple" (Đơn giản / Tác nghiệp bề nổi): Chỉ cần checklist ghi nhớ để phòng tránh.
    Sử dụng khoảng cách Cosine với 2 Vector Neo (Anchor Vectors).
    """
    if not problems:
        return []

    anchors = get_anchor_vectors()
    vec_simple = anchors.get("simple")
    vec_complex = anchors.get("complex")

    has_anchors = (vec_simple is not None and vec_complex is not None)

    classified_problems = []
    for p in problems:
        item = dict(p)
        prob_emb = p.get("embedding")

        if has_anchors and isinstance(prob_emb, list) and len(prob_emb) == EMBEDDING_DIM:
            p_vec = np.array(prob_emb, dtype=np.float32)
            p_norm = np.linalg.norm(p_vec)
            if p_norm > 0:
                p_vec = p_vec / p_norm

            score_simple = float(np.dot(p_vec, vec_simple))
            score_complex = float(np.dot(p_vec, vec_complex))

            item["score_simple"] = round(score_simple, 3)
            item["score_complex"] = round(score_complex, 3)

            # Quy tắc quyết định: Nếu độ tương quan với rủi ro phức tạp cao hơn -> Phức tạp
            if score_complex > score_simple:
                item["difficulty"] = "complex"
                item["difficulty_label"] = "Phức tạp / Chiến lược"
                item["action_recommendation"] = "Cần bài học xương máu & giải pháp ứng phó"
                item["is_complex"] = True
            else:
                item["difficulty"] = "simple"
                item["difficulty_label"] = "Tác nghiệp / Bề nổi"
                item["action_recommendation"] = "Chỉ cần lập checklist & ghi nhớ để phòng tránh"
                item["is_complex"] = False
        else:
            # Fallback heuristic nếu không có vector model: dựa vào severity
            sev_raw = item.get("severity", 2)
            try:
                sev = int(sev_raw)
            except (ValueError, TypeError):
                sev = 3 if str(sev_raw).lower() in ("cao", "nghiem_trong", "high") else 2
            if sev >= 2:
                item["difficulty"] = "complex"
                item["difficulty_label"] = "Phức tạp / Chiến lược"
                item["action_recommendation"] = "Cần bài học xương máu & giải pháp ứng phó"
                item["is_complex"] = True
            else:
                item["difficulty"] = "simple"
                item["difficulty_label"] = "Tác nghiệp / Bề nổi"
                item["action_recommendation"] = "Chỉ cần lập checklist & ghi nhớ để phòng tránh"
                item["is_complex"] = False


        classified_problems.append(item)

    return classified_problems


def select_tactical_experiences(
    problems: List[Dict[str, Any]],
    candidate_experiences: List[Dict[str, Any]],
    top_k: int = TOP_K_ITEMS,
    related_threshold: float = RELATED_SIMILARITY_THRESHOLD,
    sim_threshold: float = SIMILARITY_THRESHOLD
) -> List[Dict[str, Any]]:
    """
    Tuyển chọn 4 Kinh nghiệm thực chiến chất lượng cao:
    Nhóm 1: Ghép cặp giải pháp giải quyết trực diện cho các Vấn đề Phức tạp (cos_rel >= 0.30).
    Nhóm 2: Bổ sung các bài học xương máu phổ quát (lấy theo mật độ cụm lặp lại nhiều nhất từ DB4 còn lại).
    Đảm bảo đầu ra đủ đúng 4 kinh nghiệm mà không bao giờ bị gượng ép hay đơn điệu.
    """
    if not candidate_experiences:
        return []

    # Lọc các kinh nghiệm có vector embedding hợp lệ
    valid_exps = []
    exp_vectors = []
    for exp in candidate_experiences:
        emb = exp.get("embedding")
        if isinstance(emb, list) and len(emb) == EMBEDDING_DIM:
            valid_exps.append(exp)
            exp_vectors.append(emb)

    if not valid_exps:
        return []

    # Ma trận hóa & chuẩn hóa L2 cho DB4 (M x 1024)
    matrix_e = np.array(exp_vectors, dtype=np.float32)
    norms_e = np.linalg.norm(matrix_e, axis=1, keepdims=True)
    norms_e[norms_e == 0] = 1.0
    norm_e = matrix_e / norms_e

    used_exp_indices: Set[int] = set()
    selected_matches: List[Dict[str, Any]] = []

    # Đảm bảo các vấn đề đã được phân loại (nếu chưa có cờ is_complex thì phân loại ngay)
    classified_probs = problems
    if problems and "is_complex" not in problems[0]:
        classified_probs = classify_problems_by_anchor(problems)

    # ---------------------------------------------------------
    # GIAI ĐOẠN 1: Ghép cặp bài học cho các Vấn đề Phức tạp
    # ---------------------------------------------------------
    for prob in classified_probs:
        if not prob.get("is_complex", True):
            # Vấn đề đơn giản: chỉ cần biết để né, không ép gán bài học làm loãng thông tin
            continue

        prob_emb = prob.get("embedding")
        if not isinstance(prob_emb, list) or len(prob_emb) != EMBEDDING_DIM:
            continue

        prob_vec = np.array(prob_emb, dtype=np.float32)
        norm_p = np.linalg.norm(prob_vec)
        if norm_p > 0:
            prob_vec = prob_vec / norm_p

        # Tính Cosine thuận trực tiếp giữa kinh nghiệm và vấn đề
        cos_rel = norm_e @ prob_vec

        candidates = []
        for j in range(len(valid_exps)):
            if j in used_exp_indices:
                continue
            candidates.append((j, float(cos_rel[j])))

        if not candidates:
            continue

        # Sắp xếp theo độ liên quan giảm dần
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_j, best_rel = candidates[0]

        # Chỉ ghép nếu đạt ngưỡng liên quan tối thiểu
        if best_rel >= related_threshold:
            used_exp_indices.add(best_j)
            orig_exp = valid_exps[best_j]
            clean_exp = {k: v for k, v in orig_exp.items() if k != "embedding"}
            clean_exp["id"] = str(orig_exp.get("_id", orig_exp.get("id", "")))
            clean_exp["solves_problem_id"] = str(prob.get("_id", prob.get("id", "")))
            clean_exp["solves_problem_title"] = prob.get("title", "")
            clean_exp["cosine_score"] = round(best_rel, 3)
            clean_exp["experience_type"] = "tailored_solution"
            clean_exp["experience_type_label"] = "Giải pháp giải quyết nút thắt khó"
            selected_matches.append(clean_exp)

        if len(selected_matches) >= top_k:
            break

    # ---------------------------------------------------------
    # GIAI ĐOẠN 2: Bổ sung Kinh nghiệm Ngoài Phổ Quát (Cluster Density)
    # ---------------------------------------------------------
    if len(selected_matches) < top_k:
        needed = top_k - len(selected_matches)
        remaining_exps = [valid_exps[j] for j in range(len(valid_exps)) if j not in used_exp_indices]
        if remaining_exps:
            # Lấy các bài học có mật độ lặp lại cao nhất trong kho DB4 còn lại
            diverse_fill = extract_top_diverse_clusters(
                records=remaining_exps,
                top_k=needed,
                sim_threshold=sim_threshold
            )
            for exp in diverse_fill:
                clean_exp = {k: v for k, v in exp.items() if k != "embedding"}
                clean_exp["id"] = str(exp.get("_id", exp.get("id", "")))
                clean_exp["solves_problem_id"] = ""
                clean_exp["solves_problem_title"] = ""
                clean_exp["cosine_score"] = None
                clean_exp["experience_type"] = "core_strategic_lesson"
                clean_exp["experience_type_label"] = "Bài học xương máu phổ quát"
                selected_matches.append(clean_exp)

    return selected_matches[:top_k]


# Giữ tên hàm cũ làm alias để đảm bảo tương thích ngược tuyệt đối
match_related_experiences_for_problems = select_tactical_experiences
