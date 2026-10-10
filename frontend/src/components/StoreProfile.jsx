import React, { useState, useEffect } from 'react';
import { 
  Store, Plus, Trash2, Edit3, Save, X, DollarSign, 
  Calendar, TrendingUp, AlertCircle, ShieldCheck, 
  ArrowUpRight, ArrowDownRight, MapPin, CheckCircle2, BookmarkCheck, Users,
  ShoppingBag
} from 'lucide-react';

/**
 * StoreProfile - Giao diện Quản lý Hồ sơ Quán & Sổ sách Tài chính Đa tháng
 * Tách biệt hoàn toàn khỏi Giao diện 2 (Copilot), phục vụ quản trị dòng tiền:
 * 1. Hồ sơ Vốn & Tiền thuê hiện tại (profile)
 * 2. Thước đo Kế hoạch gốc ban đầu (simulation_profile)
 * 3. Nhật ký Sổ sách doanh thu & chi phí theo từng tháng (monthly_logs)
 */
export default function StoreProfile({ metadata, currentUser, savedStrategy, onStrategyUpdated }) {
  // Trạng thái Hồ sơ quán (Profile hiện tại)
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [budgetInput, setBudgetInput] = useState(0);
  const [rentInput, setRentInput] = useState(0);
  const [staffCountInput, setStaffCountInput] = useState(0);
  const [avgSalaryInput, setAvgSalaryInput] = useState(0);
  const [selectedSegments, setSelectedSegments] = useState([]);
  const [monthSetInput, setMonthSetInput] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);

  // Danh mục phân khúc khách hàng chuẩn hóa
  const defaultSegments = [
    { id: 301, name: "18 - 24 tuổi" },
    { id: 302, name: "25 - 34 tuổi" },
    { id: 303, name: "35 - 50 tuổi" },
    { id: 304, name: "trên 50 tuổi" }
  ];
  const availableSegments = (metadata?.customer_segments && metadata.customer_segments.length > 0)
    ? metadata.customer_segments
    : defaultSegments;

  // Trạng thái Ghi nhận Sổ sách tháng (Monthly Log Modal)
  const [showLogModal, setShowLogModal] = useState(false);
  const [logMonth, setLogMonth] = useState('');
  const [logRevenue, setLogRevenue] = useState('');
  const [logCost, setLogCost] = useState('');
  const [logNote, setLogNote] = useState('');
  const [savingLog, setSavingLog] = useState(false);
  const [logError, setLogError] = useState('');

  // Dữ liệu an toàn từ savedStrategy
  const profile = savedStrategy?.profile || {
    budget: 0,
    rent: 0,
    staff_count: 0,
    avg_salary: 0,
    customer_segment_ids: [],
    customer_segments: [],
    month_set: new Date().toISOString().slice(0, 7)
  };

  const simulationProfile = savedStrategy?.simulation_profile || {
    target_monthly_revenue: 60000000,
    expected_margin_pct: 35.0,
    zero_revenue_runway_months: 5
  };

  const monthlyLogs = savedStrategy?.monthly_logs || [];

  // Tên hiển thị các phân khúc khách hàng (duy nhất 1 tệp khách hàng)
  const displaySegments = (() => {
    const rawNames = profile.customer_segments || savedStrategy?.customer_segments;
    if (Array.isArray(rawNames) && rawNames.length > 0) return rawNames.slice(0, 1);
    const rawIds = profile.customer_segment_ids || savedStrategy?.customer_segment_ids || [];
    if (Array.isArray(rawIds) && rawIds.length > 0) {
      return rawIds.slice(0, 1).map(id => {
        const found = availableSegments.find(s => s.id === id);
        return found ? found.name : `Nhóm ${id}`;
      });
    }
    return [];
  })();

  // Danh mục sản phẩm kinh doanh của quán (từ kế sách / database)
  const displayProducts = (() => {
    // 1. Lấy trực tiếp từ product_names (ở savedStrategy hoặc profile)
    const rawNames = savedStrategy?.product_names || profile?.product_names;
    if (Array.isArray(rawNames) && rawNames.length > 0) {
      return rawNames.map(p => (typeof p === 'string' ? p : (p?.name || p?.title || String(p))));
    }
    // 2. Map từ product_ids kết hợp với metadata.products
    const rawIds = savedStrategy?.product_ids || profile?.product_ids;
    if (Array.isArray(rawIds) && rawIds.length > 0) {
      return rawIds.map(id => {
        const pInt = parseInt(id, 10);
        const found = metadata?.products?.find(p => p.id === pInt || p.id === id);
        return found ? found.name : `Sản phẩm #${id}`;
      });
    }
    // 3. Fallback từ kết quả thẩm định report_result nếu có
    const reportProducts = savedStrategy?.report_result?.business_model?.products || savedStrategy?.report_result?.products;
    if (Array.isArray(reportProducts) && reportProducts.length > 0) {
      return reportProducts.map(p => (typeof p === 'string' ? p : (p?.name || p?.title || `Sản phẩm #${p?.id || ''}`)));
    }
    return [];
  })();

  useEffect(() => {
    if (savedStrategy?.profile) {
      setBudgetInput(savedStrategy.profile.budget || 0);
      setRentInput(savedStrategy.profile.rent || 0);
      setStaffCountInput(savedStrategy.profile.staff_count || 0);
      setAvgSalaryInput(savedStrategy.profile.avg_salary || 0);
      setMonthSetInput(savedStrategy.profile.month_set || new Date().toISOString().slice(0, 7));
      const segs = savedStrategy.profile.customer_segment_ids || savedStrategy.customer_segment_ids || [];
      setSelectedSegments(Array.isArray(segs) ? segs.slice(0, 1) : []);
    } else if (savedStrategy?.customer_segment_ids) {
      setSelectedSegments(Array.isArray(savedStrategy.customer_segment_ids) ? savedStrategy.customer_segment_ids.slice(0, 1) : []);
    }
  }, [savedStrategy]);

  // Hủy chỉnh sửa & khôi phục giá trị đã lưu
  const handleCancelEdit = () => {
    setIsEditingProfile(false);
    if (savedStrategy?.profile) {
      setBudgetInput(savedStrategy.profile.budget || 0);
      setRentInput(savedStrategy.profile.rent || 0);
      setStaffCountInput(savedStrategy.profile.staff_count || 0);
      setAvgSalaryInput(savedStrategy.profile.avg_salary || 0);
      setMonthSetInput(savedStrategy.profile.month_set || new Date().toISOString().slice(0, 7));
      const segs = savedStrategy.profile.customer_segment_ids || savedStrategy.customer_segment_ids || [];
      setSelectedSegments(Array.isArray(segs) ? segs.slice(0, 1) : []);
    }
  };

  // Cập nhật Profile thực tế
  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    const token = localStorage.getItem('mlai_user_token');
    if (!token) {
      alert('Vui lòng đăng nhập để lưu hồ sơ quán!');
      return;
    }

    setSavingProfile(true);
    try {
      const res = await fetch('/api/user/strategy/profile', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          budget: parseInt(budgetInput) || 0,
          rent: parseInt(rentInput) || 0,
          staff_count: parseInt(staffCountInput) || 0,
          avg_salary: parseInt(avgSalaryInput) || 0,
          customer_segment_ids: selectedSegments.slice(0, 1),
          month_set: monthSetInput || new Date().toISOString().slice(0, 7)
        })
      });

      if (!res.ok) {
        let errorMsg = `Lỗi cập nhật hồ sơ quán (${res.status})`;
        try {
          const errData = await res.json();
          errorMsg = errData.detail || errorMsg;
        } catch {
          try {
            const rawText = await res.text();
            if (rawText) errorMsg = rawText;
          } catch {
            // Giữ nguyên lỗi mặc định
          }
        }
        throw new Error(errorMsg);
      }

      setIsEditingProfile(false);
      if (onStrategyUpdated) onStrategyUpdated();
    } catch (err) {
      alert(err.message);
    } finally {
      setSavingProfile(false);
    }
  };

  // Lưu Sổ sách tháng
  const handleSaveMonthlyLog = async (e) => {
    e.preventDefault();
    setLogError('');
    const token = localStorage.getItem('mlai_user_token');
    if (!token) {
      setLogError('Vui lòng đăng nhập để ghi chép sổ sách tháng!');
      return;
    }

    if (!logMonth) {
      setLogError('Vui lòng chọn tháng ghi nhận!');
      return;
    }

    setSavingLog(true);
    try {
      const res = await fetch('/api/user/strategy/monthly_log', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          month: logMonth,
          revenue: parseInt(logRevenue) || 0,
          cost: parseInt(logCost) || 0,
          note: logNote.trim()
        })
      });

      if (!res.ok) {
        let errorMsg = `Lỗi khi lưu sổ sách tháng (${res.status})`;
        try {
          const errData = await res.json();
          errorMsg = errData.detail || errorMsg;
        } catch {
          try {
            const rawText = await res.text();
            if (rawText) errorMsg = rawText;
          } catch {
            // Giữ nguyên lỗi mặc định
          }
        }
        throw new Error(errorMsg);
      }

      setShowLogModal(false);
      setLogMonth('');
      setLogRevenue('');
      setLogCost('');
      setLogNote('');
      if (onStrategyUpdated) onStrategyUpdated();
    } catch (err) {
      setLogError(err.message);
    } finally {
      setSavingLog(false);
    }
  };

  // Xóa Sổ sách tháng
  const handleDeleteMonth = async (month) => {
    if (!confirm(`Bạn có chắc chắn muốn xóa dữ liệu sổ sách tháng ${month}?`)) return;
    const token = localStorage.getItem('mlai_user_token');
    if (!token) return;

    try {
      const res = await fetch(`/api/user/strategy/monthly_log/${month}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok && onStrategyUpdated) {
        onStrategyUpdated();
      }
    } catch (err) {
      alert('Lỗi xóa sổ sách: ' + err.message);
    }
  };

  // Tính preview profit
  const previewRevenue = parseInt(logRevenue) || 0;
  const previewCost = parseInt(logCost) || 0;
  const previewProfit = previewRevenue - previewCost;
  const previewMargin = previewRevenue > 0 ? ((previewProfit / previewRevenue) * 100).toFixed(1) : '0.0';

  // Tổng hợp thống kê
  const totalRevenue = monthlyLogs.reduce((acc, cur) => acc + (cur.revenue || 0), 0);
  const totalCost = monthlyLogs.reduce((acc, cur) => acc + (cur.cost || 0), 0);
  const totalProfit = totalRevenue - totalCost;

  return (
    <div className="h-full w-full bg-slate-50 overflow-y-auto p-4 sm:p-6 lg:p-8 font-sans text-slate-800">
      <div className="max-w-6xl mx-auto space-y-6">
        
        {/* 1. Header Trang Quản lý Hồ sơ Quán */}
        <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="flex items-center space-x-3.5">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-600 flex items-center justify-center text-white shadow-sm shrink-0">
              <Store className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2 flex-wrap">
                <h1 className="text-base sm:text-lg font-bold text-slate-900 leading-tight">
                  {savedStrategy?.model_name || 'Hồ sơ Quán F&B'}
                </h1>
                {savedStrategy ? (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" />
                    Đã đồng bộ kế sách
                  </span>
                ) : (
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
                    Chưa lưu kế sách
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-500 mt-0.5 flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-slate-400" />
                <span>{savedStrategy?.address || 'Chưa xác định địa chỉ kinh doanh'}</span>
              </p>
              {displayProducts.length > 0 && (
                <div className="flex items-center gap-1.5 flex-wrap mt-2">
                  <span className="text-[11px] font-semibold text-slate-500 flex items-center gap-1">
                    <ShoppingBag className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Sản phẩm:</span>
                  </span>
                  {displayProducts.map((pName, idx) => (
                    <span
                      key={idx}
                      className="px-2 py-0.5 bg-emerald-50 text-emerald-800 font-semibold rounded-md text-[11px] border border-emerald-200/80"
                    >
                      {pName}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => setShowLogModal(true)}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs rounded-xl shadow-xs transition flex items-center space-x-1.5"
            >
              <Plus className="w-4 h-4" />
              <span>Ghi nhận sổ sách tháng</span>
            </button>
          </div>
        </div>

        {/* 2. Hai Khối Thông số Cốt lõi: Profile Hiện tại vs Kế hoạch Chuẩn Day 0 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          
          {/* KHỐI A: PROFILE HIỆN TẠI (Vốn, Mặt bằng & Nhân sự Thực tế) */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center">
                  <DollarSign className="w-4 h-4" />
                </div>
                <h2 className="font-bold text-xs uppercase tracking-wider text-slate-800">
                  1. Hồ sơ Vốn, Mặt bằng & Nhân sự Thực tế
                </h2>
              </div>

              {!isEditingProfile ? (
                <button
                  type="button"
                  onClick={() => setIsEditingProfile(true)}
                  className="text-xs text-indigo-600 hover:text-indigo-800 font-bold flex items-center space-x-1"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                  <span>Chỉnh sửa</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleCancelEdit}
                  className="text-xs text-slate-500 hover:text-slate-700 font-bold flex items-center space-x-1"
                >
                  <X className="w-3.5 h-3.5" />
                  <span>Hủy</span>
                </button>
              )}
            </div>

            {!isEditingProfile ? (
              <div className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                    <span className="text-[11px] text-slate-500 block">Vốn thực tế còn lại:</span>
                    <span className="font-extrabold text-indigo-700 text-base">
                      {profile.budget > 0 ? `${profile.budget.toLocaleString()} đ` : 'Chưa nhập'}
                    </span>
                  </div>
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                    <span className="text-[11px] text-slate-500 block">Tiền thuê mặt bằng:</span>
                    <span className="font-extrabold text-slate-800 text-base">
                      {profile.rent > 0 ? `${profile.rent.toLocaleString()} đ` : 'Chưa nhập'}
                    </span>
                    <span className="text-[10px] text-slate-400 block">/ tháng</span>
                  </div>
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                    <span className="text-[11px] text-slate-500 block">Số lượng nhân sự:</span>
                    <span className="font-extrabold text-slate-800 text-base">
                      {(profile.staff_count || 0) > 0 ? `${profile.staff_count} người` : '0 người (Tự làm)'}
                    </span>
                  </div>
                  <div className="bg-slate-50 p-3 rounded-xl border border-slate-100">
                    <span className="text-[11px] text-slate-500 block">Lương bình quân / người:</span>
                    <span className="font-extrabold text-slate-800 text-base">
                      {(profile.avg_salary || 0) > 0 ? `${profile.avg_salary.toLocaleString()} đ` : 'Chưa nhập'}
                    </span>
                    <span className="text-[10px] text-slate-400 block">/ người / tháng</span>
                  </div>
                </div>

                {/* Tệp khách hàng mục tiêu */}
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs space-y-1.5">
                  <div className="flex items-center justify-between text-slate-700">
                    <span className="flex items-center space-x-1.5 font-semibold text-[11px]">
                      <Users className="w-3.5 h-3.5 text-indigo-600" />
                      <span>Tệp khách hàng mục tiêu:</span>
                    </span>
                    <span className="text-[11px] text-slate-400">
                      {displaySegments.length} phân khúc
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5 pt-0.5">
                    {displaySegments.length > 0 ? (
                      displaySegments.map((segName, idx) => (
                        <span
                          key={idx}
                          className="px-2.5 py-1 bg-white border border-indigo-200 text-indigo-700 font-semibold rounded-lg text-xs shadow-2xs"
                        >
                          {segName}
                        </span>
                      ))
                    ) : (
                      <span className="text-slate-400 italic text-xs">Chưa cấu hình tệp khách hàng</span>
                    )}
                  </div>
                </div>

                {/* Danh mục sản phẩm kinh doanh */}
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-100 text-xs space-y-1.5">
                  <div className="flex items-center justify-between text-slate-700">
                    <span className="flex items-center space-x-1.5 font-semibold text-[11px]">
                      <ShoppingBag className="w-3.5 h-3.5 text-indigo-600" />
                      <span>Sản phẩm kinh doanh:</span>
                    </span>
                    <span className="text-[11px] text-slate-400">
                      {displayProducts.length} sản phẩm
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5 pt-0.5">
                    {displayProducts.length > 0 ? (
                      displayProducts.map((prodName, idx) => (
                        <span
                          key={idx}
                          className="px-2.5 py-1 bg-white border border-indigo-200 text-slate-800 font-semibold rounded-lg text-xs shadow-2xs"
                        >
                          {prodName}
                        </span>
                      ))
                    ) : (
                      <span className="text-slate-400 italic text-xs">Chưa cấu hình sản phẩm</span>
                    )}
                  </div>
                </div>

                {/* Ước tính Tổng Quỹ Lương & Chi phí Cố định Bắt buộc */}
                <div className="p-3 bg-indigo-50/50 rounded-xl border border-indigo-100/70 text-xs space-y-1.5">
                  <div className="flex items-center justify-between text-indigo-950">
                    <span className="flex items-center space-x-1.5">
                      <Users className="w-3.5 h-3.5 text-indigo-600" />
                      <span>Tổng quỹ lương tháng:</span>
                    </span>
                    <span className="font-bold">
                      {((profile.staff_count || 0) * (profile.avg_salary || 0)).toLocaleString()} đ
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-slate-600 text-[11px] pt-0.5 border-t border-indigo-100">
                    <span>Chi phí cố định bắt buộc (Thuê + Lương):</span>
                    <span className="font-bold text-slate-800">
                      {((profile.rent || 0) + ((profile.staff_count || 0) * (profile.avg_salary || 0))).toLocaleString()} đ/tháng
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs text-slate-500 px-1 pt-0.5">
                  <span>Tháng chốt số liệu gần nhất:</span>
                  <span className="font-bold text-slate-800 bg-slate-100 px-2.5 py-0.5 rounded-md">
                    {profile.month_set || 'Chưa cập nhật'}
                  </span>
                </div>
              </div>
            ) : (
              <form onSubmit={handleUpdateProfile} className="space-y-3 pt-1">
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Vốn thực tế còn lại (VNĐ):
                  </label>
                  <input
                    type="number"
                    value={budgetInput}
                    onChange={(e) => setBudgetInput(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs outline-none focus:ring-1 focus:ring-indigo-500"
                    placeholder="VD: 120000000"
                    required
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Tiền thuê mặt bằng (VNĐ/tháng):
                  </label>
                  <input
                    type="number"
                    value={rentInput}
                    onChange={(e) => setRentInput(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs outline-none focus:ring-1 focus:ring-indigo-500"
                    placeholder="VD: 12000000"
                    required
                  />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Số lượng nhân viên:
                    </label>
                    <input
                      type="number"
                      min="0"
                      value={staffCountInput}
                      onChange={(e) => setStaffCountInput(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs outline-none focus:ring-1 focus:ring-indigo-500"
                      placeholder="VD: 3"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-semibold text-slate-700 mb-1">
                      Lương TB / người (VNĐ):
                    </label>
                    <input
                      type="number"
                      min="0"
                      value={avgSalaryInput}
                      onChange={(e) => setAvgSalaryInput(e.target.value)}
                      className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs outline-none focus:ring-1 focus:ring-indigo-500"
                      placeholder="VD: 6000000"
                    />
                  </div>
                </div>
                <p className="text-[10px] text-slate-500 italic">
                  * Gợi ý: Lương bình quân = Tổng chi phí lương tháng chia đều cho số nhân sự.
                </p>

                {/* Chọn Phân khúc khách hàng mục tiêu */}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1.5 flex items-center justify-between">
                    <span>Tệp khách hàng mục tiêu:</span>
                    <span className="text-[11px] text-indigo-600 font-medium">
                      {selectedSegments.length > 0 ? 'Đã chọn 1 phân khúc' : 'Chưa chọn'}
                    </span>
                  </label>
                  <div className="grid grid-cols-2 gap-2">
                    {availableSegments.map((seg) => {
                      const isSelected = selectedSegments[0] === seg.id;
                      return (
                        <button
                          key={seg.id}
                          type="button"
                          onClick={() => {
                            setSelectedSegments([seg.id]);
                          }}
                          className={`px-3 py-2 rounded-xl text-xs font-medium border text-left transition flex items-center justify-between ${
                            isSelected
                              ? 'bg-indigo-50 border-indigo-300 text-indigo-700 font-bold shadow-2xs'
                              : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
                          }`}
                        >
                          <span>{seg.name}</span>
                          {isSelected ? (
                            <CheckCircle2 className="w-3.5 h-3.5 text-indigo-600 shrink-0" />
                          ) : (
                            <div className="w-3.5 h-3.5 rounded-full border border-slate-300 shrink-0" />
                          )}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Danh mục sản phẩm kinh doanh (Theo kế sách) */}
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/70 text-xs space-y-1.5">
                  <div className="flex items-center justify-between text-slate-700">
                    <span className="flex items-center space-x-1.5 font-semibold text-[11px]">
                      <ShoppingBag className="w-3.5 h-3.5 text-indigo-600" />
                      <span>Sản phẩm kinh doanh (theo kế sách):</span>
                    </span>
                    <span className="text-[11px] text-slate-400">
                      {displayProducts.length} sản phẩm
                    </span>
                  </div>
                  <div className="flex flex-wrap gap-1.5 pt-0.5">
                    {displayProducts.length > 0 ? (
                      displayProducts.map((prodName, idx) => (
                        <span
                          key={idx}
                          className="px-2 py-0.5 bg-white border border-slate-200 text-slate-700 font-medium rounded-md text-xs shadow-2xs"
                        >
                          {prodName}
                        </span>
                      ))
                    ) : (
                      <span className="text-slate-400 italic text-xs">Chưa cấu hình sản phẩm</span>
                    )}
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">
                    Tháng ghi nhận số liệu (YYYY-MM):
                  </label>
                  <input
                    type="month"
                    value={monthSetInput}
                    onChange={(e) => setMonthSetInput(e.target.value)}
                    className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs outline-none focus:ring-1 focus:ring-indigo-500"
                    required
                  />
                </div>
                <div className="flex items-center space-x-2 pt-1">
                  <button
                    type="button"
                    onClick={handleCancelEdit}
                    className="flex-1 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl text-xs transition"
                  >
                    Hủy
                  </button>
                  <button
                    type="submit"
                    disabled={savingProfile}
                    className="flex-1 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl text-xs transition flex items-center justify-center space-x-1"
                  >
                    <Save className="w-3.5 h-3.5" />
                    <span>{savingProfile ? 'Đang lưu...' : 'Lưu thay đổi'}</span>
                  </button>
                </div>
              </form>
            )}
          </div>

          {/* KHỐI B: SIMULATION PROFILE (Thước đo Kế hoạch gốc Day 0) */}
          <div className="bg-white rounded-2xl p-5 border border-slate-200 shadow-xs space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <div className="w-7 h-7 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <h2 className="font-bold text-xs uppercase tracking-wider text-slate-800">
                  2. Thước đo Chuẩn (Kế hoạch Day 0)
                </h2>
              </div>
              <span className="text-[10px] text-blue-700 font-bold bg-blue-50 px-2.5 py-1 rounded-full border border-blue-200">
                Thước đo so sánh
              </span>
            </div>

            <div className="grid grid-cols-3 gap-3 text-center">
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-100">
                <span className="text-[11px] text-slate-400 block mb-1">Doanh thu chuẩn</span>
                <span className="font-extrabold text-slate-800 text-base">
                  {simulationProfile.target_monthly_revenue ? `${(simulationProfile.target_monthly_revenue / 1000000).toFixed(0)}M` : '60M'}
                </span>
                <span className="text-[10px] text-slate-400 block mt-0.5">/ tháng</span>
              </div>
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-100">
                <span className="text-[11px] text-slate-400 block mb-1">Biên lãi chuẩn</span>
                <span className="font-extrabold text-emerald-600 text-base">
                  {simulationProfile.expected_margin_pct || 35}%
                </span>
                <span className="text-[10px] text-slate-400 block mt-0.5">chuẩn ngành</span>
              </div>
              <div className="bg-slate-50 p-3.5 rounded-xl border border-slate-100">
                <span className="text-[11px] text-slate-400 block mb-1">Runway sống sót</span>
                <span className="font-extrabold text-amber-600 text-base">
                  {simulationProfile.zero_revenue_runway_months || 5}
                </span>
                <span className="text-[10px] text-slate-400 block mt-0.5">tháng cầm cự</span>
              </div>
            </div>

            <p className="text-[11px] text-slate-500 leading-relaxed bg-blue-50/50 p-2.5 rounded-xl border border-blue-100/60">
              💡 Đây là các con số mục tiêu do bộ máy giả lập tính toán trước khi mở quán, dùng để đối chiếu khi AI chẩn đoán xem quán có bị lệch kế hoạch không.
            </p>
          </div>

        </div>

        {/* 3. BẢNG SỔ SÁCH TÀI CHÍNH TỪNG THÁNG (MONTHLY LOGS TABLE) */}
        <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-xs space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
            <div className="flex items-center space-x-2">
              <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <Calendar className="w-4 h-4" />
              </div>
              <div>
                <h2 className="font-bold text-xs uppercase tracking-wider text-slate-800">
                  3. Nhật ký Sổ sách Tài chính Đa tháng
                </h2>
                <p className="text-[11px] text-slate-400">
                  Lợi nhuận được hệ thống tự động tính toán chính xác (profit = revenue - cost)
                </p>
              </div>
            </div>

            {monthlyLogs.length > 0 && (
              <div className="flex items-center gap-3 text-xs">
                <span className="text-slate-500">
                  Lũy kế lãi/lỗ: <strong className={totalProfit >= 0 ? 'text-emerald-600' : 'text-red-500'}>
                    {totalProfit >= 0 ? `+${totalProfit.toLocaleString()}` : totalProfit.toLocaleString()} đ
                  </strong>
                </span>
              </div>
            )}
          </div>

          {monthlyLogs.length === 0 ? (
            <div className="text-center py-10 bg-slate-50 rounded-2xl border border-dashed border-slate-200 space-y-2">
              <Calendar className="w-8 h-8 text-slate-300 mx-auto" />
              <p className="text-xs text-slate-500 font-medium">Chưa có bản ghi sổ sách nào được lưu.</p>
              <button
                type="button"
                onClick={() => setShowLogModal(true)}
                className="text-xs text-emerald-600 font-bold hover:underline"
              >
                + Bấm vào đây để ghi nhận tháng đầu tiên
              </button>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left">
                <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                  <tr>
                    <th className="py-3 px-3.5">Tháng</th>
                    <th className="py-3 px-3.5">Doanh Thu</th>
                    <th className="py-3 px-3.5">Tổng Chi Phí (Gồm nhà)</th>
                    <th className="py-3 px-3.5">Lợi Nhuận (Tự tính)</th>
                    <th className="py-3 px-3.5">Biên Lãi (%)</th>
                    <th className="py-3 px-3.5">Ghi Chú Sự Kiện</th>
                    <th className="py-3 px-3.5 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {monthlyLogs.map((log) => {
                    const profitVal = log.profit !== undefined ? log.profit : (log.revenue - log.cost);
                    const marginVal = log.margin_pct !== undefined ? log.margin_pct : (log.revenue > 0 ? ((profitVal / log.revenue) * 100).toFixed(1) : 0);
                    const isPositive = profitVal >= 0;

                    return (
                      <tr key={log.month} className="hover:bg-slate-50 transition">
                        <td className="py-3 px-3.5 font-bold text-slate-900">
                          Tháng {log.month}
                        </td>
                        <td className="py-3 px-3.5 text-slate-700 font-semibold">
                          {log.revenue.toLocaleString()} đ
                        </td>
                        <td className="py-3 px-3.5 text-slate-700">
                          {log.cost.toLocaleString()} đ
                        </td>
                        <td className="py-3 px-3.5 font-extrabold">
                          <span className={`inline-flex items-center ${isPositive ? 'text-emerald-600' : 'text-red-500'}`}>
                            {isPositive ? <ArrowUpRight className="w-3.5 h-3.5 mr-0.5" /> : <ArrowDownRight className="w-3.5 h-3.5 mr-0.5" />}
                            {profitVal.toLocaleString()} đ
                          </span>
                        </td>
                        <td className="py-3 px-3.5 font-semibold text-slate-700">
                          {marginVal}%
                        </td>
                        <td className="py-3 px-3.5 text-slate-500 max-w-xs truncate" title={log.note}>
                          {log.note || '—'}
                        </td>
                        <td className="py-3 px-3.5 text-right">
                          <button
                            type="button"
                            onClick={() => handleDeleteMonth(log.month)}
                            className="p-1.5 text-slate-400 hover:text-red-600 rounded-lg hover:bg-red-50 transition"
                            title="Xóa bản ghi này"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

      </div>

      {/* MODAL GHI CHÉP SỔ SÁCH THÁNG */}
      {showLogModal && (
        <div className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 space-y-4 shadow-xl border border-slate-100">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2 font-bold text-slate-800 text-sm">
                <Calendar className="w-4 h-4 text-emerald-600" />
                <span>Ghi nhận Sổ sách Tài chính Tháng</span>
              </div>
              <button
                type="button"
                onClick={() => setShowLogModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {logError && (
              <div className="p-2.5 bg-red-50 text-red-700 rounded-xl text-xs flex items-center space-x-1.5 border border-red-200">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{logError}</span>
              </div>
            )}

            <form onSubmit={handleSaveMonthlyLog} className="space-y-3.5 text-xs">
              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  1. Tháng ghi nhận: <span className="text-red-500">*</span>
                </label>
                <input
                  type="month"
                  value={logMonth}
                  onChange={(e) => setLogMonth(e.target.value)}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-1 focus:ring-emerald-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  2. Doanh thu tổng trong tháng (VNĐ): <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  value={logRevenue}
                  onChange={(e) => setLogRevenue(e.target.value)}
                  placeholder="VD: 55000000"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-1 focus:ring-emerald-500"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  3. Tổng chi phí trong tháng (VNĐ): <span className="text-red-500">*</span>
                </label>
                <input
                  type="number"
                  value={logCost}
                  onChange={(e) => setLogCost(e.target.value)}
                  placeholder="VD: 36000000"
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-1 focus:ring-emerald-500"
                  required
                />
                <span className="text-[10px] text-slate-400 block mt-1">
                  * Lưu ý: Đã bao gồm cả tiền thuê mặt bằng, nhân công, nguyên liệu và điện nước.
                </span>
              </div>

              {/* Preview Lợi nhuận tự tính */}
              {(logRevenue || logCost) && (
                <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 text-xs space-y-1.5">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Lợi nhuận dự tính:</span>
                    <span className={`font-extrabold ${previewProfit >= 0 ? 'text-emerald-600' : 'text-red-500'}`}>
                      {previewProfit.toLocaleString()} đ
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Biên lợi nhuận:</span>
                    <span className="font-bold text-slate-700">{previewMargin}%</span>
                  </div>
                  <p className="text-[10px] text-slate-400 italic pt-0.5">
                    * Lợi nhuận do hệ thống tự tính tự động: profit = revenue - cost
                  </p>
                </div>
              )}

              <div>
                <label className="block text-xs font-bold text-slate-700 mb-1">
                  4. Ghi chú sự kiện trong tháng (Tùy chọn):
                </label>
                <textarea
                  value={logNote}
                  onChange={(e) => setLogNote(e.target.value)}
                  placeholder="VD: Tháng này sinh viên nghỉ hè, đổi nhân viên pha chế mới..."
                  rows={2}
                  className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:ring-1 focus:ring-emerald-500 resize-none"
                />
              </div>

              <div className="flex items-center space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowLogModal(false)}
                  className="flex-1 py-2.5 bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold rounded-xl transition"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={savingLog}
                  className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-xl transition flex items-center justify-center space-x-1"
                >
                  <Save className="w-3.5 h-3.5" />
                  <span>{savingLog ? 'Đang lưu...' : 'Lưu sổ sách'}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
