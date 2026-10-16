import React, { useState } from 'react';
import { CheckSquare, Square, ChevronRight, Quote, MessageCircle, HelpCircle, Clock } from 'lucide-react';

/**
 * FormattedMarkdown - Component render văn bản Markdown thông minh
 * Chuyên xử lý định dạng trả về từ LLM:
 * 1. Tiêu đề "###": Làm lớn hơn, có thanh màu nhấn bên trái, nổi bật rõ ràng
 * 2. In đậm "**": Làm đậm rõ rệt (font-bold text-slate-900)
 * 3. Bullet points "- ", "* ": Biến thành danh sách đẹp mắt có chấm tròn màu
 * 4. Checkbox "- [ ]", "- [x]": Biến thành ô tick tương tác người dùng có thể bấm vào
 * 5. Trích dẫn / Lời thoại "> " hoặc "Lời thoại:": Đóng khung hội thoại nổi bật
 * 6. Danh sách số "1. ", "2. ": Đánh số màu xanh nổi bật
 */
/**
 * Phân tích các định dạng nội dòng (Inline Formatting):
 * - **chữ đậm ở đầu dòng** (Lead-in Bold) -> font-black text-slate-950 text-[13.5px] sm:text-sm
 * - **chữ đậm trong câu** -> font-bold text-slate-900 (không nền, không viền)
 * - *chữ nghiêng* -> <em>
 * - `code` -> <code>
 */
export const renderInline = (text, checkLeadIn = false) => {
  if (!text || typeof text !== 'string') return text || null;

  const inlineRegex = /(\*\*.*?\*\*|\*.*?\*|`.*?`)/g;
  const tokens = text.split(inlineRegex);

  // Xác định xem token bold đầu tiên có phải là đầu dòng (Lead-in) hay không
  let firstBoldIndex = -1;
  if (checkLeadIn) {
    for (let i = 0; i < tokens.length; i++) {
      const tok = tokens[i];
      if (tok && typeof tok === 'string' && tok.startsWith('**') && tok.endsWith('**') && tok.length >= 4) {
        const prefix = tokens.slice(0, i).join('').trim();
        // Nếu trước token bold chỉ là chuỗi rỗng hoặc ký tự đầu dòng
        if (prefix === '' || prefix === '-' || prefix === '*' || prefix === '+') {
          firstBoldIndex = i;
        }
        break;
      }
    }
  }

  return tokens.map((token, i) => {
    if (!token || typeof token !== 'string') return token || null;
    if (token.startsWith('**') && token.endsWith('**') && token.length >= 4) {
      const innerText = token.slice(2, -2);
      const isLeadIn = (i === firstBoldIndex);

      if (isLeadIn) {
        return (
          <strong key={i} className="font-black text-slate-950 text-sm sm:text-[13.5px] tracking-tight inline-block mr-1">
            {innerText}
          </strong>
        );
      }

      return (
        <strong key={i} className="font-bold text-slate-800">
          {innerText}
        </strong>
      );
    } else if (token.startsWith('*') && token.endsWith('*') && token.length >= 2) {
      const innerText = token.slice(1, -1);
      return (
        <em key={i} className="italic text-slate-700">
          {innerText}
        </em>
      );
    } else if (token.startsWith('`') && token.endsWith('`') && token.length >= 2) {
      const innerText = token.slice(1, -1);
      return (
        <code key={i} className="font-mono text-xs bg-slate-100 text-blue-700 px-1.5 py-0.5 rounded border border-slate-200">
          {innerText}
        </code>
      );
    }
    return token;
  });
};

export default function FormattedMarkdown({ content, className = '' }) {
  if (!content) return null;

  // State lưu trữ các checkbox người dùng đã tick chọn
  const [checkedItems, setCheckedItems] = useState({});

  const toggleCheck = (key, initialChecked = false) => {
    setCheckedItems(prev => {
      const current = prev[key] !== undefined ? prev[key] : initialChecked;
      return {
        ...prev,
        [key]: !current
      };
    });
  };
  const isWhyReason = (text) => {
    if (!text || typeof text !== 'string') return false;
    const lower = text.toLowerCase().trim();
    return lower.startsWith('tại sao') || 
           lower.startsWith('**tại sao') || 
           lower.startsWith('*tại sao') ||
           lower.startsWith('vì sao') ||
           lower.startsWith('**vì sao') ||
           lower.includes('tại sao:');
  };

  /**
   * Nhận diện và bóc tách dòng checklist/checkbox:
   * Hỗ trợ mọi biến thể markdown mà LLM có thể sinh ra:
   * 1. Tiền tố: '-', '*', '+', số dạng '1.', '2.', hoặc không có tiền tố
   * 2. Cặp ngoặc: '[ ]', '[]' (ngoặc rỗng không có dấu cách), '[  ]', '[x]', '[X]', '[v]', '[V]', '[✓]'
   * 3. Khoảng cách: có hoặc không có khoảng trắng sau dấu ngoặc
   */
  const parseCheckboxLine = (str) => {
    if (!str || typeof str !== 'string') return null;
    const trimmed = str.trim();
    const match = trimmed.match(/^(?:(?:[-*+]|\d+\.)\s*)?\[\s*([xXvV\u2713\u2714]?)\s*\]\s*(.*)$/);
    if (!match) return null;

    const mark = (match[1] || '').trim();
    const isChecked = mark.length > 0;
    const text = match[2] || '';

    return { isChecked, text };
  };

  /**
   * Nhận diện các dòng là Tiêu đề con (kết thúc bằng dấu ":" và không có nội dung tiếp nối trên cùng dòng):
   * Ví dụ: "Checklist hành động:", "Kế hoạch điều chỉnh Plan B:", "Giai đoạn 30 ngày đầu:"
   */
  const getSubHeaderInfo = (lineStr) => {
    if (!lineStr || typeof lineStr !== 'string') return null;
    const trimmed = lineStr.trim();
    if (trimmed.startsWith('#')) return null;

    // Bỏ qua nếu là checkbox hoặc quote hoặc separator
    if (
      parseCheckboxLine(trimmed) || trimmed.startsWith('>') || trimmed === '---' || trimmed === '***'
    ) {
      return null;
    }

    // Gọt bỏ ký tự bullet hoặc số đầu dòng: '-', '*', '+', '1.'
    const strippedMarker = trimmed.replace(/^([-*+]|\d+\.)\s+/, '').trim();
    // Bỏ định dạng ** để lấy chữ thuần
    const clean = strippedMarker.replace(/\*\*/g, '').trim();

    // Điều kiện: kết thúc bằng ":" và độ dài phù hợp tiêu đề con (< 90 ký tự)
    if (clean.endsWith(':') && clean.length > 1 && clean.length < 90) {
      const lower = clean.toLowerCase();
      const isPhase = lower.includes('giai đoạn') || lower.includes('lộ trình') || lower.includes('phase');
      const isDialogue = lower.includes('lời thoại');
      return {
        clean,
        isPhase,
        isDialogue
      };
    }
    return null;
  };

  // Tách văn bản thành các dòng và tiền xử lý gom nhóm thông minh
  const rawLines = content.split('\n');
  const processedBlocks = [];

  for (let i = 0; i < rawLines.length; i++) {
    const line = rawLines[i];
    const trimmed = line.trim();

    if (!trimmed) {
      processedBlocks.push({ type: 'empty' });
      continue;
    }

    // Tiêu đề Markdown cấp độ chuẩn (#, ##, ###, ####)
    if (trimmed.startsWith('#')) {
      processedBlocks.push({ type: 'markdown_heading', raw: trimmed, trimmed: trimmed });
      continue;
    }

    const subInfo = getSubHeaderInfo(trimmed);

    // Gom Lời thoại mẫu thành một khung duy nhất (nếu ngay sau đó có trích dẫn hoặc câu thoại)
    if (subInfo && subInfo.isDialogue) {
      let nextIdx = i + 1;
      while (nextIdx < rawLines.length && !rawLines[nextIdx].trim()) {
        nextIdx++;
      }
      if (nextIdx < rawLines.length) {
        const nextTrimmed = rawLines[nextIdx].trim();
        if (nextTrimmed.startsWith('>') || nextTrimmed.startsWith('"') || nextTrimmed.startsWith('“')) {
          const quotes = [];
          while (nextIdx < rawLines.length) {
            const curTrimmed = rawLines[nextIdx].trim();
            if (!curTrimmed) break;
            if (curTrimmed.startsWith('>') || curTrimmed.startsWith('"') || curTrimmed.startsWith('“')) {
              quotes.push(curTrimmed.replace(/^>\s*/, '').replace(/^["“]|["”]$/g, ''));
              nextIdx++;
            } else {
              break;
            }
          }
          processedBlocks.push({
            type: 'dialogue_merged',
            title: subInfo.clean,
            quote: quotes.join(' ')
          });
          i = nextIdx - 1;
          continue;
        }
      }
    }

    // Tiêu đề con (kết thúc bằng dấu ":")
    if (subInfo) {
      if (subInfo.isPhase) {
        processedBlocks.push({
          type: 'phase_header',
          text: subInfo.clean
        });
      } else {
        processedBlocks.push({
          type: 'sub_header',
          text: subInfo.clean
        });
      }
      continue;
    }

    // Các dòng văn bản / danh sách thông thường
    processedBlocks.push({
      type: 'line',
      raw: line,
      trimmed: trimmed,
      idx: i
    });
  }

  return (
    <div className={`space-y-2 text-slate-700 leading-relaxed ${className}`}>
      {processedBlocks.map((block, idx) => {
        // 1. DÒNG TRỐNG
        if (block.type === 'empty') {
          return <div key={idx} className="h-1.5" />;
        }

        // 2. TIÊU ĐỀ GIAI ĐOẠN: Nới rộng khoảng cách, thoáng mắt, có biểu tượng đồng hồ
        if (block.type === 'phase_header') {
          return (
            <div key={idx} className="mt-7 mb-3.5 pt-2">
              <div className="inline-flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-indigo-50 border border-indigo-200/90 text-indigo-950 shadow-2xs">
                <Clock className="w-4 h-4 text-indigo-600 flex-shrink-0" />
                <span className="font-extrabold text-xs sm:text-sm tracking-wide">
                  {block.text}
                </span>
              </div>
            </div>
          );
        }

        // 3. TIÊU ĐỀ CON KẾT THÚC DẤU ":": Màu xanh dương sáng, in hoa đậm, tách biệt khỏi gạch đầu dòng
        if (block.type === 'sub_header') {
          return (
            <div key={idx} className="mt-4 mb-2 pt-1">
              <div className="flex items-center space-x-2 text-blue-600 font-extrabold text-xs sm:text-sm uppercase tracking-wide">
                <span className="w-1.5 h-3.5 bg-blue-600 rounded-xs flex-shrink-0"></span>
                <span>{block.text}</span>
              </div>
            </div>
          );
        }

        // 4. LỜI THOẠI MẪU THỰC CHIẾN: Gộp thành một khuôn duy nhất, tinh tế, không bị tách thành hai ô
        if (block.type === 'dialogue_merged') {
          return (
            <div key={idx} className="my-3 p-3.5 sm:p-4 rounded-xl bg-blue-50/50 border border-blue-200/80 shadow-2xs">
              <div className="flex items-center space-x-2 text-blue-700 font-bold text-xs sm:text-[13px] uppercase tracking-wider mb-2">
                <MessageCircle className="w-4 h-4 text-blue-600 flex-shrink-0" />
                <span>{block.title}</span>
              </div>
              <div className="pl-3 border-l-2 border-blue-400 text-xs sm:text-sm font-medium text-slate-800 italic leading-relaxed">
                "{block.quote}"
              </div>
            </div>
          );
        }

        // 5. TIÊU ĐỀ MARKDOWN (#, ##, ###, ####)
        if (block.type === 'markdown_heading') {
          const headingRaw = block.raw || block.trimmed || '';
          if (headingRaw.startsWith('####')) {
            const headingText = headingRaw.replace(/^####\s*/, '');
            return (
              <div key={idx} className="mt-5 mb-2.5 pt-1">
                <h4 className="font-extrabold text-xs sm:text-sm uppercase tracking-wide text-slate-900 flex items-center space-x-2">
                  <span className="w-1.5 h-3.5 bg-indigo-500 rounded-xs flex-shrink-0"></span>
                  <span>{renderInline(headingText, true)}</span>
                </h4>
              </div>
            );
          }

          if (headingRaw.startsWith('###')) {
            const headingText = headingRaw.replace(/^###\s*/, '');
            return (
              <div key={idx} className="mt-8 mb-4 pt-3 first:mt-1 first:pt-0">
                <div className="flex items-center space-x-2.5 pb-2.5 border-b-2 border-blue-600/80">
                  <span className="w-2.5 h-2.5 rounded-full bg-blue-600 flex-shrink-0 animate-pulse"></span>
                  <h3 className="font-black text-base sm:text-lg text-slate-900 tracking-tight">
                    {renderInline(headingText, true)}
                  </h3>
                </div>
              </div>
            );
          }

          if (headingRaw.startsWith('##')) {
            const headingText = headingRaw.replace(/^##\s*/, '');
            return (
              <div key={idx} className="mt-8 mb-4">
                <div className="p-3 rounded-xl bg-slate-50 border-l-4 border-indigo-600 border border-slate-200">
                  <h2 className="font-black text-lg sm:text-xl text-indigo-950 tracking-tight">
                    {renderInline(headingText, true)}
                  </h2>
                </div>
              </div>
            );
          }

          const headingText = headingRaw.replace(/^#+\s*/, '');
          return (
            <h1 key={idx} className="font-black text-xl sm:text-2xl text-blue-900 mt-7 mb-4 pb-2 border-b-2 border-slate-200">
              {renderInline(headingText, true)}
            </h1>
          );
        }

        // CÁC LOẠI DÒNG NỘI DUNG KHÁC
        const trimmed = (block.trimmed || block.raw || '').trim();
        const lineKey = block.idx !== undefined ? block.idx : idx;

        if (!trimmed) {
          return <div key={idx} className="h-1.5" />;
        }

        // 6. CHECKBOX INTERACTIVE: "- [ ]", "- []", "* [ ]", "1. [ ]", "[ ]", v.v.
        const checkboxInfo = parseCheckboxLine(trimmed);
        if (checkboxInfo) {
          const isInitiallyChecked = checkboxInfo.isChecked;
          const isChecked = checkedItems[lineKey] !== undefined ? checkedItems[lineKey] : isInitiallyChecked;
          const cleanText = checkboxInfo.text;

          return (
            <div 
              key={idx} 
              onClick={() => toggleCheck(lineKey, isInitiallyChecked)}
              className={`flex items-start space-x-3 p-2.5 my-1.5 rounded-xl border transition-all cursor-pointer select-none ${
                isChecked
                  ? 'bg-slate-50 border-emerald-300 text-emerald-900'
                  : 'bg-white hover:bg-slate-50/80 border-slate-200 text-slate-800 shadow-2xs'
              }`}
            >
              <button type="button" className="mt-0.5 flex-shrink-0 text-blue-600">
                {isChecked ? (
                  <CheckSquare className="w-4 h-4 text-emerald-600" />
                ) : (
                  <Square className="w-4 h-4 text-slate-400 hover:text-blue-600" />
                )}
              </button>
              <span className={`text-sm sm:text-[15px] font-medium leading-relaxed ${isChecked ? 'line-through text-emerald-700/70' : ''}`}>
                {renderInline(cleanText, true)}
              </span>
            </div>
          );
        }

        // 7. LỜI THOẠI ĐƠN LẺ HOẶC TRÍCH DẪN ĐỘC LẬP
        if (trimmed.includes('Lời thoại') || trimmed.startsWith('> ')) {
          const cleanText = trimmed.replace(/^>\s*/, '');
          return (
            <div key={idx} className="my-2.5 p-3.5 rounded-xl bg-blue-50/50 border-l-4 border-blue-500 border border-blue-200/70 shadow-2xs flex items-start space-x-2.5">
              <MessageCircle className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
              <div className="text-sm sm:text-[15px] font-medium text-slate-800 italic leading-relaxed">
                {renderInline(cleanText, true)}
              </div>
            </div>
          );
        }

        // 8. GẠCH ĐẦU DÒNG (BULLET POINTS): "-", "*", "+"
        if (trimmed.startsWith('- ') || trimmed.startsWith('* ') || trimmed.startsWith('+ ')) {
          const bulletText = trimmed.replace(/^[-*+]\s+/, '');

          // Phân biệt rõ phần lý giải "Tại sao" / "Vì sao" với icon và khung tinh tế, êm mắt
          if (isWhyReason(bulletText)) {
            return (
              <div key={idx} className="my-2.5 p-3.5 rounded-xl bg-slate-50/90 border-l-4 border-amber-400 border border-slate-200/70 text-slate-800 shadow-2xs">
                <div className="flex items-center space-x-1.5 text-amber-800 font-bold text-xs uppercase tracking-wider mb-1">
                  <HelpCircle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                  <span>Lý do & Bản chất chiến lược</span>
                </div>
                <div className="text-sm sm:text-[15px] text-slate-800 leading-relaxed font-normal">
                  {renderInline(bulletText.replace(/^(tại sao|vì sao|tại sao:|\*\*tại sao:\*\*|\*\*tại sao\*\*)\s*/i, ''), true)}
                </div>
              </div>
            );
          }

          return (
            <div key={idx} className="flex items-start space-x-2.5 my-2 pl-2">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400 mt-2 flex-shrink-0"></span>
              <div className="text-sm sm:text-[15px] text-slate-800 leading-relaxed font-normal flex-1">
                {renderInline(bulletText, true)}
              </div>
            </div>
          );
        }

        // 9. DANH SÁCH ĐÁNH SỐ: "1. ", "2. ", v.v.
        const numberedMatch = trimmed.match(/^(\d+)\.\s+(.*)/);
        if (numberedMatch) {
          const num = numberedMatch[1];
          const text = numberedMatch[2];
          return (
            <div key={idx} className="flex items-start space-x-2.5 my-2 pl-2">
              <span className="font-extrabold text-blue-600 text-sm sm:text-base flex-shrink-0 mt-0.5">
                {num}.
              </span>
              <div className="text-sm sm:text-[15px] text-slate-800 leading-relaxed flex-1">
                {renderInline(text, true)}
              </div>
            </div>
          );
        }

        // 10. ĐƯỜNG PHÂN CÁCH NGANG: "---"
        if (trimmed === '---' || trimmed === '***') {
          return <hr key={idx} className="my-5 border-slate-200" />;
        }

        // 11. ĐOẠN VĂN GIẢI THÍCH "TẠI SAO" ĐỘC LẬP
        if (isWhyReason(trimmed)) {
          return (
            <div key={idx} className="my-2.5 p-3.5 rounded-xl bg-slate-50/90 border-l-4 border-amber-400 border border-slate-200/70 text-slate-800 shadow-2xs">
              <div className="flex items-center space-x-1.5 text-amber-800 font-bold text-xs uppercase tracking-wider mb-1">
                <HelpCircle className="w-3.5 h-3.5 text-amber-600 flex-shrink-0" />
                <span>Lý do & Bản chất chiến lược</span>
              </div>
              <div className="text-sm sm:text-[15px] text-slate-800 leading-relaxed font-medium">
                {renderInline(trimmed.replace(/^(tại sao|vì sao|tại sao:|\*\*tại sao:\*\*|\*\*tại sao\*\*)\s*/i, ''), true)}
              </div>
            </div>
          );
        }

        // 12. ĐOẠN VĂN THÔNG THƯỜNG
        return (
          <p key={idx} className="text-sm sm:text-[15px] text-slate-800 leading-relaxed my-1.5">
            {renderInline(block.raw, true)}
          </p>
        );
      })}
    </div>
  );
}
