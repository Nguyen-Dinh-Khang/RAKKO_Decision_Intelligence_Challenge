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
from ...config import OLLAMA_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Bạn là Trợ lý Cố vấn Chiến thuật Đồng hành (Tactical Co-pilot) cho chủ quán F&B và Bán lẻ thực chiến tại Việt Nam.
Phong cách phản hồi:
- Trực diện, sắc bén, thực tế và gãy gọn; nói thẳng vào nguyên nhân và hành động cụ thể, tuyệt đối không nói lý thuyết sáo rỗng.
- Văn phong tự nhiên, chân thành, tôn trọng và đồng hành cùng chủ quán.
- TUYỆT ĐỐI KHÔNG xưng hô gượng gạo hay đóng vai bất kỳ nhân vật hư cấu nào.
- TUYỆT ĐỐI KHÔNG dùng các câu phán xét gượng gạo hay gán nhãn tiêu cực cho chủ quán. Hãy mở đầu tự nhiên, điềm tĩnh và đi thẳng vào phân tích thực tế của quán (ví dụ: "Với tình huống này của quán, điểm mấu chốt nằm ở...", "Khi gặp trường hợp này, giải pháp ưu tiên là...").
- Dùng xưng hô lịch sự, gần gũi: "chủ quán" hoặc "bạn".

NGUYÊN TẮC HOẠT ĐỘNG BẮT BUỘC:
1. CĂN CỨ VÀO SỐ LIỆU ĐƯỢC GIAO: Chỉ lập luận trên dữ liệu đối thủ, nhân khẩu học và bài học trong CONTEXT. Tuyệt đối không bịa đặt số liệu sách vở.
2. TẬP TRUNG TUYỆT ĐỐI VÀO MẶT HÀNG CỦA NGƯỜI DÙNG: Áp dụng bài học đúng vào ngành hàng và sản phẩm chủ quán đang kinh doanh.
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
    """Class điều phối suy luận với mô hình Qwen3.5 4B qua Ollama."""

    def __init__(self):
        raw_url = OLLAMA_BASE_URL.rstrip('/')
        # Ưu tiên sử dụng IPv4 127.0.0.1 để tránh lỗi phân giải IPv6/từ chối cổng trên Windows
        if "localhost" in raw_url:
            raw_url = raw_url.replace("localhost", "127.0.0.1")
        self.api_url = f"{raw_url}/api/generate"
        self.model = LLM_MODEL

    def _call_ollama(self, prompt: str, temperature: float = 0.3, system: Optional[str] = None) -> str:
        """Gửi request tới Ollama HTTP API và nhận câu trả lời đầy đủ dạng text (đồng bộ)."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or SYSTEM_PROMPT,
            "stream": False,
            "think": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "num_ctx": 12288,  # Kích thước Context Window đầu vào
                "num_predict": 3500  # Ngưỡng token đầu ra tối đa để không bị ngắt giữa chừng
            }
        }
        logger.info(f"[*] Đang gửi prompt tới Ollama ({self.model})...")

        # Thử 127.0.0.1 trước, nếu lỗi thì thử localhost
        urls_to_try = [self.api_url]
        if "127.0.0.1" in self.api_url:
            urls_to_try.append(self.api_url.replace("127.0.0.1", "localhost"))
        elif "localhost" in self.api_url:
            urls_to_try.append(self.api_url.replace("localhost", "127.0.0.1"))

        last_error = None
        for target_url in urls_to_try:
            try:
                response = requests.post(target_url, json=payload, timeout=180)
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "").strip()
                else:
                    logger.error(f"[!] Ollama ({target_url}) trả về mã lỗi: {response.status_code} - {response.text}")
            except requests.exceptions.RequestException as e:
                last_error = e
                logger.warning(f"[!] Thử kết nối Ollama tại {target_url} thất bại: {e}")
                continue

        logger.error(f"[!] Toàn bộ kết nối tới Ollama thất bại. Lỗi cuối: {last_error}")
        return (
            "⚠️ Hệ thống AI Copilot tạm thời chưa kết nối được tới máy chủ LLM Ollama (cổng 11434). "
            "Vui lòng đảm bảo ứng dụng Ollama đã được khởi động và mô hình 'qwen3.5:4b' đã sẵn sàng trên máy."
        )

    def _stream_ollama(self, prompt: str, temperature: float = 0.25, system: Optional[str] = None) -> Generator[str, None, None]:
        """Gửi request tới Ollama HTTP API và nhận phản hồi dòng token-by-token (SSE)."""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system or SYSTEM_PROMPT,
            "stream": True,
            "think": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "num_ctx": 12288,
                "num_predict": 3500
            }
        }
        logger.info(f"[*] Bắt đầu streaming từ Ollama ({self.model})...")

        urls_to_try = [self.api_url]
        if "127.0.0.1" in self.api_url:
            urls_to_try.append(self.api_url.replace("127.0.0.1", "localhost"))
        elif "localhost" in self.api_url:
            urls_to_try.append(self.api_url.replace("localhost", "127.0.0.1"))

        connected = False
        for target_url in urls_to_try:
            try:
                with requests.post(target_url, json=payload, stream=True, timeout=180) as response:
                    if response.status_code != 200:
                        continue
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

        if not connected:
            yield (
                "\n\n⚠️ Không thể kết nối với máy chủ AI Ollama (cổng 11434). "
                "Vui lòng kiểm tra ứng dụng Ollama đã được khởi động với mô hình 'qwen3.5:4b'."
            )

    def evaluate_feasibility(
        self,
        form_data: Dict[str, Any],
        demographics: Dict[str, Any],
        competitors: List[Dict[str, Any]],
        market_gaps: Dict[str, Any],
        stress_test: Any,
        tactical_playbook: Optional[Dict[str, Any]] = None
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
        return self._call_ollama(prompt, temperature=0.3, system=system_prompt)

    def stream_evaluate_feasibility(
        self,
        form_data: Dict[str, Any],
        demographics: Dict[str, Any],
        competitors: List[Dict[str, Any]],
        market_gaps: Dict[str, Any],
        stress_test: Any,
        tactical_playbook: Optional[Dict[str, Any]] = None
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
        for token in self._stream_ollama(prompt, temperature=0.3, system=system_prompt):
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
        conversation_history: Optional[List[Dict[str, str]]] = None
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
        return self._call_ollama(prompt, temperature=0.25, system=system_prompt)

    def stream_tactical_copilot(
        self,
        user_query: str,
        model_name: str,
        context_markdown: str,
        intent: str = "INTERNAL",
        branch: Optional[str] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
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
        for token in self._stream_ollama(prompt, temperature=0.25, system=system_prompt):
            yield token
