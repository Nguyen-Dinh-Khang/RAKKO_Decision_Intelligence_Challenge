"""
engine.py - Cỗ máy điều phối Bộ Sách lược Chiến thuật (Tactical Playbook Engine)
Được chuẩn hóa theo tài liệu đặc tả: Word/Function_md/tactical_playbook_engine.md (Mục 1, 3.4, 4 & 5)
"""

import logging
from typing import Dict, Any, List, Optional
from ...database import get_db
from .config import TOP_K_ITEMS, SIMILARITY_THRESHOLD, RELATED_SIMILARITY_THRESHOLD
from .diversity_selector import (
    extract_top_diverse_clusters,
    classify_problems_by_anchor,
    select_tactical_experiences
)

logger = logging.getLogger(__name__)


def run_tactical_playbook(
    model_id: int,
    product_ids: List[int],
    db=None
) -> Dict[str, Any]:
    """
    Rút trích 4 Vấn đề cốt tử (DB3) và 4 Kinh nghiệm thực chiến (DB4) tiêu biểu nhất.
    Tự động chèn Tag 0 vào câu query theo quy tắc nghiệp vụ bắt buộc.
    Áp dụng cơ chế Vector Neo phân loại vấn đề (Dễ/Tác nghiệp vs Khó/Chiến lược)
    và tuyển chọn kép 4 kinh nghiệm: giải quyết vấn đề khó + bài học xương máu phổ quát.
    """
    if db is None:
        db = get_db()

    clean_prods = [int(p) for p in product_ids]
    # Nguyên tắc sống còn: Tự động thêm Tag 0 để lấy bài học nền tảng chung
    query_tags = [0, int(model_id)] + clean_prods

    db3_candidates = []
    db4_candidates = []

    if db is not None:
        try:
            # Truy vấn DB3 (Vấn đề & Rủi ro)
            cursor3 = db["problems"].find({"tag_ids": {"$in": query_tags}})
            db3_candidates = list(cursor3)
        except Exception as e:
            logger.warning(f"[!] Lỗi truy vấn DB3 trong tactical_playbook: {e}")

        try:
            # Truy vấn DB4 (Kinh nghiệm & Bài học)
            cursor4 = db["experiences"].find({"tag_ids": {"$in": query_tags}})
            db4_candidates = list(cursor4)
        except Exception as e:
            logger.warning(f"[!] Lỗi truy vấn DB4 trong tactical_playbook: {e}")

    # Bước 1: Greedy Diversity Pruning cho DB3 (giữ lại embedding để phân loại & so khớp DB4)
    selected_problems = extract_top_diverse_clusters(
        records=db3_candidates,
        top_k=TOP_K_ITEMS,
        sim_threshold=SIMILARITY_THRESHOLD,
        keep_embedding=True
    )

    # Bước 2: Phân loại độ phức tạp cho các vấn đề qua Vector Neo
    classified_problems = classify_problems_by_anchor(selected_problems)

    # Bước 3: Tuyển chọn kép 4 Kinh nghiệm thực chiến cho DB4:
    # - Ghép cặp trực diện cho các vấn đề phức tạp
    # - Bổ sung kinh nghiệm ngoài phổ quát (mật độ cụm cao nhất) cho đủ 4 suất
    selected_experiences = select_tactical_experiences(
        problems=classified_problems,
        candidate_experiences=db4_candidates,
        top_k=TOP_K_ITEMS,
        related_threshold=RELATED_SIMILARITY_THRESHOLD,
        sim_threshold=SIMILARITY_THRESHOLD
    )

    # Đóng gói dữ liệu đầu ra chuẩn kèm ID bảo toàn đối soát
    formatted_problems: List[Dict[str, Any]] = []
    for p in classified_problems:
        formatted_problems.append({
            "id": str(p.get("_id", p.get("id", ""))),
            "title": p.get("title", ""),
            "summary": p.get("summary", ""),
            "severity": p.get("severity", 2),
            "difficulty": p.get("difficulty", "complex"),
            "difficulty_label": p.get("difficulty_label", "Phức tạp / Chiến lược"),
            "action_recommendation": p.get("action_recommendation", "Cần bài học xương máu & giải pháp ứng phó"),
            "is_complex": p.get("is_complex", True)
        })

    formatted_experiences: List[Dict[str, Any]] = []
    for exp in selected_experiences:
        formatted_experiences.append({
            "id": str(exp.get("_id", exp.get("id", ""))),
            "title": exp.get("title", ""),
            "key_takeaway": exp.get("key_takeaway", ""),
            "dialogue_script": exp.get("dialogue_script", ""),
            "solves_problem_id": exp.get("solves_problem_id", ""),
            "solves_problem_title": exp.get("solves_problem_title", ""),
            "cosine_score": exp.get("cosine_score"),
            "experience_type": exp.get("experience_type", "tailored_solution"),
            "experience_type_label": exp.get("experience_type_label", "Giải pháp gỡ nút thắt khó")
        })

    return {
        "top_4_problems": formatted_problems,
        "top_4_experiences": formatted_experiences
    }


class TacticalPlaybookEngine:
    """
    Class giao diện của bộ máy Tactical Playbook Engine.
    """
    def __init__(self, db=None):
        self.db = db

    def run_tactical_playbook(
        self,
        model_id: int,
        product_ids: List[int],
        db=None
    ) -> Dict[str, Any]:
        return run_tactical_playbook(
            model_id=model_id,
            product_ids=product_ids,
            db=db or self.db
        )
