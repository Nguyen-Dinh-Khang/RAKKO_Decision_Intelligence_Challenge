import React, { useState, useRef, useEffect } from 'react';
import { 
  Bot, Sparkles, Send, Store, PanelLeftClose, PanelLeft, 
  HelpCircle, CheckCircle2, XCircle, ArrowRight, ArrowDown, Layers, 
  ShieldAlert, Cpu, RefreshCw, User, DollarSign, Users, Calendar,
  TrendingUp, MapPin, Tag, ShieldCheck, BookOpen, BookmarkCheck, Bookmark
} from 'lucide-react';
import FormattedMarkdown from './FormattedMarkdown';
import TacticalPlaybookModal from './TacticalPlaybookModal';

/**
 * TacticalCopilot - Giao diện 2: Trợ lý Chiến thuật Đồng hành (Day 1 - 365)
 * Cố vấn tác chiến, giải quyết sự cố, cạnh tranh và chẩn đoán hiệu quả kinh doanh
 */
export default function TacticalCopilot({ metadata, currentUser, savedStrategy, llmConfig }) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [chatInput, setChatInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  const userScrolledUpRef = useRef(false);
  const [showScrollBottomBtn, setShowScrollBottomBtn] = useState(false);

  // Sổ tay tác chiến (Tactical Playbook)
  const [isPlaybookOpen, setIsPlaybookOpen] = useState(false);
  const [savedPlaybookMap, setSavedPlaybookMap] = useState({});
  const [savingPlaybookId, setSavingPlaybookId] = useState(null);
  const [pendingTasksCount, setPendingTasksCount] = useState(0);

  // Lấy thống kê nhiệm vụ chưa làm từ Sổ tay tác chiến
  const fetchPlaybookStats = async () => {
    try {
      const token = localStorage.getItem('mlai_user_token');
      const headers = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch('/api/copilot/playbook/entries', { headers });
      if (res.ok) {
        const data = await res.json();
        const pending = (data.total_tasks || 0) - (data.total_completed || 0);
        setPendingTasksCount(Math.max(0, pending));
      }
    } catch (err) {
      console.warn('Không thể tải thống kê sổ tay tác chiến:', err);
    }
  };

  useEffect(() => {
    fetchPlaybookStats();
  }, [currentUser]);

  // Lưu kế sách vào Sổ tay tác chiến
  const handleSaveToPlaybook = async (msg) => {
    try {
      const token = localStorage.getItem('mlai_user_token');
      if (!token) {
        alert('Vui lòng đăng nhập để lưu vào Sổ tay tác chiến!');
        return;
      }
      setSavingPlaybookId(msg.id);
      
      const userQuery = msg.routerData?.query || messages.slice().reverse().find(m => m.sender === 'user')?.text || 'Câu hỏi tình huống';
      const payload = {
        query: userQuery,
        branch_id: msg.routerData?.branch || 'BRANCH_UNKNOWN',
        branch_name: msg.routerData?.branch_name || 'Tác chiến vận hành',
        model_name: modelName,
        strategy_id: savedStrategy?._id || null,
        answer_markdown: msg.answer
      };

      const res = await fetch('/api/copilot/playbook/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        setSavedPlaybookMap(prev => ({ ...prev, [msg.id]: true }));
        await fetchPlaybookStats();
      } else {
        const errData = await res.json().catch(() => ({}));
        alert(errData.detail || 'Lỗi khi lưu kế sách');
      }
    } catch (err) {
      console.error('Lỗi lưu sổ tay:', err);
      alert('Không thể kết nối đến máy chủ để lưu kế sách!');
    } finally {
      setSavingPlaybookId(null);
    }
  };

  // Lấy thông tin cơ bản từ kế sách quán đã lưu & Profile người dùng
  const modelName = savedStrategy?.model_name || savedStrategy?.business_model_name || 'Chưa thiết lập mô hình';
  const address = savedStrategy?.address || 'Cổng ĐH Bách Khoa, Tô Hiến Thành, Q10';
  const productNames = savedStrategy?.product_names?.join(', ') || 'Chưa thiết lập sản phẩm/dịch vụ';

  const profile = savedStrategy?.profile || {};
  const simulationProfile = savedStrategy?.simulation_profile || {};
  const monthlyLogs = savedStrategy?.monthly_logs || [];
  const latestLog = monthlyLogs.length > 0 ? monthlyLogs[monthlyLogs.length - 1] : null;

  // Tên hiển thị các phân khúc khách hàng
  const displaySegments = (() => {
    const rawNames = profile.customer_segments || savedStrategy?.customer_segments;
    if (Array.isArray(rawNames) && rawNames.length > 0) return rawNames.join(', ');
    const rawIds = profile.customer_segment_ids || savedStrategy?.customer_segment_ids || [];
    if (Array.isArray(rawIds) && rawIds.length > 0) {
      return rawIds.map(id => {
        const found = metadata?.customer_segments?.find(s => s.id === id);
        return found ? found.name : `Nhóm ${id}`;
      }).join(', ');
    }
    return 'Chưa xác định';
  })();

  // Danh mục 5 kịch bản gợi ý đại diện cho 5 nhánh tư duy từ Mục 1.2
  const samplePrompts = [
    { 
      tag: "Nhóm A", 
      branchId: "BRANCH_A",
      title: "Hỏi Kinh nghiệm Thuần túy", 
      text: "Cho tôi một số kinh nghiệm chọn thịt bò tươi buổi sáng" 
    },
    { 
      tag: "Nhóm B", 
      branchId: "BRANCH_B",
      title: "Gỡ rối Sự cố Nội bộ", 
      text: "Khách than đợi bánh mì lâu quá bỏ đi" 
    },
    { 
      tag: "Nhóm C", 
      branchId: "BRANCH_C",
      title: "Giả định Chiến lược (What-If)", 
      text: "Nếu tôi hạ giá 15% thì sao?" 
    },
    { 
      tag: "Nhóm D", 
      branchId: "BRANCH_D",
      title: "Phản công Cạnh tranh Vi mô", 
      text: "Quán đối diện đông quá, làm sao kéo khách họ sang?" 
    },
    { 
      tag: "Nhóm E", 
      branchId: "BRANCH_E",
      title: "Chẩn đoán Bệnh kinh doanh", 
      text: "Dạo này doanh thu vẫn vậy mà cuối tháng không thấy tiền dư đâu cả?" 
    }
  ];

  // Khởi tạo tin nhắn chào ban đầu
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'bot',
      isWelcome: true,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    }
  ]);

  // Cuộn xuống tin nhắn mới nhất
  const scrollToBottom = (behavior = 'auto') => {
    if (chatContainerRef.current) {
      chatContainerRef.current.scrollTo({
        top: chatContainerRef.current.scrollHeight,
        behavior: behavior
      });
    }
    userScrolledUpRef.current = false;
    setShowScrollBottomBtn(false);
  };

  // Lắng nghe sự kiện cuộn của user: nếu user chủ động cuộn lên trên để đọc thì dừng auto-scroll
  const handleScroll = (e) => {
    const { scrollTop, scrollHeight, clientHeight } = e.currentTarget;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    // Nếu người dùng lướt lên cách đáy > 100px, ghi nhận để KHÔNG tự động giật xuống
    if (distanceFromBottom > 100) {
      userScrolledUpRef.current = true;
      setShowScrollBottomBtn(true);
    } else {
      userScrolledUpRef.current = false;
      setShowScrollBottomBtn(false);
    }
  };

  useEffect(() => {
    // Chỉ cuộn xuống đáy nếu người dùng KHÔNG chủ động cuộn lên trên để đọc
    if (!userScrolledUpRef.current && chatContainerRef.current) {
      chatContainerRef.current.scrollTop = chatContainerRef.current.scrollHeight;
    }
  }, [messages]);

  // Cấu hình giao diện màu sắc cho 5 nhánh
  const getBranchStyle = (branchId) => {
    switch (branchId) {
      case 'BRANCH_A':
        return {
          bg: 'bg-amber-50',
          border: 'border-amber-200',
          text: 'text-amber-800',
          badge: 'bg-amber-100 text-amber-800 border-amber-300',
          barColor: 'bg-amber-500',
          dot: 'bg-amber-500'
        };
      case 'BRANCH_B':
        return {
          bg: 'bg-rose-50',
          border: 'border-rose-200',
          text: 'text-rose-800',
          badge: 'bg-rose-100 text-rose-800 border-rose-300',
          barColor: 'bg-rose-500',
          dot: 'bg-rose-500'
        };
      case 'BRANCH_C':
        return {
          bg: 'bg-blue-50',
          border: 'border-blue-200',
          text: 'text-blue-800',
          badge: 'bg-blue-100 text-blue-800 border-blue-300',
          barColor: 'bg-blue-500',
          dot: 'bg-blue-500'
        };
      case 'BRANCH_D':
        return {
          bg: 'bg-purple-50',
          border: 'border-purple-200',
          text: 'text-purple-800',
          badge: 'bg-purple-100 text-purple-800 border-purple-300',
          barColor: 'bg-purple-500',
          dot: 'bg-purple-500'
        };
      case 'BRANCH_E':
        return {
          bg: 'bg-emerald-50',
          border: 'border-emerald-200',
          text: 'text-emerald-800',
          badge: 'bg-emerald-100 text-emerald-800 border-emerald-300',
          barColor: 'bg-emerald-500',
          dot: 'bg-emerald-500'
        };
      default:
        return {
          bg: 'bg-slate-50',
          border: 'border-slate-200',
          text: 'text-slate-800',
          badge: 'bg-slate-100 text-slate-800 border-slate-300',
          barColor: 'bg-indigo-500',
          dot: 'bg-indigo-500'
        };
    }
  };

  // Gửi prompt sang backend để kích hoạt Bộ định tuyến BGE & Streaming LLM
  const handleSendMessage = async (textToSend) => {
    const query = (textToSend || chatInput).trim();
    if (!query || isLoading) return;

    const userMsgId = Date.now().toString();
    const nowTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

    // 1. Thêm tin nhắn của User vào danh sách
    setMessages((prev) => [
      ...prev,
      {
        id: userMsgId,
        sender: 'user',
        text: query,
        timestamp: nowTime
      }
    ]);

    setChatInput('');
    setIsLoading(true);
    userScrolledUpRef.current = false;
    setShowScrollBottomBtn(false);
    setTimeout(() => {
      scrollToBottom('smooth');
    }, 50);

    const botMsgId = (Date.now() + 1).toString();
    // Tạo sẵn bubble của Bot với trạng thái isStreaming = true
    setMessages((prev) => [
      ...prev,
      {
        id: botMsgId,
        sender: 'bot',
        routerData: null,
        answer: '',
        isStreaming: true,
        timestamp: nowTime
      }
    ]);

    try {
      const token = localStorage.getItem('mlai_user_token');
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers['Authorization'] = `Bearer ${token}`;

      // Xây dựng lịch sử hội thoại gần nhất (tối đa 6 lượt)
      const convHistory = messages
        .filter((m) => !m.isWelcome && !m.isError)
        .map((m) => ({
          role: m.sender === 'user' ? 'user' : 'assistant',
          content: m.sender === 'user' ? m.text : (m.answer || m.routerData?.query || '')
        }))
        .filter((m) => m.content)
        .slice(-6);

      // Gọi API sang FastAPI Backend qua kênh SSE Streaming
      const res = await fetch('/api/copilot/chat/stream', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          query,
          model_id: savedStrategy?.model_id || 105,
          address: savedStrategy?.address || address,
          coordinates: savedStrategy?.coordinates,
          product_ids: savedStrategy?.product_ids || [],
          customer_segment_ids: savedStrategy?.customer_segment_ids || (savedStrategy?.profile?.customer_segment_ids || []),
          conversation_history: convHistory,
          llm_config: llmConfig
        })
      });

      if (!res.ok) {
        let errMessage = `Mã lỗi máy chủ: ${res.status}`;
        try {
          const errData = await res.json();
          errMessage = errData.detail || errMessage;
        } catch {
          // ignore
        }
        throw new Error(errMessage);
      }

      if (!res.body) {
        throw new Error('Trình duyệt không hỗ trợ đọc luồng dữ liệu SSE (ReadableStream)');
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data:')) continue;
          const jsonStr = trimmed.slice(5).trim();
          if (!jsonStr) continue;

          try {
            const parsed = JSON.parse(jsonStr);

            if (parsed.type === 'metadata') {
              // PHA 1: NHẬN NGAY LẬP TỨC METADATA ĐỊNH TUYẾN 5 NHÁNH
              setIsLoading(false);
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === botMsgId
                    ? { ...m, routerData: parsed, isStreaming: true }
                    : m
                )
              );
            } else if (parsed.type === 'chunk') {
              // PHA 2: STREAMING TỪNG TỪ CỦA LLM QWEN3.5
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === botMsgId
                    ? { ...m, answer: (m.answer || '') + (parsed.text || ''), isStreaming: true }
                    : m
                )
              );
            } else if (parsed.type === 'done') {
              // HOÀN TẤT STREAM
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === botMsgId
                    ? { ...m, isStreaming: false }
                    : m
                )
              );
            }
          } catch (parseErr) {
            console.warn('Lỗi phân tích SSE packet trong Copilot:', parseErr, jsonStr);
          }
        }
      }
    } catch (err) {
      console.error('Lỗi khi streaming Copilot:', err);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === botMsgId
            ? {
                ...m,
                isError: true,
                isStreaming: false,
                errorText: `Không thể kết nối đến trợ lý AI: ${err.message}`
              }
            : m
        )
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  return (
    <div className="flex h-full w-full bg-slate-100 overflow-hidden relative font-sans text-slate-800">
      
      {/* ========================================================================= */}
      {/* 1. CỘT BÊN TRÁI: NGỮ CẢNH QUÁN & TÌNH HUỐNG MẪU 5 NHÁNH                  */}
      {/* ========================================================================= */}
      <aside 
        className={`${
          isSidebarOpen ? 'translate-x-0 w-80 lg:w-[330px]' : '-translate-x-full w-0 md:w-0'
        } fixed md:relative z-30 inset-y-0 left-0 bg-white border-r border-slate-200 flex flex-col h-full transition-all duration-300 ease-in-out shrink-0 shadow-lg md:shadow-none overflow-hidden`}
      >
        {/* Header Sidebar */}
        <div className="p-4 border-b border-slate-200 flex items-center justify-between gap-2 shrink-0 bg-slate-50">
          <div className="flex items-center space-x-2.5">
            <div className="w-8 h-8 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-sm">
              <User className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-xs sm:text-sm text-slate-900 leading-tight">
                Hồ Sơ Cơ Sở Kinh Doanh
              </h3>
              <p className="text-[10px] text-slate-500">
                Ngữ cảnh thực tế đồng hành
              </p>
            </div>
          </div>

          <button
            type="button"
            onClick={() => setIsSidebarOpen(false)}
            className="md:hidden p-1.5 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        </div>

        {/* Nội dung Sidebar: Profile User */}
        <div className="flex-1 overflow-y-auto p-4 space-y-3.5 text-xs">
          
          {/* 1. Thẻ Tài khoản Người dùng */}
          <div className="bg-gradient-to-br from-indigo-50/80 via-white to-slate-50 rounded-2xl border border-indigo-100 p-3.5 shadow-2xs space-y-2">
            <div className="flex items-center space-x-2.5">
              <div className="w-9 h-9 rounded-full bg-indigo-600 text-white font-extrabold flex items-center justify-center text-sm shadow-sm">
                {(currentUser?.full_name?.[0] || currentUser?.username?.[0] || 'U').toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-bold text-slate-900 truncate text-xs sm:text-sm">
                  {currentUser?.full_name || currentUser?.username || 'Khách Vãng Lai'}
                </div>
                <div className="text-[10px] text-slate-500 flex items-center space-x-1">
                  <span>{currentUser ? `@${currentUser.username}` : 'Chưa đăng nhập'}</span>
                </div>
              </div>
              <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                currentUser ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-500'
              }`}>
                {currentUser ? 'Đã liên kết' : 'Khách'}
              </span>
            </div>
          </div>

          {/* 2. Thẻ Thông tin Cơ sở Kinh doanh */}
          <div className="bg-slate-50 rounded-2xl border border-slate-200 p-3.5 space-y-2.5">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-200/80">
              <span className="font-bold text-slate-800 text-[11px] uppercase tracking-wider flex items-center space-x-1.5">
                <Store className="w-3.5 h-3.5 text-indigo-600" />
                <span>Cơ Sở Kinh Doanh</span>
              </span>
              <span className="text-[10px] text-indigo-600 font-semibold bg-indigo-50 px-1.5 py-0.5 rounded">
                {savedStrategy ? 'Đang kích hoạt' : 'Mặc định'}
              </span>
            </div>

            <div className="space-y-2 text-[11px]">
              <div>
                <span className="text-slate-400 block text-[10px]">Mô hình:</span>
                <span className="font-bold text-slate-800 text-xs">{modelName}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Sản phẩm chính:</span>
                <span className="font-semibold text-slate-700">{productNames}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px]">Địa chỉ cơ sở:</span>
                <span className="text-slate-600 line-clamp-2" title={address}>
                  {address}
                </span>
              </div>
            </div>
          </div>

          {/* 3. Thẻ Định Phí & Vận Hành Thực Tế */}
          <div className="bg-slate-50 rounded-2xl border border-slate-200 p-3.5 space-y-2.5">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-200/80">
              <span className="font-bold text-slate-800 text-[11px] uppercase tracking-wider flex items-center space-x-1.5">
                <DollarSign className="w-3.5 h-3.5 text-emerald-600" />
                <span>Định Phí & Vận Hành</span>
              </span>
              {profile.month_set && (
                <span className="text-[10px] text-slate-400 font-mono">
                  {profile.month_set}
                </span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="bg-white p-2 rounded-xl border border-slate-200/80">
                <span className="text-slate-400 block text-[10px]">Vốn dự phòng:</span>
                <span className="font-bold text-slate-800">
                  {profile.budget ? `${(Number(profile.budget) / 1e6).toFixed(0)}Tr` : (savedStrategy?.budget ? `${(Number(savedStrategy.budget) / 1e6).toFixed(0)}Tr` : '—')}
                </span>
              </div>
              <div className="bg-white p-2 rounded-xl border border-slate-200/80">
                <span className="text-slate-400 block text-[10px]">Tiền thuê/tháng:</span>
                <span className="font-bold text-slate-800">
                  {profile.rent ? `${(Number(profile.rent) / 1e6).toFixed(1)}Tr` : (savedStrategy?.rent ? `${(Number(savedStrategy.rent) / 1e6).toFixed(1)}Tr` : '—')}
                </span>
              </div>
              <div className="bg-white p-2 rounded-xl border border-slate-200/80">
                <span className="text-slate-400 block text-[10px]">Nhân sự:</span>
                <span className="font-bold text-slate-800">
                  {(profile.staff_count !== undefined && profile.staff_count !== null) ? (profile.staff_count > 0 ? `${profile.staff_count} người` : '0 người') : '—'}
                </span>
              </div>
              <div className="bg-white p-2 rounded-xl border border-slate-200/80">
                <span className="text-slate-400 block text-[10px]">Lương TB:</span>
                <span className="font-bold text-slate-800">
                  {profile.avg_salary ? `${(Number(profile.avg_salary) / 1e6).toFixed(1)}Tr` : '—'}
                </span>
              </div>
            </div>

            <div className="pt-1">
              <span className="text-slate-400 block text-[10px]">Tệp khách hàng mục tiêu:</span>
              <span className="font-semibold text-slate-700 text-[11px]">{displaySegments}</span>
            </div>
          </div>

          {/* 4. Thẻ Sổ Sách Tháng Gần Nhất */}
          <div className="bg-slate-50 rounded-2xl border border-slate-200 p-3.5 space-y-2">
            <div className="flex items-center justify-between pb-1.5 border-b border-slate-200/80">
              <span className="font-bold text-slate-800 text-[11px] uppercase tracking-wider flex items-center space-x-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-blue-600" />
                <span>Sổ Sách Gần Nhất</span>
              </span>
              {latestLog && (
                <span className="text-[10px] text-blue-600 font-semibold bg-blue-50 px-1.5 py-0.5 rounded">
                  {latestLog.month}
                </span>
              )}
            </div>

            {latestLog ? (
              <div className="space-y-1.5 text-[11px]">
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Doanh thu:</span>
                  <span className="font-bold text-slate-800">{Number(latestLog.revenue).toLocaleString('vi-VN')} đ</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Lợi nhuận:</span>
                  <span className={`font-bold ${latestLog.profit >= 0 ? 'text-emerald-700' : 'text-rose-600'}`}>
                    {Number(latestLog.profit).toLocaleString('vi-VN')} đ
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500">Biên lợi nhuận:</span>
                  <span className="font-semibold text-indigo-700 font-mono">
                    {latestLog.margin_pct ? `${Number(latestLog.margin_pct).toFixed(1)}%` : '—'}
                  </span>
                </div>
              </div>
            ) : (
              <p className="text-[11px] text-slate-400 italic">
                Chưa có dữ liệu sổ sách tháng. Bạn có thể cập nhật ở mục Hồ Sơ & Sổ Sách.
              </p>
            )}
          </div>

          {!savedStrategy && (
            <div className="p-3 bg-amber-50 rounded-xl border border-amber-200 text-amber-800 text-[11px] space-y-1">
              <span className="font-bold block">💡 Gợi ý cho bạn:</span>
              <p className="text-[10px] leading-relaxed">
                Hãy thẩm định ý tưởng ở Tab 1 và bấm "Lưu & Áp Dụng Kế Sách" để đồng bộ hồ sơ cơ sở vào Copilot.
              </p>
            </div>
          )}

        </div>
      </aside>

      {/* ========================================================================= */}
      {/* 2. KHU VỰC CHÍNH: KHUNG CHAT TRỰC QUAN GIAO DIỆN 2                         */}
      {/* ========================================================================= */}
      <main className="flex-1 flex flex-col h-full bg-slate-50 overflow-hidden relative">
        
        {/* Header Giao diện 2 */}
        <header className="h-14 bg-white border-b border-slate-200 px-4 flex items-center justify-between shrink-0 shadow-2xs">
          <div className="flex items-center space-x-3">
            {!isSidebarOpen && (
              <button
                type="button"
                onClick={() => setIsSidebarOpen(true)}
                className="p-1.5 text-slate-500 hover:text-slate-800 rounded-lg hover:bg-slate-100 transition cursor-pointer"
                title="Mở hồ sơ cơ sở"
              >
                <PanelLeft className="w-4 h-4" />
              </button>
            )}
            <div className="w-8 h-8 rounded-xl bg-indigo-50 border border-indigo-200 flex items-center justify-center text-indigo-600">
              <Bot className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900 leading-tight flex items-center gap-2">
                <span>Trợ lý Chiến thuật Đồng hành</span>
                <span className="text-[10px] px-2.5 py-0.5 rounded-full font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  <span>Đang hoạt động</span>
                </span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Tư vấn Tác chiến & Xử lý Tình huống Vận hành Thực tế
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {/* Nút mở Sổ tay tác chiến */}
            <button
              type="button"
              onClick={() => setIsPlaybookOpen(true)}
              className="px-3 py-1.5 rounded-xl bg-gradient-to-r from-indigo-50 to-purple-50 hover:from-indigo-100 hover:to-purple-100 text-indigo-800 border border-indigo-200 text-xs font-bold flex items-center space-x-1.5 transition shadow-2xs cursor-pointer"
              title="Mở Sổ tay tác chiến & Bảng checklist"
            >
              <BookOpen className="w-3.5 h-3.5 text-indigo-600" />
              <span>Sổ Tay Tác Chiến</span>
              {pendingTasksCount > 0 ? (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-amber-500 text-white font-extrabold animate-pulse">
                  {pendingTasksCount}
                </span>
              ) : (
                <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-indigo-100 text-indigo-700 font-extrabold">
                  ✓
                </span>
              )}
            </button>

            <button
              type="button"
              onClick={() => {
                setMessages([
                  {
                    id: 'welcome',
                    sender: 'bot',
                    isWelcome: true,
                    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
                  }
                ]);
              }}
              className="p-2 text-slate-400 hover:text-slate-600 rounded-lg hover:bg-slate-100 transition cursor-pointer"
              title="Làm mới cuộc trò chuyện"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <span className="text-xs font-semibold text-slate-600 bg-slate-100 px-3 py-1 rounded-lg">
              {currentUser ? `User: ${currentUser.username}` : 'Chế độ Khách'}
            </span>
          </div>
        </header>

        {/* Khung Canvas Tin nhắn (Chat Canvas) */}
        <div 
          ref={chatContainerRef}
          onScroll={handleScroll}
          className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4 relative"
        >
          <div className="max-w-3xl mx-auto space-y-4">
            
            {messages.map((msg) => {
              // 1. Thẻ Chào mừng Ban đầu
              if (msg.isWelcome) {
                return (
                  <div key={msg.id} className="bg-white rounded-2xl border border-slate-200 p-5 sm:p-6 shadow-xs space-y-4">
                    <div className="flex items-center space-x-2 text-indigo-600 font-bold text-sm sm:text-base">
                      <Sparkles className="w-5 h-5" />
                      <span>Chào bạn! Trợ lý Chiến thuật Đồng hành đã sẵn sàng</span>
                    </div>
                    <p className="text-xs sm:text-sm text-slate-600 leading-relaxed">
                      Tôi đồng hành cùng bạn trong suốt quá trình vận hành kinh doanh. Khi gặp bất kỳ khó khăn nào về khách hàng, đối thủ xung quanh, nhân sự hay tài chính, hãy đặt câu hỏi để nhận ngay <strong>kế sách tác chiến cụ thể trong 24h kèm lời thoại thực tế</strong>:
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 text-xs sm:text-sm">
                      <div className="p-3 rounded-xl border border-amber-200 bg-amber-50/70 space-y-1">
                        <span className="font-bold text-amber-900 block text-xs sm:text-sm">💡 Kinh nghiệm & Kỹ thuật nghề</span>
                        <span className="text-xs text-amber-800">Chọn nguyên vật liệu, kiểm soát hao hụt, tiêu chuẩn chất lượng sản phẩm/dịch vụ</span>
                      </div>
                      <div className="p-3 rounded-xl border border-rose-200 bg-rose-50/70 space-y-1">
                        <span className="font-bold text-rose-900 block text-xs sm:text-sm">🚨 Gỡ rối Sự cố Vận hành</span>
                        <span className="text-xs text-rose-800">Khách phàn nàn, nhân viên nghỉ đột xuất, chậm tiến độ phục vụ/giao hàng</span>
                      </div>
                      <div className="p-3 rounded-xl border border-blue-200 bg-blue-50/70 space-y-1">
                        <span className="font-bold text-blue-900 block text-xs sm:text-sm">⚖️ Đánh giá Quyết định (What-If)</span>
                        <span className="text-xs text-blue-800">Giả định tăng/hạ giá, mở thêm sản phẩm/dịch vụ mới, đổi giờ mở cửa</span>
                      </div>
                      <div className="p-3 rounded-xl border border-purple-200 bg-purple-50/70 space-y-1">
                        <span className="font-bold text-purple-900 block text-xs sm:text-sm">🎯 Đối phó Cạnh tranh</span>
                        <span className="text-xs text-purple-800">Đối thủ mở sát vách, phá giá giành khách, giữ chân khách quen</span>
                      </div>
                      <div className="p-3 rounded-xl border border-emerald-200 bg-emerald-50/70 sm:col-span-2 space-y-1">
                        <span className="font-bold text-emerald-900 block text-xs sm:text-sm">🩺 Chẩn đoán Sức khỏe Doanh thu</span>
                        <span className="text-xs text-emerald-800">Đông khách mà không thấy tiền dư, doanh thu chững lại, tìm lỗ rò rỉ dòng tiền</span>
                      </div>
                    </div>

                    <p className="text-xs text-slate-400 italic">
                      👉 Nhập câu hỏi hoặc tình huống kinh doanh vào ô bên dưới để bắt đầu tham vấn!
                    </p>
                  </div>
                );
              }

              // 2. Tin nhắn của Người dùng (Zoom kích thước chữ)
              if (msg.sender === 'user') {
                return (
                  <div key={msg.id} className="flex justify-end items-start space-x-2.5">
                    <div className="bg-indigo-600 text-white rounded-2xl rounded-tr-xs px-4 py-3 max-w-xl shadow-xs">
                      <p className="text-sm sm:text-base font-medium leading-relaxed whitespace-pre-wrap">
                        {msg.text}
                      </p>
                      <span className="text-[10px] text-indigo-200 block text-right mt-1">
                        {msg.timestamp}
                      </span>
                    </div>
                    <div className="w-8 h-8 rounded-full bg-indigo-100 border border-indigo-200 flex items-center justify-center text-indigo-600 shrink-0 mt-0.5 shadow-2xs">
                      <User className="w-4 h-4" />
                    </div>
                  </div>
                );
              }

              // 3. Tin nhắn Báo lỗi nếu có
              if (msg.isError) {
                return (
                  <div key={msg.id} className="flex justify-start items-start space-x-2.5">
                    <div className="w-8 h-8 rounded-full bg-rose-100 border border-rose-200 flex items-center justify-center text-rose-600 shrink-0 mt-0.5">
                      <ShieldAlert className="w-4 h-4" />
                    </div>
                    <div className="bg-rose-50 border border-rose-200 text-rose-800 rounded-2xl rounded-tl-xs p-3.5 max-w-lg text-xs sm:text-sm space-y-1">
                      <span className="font-bold block">Đã có lỗi xảy ra</span>
                      <p>{msg.errorText}</p>
                    </div>
                  </div>
                );
              }

              // 4. Nếu Bot đang đợi tính toán (chưa có routerData):
              if (!msg.routerData) {
                return (
                  <div key={msg.id} className="flex justify-start items-start space-x-2.5">
                    <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-2xs">
                      <Cpu className="w-4 h-4 animate-spin" />
                    </div>
                    <div className="bg-white rounded-2xl rounded-tl-xs border border-slate-200 p-4 max-w-lg shadow-xs space-y-2 text-xs sm:text-sm">
                      <div className="flex items-center space-x-2.5 text-indigo-600">
                        <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                        <span className="font-semibold text-slate-700">Trợ lý đang phân tích tình huống & trích xuất bài học thực tế...</span>
                      </div>
                    </div>
                  </div>
                );
              }
              // 5. Phản hồi Chiến thuật Thực tế từ Bot
              return (
                <div key={msg.id} className="flex justify-start items-start space-x-2.5">
                  <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center shrink-0 mt-0.5 shadow-2xs">
                    <Cpu className="w-4 h-4" />
                  </div>

                  <div className="bg-white rounded-2xl rounded-tl-xs border border-slate-200 p-5 sm:p-6 max-w-3xl shadow-xs space-y-4 text-xs sm:text-sm w-full">

                    {/* Phản hồi Chiến thuật Thực tế từ AI (Streaming Token-by-Token) */}
                    {(msg.answer || msg.isStreaming) && (
                      <div className="pt-2 space-y-3">
                        <div className="flex items-center justify-between text-xs sm:text-sm font-bold text-slate-700">
                          <div className="flex items-center space-x-2 text-indigo-700">
                            <Sparkles className="w-4 h-4" />
                            <span>Tư vấn Chiến thuật Thực tế:</span>
                          </div>
                          {msg.isStreaming && (
                            <span className="text-xs text-indigo-600 bg-indigo-50 border border-indigo-200 px-3 py-1 rounded-full flex items-center space-x-1.5 animate-pulse">
                              <span className="w-1.5 h-1.5 rounded-full bg-indigo-600 animate-ping"></span>
                              <span>AI đang gõ từng chữ...</span>
                            </span>
                          )}
                        </div>

                        {msg.answer ? (
                          <div className="text-slate-800 leading-relaxed text-sm sm:text-[15px]">
                            <FormattedMarkdown content={msg.answer} />
                            {msg.isStreaming && (
                              <span className="inline-block w-2 h-4 ml-1 bg-indigo-600 animate-pulse align-middle" />
                            )}
                          </div>
                        ) : (
                          <div className="flex items-center space-x-2 text-slate-400 italic text-xs py-2">
                            <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                            <span>Trợ lý đang lập kịch bản hành động tác chiến thực tế...</span>
                          </div>
                        )}
                      </div>
                    )}

                    <div className="text-[11px] text-slate-400 pt-2 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-t border-slate-100">
                      <div className="flex items-center space-x-2 flex-wrap gap-y-1">
                        <span>✓ Kế sách tác chiến đã đối soát thực tế</span>
                        {msg.answer && !msg.isStreaming && (
                          <button
                            type="button"
                            onClick={() => handleSaveToPlaybook(msg)}
                            disabled={savedPlaybookMap[msg.id] || savingPlaybookId === msg.id}
                            className={`inline-flex items-center space-x-1 px-2.5 py-1 rounded-lg text-xs font-bold transition cursor-pointer ${
                              savedPlaybookMap[msg.id]
                                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                : 'bg-indigo-50 text-indigo-700 hover:bg-indigo-100 border border-indigo-200 shadow-2xs hover:shadow-xs'
                            }`}
                          >
                            {savedPlaybookMap[msg.id] ? (
                              <>
                                <BookmarkCheck className="w-3.5 h-3.5 text-emerald-600" />
                                <span>Đã lưu vào Sổ tay</span>
                              </>
                            ) : savingPlaybookId === msg.id ? (
                              <>
                                <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                                <span>Đang lưu...</span>
                              </>
                            ) : (
                              <>
                                <Bookmark className="w-3.5 h-3.5" />
                                <span>Lưu vào Sổ tay</span>
                              </>
                            )}
                          </button>
                        )}
                      </div>
                      <span>{msg.timestamp}</span>
                    </div>

                  </div>
                </div>
              );
            })}

            {/* Hiệu ứng Đang tải / Đang tính toán */}
            {isLoading && (
              <div className="flex justify-start items-center space-x-2.5 text-xs text-slate-500 p-2">
                <div className="w-6 h-6 rounded-full bg-indigo-100 border border-indigo-200 flex items-center justify-center text-indigo-600 animate-spin">
                  <RefreshCw className="w-3.5 h-3.5" />
                </div>
                <span className="italic">
                  Trợ lý đang phân tích tình huống & lên kịch bản tác chiến...
                </span>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Nút nổi hỗ trợ người dùng cuộn nhanh xuống đáy khi đang lướt đọc ở trên */}
          {showScrollBottomBtn && (
            <button
              type="button"
              onClick={() => scrollToBottom('smooth')}
              className="sticky bottom-4 ml-auto mr-4 z-20 bg-indigo-600 hover:bg-indigo-700 text-white shadow-lg px-3.5 py-2 rounded-full text-xs font-bold flex items-center space-x-1.5 transition cursor-pointer"
            >
              <ArrowDown className="w-3.5 h-3.5" />
              <span>Cuộn xuống mới nhất</span>
            </button>
          )}
        </div>

        {/* Khung nhập liệu bên dưới (Sticky Bottom Input Bar - Zoom kích thước) */}
        <div className="p-3.5 sm:p-4 bg-white border-t border-slate-200 shrink-0">
          <div className="max-w-3xl mx-auto">
            <div className="flex items-center space-x-3 bg-slate-50 border border-slate-300 hover:border-slate-400 rounded-2xl p-2 sm:p-2.5 shadow-xs focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-100 focus-within:bg-white transition">
              <input
                type="text"
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Nhập câu hỏi hoặc tình huống kinh doanh để nhận cố vấn tác chiến..."
                className="flex-1 bg-transparent text-sm sm:text-base py-1 px-2.5 outline-none text-slate-800 placeholder:text-slate-400 font-medium"
                disabled={isLoading || messages.some((m) => m.isStreaming)}
              />
              <button
                type="button"
                onClick={() => handleSendMessage()}
                disabled={!chatInput.trim() || isLoading || messages.some((m) => m.isStreaming)}
                className="px-4 py-2 sm:px-5 sm:py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-300 text-white font-bold rounded-xl text-xs sm:text-sm transition flex items-center space-x-1.5 cursor-pointer shrink-0 shadow-sm"
              >
                <span>Gửi hỏi</span>
                <Send className="w-4 h-4" />
              </button>
            </div>
            {/* DÒNG LƯU Ý PHÁP LÝ & QUYỀN TỰ QUYẾT */}
            <div className="mt-2 text-center text-[10px] text-slate-400 leading-normal max-w-2xl mx-auto">
              💡 <strong>Lưu ý</strong>: Trợ lý cung cấp chiến lược gợi ý dựa trên dữ liệu thực tế, quyền quyết định hoàn toàn thuộc về bạn. Các thủ tục hành chính, giấy tờ pháp lý không nằm trong phạm vi nhiệm vụ của hệ thống.
            </div>
          </div>
        </div>

      </main>

      {/* MODAL SỔ TAY TÁC CHIẾN & BẢNG CHECKLIST */}
      <TacticalPlaybookModal
        isOpen={isPlaybookOpen}
        onClose={() => setIsPlaybookOpen(false)}
        onTaskToggled={fetchPlaybookStats}
      />

    </div>
  );
}
