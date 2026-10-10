"""
clustering_engine.py - Thuật toán xác định Điểm yếu trùng lặp hệ thống (Systemic Weaknesses)
Được chuẩn hóa theo tài liệu đặc tả: Word/Function_md/market_analyse_engine.md (Mục 3.2)
"""

import logging
from typing import Dict, Any, List, Set, Tuple
import numpy as np
from ..semantic_search import get_embedding_model
from .config import WEAKNESS_SIMILARITY_THRESHOLD, MIN_CLUSTER_SIZE_SYSTEMIC

logger = logging.getLogger(__name__)

INVALID_WEAKNESS_VALUES = {"", "n/a", "none", "null", "chưa có", "không có", "không có thông tin", "chưa rõ"}


class DisjointSetUnion:
    """Cấu trúc dữ liệu Disjoint Set Union (DSU) phục vụ gom cụm đồ thị."""
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, i: int) -> int:
        if self.parent[i] == i:
            return i
        self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i: int, j: int):
        root_i = self.find(i)
        root_j = self.find(j)
        if root_i != root_j:
            self.parent[root_i] = root_j


def cluster_systemic_weaknesses(competitors: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Gom cụm điểm yếu đối thủ dùng BAAI/bge-m3 qua phép nhân ma trận S = M @ M.T.
    Trả về các cụm điểm yếu hệ thống lặp lại >= 2 lần và tập ID các quán mang điểm yếu hệ thống.
    """
    # Bước 1: Lọc dữ liệu đầu vào (Input Sanitization)
    valid_candidates: List[Tuple[int, Dict[str, Any], str]] = []
    for idx, comp in enumerate(competitors):
        raw_w = str(comp.get("weakness", "")).strip()
        if raw_w and raw_w.lower() not in INVALID_WEAKNESS_VALUES:
            valid_candidates.append((idx, comp, raw_w))

    if len(valid_candidates) < MIN_CLUSTER_SIZE_SYSTEMIC:
        return {
            "has_systemic": False,
            "clusters": [],
            "systemic_comp_ids": set()
        }

    texts = [item[2] for item in valid_candidates]

    # Bước 2: Mã hóa Vector Ma trận (Runtime Batch Encoding)
    model = get_embedding_model()
    if model is None:
        logger.warning("[!] Không nạp được BGE-M3 model cho clustering_engine.")
        return {
            "has_systemic": False,
            "clusters": [],
            "systemic_comp_ids": set()
        }

    embeddings = model.encode(texts, normalize_embeddings=True)
    matrix_m = np.array(embeddings, dtype=np.float32)

    # Bước 3: Đo tương đồng chéo toàn bộ (Pairwise Similarity qua đúng 1 phép nhân ma trận)
    sim_matrix = matrix_m @ matrix_m.T
    n = len(valid_candidates)

    # Bước 4: Gom cụm theo Ngưỡng Tử Huyệt (DSU Clustering >= 0.70)
    dsu = DisjointSetUnion(n)
    for i in range(n):
        for j in range(i + 1, n):
            if sim_matrix[i, j] >= WEAKNESS_SIMILARITY_THRESHOLD:
                dsu.union(i, j)

    groups: Dict[int, List[int]] = {}
    for i in range(n):
        root = dsu.find(i)
        groups.setdefault(root, []).append(i)

    # Bước 5: Đóng gói kết quả đầu ra
    clusters: List[Dict[str, Any]] = []
    all_systemic_ids: Set[str] = set()

    for root, member_indices in groups.items():
        if len(member_indices) >= MIN_CLUSTER_SIZE_SYSTEMIC:
            cluster_members = [valid_candidates[idx] for idx in member_indices]
            
            # Chọn câu đại diện của quán có review_count cao nhất, hòa xét rating cao nhất
            def sort_key(item):
                c = item[1]
                rev = int(c.get("review_count", c.get("reviews", 0)) or 0)
                rat = float(c.get("rating", 0.0) or 0.0)
                return (rev, rat)

            best_rep = max(cluster_members, key=sort_key)
            affected_ids = [str(item[1].get("id") or item[1].get("_id") or "") for item in cluster_members]
            all_systemic_ids.update(affected_ids)

            clusters.append({
                "representative_weakness": best_rep[2],
                "affected_ids": affected_ids,
                "count": len(cluster_members)
            })

    # Sắp xếp các cụm điểm yếu theo số lần lặp lại giảm dần
    clusters.sort(key=lambda x: x["count"], reverse=True)

    return {
        "has_systemic": len(clusters) > 0,
        "clusters": clusters,
        "systemic_comp_ids": all_systemic_ids
    }
