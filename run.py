"""
run.py - Điểm khởi chạy chính của Client App (FastAPI + React Frontend)
Cách chạy từ thư mục gốc MLAI:
    .\\.venv\\Scripts\\python.exe client_app/run.py
"""

import sys
import shutil
import subprocess
from pathlib import Path

# Đảm bảo console Windows in tiếng Việt UTF-8
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Thêm client_app và thư mục cha MLAI vào sys.path để import dễ dàng
CURRENT_DIR = Path(__file__).resolve().parent
PARENT_DIR = CURRENT_DIR.parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

import uvicorn
from backend.config import PORT, HOST, LLM_MODEL, NUM_CTX, EMBEDDING_QUANTIZATION, DEVICE


def build_frontend():
    """Install frontend dependencies when absent, then rebuild the production bundle."""
    frontend_dir = CURRENT_DIR / "frontend"
    npm = shutil.which("npm") or shutil.which("npm.cmd")
    if not npm:
        raise SystemExit("Không tìm thấy npm. Hãy cài Node.js rồi chạy lại ứng dụng.")

    if not (frontend_dir / "node_modules" / "vite" / "package.json").is_file():
        print("[*] Chưa có frontend dependencies; đang chạy npm ci...")
        subprocess.run([npm, "ci"], cwd=frontend_dir, check=True)

    print("[*] Đang build frontend production...")
    subprocess.run([npm, "run", "build"], cwd=frontend_dir, check=True)


if __name__ == "__main__":
    build_frontend()

    print("\n" + "=" * 75)
    print("🚀 NỀN TẢNG RA QUYẾT ĐỊNH & TRỢ LÝ KINH DOANH THỰC CHIẾN (CLIENT APP)")
    print(f"👉 Ứng dụng Web (React Frontend): http://localhost:{PORT}")
    print(f"👉 API Documentation (Swagger):   http://localhost:{PORT}/docs")
    print(f"👉 Trạng thái hệ thống:           http://localhost:{PORT}/api/health")
    print(f"🗄️  Cơ sở dữ liệu:                 MongoDB Atlas (5 CSDL)")
    print(f"🧠 Mô hình Vector Embedding:      BAAI/bge-m3 ({EMBEDDING_QUANTIZATION.upper()} trên {DEVICE.upper()})")
    print(f"🤖 Mô hình Trợ lý Suy luận:       {LLM_MODEL} (Ollama | Context Window: {NUM_CTX})")
    print("=" * 75)
    print("Nhấn Ctrl + C để dừng máy chủ bất kỳ lúc nào.\n")

    uvicorn.run("backend.main:app", host=HOST, port=PORT, reload=False)

