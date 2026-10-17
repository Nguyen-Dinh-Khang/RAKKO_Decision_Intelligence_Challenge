"""
llm_copilot.py - Mắt xích 6: Bộ Não Suy Luận Cố Vấn (Qwen3.5 4B qua Ollama)
Chức năng:
1. Kết nối với mô hình Qwen3.5 4B đang chạy cục bộ trên Ollama (cổng 11434).
2. Hỗ trợ 2 chế độ suy luận:
   - Synchronous Response (_call_ollama): Trả về toàn bộ text
   - Real-time Streaming Response (_stream_ollama): Trả về từng token theo thời gian thực (SSE)
3. Hỗ trợ Bộ nhớ Đa lượt (Multi-turn Context Memory):
   - Lưu 2 - 3 lượt trao đổi gần nhất để người dùng hỏi đào sâu, tiếp nối ngữ cảnh
4. Cấu trúc câu trả lời thực chiến 3 phần:
   - Phần 1: Nguyên nhân cốt lõi
   - Phần 2: Kịch bản 24h (Checklist + Lời thoại mẫu)
   - Phần 3: Con số mục tiêu đo lường
"""

import json
import logging
import requests
from typing import Dict, List, Any, Optional, Generator
from ...config import OLLAMA_BASE_URL, LLM_MODEL, NUM_CTX

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là Trợ lý Cố vấn Chiến thuật Đồng hành (Tactical Co-pilot) cho Hộ kinh doanh Bán lẻ & Dịch vụ Đời sống thực chiến tại Việt Nam.
Phong cách phản hồi:
- Trực diện, sắc bén, thực tế và gãy gọn; nói thẳng vào nguyên nhân và hành động cụ thể, tuyệt đối không nói lý thuyết sáo rỗng.
- Văn phong tự nhiên, chân thành, tôn trọng và đồng hành cùng chủ cơ sở.
- TUYỆT ĐỐI KHÔNG xưng hô gượng gạo hay đóng vai bất kỳ nhân vật hư cấu nào.
- TUYỆT ĐỐI KHÔNG dùng các câu phán xét gượng gạo hay gán nhãn tiêu cực cho người kinh doanh. Hãy mở đầu tự nhiên, điềm tĩnh và đi thẳng vào phân tích thực tế của cơ sở (ví dụ: "Với tình huống này của bạn, điểm mấu chốt nằm ở...", "Khi gặp trường hợp này, giải pháp ưu tiên là...").
- Dùng xưng hô lịch sự, gần gũi: "bạn" hoặc "chủ cơ sở" (hoặc "chủ quán" nếu là mô hình ăn uống).

NGUYÊN TẮC HOẠT ĐỘNG BẮT BUỘC:
1. CĂN CỨ VÀO SỐ LIỆU ĐƯỢC GIAO: Chỉ lập luận trên dữ liệu đối thủ, nhân khẩu học và bài học trong CONTEXT. Tuyệt đối không bịa đặt số liệu sách vở.
2. TẬP TRUNG TUYỆT ĐỐI VÀO MẶT HÀNG CỦA NGƯỜI DÙNG: Áp dụng bài học đúng vào ngành hàng và sản phẩm/dịch vụ người dùng đang kinh doanh.
3. NÓI RÕ CON SỐ & HÀNH ĐỘNG CỤ THỂ: Không khuyên chung chung kiểu "cần marketing", phải nói rõ ví dụ như "làm combo giữ giá và xuất đơn dưới 60 giây".
4. TRẢ LỜI ĐÚNG TRỌNG TÂM CẤU TRÚC:
   - Nếu là Thẩm định ý tưởng (Day 0, Runway > 0): Đủ 5 phần (Dòng tiền, Đối thủ 1km, Đòn tấn công 3 mũi, Bài học rủi ro & kinh nghiệm, Chiến lược ngắn - dài hạn).
   - Nếu là Báo động cạn vốn (Runway <= 0): Tập trung bóc tách dòng tiền và tái cấu trúc vốn.
   - Nếu là Trợ lý sự cố / phản công (Copilot): Trả lời đúng 3 phần gãy gọn:
     1. Nguyên nhân cốt lõi (Phân tích khách quan tình huống và tâm lý khách hàng);
     2. Kịch bản hành động trong 24h (Checklist việc cần làm ngay + Lời thoại mẫu đàm phán/giao tiếp);
     3. Con số mục tiêu cần theo dõi.
"""


class LLMCopilot:
    """Class điều phối suy luận với mô hình Qwen3.5 4B qua Ollama (hỗ trợ Server & Local Fallback)."""

    def __init__(self):
        self.model = LLM_MODEL
        self.num_ctx = NUM_CTX
        self._active_url: Optional[str] = None

    def _get_target_urls(self) -> List[str]:
        """Tự động sinh danh sách URL ưu tiên và fallback chéo giữa Server (11435) và Local (11434)."""
        raw_url = OLLAMA_BASE_URL.rstrip('/')
        candidates = [raw_url]

        # Tự động hỗ trợ Fallback chéo giữa cổng 11435 (Server) và 11434 (Local mặc định)
        if ":11435" in raw_url:
            candidates.append(raw_url.replace(":11435", ":11434"))
        elif ":11434" in raw_url:
            candidates.append(raw_url.replace(":11434", ":11435"))
        else:
            candidates.extend(["http://127.0.0.1:11435", "http://127.0.0.1:11434"])

        urls = []
        # Ưu tiên URL đang kết nối tốt trước đó
        if self._active_url and self._active_url not in urls:
            urls.append(self._active_url)

        for c in candidates:
            # Ưu tiên IPv4 127.0.0.1 để tránh lỗi phân giải IPv6/từ chối cổng trên Windows
            ipv4_url = c.replace("localhost", "127.0.0.1") + "/api/generate"
            named_url = c.replace("127.0.0.1", "localhost") + "/api/generate"
            for u in (ipv4_url, named_url):
                if u not in urls:
                    urls.append(u)
        return urls

    def _call_ollama(self, prompt: str, temperature: float = 0.3, system: Optional[str] = None) -> str:
        """Gửi request tới Ollama HTTP API và nhận câu trả lời đầy đủ dạng text (đồng bộ)."""
        urls_to_try = self._get_target_urls()
        ctx_to_try = [self.num_ctx]
        # Fallback context window nếu 20480 quá tải trên máy tính local ít VRAM
        if self.num_ctx > 8192:
            ctx_to_try.append(8192)

        last_error = None
        for current_ctx in ctx_to_try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system or SYSTEM_PROMPT,
                "stream": False,
                "think": False,
                "options": {
                    "temperature": temperature,
                    "top_p": 0.9,
                    "num_ctx": current_ctx,  # Kích thước Context Window (20480 trên GPU, fallback 8192)
                    "num_predict": 3500
                }
            }
            logger.info(f"[*] Đang gửi prompt tới Ollama ({self.model}, num_ctx={current_ctx})...")

            for target_url in urls_to_try:
                try:
                    response = requests.post(target_url, json=payload, timeout=180)
                    if response.status_code == 200:
                        self._active_url = target_url
                        result = response.json()
                        return result.get("response", "").strip()
                    else:
                        logger.warning(f"[!] Ollama ({target_url}) trả về mã lỗi: {response.status_code} - {response.text[:200]}")
                except requests.exceptions.RequestException as e:
                    last_error = e
                    continue

        logger.error(f"[!] Toàn bộ kết nối tới Ollama thất bại. Lỗi cuối: {last_error}")
        return (
            "⚠️ Hệ thống AI Copilot tạm thời chưa kết nối được tới máy chủ LLM Ollama. "
            "Vui lòng đảm bảo ứng dụng Ollama đã được khởi động (cổng 11435 trên server hoặc 11434 local) "
            f"và mô hình '{self.model}' đã sẵn sàng trên máy."
        )

    def _stream_ollama(self, prompt: str, temperature: float = 0.25, system: Optional[str] = None) -> Generator[str, None, None]:
        """Gửi request tới Ollama HTTP API và nhận phản hồi dòng token-by-token (SSE)."""
        urls_to_try = self._get_target_urls()
        ctx_to_try = [self.num_ctx]
        if self.num_ctx > 8192:
            ctx_to_try.append(8192)

        connected = False
        for current_ctx in ctx_to_try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "system": system or SYSTEM_PROMPT,
                "stream": True,
                "think": False,
                "options": {
                    "temperature": temperature,
                    "top_p": 0.9,
                    "num_ctx": current_ctx,
                    "num_predict": 3500
                }
            }
            logger.info(f"[*] Bắt đầu streaming từ Ollama ({self.model}, num_ctx={current_ctx})...")

            for target_url in urls_to_try:
                try:
                    with requests.post(target_url, json=payload, stream=True, timeout=180) as response:
                        if response.status_code != 200:
                            continue
                        self._active_url = target_url
                        connected = True
                        for line in response.iter_lines(decode_unicode=True):
                            if line:
                                try:
                                    chunk_data = json.loads(line)
                                    token = chunk_data.get("response", "")
                                    if token:
                                        yield token
                                    if chunk_data.get("done", False):
                                        break
                                except Exception:
                                    continue
                        return
                except Exception as e:
                    logger.warning(f"[!] Thử stream Ollama tại {target_url} thất bại: {e}")
                    continue

            if connected:
                break

        if not connected:
            yield (
                "\n\n⚠️ Không thể kết nối với máy chủ AI Ollama. "
                "Vui lòng kiểm tra dịch vụ Ollama đã được khởi động (cổng 11435 trên server hoặc 11434 local) "
                f"với mô hình '{self.model}'."
            )


    def _dispatch_call(
        self,
        prompt: str,
        temperature: float = 0.3,
        system: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Điều phối suy luận đồng bộ: Cloud API Key (nếu bật) hoặc Local Ollama (mặc định)."""
        from .cloud_provider import is_cloud_config_active, call_cloud_llm
        if is_cloud_config_active(llm_config):
            return call_cloud_llm(
                llm_config=llm_config,
                prompt=prompt,
                system=system or SYSTEM_PROMPT,
                temperature=temperature
            )
        return self._call_ollama(prompt, temperature=temperature, system=system)

    def _dispatch_stream(
        self,
        prompt: str,
        temperature: float = 0.25,
        system: Optional[str] = None,
        llm_config: Optional[Dict[str, Any]] = None
    ) -> Generator[str, None, None]:
        """Điều phối suy luận SSE Streaming: Cloud API Key (nếu bật) hoặc Local Ollama (mặc định)."""
        from .cloud_provider import is_cloud_config_active, stream_cloud_llm
        if is_cloud_config_active(llm_config):
            yield from stream_cloud_llm(
                llm_config=llm_config,
                prompt=prompt,
                system=system or SYSTEM_PROMPT,
                temperature=temperature
            )
            return
        for token in self._stream_ollama(prompt, temperature=temperature, system=system):
            yield token

    def evaluate_feasibility(
        self,
        form_data: Dict[str, Any],
        demographics: Dict[str, Any],
        competitors: List[Dict[str, Any]],
        market_gaps: Dict[str, Any],
        stress_test: Any,
        tactical_playbook: Optional[Dict[str, Any]] = None,
        llm_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Chế độ 1: Thẩm định Ý tưởng (Day 0) - Bộ não Cố vấn Chiến lược và Tác chiến
        Logic tạo Prompt và Lộ trình Suy luận được tách độc lập tại `scanner_prompt.py`.
        """
        from .scanner_prompt import build_scanner_prompt
        prompt, system_prompt = build_scanner_prompt(
            form_data=form_data,
            demographics=demographics,
            competitors=competitors,
            market_gaps=market_gaps,
            stress_test=stress_test,
            tactical_playbook=tactical_playbook
        )
        return self._dispatch_call(prompt, temperature=0.3, system=system_prompt, llm_config=llm_config)

    def stream_evaluate_feasibility(
        self,
        form_data: Dict[str, Any],
        demographics: Dict[str, Any],
        competitors: List[Dict[str, Any]],
        market_gaps: Dict[str, Any],
        stress_test: Any,
        tactical_playbook: Optional[Dict[str, Any]] = None,
        llm_config: Optional[Dict[str, Any]] = None
    ) -> Generator[str, None, None]:
        """
        Chế độ 1 streaming (SSE): Đẩy từng token phân tích thẩm định của Qwen3.5 4B theo thời gian thực.
        """
        from .scanner_prompt import build_scanner_prompt
        prompt, system_prompt = build_scanner_prompt(
            form_data=form_data,
            demographics=demographics,
            competitors=competitors,
            market_gaps=market_gaps,
            stress_test=stress_test,
            tactical_playbook=tactical_playbook
        )
        for token in self._dispatch_stream(prompt, temperature=0.3, system=system_prompt, llm_config=llm_config):
            yield token

    def _build_tactical_prompt(
        self,
        user_query: str,
        model_name: str,
        context_markdown: str,
        intent: str = "INTERNAL",
        branch: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> tuple:
        """
        Ghép nối prompt chuẩn cho Copilot theo 5 nhánh chuyên biệt (BRANCH_A -> BRANCH_E).
        Sử dụng copilot_prompts.py để đảm bảo tính module hóa và đa dạng văn phong.
        """
        from .copilot_prompts import build_branch_prompt

        resolved_branch = branch
        if not resolved_branch:
            resolved_branch = "BRANCH_D" if intent == "COMPETITIVE" else "BRANCH_B"

        return build_branch_prompt(
            branch=resolved_branch,
            user_query=user_query,
            model_name=model_name,
            context_markdown=context_markdown,
            conversation_history=conversation_history
        )

    def answer_tactical_copilot(
        self,
        user_query: str,
        model_name: str,
        context_markdown: str,
        intent: str = "INTERNAL",
        branch: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        llm_config: Optional[Dict[str, Any]] = None
    ) -> str:
        """Chế độ 2 đồng bộ: Trả về toàn bộ câu trả lời dạng chuỗi theo 5 nhánh chuyên biệt."""
        prompt, system_prompt = self._build_tactical_prompt(
            user_query=user_query,
            model_name=model_name,
            context_markdown=context_markdown,
            intent=intent,
            branch=branch,
            conversation_history=conversation_history
        )
        return self._dispatch_call(prompt, temperature=0.25, system=system_prompt, llm_config=llm_config)

    def stream_tactical_copilot(
        self,
        user_query: str,
        model_name: str,
        context_markdown: str,
        intent: str = "INTERNAL",
        branch: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        llm_config: Optional[Dict[str, Any]] = None
    ) -> Generator[str, None, None]:
        """Chế độ 2 streaming (SSE): Đẩy từng token theo thời gian thực theo 5 nhánh chuyên biệt."""
        prompt, system_prompt = self._build_tactical_prompt(
            user_query=user_query,
            model_name=model_name,
            context_markdown=context_markdown,
            intent=intent,
            branch=branch,
            conversation_history=conversation_history
        )
        for token in self._dispatch_stream(prompt, temperature=0.25, system=system_prompt, llm_config=llm_config):
            yield token

