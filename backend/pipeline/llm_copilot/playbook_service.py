"""
playbook_service.py - Module Quản lý Dịch vụ Sổ tay Tác chiến (Tactical Playbook)
Mô hình Embedded Document (MongoDB):
- Lưu trữ các kế sách, quy trình xử lý sự cố do Copilot tư vấn.
- Nhúng mảng `tasks` (mỗi task có task_id độc lập) trực tiếp trong document của kế sách.
- Cập nhật nguyên tử trạng thái hoàn thành của task bằng toán tử positional `tasks.$`.
"""

import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

# Regex nhận diện dòng Checklist đa dạng từ Markdown của LLM:
# Hỗ trợ: '-', '*', '+', '1.', '2.', không dấu gạch đầu dòng; các kiểu ngoặc [ ], [], [x], [X], [v], [✓]
CHECKBOX_REGEX = re.compile(
    r'^(?:(?:[-*+]|\d+\.)\s*)?\[\s*([xXvV\u2713\u2714]?)\s*\]\s*(.*)$'
)


def extract_playbook_tasks(markdown_text: str) -> List[Dict[str, Any]]:
    """
    Bóc tách tất cả các dòng checklist trong văn bản markdown phản hồi của Copilot.
    Mỗi đầu việc được gán một task_id (UUID) độc lập để lưu trạng thái tick riêng biệt.
    """
    if not markdown_text or not isinstance(markdown_text, str):
        return []

    tasks = []
    lines = markdown_text.split("\n")
    now_iso = datetime.now(timezone.utc).isoformat()

    for line in lines:
        trimmed = line.strip()
        if not trimmed:
            continue

        match = CHECKBOX_REGEX.match(trimmed)
        if match:
            check_mark = (match.group(1) or "").strip()
            task_text = (match.group(2) or "").strip()

            # Bỏ qua dòng rỗng hoặc không có nội dung chữ
            if not task_text:
                continue

            # Giữ nguyên định dạng Markdown (như **Bước 1**) để Frontend renderInline hiển thị in đậm
            clean_text = task_text

            is_completed = len(check_mark) > 0
            task_id = f"task_{uuid.uuid4().hex[:12]}"

            tasks.append({
                "task_id": task_id,
                "text": clean_text,
                "is_completed": is_completed,
                "completed_at": now_iso if is_completed else None,
                "created_at": now_iso
            })

    return tasks


def extract_dialogue_script(markdown_text: str) -> Optional[str]:
    """
    Trích xuất câu lời thoại mẫu thực chiến từ nội dung phản hồi của Copilot (nếu có).
    """
    if not markdown_text or not isinstance(markdown_text, str):
        return None

    lines = markdown_text.split("\n")
    for line in lines:
        trimmed = line.strip()
        # Tìm các dòng có chữ "lời thoại" hoặc bắt đầu bằng dấu trích dẫn >
        if "lời thoại" in trimmed.lower() or trimmed.startswith(">"):
            match = re.search(r'["“]([^"”]{5,250})["”]', trimmed)
            if match:
                return match.group(1).strip()
            # Fallback nếu không có ngoặc kép nhưng có dấu trích dẫn >
            if trimmed.startswith(">"):
                clean = re.sub(r'^>\s*(?:Lời thoại:\s*)?', '', trimmed).strip(' "\'“”')
                if len(clean) >= 5:
                    return clean

    return None


def _generate_playbook_title(query: str, branch_name: str) -> str:
    """Tạo tiêu đề ngắn gọn cho kế sách dựa trên câu hỏi của người dùng."""
    if not query:
        return f"Kế sách {branch_name or 'Tác chiến'}"

    clean = query.strip().rstrip("?.!")
    if len(clean) <= 60:
        return clean
    return clean[:57] + "..."


def save_playbook_entry(db, username: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lưu một kế sách từ Copilot vào collection `copilot_playbooks` theo mô hình Embedded.
    Tự động bóc tách tasks và lời thoại mẫu.
    """
    answer_md = payload.get("answer_markdown", "") or payload.get("answer", "")
    query = payload.get("query", "").strip()
    branch_id = payload.get("branch_id", "BRANCH_UNKNOWN")
    branch_name = payload.get("branch_name", "Tác chiến vận hành")
    model_name = payload.get("model_name", "")
    strategy_id = payload.get("strategy_id")

    # Bóc tách tasks
    tasks = payload.get("tasks")
    if not tasks or not isinstance(tasks, list):
        tasks = extract_playbook_tasks(answer_md)

    # Bóc tách lời thoại
    dialogue = payload.get("dialogue_script") or extract_dialogue_script(answer_md)

    # Tiêu đề tình huống
    title = payload.get("title") or _generate_playbook_title(query, branch_name)

    now_iso = datetime.now(timezone.utc).isoformat()
    playbook_id = f"pb_{uuid.uuid4().hex[:12]}"

    task_count = len(tasks)
    completed_task_count = sum(1 for t in tasks if t.get("is_completed"))

    doc = {
        "playbook_id": playbook_id,
        "username": username,
        "strategy_id": str(strategy_id) if strategy_id else None,
        "title": title,
        "query": query,
        "branch_id": branch_id,
        "branch_name": branch_name,
        "model_name": model_name,
        "answer_markdown": answer_md,
        "dialogue_script": dialogue,
        "tasks": tasks,
        "task_count": task_count,
        "completed_task_count": completed_task_count,
        "created_at": now_iso,
        "updated_at": now_iso
    }

    db["copilot_playbooks"].insert_one(doc)
    doc.pop("_id", None)
    logger.info(f"[✓] Đã lưu Sổ tay tác chiến '{playbook_id}' cho user '{username}' ({task_count} tasks).")
    return doc


def get_user_playbooks(db, username: str) -> List[Dict[str, Any]]:
    """
    Lấy toàn bộ danh sách các kế sách trong Sổ tay tác chiến của user.
    Trả về cả mảng tasks nhúng trong mỗi kế sách.
    """
    cursor = db["copilot_playbooks"].find({"username": username}).sort("created_at", -1)
    results = []

    for item in cursor:
        item.pop("_id", None)
        tasks = item.get("tasks", [])
        item["task_count"] = len(tasks)
        item["completed_task_count"] = sum(1 for t in tasks if t.get("is_completed"))
        results.append(item)

    return results


def toggle_playbook_task(
    db, username: str, task_id: str, is_completed: Optional[bool] = None
) -> Optional[Dict[str, Any]]:
    """
    Cập nhật trạng thái tick/untick của 1 task cụ thể trong mảng nhúng bằng toán tử positional 'tasks.$'.
    Nếu is_completed là None, tự động đảo ngược trạng thái hiện tại.
    """
    # 1. Tìm kế sách chứa task_id này
    doc = db["copilot_playbooks"].find_one({
        "username": username,
        "tasks.task_id": task_id
    })

    if not doc:
        return None

    # Tìm task hiện tại
    current_task = None
    for t in doc.get("tasks", []):
        if t.get("task_id") == task_id:
            current_task = t
            break

    if not current_task:
        return None

    # Xác định trạng thái mới
    if is_completed is None:
        new_status = not current_task.get("is_completed", False)
    else:
        new_status = bool(is_completed)

    now_iso = datetime.now(timezone.utc).isoformat()
    completed_time = now_iso if new_status else None

    # 2. Cập nhật nguyên tử vào MongoDB
    db["copilot_playbooks"].update_one(
        {"username": username, "tasks.task_id": task_id},
        {
            "$set": {
                "tasks.$.is_completed": new_status,
                "tasks.$.completed_at": completed_time,
                "updated_at": now_iso
            }
        }
    )

    # 3. Cập nhật lại completed_task_count tổng của document
    updated_doc = db["copilot_playbooks"].find_one({"username": username, "tasks.task_id": task_id})
    if updated_doc:
        comp_count = sum(1 for t in updated_doc.get("tasks", []) if t.get("is_completed"))
        db["copilot_playbooks"].update_one(
            {"_id": updated_doc["_id"]},
            {"$set": {"completed_task_count": comp_count}}
        )

    return {
        "task_id": task_id,
        "playbook_id": doc.get("playbook_id"),
        "is_completed": new_status,
        "completed_at": completed_time,
        "updated_at": now_iso
    }


def delete_playbook_entry(db, username: str, playbook_id: str) -> bool:
    """
    Xóa 1 kế sách khỏi Sổ tay tác chiến.
    Do dùng mô hình Embedded, toàn bộ task con tự động biến mất theo document, không lo task mồ côi.
    """
    res = db["copilot_playbooks"].delete_one({
        "username": username,
        "playbook_id": playbook_id
    })
    return res.deleted_count > 0
