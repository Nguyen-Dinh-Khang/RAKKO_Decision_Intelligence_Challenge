import React, { useState, useEffect } from 'react';
import { 
  BookOpen, CheckSquare, Square, Trash2, X, ChevronDown, ChevronUp, 
  Sparkles, MessageCircle, Clock, Filter, AlertCircle, CheckCircle2, 
  Layers, ArrowRight, RefreshCw, ExternalLink
} from 'lucide-react';
import FormattedMarkdown, { renderInline } from './FormattedMarkdown';

export default function TacticalPlaybookModal({ isOpen, onClose, onTaskToggled }) {
  const [activeTab, setActiveTab] = useState('tasks'); // 'tasks' | 'entries'
  const [filterStatus, setFilterStatus] = useState('pending'); // 'all' | 'pending' | 'completed'
  const [playbooks, setPlaybooks] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [expandedEntryId, setExpandedEntryId] = useState(null);
  const [actionLoading, setActionLoading] = useState(null); // task_id or playbook_id

  // Tải dữ liệu Sổ tay tác chiến
  const fetchPlaybooks = async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem('mlai_user_token');
      const headers = {};
      if (token) headers.Authorization = `Bearer ${token}`;

      const res = await fetch('/api/copilot/playbook/entries', { headers });
      if (res.ok) {
        const data = await res.json();
        setPlaybooks(data.entries || []);
      }
    } catch (err) {
      console.error('Lỗi tải sổ tay tác chiến:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchPlaybooks();
    }
  }, [isOpen]);

  // Cập nhật trạng thái Task (Tick / Untick)
  const handleToggleTask = async (taskId, currentStatus) => {
    const nextStatus = !currentStatus;
    
    // Cập nhật lạc quan (Optimistic update)
    setPlaybooks(prev => prev.map(pb => {
      const hasTask = pb.tasks?.some(t => t.task_id === taskId);
      if (!hasTask) return pb;

      const updatedTasks = pb.tasks.map(t => {
        if (t.task_id === taskId) {
          return {
            ...t,
            is_completed: nextStatus,
            completed_at: nextStatus ? new Date().toISOString() : null
          };
        }
        return t;
      });

      return {
        ...pb,
        tasks: updatedTasks,
        completed_task_count: updatedTasks.filter(t => t.is_completed).length
      };
    }));

    if (onTaskToggled) onTaskToggled();

    // Gọi API nền
    try {
      const token = localStorage.getItem('mlai_user_token');
      const headers = { 'Content-Type': 'application/json' };
      if (token) headers.Authorization = `Bearer ${token}`;

      await fetch(`/api/copilot/playbook/tasks/${taskId}/toggle`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify({ is_completed: nextStatus })
      });
    } catch (err) {
      console.error('Lỗi cập nhật task:', err);
      // Revert nếu lỗi
      fetchPlaybooks();
    }
  };

  // Xóa Kế sách khỏi Sổ tay
  const handleDeletePlaybook = async (playbookId, e) => {
    e.stopPropagation();
    if (!window.confirm('Bạn có chắc chắn muốn xóa kế sách này khỏi Sổ tay tác chiến?')) return;

    setActionLoading(playbookId);
    try {
      const token = localStorage.getItem('mlai_user_token');
      const headers = {};
      if (token) headers.Authorization = `Bearer ${token}`;

      const res = await fetch(`/api/copilot/playbook/entries/${playbookId}`, {
        method: 'DELETE',
        headers
      });

      if (res.ok) {
        setPlaybooks(prev => prev.filter(pb => pb.playbook_id !== playbookId));
        if (onTaskToggled) onTaskToggled();
      }
    } catch (err) {
      console.error('Lỗi xóa kế sách:', err);
    } finally {
      setActionLoading(null);
    }
  };

  if (!isOpen) return null;

  // Trải phẳng (flat) toàn bộ danh sách tasks từ tất cả kế sách
  const allTasks = playbooks.flatMap(pb => 
    (pb.tasks || []).map(t => ({
      ...t,
      playbook_id: pb.playbook_id,
      situation_title: pb.title || pb.query,
      branch_name: pb.branch_name,
      branch_id: pb.branch_id
    }))
  );

  const totalTasks = allTasks.length;
  const completedTasks = allTasks.filter(t => t.is_completed).length;
  const pendingTasks = totalTasks - completedTasks;
  const progressPercent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;

  // Lọc tasks theo tab filter
  const filteredTasks = allTasks.filter(t => {
    if (filterStatus === 'pending') return !t.is_completed;
    if (filterStatus === 'completed') return t.is_completed;
    return true;
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-900/60 backdrop-blur-xs animate-fadeIn">
      <div 
        className="bg-white w-full max-w-4xl h-[90vh] rounded-3xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* 1. HEADER MODAL */}
        <div className="px-6 py-4 bg-gradient-to-r from-indigo-900 via-indigo-800 to-slate-900 text-white flex items-center justify-between shrink-0 shadow-sm">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-white/10 text-white border border-white/15">
              <BookOpen className="w-5 h-5 text-indigo-300" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="font-extrabold text-base sm:text-lg tracking-tight">
                  Sổ Tay Tác Chiến Vận Hành
                </h3>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-indigo-500/30 text-indigo-200 border border-indigo-400/30 uppercase tracking-wider">
                  Tactical Playbook
                </span>
              </div>
              <p className="text-xs text-indigo-200/80 font-normal mt-0.5">
                Kho kế sách thực chiến & Bảng kiểm soát đầu việc đã lưu từ Copilot
              </p>
            </div>
          </div>
          <button 
            type="button" 
            onClick={onClose}
            className="p-2 rounded-xl text-indigo-200 hover:text-white hover:bg-white/10 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* 2. THANH TIẾN ĐỘ & THANH TAB */}
        <div className="bg-slate-50 border-b border-slate-200 px-6 py-3 shrink-0 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          {/* Thanh Tiến Độ */}
          <div className="flex items-center space-x-3 flex-1 max-w-md">
            <div className="flex-1 bg-slate-200 rounded-full h-2.5 overflow-hidden">
              <div 
                className="bg-emerald-500 h-2.5 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${progressPercent}%` }}
              />
            </div>
            <span className="text-xs font-bold text-slate-700 whitespace-nowrap">
              {completedTasks}/{totalTasks} việc ({progressPercent}%)
            </span>
          </div>

          {/* Tab Navigation */}
          <div className="flex items-center space-x-1.5 bg-slate-200/80 p-1 rounded-xl self-start sm:self-auto">
            <button
              type="button"
              onClick={() => setActiveTab('tasks')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5 ${
                activeTab === 'tasks' 
                  ? 'bg-white text-indigo-900 shadow-xs' 
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <CheckSquare className="w-3.5 h-3.5" />
              <span>Nhiệm Vụ Checklist</span>
              {pendingTasks > 0 && (
                <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-amber-100 text-amber-800 font-extrabold">
                  {pendingTasks}
                </span>
              )}
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('entries')}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition flex items-center space-x-1.5 ${
                activeTab === 'entries' 
                  ? 'bg-white text-indigo-900 shadow-xs' 
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Kế Sách Đã Lưu</span>
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-slate-200 text-slate-700 font-extrabold">
                {playbooks.length}
              </span>
            </button>
          </div>
        </div>

        {/* 3. NỘI DUNG CUỘN CHÍNH */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {isLoading ? (
            <div className="flex flex-col items-center justify-center h-64 text-slate-400 space-y-3">
              <RefreshCw className="w-7 h-7 text-indigo-600 animate-spin" />
              <p className="text-xs font-medium">Đang tải dữ liệu Sổ tay tác chiến...</p>
            </div>
          ) : playbooks.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-slate-400 space-y-3 text-center p-6 border-2 border-dashed border-slate-200 rounded-2xl">
              <div className="p-3.5 rounded-2xl bg-indigo-50 text-indigo-600">
                <BookOpen className="w-8 h-8" />
              </div>
              <div className="space-y-1">
                <h4 className="font-bold text-slate-800 text-sm">Chưa có kế sách nào được lưu</h4>
                <p className="text-xs text-slate-500 max-w-sm">
                  Khi chat với Trợ lý Copilot, hãy bấm nút <strong>"🔖 Lưu vào Sổ tay"</strong> dưới mỗi câu trả lời để ghim các quy trình và checklist quan trọng vào đây.
                </p>
              </div>
            </div>
          ) : activeTab === 'tasks' ? (
            /* TAB 1: BẢNG CHECKLIST NHIỆM VỤ TỔNG HỢP */
            <div className="space-y-4">
              {/* Thanh lọc trạng thái */}
              <div className="flex items-center justify-between pb-2 border-b border-slate-100">
                <div className="flex items-center space-x-2">
                  <Filter className="w-3.5 h-3.5 text-slate-400" />
                  <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">Lọc nhiệm vụ:</span>
                </div>
                <div className="flex items-center space-x-1.5 text-xs">
                  <button
                    type="button"
                    onClick={() => setFilterStatus('pending')}
                    className={`px-2.5 py-1 rounded-md font-semibold transition ${
                      filterStatus === 'pending'
                        ? 'bg-amber-100 text-amber-900 border border-amber-300'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    Chưa làm ({pendingTasks})
                  </button>
                  <button
                    type="button"
                    onClick={() => setFilterStatus('completed')}
                    className={`px-2.5 py-1 rounded-md font-semibold transition ${
                      filterStatus === 'completed'
                        ? 'bg-emerald-100 text-emerald-900 border border-emerald-300'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    Đã xong ({completedTasks})
                  </button>
                  <button
                    type="button"
                    onClick={() => setFilterStatus('all')}
                    className={`px-2.5 py-1 rounded-md font-semibold transition ${
                      filterStatus === 'all'
                        ? 'bg-indigo-100 text-indigo-900 border border-indigo-300'
                        : 'text-slate-600 hover:bg-slate-100'
                    }`}
                  >
                    Tất cả ({totalTasks})
                  </button>
                </div>
              </div>

              {/* Danh sách Tasks */}
              {filteredTasks.length === 0 ? (
                <div className="py-12 text-center text-slate-400 text-xs">
                  Không có nhiệm vụ nào trong mục này.
                </div>
              ) : (
                <div className="space-y-2.5">
                  {filteredTasks.map((task) => (
                    <div
                      key={task.task_id}
                      onClick={() => handleToggleTask(task.task_id, task.is_completed)}
                      className={`p-3.5 rounded-2xl border transition-all cursor-pointer select-none flex items-start space-x-3 ${
                        task.is_completed
                          ? 'bg-slate-50 border-emerald-200/90 text-slate-500'
                          : 'bg-white hover:bg-slate-50/80 border-slate-200 text-slate-900 shadow-2xs hover:shadow-xs'
                      }`}
                    >
                      <button type="button" className="mt-0.5 shrink-0">
                        {task.is_completed ? (
                          <CheckSquare className="w-5 h-5 text-emerald-600" />
                        ) : (
                          <Square className="w-5 h-5 text-slate-400 hover:text-indigo-600" />
                        )}
                      </button>
                      <div className="flex-1 space-y-1">
                        <p className={`text-sm leading-relaxed font-medium ${
                          task.is_completed ? 'line-through text-slate-400' : 'text-slate-800'
                        }`}>
                          {renderInline(task.text, true)}
                        </p>
                        <div className="flex flex-wrap items-center gap-2 pt-0.5">
                          <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                            📌 {task.situation_title}
                          </span>
                          {task.branch_name && (
                            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100">
                              {task.branch_name}
                            </span>
                          )}
                          {task.completed_at && (
                            <span className="text-[10px] text-emerald-600 font-medium">
                              ✓ Xong lúc {new Date(task.completed_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            /* TAB 2: DANH SÁCH KẾ SÁCH ĐÃ LƯU */
            <div className="space-y-4">
              {playbooks.map((pb) => {
                const isExpanded = expandedEntryId === pb.playbook_id;
                const pbTasks = pb.tasks || [];
                const pbCompleted = pbTasks.filter(t => t.is_completed).length;

                return (
                  <div
                    key={pb.playbook_id}
                    className="bg-white rounded-2xl border border-slate-200/90 shadow-2xs overflow-hidden transition hover:border-indigo-200"
                  >
                    {/* Header Thẻ Kế Sách */}
                    <div 
                      onClick={() => setExpandedEntryId(isExpanded ? null : pb.playbook_id)}
                      className="p-4 sm:p-5 flex items-start justify-between gap-3 cursor-pointer select-none hover:bg-slate-50/60 transition"
                    >
                      <div className="space-y-1.5 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="text-[10px] font-extrabold px-2.5 py-0.5 rounded-full bg-indigo-100 text-indigo-900 uppercase tracking-wider">
                            {pb.branch_name || 'Tác chiến'}
                          </span>
                          <span className="text-[11px] text-slate-400">
                            {new Date(pb.created_at).toLocaleDateString('vi-VN')}
                          </span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md ${
                            pbCompleted === pbTasks.length && pbTasks.length > 0
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-amber-100 text-amber-800'
                          }`}>
                            {pbCompleted}/{pbTasks.length} nhiệm vụ
                          </span>
                        </div>
                        <h4 className="font-bold text-sm sm:text-base text-slate-900 leading-snug">
                          {pb.title}
                        </h4>
                        <p className="text-xs text-slate-500 italic">
                          "Câu hỏi: {pb.query}"
                        </p>
                      </div>

                      <div className="flex items-center space-x-1 shrink-0 pt-1">
                        <button
                          type="button"
                          onClick={(e) => handleDeletePlaybook(pb.playbook_id, e)}
                          title="Xóa kế sách này"
                          className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 hover:bg-rose-50 transition"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                        <div className="p-1.5 text-slate-400">
                          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                        </div>
                      </div>
                    </div>

                    {/* Lời Thoại Mẫu Nếu Có (Luôn hiển thị) */}
                    {pb.dialogue_script && (
                      <div className="mx-4 sm:mx-5 mb-3 p-3 rounded-xl bg-blue-50/70 border border-blue-200/80 flex items-start space-x-2 text-xs">
                        <MessageCircle className="w-4 h-4 text-blue-600 shrink-0 mt-0.5" />
                        <div className="text-slate-800 italic font-medium leading-relaxed">
                          💬 Lời thoại mẫu: "{pb.dialogue_script}"
                        </div>
                      </div>
                    )}

                    {/* Vùng Mở Rộng Chi Tiết Toàn Văn & Checklist Riêng */}
                    {isExpanded && (
                      <div className="p-4 sm:p-5 bg-slate-50/70 border-t border-slate-100 space-y-4">
                        {/* Checklist riêng của tình huống này */}
                        {pbTasks.length > 0 && (
                          <div className="space-y-2">
                            <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block">
                              Checklist Hành Động Gắn Với Tình Huống:
                            </span>
                            <div className="space-y-1.5">
                              {pbTasks.map(task => (
                                <div
                                  key={task.task_id}
                                  onClick={() => handleToggleTask(task.task_id, task.is_completed)}
                                  className={`p-2.5 rounded-xl border text-xs flex items-start space-x-2.5 cursor-pointer transition select-none ${
                                    task.is_completed 
                                      ? 'bg-slate-100 border-slate-200 text-slate-500 line-through' 
                                      : 'bg-white border-slate-200 text-slate-800 shadow-2xs'
                                  }`}
                                >
                                  <button type="button" className="mt-0.5 shrink-0">
                                    {task.is_completed ? (
                                      <CheckSquare className="w-3.5 h-3.5 text-emerald-600" />
                                    ) : (
                                      <Square className="w-3.5 h-3.5 text-slate-400 hover:text-indigo-600" />
                                    )}
                                  </button>
                                  <span className="flex-1 font-medium">{renderInline(task.text, true)}</span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Toàn văn Markdown phản hồi */}
                        <div className="space-y-2 pt-2 border-t border-slate-200/80">
                          <span className="text-[11px] font-bold text-slate-700 uppercase tracking-wider block">
                            Chi Tiết Toàn Văn Kế Sách Từ Copilot:
                          </span>
                          <div className="p-4 rounded-xl bg-white border border-slate-200 text-xs sm:text-sm">
                            <FormattedMarkdown content={pb.answer_markdown} />
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 4. FOOTER MODAL */}
        <div className="px-6 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500 shrink-0">
          <span>
            💡 Mẹo: Tick vào các đầu việc để ghi nhớ tiến độ thực hiện trong ca làm việc.
          </span>
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-slate-200 text-slate-700 font-bold hover:bg-slate-300 transition"
          >
            Đóng
          </button>
        </div>
      </div>
    </div>
  );
}
