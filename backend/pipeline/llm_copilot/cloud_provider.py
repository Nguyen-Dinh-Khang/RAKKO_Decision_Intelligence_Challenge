"""
cloud_provider.py - Module kết nối các dịch vụ Cloud LLM bằng API Key cá nhân của người dùng.
Hỗ trợ:
- Google Gemini API (gemini)
- OpenAI API (openai)
- Groq Cloud (groq)
- DeepSeek API (deepseek)
- OpenRouter (openrouter)
Hỗ trợ cả 2 chế độ: Đồng bộ (Synchronous) và Luồng thời gian thực (SSE Streaming).
"""

import json
import logging
import requests
from typing import Dict, Any, Optional, Generator, Tuple

logger = logging.getLogger(__name__)

DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "groq": "llama-3.3-70b-versatile",
    "deepseek": "deepseek-chat",
    "openrouter": "google/gemini-2.5-flash"
}

OPENAI_COMPATIBLE_URLS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "groq": "https://api.groq.com/openai/v1/chat/completions",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "openrouter": "https://openrouter.ai/api/v1/chat/completions"
}


def is_cloud_config_active(llm_config: Optional[Dict[str, Any]]) -> bool:
    """Kiểm tra xem cấu hình người dùng gửi lên có kích hoạt chế độ Cloud API Key hợp lệ không."""
    if not llm_config or not isinstance(llm_config, dict):
        return False
    mode = str(llm_config.get("mode") or "local").strip().lower()
    api_key = str(llm_config.get("api_key") or "").strip()
    return mode == "cloud" and len(api_key) > 0


def _resolve_config(llm_config: Dict[str, Any]) -> Tuple[str, str, str]:
    """Chuẩn hóa provider, api_key và model từ llm_config."""
    provider = str(llm_config.get("provider") or "gemini").strip().lower()
    if provider not in DEFAULT_MODELS:
        provider = "gemini"
    api_key = str(llm_config.get("api_key") or "").strip()
    model = str(llm_config.get("model") or "").strip() or DEFAULT_MODELS[provider]
    return provider, api_key, model


def _call_gemini_sync(api_key: str, model: str, prompt: str, system: str, temperature: float) -> str:
    """Gọi đồng bộ Google Gemini REST API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    payload = {
        "system_instruction": {
            "parts": [{"text": system}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": temperature,
            "topP": 0.9,
            "maxOutputTokens": 4096
        }
    }
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    if response.status_code != 200:
        err_msg = _extract_error_message(response)
        raise RuntimeError(f"Gemini API ({response.status_code}): {err_msg}")

    data = response.json()
    candidates = data.get("candidates", [])
    if not candidates:
        return "⚠️ Gemini API không trả về nội dung phản hồi."
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()


def _stream_gemini(api_key: str, model: str, prompt: str, system: str, temperature: float) -> Generator[str, None, None]:
    """Gọi SSE Streaming Google Gemini REST API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse"
    headers = {
        "Content-Type": "application/json",
        "x-goog-api-key": api_key
    }
    payload = {
        "system_instruction": {
            "parts": [{"text": system}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": temperature,
            "topP": 0.9,
            "maxOutputTokens": 4096
        }
    }
    with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as response:
        if response.status_code != 200:
            err_msg = _extract_error_message(response)
            yield f"\n\n⚠️ Lỗi từ Gemini API ({response.status_code}): {err_msg}"
            return

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            trimmed = line.strip()
            if not trimmed.startswith("data:"):
                continue
            json_str = trimmed[5:].strip()
            if not json_str or json_str == "[DONE]":
                continue
            try:
                chunk = json.loads(json_str)
                candidates = chunk.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    for part in parts:
                        text = part.get("text", "")
                        if text:
                            yield text
            except Exception:
                continue


def _call_openai_compat_sync(
    provider: str, api_key: str, model: str, prompt: str, system: str, temperature: float
) -> str:
    """Gọi đồng bộ chuẩn OpenAI-compatible (OpenAI, Groq, DeepSeek, OpenRouter)."""
    url = OPENAI_COMPATIBLE_URLS.get(provider, OPENAI_COMPATIBLE_URLS["openai"])
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": 4096,
        "stream": False
    }
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    if response.status_code != 200:
        err_msg = _extract_error_message(response)
        raise RuntimeError(f"{provider.upper()} API ({response.status_code}): {err_msg}")

    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        return f"⚠️ {provider.upper()} API không trả về nội dung phản hồi."
    return (choices[0].get("message", {}).get("content") or "").strip()


def _stream_openai_compat(
    provider: str, api_key: str, model: str, prompt: str, system: str, temperature: float
) -> Generator[str, None, None]:
    """Gọi SSE Streaming chuẩn OpenAI-compatible (OpenAI, Groq, DeepSeek, OpenRouter)."""
    url = OPENAI_COMPATIBLE_URLS.get(provider, OPENAI_COMPATIBLE_URLS["openai"])
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": 4096,
        "stream": True
    }
    with requests.post(url, headers=headers, json=payload, stream=True, timeout=120) as response:
        if response.status_code != 200:
            err_msg = _extract_error_message(response)
            yield f"\n\n⚠️ Lỗi từ {provider.upper()} API ({response.status_code}): {err_msg}"
            return

        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            trimmed = line.strip()
            if not trimmed.startswith("data:"):
                continue
            json_str = trimmed[5:].strip()
            if not json_str or json_str == "[DONE]":
                break
            try:
                chunk = json.loads(json_str)
                choices = chunk.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield token
            except Exception:
                continue


def _extract_error_message(response: requests.Response) -> str:
    """Trích xuất thông báo lỗi ngắn gọn từ phản hồi HTTP lỗi của nhà cung cấp Cloud."""
    try:
        data = response.json()
        if isinstance(data, dict):
            err = data.get("error")
            if isinstance(err, dict):
                return err.get("message") or str(err)
            if isinstance(err, str):
                return err
        return response.text[:250]
    except Exception:
        return response.text[:250] if response.text else f"HTTP {response.status_code}"


def call_cloud_llm(
    llm_config: Dict[str, Any],
    prompt: str,
    system: str,
    temperature: float = 0.3
) -> str:
    """Điều phối lệnh gọi đồng bộ tới Cloud LLM theo cấu hình người dùng."""
    provider, api_key, model = _resolve_config(llm_config)
    logger.info(f"[*] Đang gọi Cloud LLM ({provider} | model={model})...")
    try:
        if provider == "gemini":
            return _call_gemini_sync(api_key, model, prompt, system, temperature)
        return _call_openai_compat_sync(provider, api_key, model, prompt, system, temperature)
    except Exception as e:
        logger.error(f"[!] Lỗi gọi Cloud LLM ({provider}): {e}")
        return f"⚠️ Không thể sinh phản hồi từ Cloud API ({provider.upper()} - {model}): {str(e)}"


def stream_cloud_llm(
    llm_config: Dict[str, Any],
    prompt: str,
    system: str,
    temperature: float = 0.25
) -> Generator[str, None, None]:
    """Điều phối luồng SSE Streaming tới Cloud LLM theo cấu hình người dùng."""
    provider, api_key, model = _resolve_config(llm_config)
    logger.info(f"[*] Bắt đầu streaming từ Cloud LLM ({provider} | model={model})...")
    try:
        if provider == "gemini":
            yield from _stream_gemini(api_key, model, prompt, system, temperature)
        else:
            yield from _stream_openai_compat(provider, api_key, model, prompt, system, temperature)
    except Exception as e:
        logger.error(f"[!] Lỗi stream Cloud LLM ({provider}): {e}")
        yield f"\n\n⚠️ Kết nối tới Cloud API ({provider.upper()} - {model}) bị gián đoạn: {str(e)}"


def verify_cloud_api_key(provider: str, api_key: str, model: Optional[str] = None) -> Tuple[bool, str, str]:
    """
    Kiểm tra nhanh tính hợp lệ của API Key và Model bằng 1 request tối giản.
    Trả về: (is_valid, resolved_model, message)
    """
    cfg = {
        "mode": "cloud",
        "provider": provider,
        "api_key": api_key,
        "model": model
    }
    resolved_provider, clean_key, resolved_model = _resolve_config(cfg)
    if not clean_key:
        return False, resolved_model, "Vui lòng nhập API Key!"

    test_prompt = "Trả lời ngắn gọn chữ: OK"
    test_system = "Bạn là trợ lý kiểm tra kết nối."
    try:
        if resolved_provider == "gemini":
            _call_gemini_sync(clean_key, resolved_model, test_prompt, test_system, 0.1)
        else:
            _call_openai_compat_sync(resolved_provider, clean_key, resolved_model, test_prompt, test_system, 0.1)
        return True, resolved_model, f"Kết nối thành công với {resolved_provider.upper()} ({resolved_model})!"
    except Exception as e:
        return False, resolved_model, str(e)
