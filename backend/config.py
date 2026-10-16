"""
config.py - Cấu hình hệ thống Client App
Đọc các biến môi trường từ file .env với giá trị mặc định an toàn.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Đường dẫn tới thư mục client_app và file cấu hình .env
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
BACKEND_ENV = Path(__file__).resolve().parent / ".env"

# Nạp biến môi trường từ file .env
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
elif BACKEND_ENV.exists():
    load_dotenv(dotenv_path=BACKEND_ENV)
else:
    load_dotenv()

# Cấu hình Cổng và Địa chỉ chạy FastAPI
PORT = int(os.getenv("PORT", "5000"))
HOST = os.getenv("HOST", "0.0.0.0")

# Cấu hình Kết nối MongoDB Atlas (được nạp từ biến môi trường trong file .env)
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("DB_NAME", "MLAI_Hackathon_2026")

# Cấu hình Máy chủ LLM Ollama (Tự động fallback giữa Server 11435 và Local 11434)
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11435")
LLM_MODEL = os.getenv("LLM_MODEL", "qwen3.5:4b")
NUM_CTX = int(os.getenv("NUM_CTX", "20480"))

# Cấu hình Mô hình Vector Embedding (BAAI/bge-m3 Quantization)
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_QUANTIZATION = os.getenv("EMBEDDING_QUANTIZATION", "fp16")
DEVICE = os.getenv("DEVICE", "cuda")  # Tự động fallback CPU nếu không có GPU CUDA

# Đường dẫn file ánh xạ Tag chuẩn hóa
TAG_MAP_PATH = Path(__file__).resolve().parent / "tag_map.json"

