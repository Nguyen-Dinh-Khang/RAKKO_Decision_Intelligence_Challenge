import React, { useState, useEffect } from 'react';
import { 
  Search, MapPin, DollarSign, Store, Tag, AlertTriangle, 
  CheckCircle2, TrendingUp, ShieldAlert, ArrowRight, Sparkles, RefreshCw, BarChart3, Users,
  Bookmark, BookmarkCheck, Clock, Target, Lightbulb, Award, Activity, Sliders
} from 'lucide-react';
import FormattedMarkdown from './FormattedMarkdown';

/**
 * Bảng ánh xạ tương thích giữa 10 Mô hình kinh doanh (101 - 110) và 20 Nhóm sản phẩm (201 - 220)
 * Kiểm tra ngay tại Frontend để phản hồi tức thì cho người dùng.
 */
const MODEL_PRODUCT_COMPATIBILITY = {
  101: [201, 202, 203, 204, 205], // Quán ăn sáng: Đồ uống, Cơm, Món nước, Bánh mì & Điểm tâm, Đồ ăn vặt
  102: [201, 204, 205],           // Quán nước / Cà phê: Đồ uống, Bánh mì & Điểm tâm, Đồ ăn vặt
  103: [201, 202, 203, 206],      // Quán cơm / Nhà hàng nhỏ: Đồ uống, Cơm, Món nước, Món nhậu/Lẩu/Nướng
  104: [201, 205, 206],           // Quán nhậu / Ăn vặt: Đồ uống, Đồ ăn vặt, Món nhậu/Lẩu/Nướng
  105: [201, 204, 205],           // Kiosk / Xe đẩy mang đi: Đồ uống, Bánh mì & Điểm tâm, Đồ ăn vặt tinh gọn
  106: [201, 207, 208, 217, 218], // Tạp hóa / Đại lý: Đồ uống, Thực phẩm tươi, Tạp hóa, Gia dụng, Văn phòng phẩm
  107: [208, 209, 210, 211, 215, 216, 217, 218], // Bán lẻ chuyên doanh: Quần áo, Giày dép, Mỹ phẩm, Thuốc, Phụ kiện, Quà tặng
  108: [211, 212, 213, 214],      // Tiệm làm đẹp / Spa: Mỹ phẩm, Cắt tóc, Massage/Spa, Nail & Mi
  109: [218, 219, 220],           // Dịch vụ dân sinh: Văn phòng phẩm/In ấn, Giặt ủi, Sửa xe máy
  110: [201, 204, 205, 207, 208, 211, 217] // Siêu thị mini: Đồ uống, Bánh mì, Ăn vặt, Thực phẩm tươi, Tạp hóa, Mỹ phẩm, Gia dụng
};

/**
 * FeasibilityScanner - Giao diện 1: Máy quét Thẩm định Ý tưởng (Day 0)
 * Giúp người dùng kiểm tra tính khả thi trước khi bỏ vốn.
 * Chạy trọn vẹn pipeline 5 mắt xích và trả về bản phân tích 5 khối chuyên sâu.
 * Hỗ trợ lưu trữ mô hình (1xx), món định bán (2xx), địa chỉ, tọa độ và kế sách vào hồ sơ cá nhân.
 */
export default function FeasibilityScanner({ metadata, currentUser, savedStrategy, onStrategySaved, llmConfig }) {
  // Form State - Không điền sẵn dữ liệu, chỉ hiển thị placeholder
  const [address, setAddress] = useState('');
  const [modelId, setModelId] = useState('');
  const [selectedProductIds, setSelectedProductIds] = useState([]);
  const [compatibilityNotice, setCompatibilityNotice] = useState(null);
  const [budget, setBudget] = useState('');
  const [rent, setRent] = useState(''); // Để trống để hệ thống tự tính

  // Request State
  const [loading, setLoading] = useState(false);
  const [isStreamingAi, setIsStreamingAi] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [scenarioTab, setScenarioTab] = useState('normal'); // 'normal' | 'premium'

  // Trạng thái lưu kế sách chiến lược
  const [showSavePrompt, setShowSavePrompt] = useState(false);
  const [savingStrategy, setSavingStrategy] = useState(false);
  const [saveSuccessMessage, setSaveSuccessMessage] = useState(null);
  const [isCurrentReportSaved, setIsCurrentReportSaved] = useState(true);
  const [showScenarioModal, setShowScenarioModal] = useState(false);
  const [chosenScenarioToSave, setChosenScenarioToSave] = useState('normal'); // 'normal' | 'premium'

  // Tự động nạp thông tin cá nhân và kế sách đã lưu khi người dùng đăng nhập
  useEffect(() => {
    if (savedStrategy) {
      if (savedStrategy.address) setAddress(savedStrategy.address);
      if (savedStrategy.model_id) setModelId(savedStrategy.model_id);
      if (savedStrategy.product_ids && Array.isArray(savedStrategy.product_ids)) {
        setSelectedProductIds(savedStrategy.product_ids);
      }
      if (savedStrategy.report_result) {
        setResult(savedStrategy.report_result);
      }
      const p = savedStrategy.profile;
      if (p) {
        if (p.budget !== undefined && p.budget !== null && p.budget > 0) {
          setBudget(p.budget.toString());
        }
        if (p.rent !== undefined && p.rent !== null && p.rent >= 0) {
          setRent(p.rent.toString());
        }
      }
      setIsCurrentReportSaved(true);
      setShowSavePrompt(false);
    }
  }, [savedStrategy]);

  // Xử lý khi đổi mô hình: Tự động lọc bỏ các món không còn phù hợp
  const handleModelChange = (newModelIdStr) => {
    setModelId(newModelIdStr);
    setCompatibilityNotice(null);
    if (!newModelIdStr) return;

    const mid = parseInt(newModelIdStr);
    const allowed = MODEL_PRODUCT_COMPATIBILITY[mid] || [];

    const invalidSelected = selectedProductIds.filter(pid => !allowed.includes(pid));
    if (invalidSelected.length > 0) {
      const validSelected = selectedProductIds.filter(pid => allowed.includes(pid));
      setSelectedProductIds(validSelected);
      setCompatibilityNotice('Hệ thống đã tự động bỏ chọn các sản phẩm không phù hợp với mô hình kinh doanh mới.');
      setTimeout(() => setCompatibilityNotice(null), 4500);
    }
  };

  // Toggle chọn sản phẩm (Chọn từ 1 đến 3 món, chặn món không tương thích)
  const toggleProduct = (productId) => {
    if (modelId) {
      const allowed = MODEL_PRODUCT_COMPATIBILITY[parseInt(modelId)] || [];
      if (!allowed.includes(productId)) return;
    }
    if (selectedProductIds.includes(productId)) {
      setSelectedProductIds(selectedProductIds.filter(id => id !== productId));
    } else {
      if (selectedProductIds.length < 3) {
        setSelectedProductIds([...selectedProductIds, productId]);
      }
    }
  };

  // Đặt một món đã chọn làm Món chủ lực (đưa lên đầu mảng selectedProductIds)
  const setPrimaryProduct = (productId) => {
    if (!selectedProductIds.includes(productId)) return;
    const remaining = selectedProductIds.filter(id => id !== productId);
    setSelectedProductIds([productId, ...remaining]);
  };

  // Điều kiện kiểm tra đã điền đủ toàn bộ các trường bắt buộc (tiền thuê bắt buộc, cho phép nhập 0)
  const isRentValid = rent !== '' && !isNaN(Number(rent)) && Number(rent) >= 0;
  const isFormValid = Boolean(
    address.trim() &&
    modelId &&
    selectedProductIds.length > 0 &&
    budget &&
    !isNaN(Number(budget)) &&
    Number(budget) > 0 &&
    isRentValid
  );

  // Bắt đầu quy trình lưu kế sách: nếu có cả 2 kịch bản thì hiển thị modal hỏi người dùng
  const handleInitiateSave = () => {
    if (!currentUser) {
      alert('Vui lòng đăng nhập trước khi lưu kế sách chiến lược!');
      return;
    }
    const currentReport = result || savedStrategy?.report_result;
    if (!currentReport) {
      alert('Chưa có kết quả thẩm định để lưu!');
      return;
    }

    const stressList = Array.isArray(currentReport?.stress_test) ? currentReport.stress_test : [];
    const normalScen = stressList.find(s => s.scenario === 'normal') || stressList[0];
    const premiumScen = stressList.find(s => s.scenario === 'premium');

    // Nếu có cả 2 kịch bản thì mở modal hỏi người dùng muốn lưu bản nào
    if (normalScen && premiumScen) {
      setChosenScenarioToSave(scenarioTab === 'premium' ? 'premium' : 'normal');
      setShowScenarioModal(true);
    } else {
      // Chỉ có 1 kịch bản thì lưu luôn kịch bản thường
      executeSaveStrategy('normal');
    }
  };

  // Thực hiện lưu kế sách với kịch bản được chọn ('normal' hoặc 'premium')
  const executeSaveStrategy = async (selectedScenarioType = 'normal') => {
    if (!currentUser) {
      alert('Vui lòng đăng nhập trước khi lưu kế sách chiến lược!');
      return;
    }
    const currentReport = result || savedStrategy?.report_result;
    if (!currentReport) {
      alert('Chưa có kết quả thẩm định để lưu!');
      return;
    }

    setSavingStrategy(true);
    try {
      const token = localStorage.getItem('mlai_user_token');
      if (!token) {
        throw new Error('Chưa tìm thấy phiên đăng nhập. Vui lòng đăng nhập lại!');
      }

      // Xử lý tọa độ chuẩn xác (hỗ trợ cả Array [lng, lat] và Object {lng, lat})
      let lng = 0.0;
      let lat = 0.0;
      const coords = currentReport?.location_info?.coordinates || savedStrategy?.coordinates;
      if (Array.isArray(coords) && coords.length >= 2) {
        lng = parseFloat(coords[0]) || 0.0;
        lat = parseFloat(coords[1]) || 0.0;
      } else if (coords && typeof coords === 'object') {
        lng = parseFloat(coords.lng) || 0.0;
        lat = parseFloat(coords.lat) || 0.0;
      }

      // Xử lý mô hình và sản phẩm
      const finalModelId = parseInt(modelId) || (savedStrategy?.model_id ? parseInt(savedStrategy.model_id) : 101);
      const rawProducts = (selectedProductIds && selectedProductIds.length > 0)
        ? selectedProductIds
        : (savedStrategy?.product_ids || [201]);
      const finalProductIds = rawProducts.map(p => parseInt(p)).filter(p => !isNaN(p));

      // Xử lý địa chỉ
      const finalAddress = (
        currentReport?.location_info?.recognized_area ||
        address.trim() ||
        savedStrategy?.address ||
        'Địa chỉ chưa xác định'
      ).trim();

      // Xử lý số vốn và tiền thuê (số thực)
      const parsedBudget = parseFloat(budget);
      const finalBudget = !isNaN(parsedBudget) ? parsedBudget : (savedStrategy?.profile?.budget || 0);

      const parsedRent = parseFloat(rent);
      const finalRent = !isNaN(parsedRent) ? parsedRent : (savedStrategy?.profile?.rent || 0);

      const savePayload = {
        address: finalAddress,
        coordinates: { lng, lat },
        model_id: finalModelId,
        product_ids: finalProductIds,
        report_result: currentReport,
        budget: finalBudget,
        rent: finalRent,
        selected_scenario: selectedScenarioType
      };

      const res = await fetch('/api/user/strategy/save', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(savePayload)
      });

      let data = null;
      const contentType = res.headers.get('content-type') || '';
      if (contentType.includes('application/json')) {
        try {
          data = await res.json();
        } catch {
          data = null;
        }
      }

      if (!res.ok) {
        let errorMsg = `Lỗi khi lưu kế sách chiến lược (${res.status})`;
        if (data) {
          if (typeof data.detail === 'string') {
            errorMsg = data.detail;
          } else if (Array.isArray(data.detail)) {
            errorMsg = data.detail.map(d => `${d.loc?.join('.') || 'Trường'}: ${d.msg}`).join('\n');
          } else if (data.detail && typeof data.detail === 'object') {
            errorMsg = JSON.stringify(data.detail);
          }
        } else {
          try {
            const rawText = await res.text();
            if (rawText) errorMsg = rawText;
          } catch {
            // Giữ nguyên mã lỗi mặc định
          }
        }
        throw new Error(errorMsg);
      }

      setIsCurrentReportSaved(true);
      setShowSavePrompt(false);
      setShowScenarioModal(false);
      const scenLabel = selectedScenarioType === 'premium' ? 'Nâng cao (Premium)' : 'Thông thường (Normal)';
      setSaveSuccessMessage(`Đã lưu thành công Kế sách [${scenLabel}] vào hồ sơ cá nhân của bạn!`);
      if (onStrategySaved && data?.strategy) {
        onStrategySaved(data.strategy);
      }
    } catch (err) {
      alert(err.message);
    } finally {
      setSavingStrategy(false);
    }
  };

  // Gửi Form thẩm định tới FastAPI (Streaming 2 Pha: Logic tức thì -> AI Token-by-Token)
  const handleEvaluate = async (e) => {
    e.preventDefault();
    if (!isFormValid) {
      alert('Vui lòng điền đầy đủ tất cả các trường bắt buộc trước khi thẩm định!');
      return;
    }

    setLoading(true);
    setIsStreamingAi(false);
    setError(null);
    setResult(null);
    setIsCurrentReportSaved(false);
    setShowSavePrompt(false);
    setSaveSuccessMessage(null);

    // Hiệu ứng chuyển bước pipeline trực quan trong lúc đợi tính toán logic
    const stepsInterval = setInterval(() => {
      setActiveStep((prev) => (prev < 4 ? prev + 1 : prev));
    }, 1200);

    try {
      const response = await fetch('/api/scanner/evaluate/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          address: address.trim(),
          model_id: parseInt(modelId),
          product_ids: selectedProductIds,
          budget: parseFloat(budget),
          rent: parseFloat(rent),
          llm_config: llmConfig
        })
      });

      clearInterval(stepsInterval);

      if (!response.ok) {
        let errMessage = 'Lỗi xử lý pipeline thẩm định';
        try {
          const errData = await response.json();
          errMessage = errData.detail || errMessage;
        } catch {
          // ignore
        }
        throw new Error(errMessage);
      }

      if (!response.body) {
        throw new Error('Trình duyệt không hỗ trợ đọc luồng dữ liệu SSE (ReadableStream)');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let currentResult = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Giữ lại phần dở dang của dòng cuối

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed.startsWith('data:')) continue;
          const jsonStr = trimmed.slice(5).trim();
          if (!jsonStr) continue;

          try {
            const parsed = JSON.parse(jsonStr);

            if (parsed.type === 'error') {
              clearInterval(stepsInterval);
              setResult(null);
              setError(parsed.message || 'Lỗi xử lý pipeline thẩm định');
              setIsStreamingAi(false);
              setLoading(false);
              return;
            }

            if (parsed.type === 'logic_results') {
              // PHA 1: NHẬN NGAY LẬP TỨC TOÀN BỘ KẾT QUẢ LOGIC TỪ BACKEND
              // Tắt loading form để UI lập tức hiển thị 4 khối logic
              clearInterval(stepsInterval);
              setLoading(false);
              setIsStreamingAi(true);

              currentResult = {
                ...parsed.data,
                ai_report: '',
                is_streaming_ai: true
              };
              setResult(currentResult);

              // In toàn bộ ID và Object được sử dụng ra Console của Trình duyệt (Đã tắt hiển thị theo yêu cầu)
              const ENABLE_CONSOLE_LOG_IDS = false;
              if (ENABLE_CONSOLE_LOG_IDS && (parsed.data.used_objects || parsed.data.used_object_ids)) {
                console.group('🔍 [FEASIBILITY SCANNER] TOÀN BỘ ID & OBJECT ĐƯỢC SỬ DỤNG TRONG GIAO DIỆN 1');
                console.log('📌 Danh sách ID tóm tắt (All Used IDs):', parsed.data.used_object_ids || parsed.data.used_objects?.all_used_ids);
                console.log('🏛️ DB1 (Dân cư & Khu vực):', parsed.data.used_objects?.demographics);
                const compList = parsed.data.used_objects?.competitors || [];
                console.log(`🏬 DB2 (Toàn bộ ${compList.length} đối thủ qua Market Analyse Engine & LLM):`, compList);
                if (compList.length > 0) {
                  try {
                    console.table(compList.map(c => ({
                      id: c.id,
                      name: c.name,
                      distance: `${Math.round(c.distance_m || 0)}m`,
                      model_id: c.business_model_id,
                      weakness: c.weakness || '—'
                    })));
                  } catch {
                    // Fallback
                  }
                }
                console.log('🎯 DB5 (Phân khúc thị trường mục tiêu):', parsed.data.used_objects?.market_segment);
                console.log('⚠️ DB3 (Vấn đề cốt tử Playbook):', parsed.data.used_objects?.tactical_problems);
                console.log('💡 DB4 (Kinh nghiệm thực chiến Playbook):', parsed.data.used_objects?.tactical_experiences);
                console.log('🛡️ DB4 (Bài học hóa giải điểm yếu đối thủ):', parsed.data.used_objects?.market_lessons);
                console.groupEnd();
              }
            } else if (parsed.type === 'chunk') {
              // PHA 2: STREAMING TỪNG TỪ/TOKEN VÀO BÁO CÁO AI
              if (currentResult) {
                currentResult = {
                  ...currentResult,
                  ai_report: (currentResult.ai_report || '') + (parsed.text || ''),
                  is_streaming_ai: true
                };
                setResult({ ...currentResult });
              }
            } else if (parsed.type === 'done') {
              // KẾT THÚC STREAMING
              setIsStreamingAi(false);
              if (currentResult) {
                currentResult = {
                  ...currentResult,
                  is_streaming_ai: false
                };
                setResult({ ...currentResult });
                setIsCurrentReportSaved(false);
                if (currentUser) {
                  setShowSavePrompt(true);
                }
              }
            }
          } catch (jsonErr) {
            console.warn('Lỗi phân tích SSE packet:', jsonErr, jsonStr);
          }
        }
      }
    } catch (err) {
      clearInterval(stepsInterval);
      setError(err.message);
    } finally {
      clearInterval(stepsInterval);
      setLoading(false);
      setIsStreamingAi(false);
      setActiveStep(0);
    }
  };

  const formatVND = (amount) => {
    if (!amount) return '0 đ';
    return new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND' }).format(amount);
  };

  return (
    <div className="flex flex-col lg:flex-row h-full w-full overflow-hidden bg-slate-100">
      
      {/* ============================================================= */}
      {/* CỘT TRÁI: FORM ĐIỀN DỮ LIỆU FIT HẲN SANG MỘT BÊN (CHATGPT-STYLE) */}
      {/* ============================================================= */}
      <div className="w-full lg:w-[380px] xl:w-[410px] shrink-0 h-full overflow-y-auto border-r border-slate-200 bg-white p-5 space-y-4 shadow-xs">
        <div>
          <div className="flex items-center space-x-2 text-blue-600 mb-1">
            <Sparkles className="w-5 h-5" />
            <h2 className="font-bold text-slate-900 text-base lg:text-lg">Máy Quét Thẩm Định</h2>
          </div>
          <p className="text-[11px] text-slate-500">
            Kiểm tra tính khả thi trước khi bỏ vốn. Nhập đầy đủ 5 thông số bên dưới để chạy mô phỏng.
          </p>
        </div>

          <form onSubmit={handleEvaluate} className="space-y-4">
            
            {/* 1. Địa chỉ dự kiến */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                1. Địa chỉ / Vị trí dự kiến <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <MapPin className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="text"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="VD: đường, Quận/thành phố"
                  className="w-full pl-9 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none transition"
                  required
                />
              </div>
            </div>

            {/* 2. Mô hình kinh doanh (10 Mô hình) */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                2. Mô hình kinh doanh <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <Store className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <select
                  value={modelId}
                  onChange={(e) => handleModelChange(e.target.value)}
                  className={`w-full pl-9 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none transition appearance-none ${
                    !modelId ? 'text-slate-400' : 'text-slate-900'
                  }`}
                  required
                >
                  <option value="" disabled>-- Chọn mô hình kinh doanh --</option>
                  {metadata?.business_models?.map((m) => (
                    <option key={m.id} value={m.id} className="text-slate-900">
                      {m.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {/* 3. Nhóm sản phẩm định bán (Top 20) */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider">
                  3. Sản phẩm / Dịch vụ định bán (Chọn 1 - 3) <span className="text-red-500">*</span>
                </label>
                <span className={`text-[11px] font-medium ${selectedProductIds.length === 0 ? 'text-slate-400' : 'text-blue-600 font-semibold'}`}>
                  {selectedProductIds.length === 0 ? 'Chưa chọn' : `Đã chọn: ${selectedProductIds.length}/3`}
                </span>
              </div>
              {compatibilityNotice && (
                <div className="mb-2 p-2 rounded-lg bg-amber-50 border border-amber-200 text-amber-800 text-[11px] flex items-center gap-1.5 animate-fadeIn">
                  <AlertTriangle className="w-3.5 h-3.5 shrink-0 text-amber-600" />
                  <span>{compatibilityNotice}</span>
                </div>
              )}
              <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto p-1.5 bg-slate-50 rounded-xl border border-slate-200">
                {metadata?.products?.map((p) => {
                  const allowedList = modelId ? (MODEL_PRODUCT_COMPATIBILITY[parseInt(modelId)] || []) : null;
                  const isCompatible = !allowedList || allowedList.includes(p.id);
                  const isSelected = selectedProductIds.includes(p.id);
                  const isPrimary = isSelected && selectedProductIds[0] === p.id;
                  return (
                    <button
                      key={p.id}
                      type="button"
                      disabled={!isCompatible}
                      onClick={() => toggleProduct(p.id)}
                      title={!isCompatible ? 'Sản phẩm/dịch vụ không phù hợp với mô hình kinh doanh này' : isPrimary ? 'Sản phẩm/Dịch vụ chủ lực (Định hình dải giá & giờ vàng)' : isSelected ? 'Sản phẩm/Dịch vụ bán kèm' : p.name}
                      className={`text-xs px-2.5 py-1 rounded-lg font-medium transition flex items-center gap-1 ${
                        !isCompatible
                          ? 'bg-slate-100 text-slate-400 border border-slate-200 opacity-35 cursor-not-allowed'
                          : isPrimary
                            ? 'bg-blue-600 text-white shadow-sm ring-2 ring-blue-400/60 font-bold'
                            : isSelected
                              ? 'bg-indigo-600 text-white shadow-sm font-semibold'
                              : 'bg-white text-slate-700 hover:bg-slate-200 border border-slate-200'
                      }`}
                    >
                      {isPrimary && <span>★</span>}
                      {isSelected && !isPrimary && <span className="text-[10px] opacity-80">+</span>}
                      <span>{p.name}</span>
                    </button>
                  );
                })}
              </div>

              {/* Tóm tắt cơ cấu Sản phẩm chủ lực & Bán kèm */}
              {selectedProductIds.length > 0 && (
                <div className="mt-2 p-2 rounded-lg bg-blue-50/70 border border-blue-100 text-[11px] space-y-1">
                  <div className="flex items-center justify-between text-slate-600 font-semibold">
                    <span>Cơ cấu sản phẩm & dịch vụ:</span>
                    <span className="text-[10px] text-blue-700 font-normal">
                      * Sản phẩm/dịch vụ chủ lực định hình dải giá & giờ vàng
                    </span>
                  </div>
                  <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                    {selectedProductIds.map((pid, idx) => {
                      const prod = metadata?.products?.find(p => p.id === pid);
                      const isPrimary = idx === 0;
                      return (
                        <span
                          key={pid}
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md ${
                            isPrimary
                              ? 'bg-blue-600 text-white font-bold shadow-2xs'
                              : 'bg-white text-slate-700 border border-slate-200'
                          }`}
                        >
                          <span>{isPrimary ? '★ Chủ lực: ' : '➕ Bán kèm: '}</span>
                          <strong>{prod?.name || pid}</strong>
                          {!isPrimary && (
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setPrimaryProduct(pid);
                              }}
                              title="Đặt làm sản phẩm/dịch vụ chủ lực"
                              className="ml-1 text-[10px] text-blue-600 hover:text-blue-800 underline font-semibold cursor-pointer"
                            >
                              (Đổi làm chính)
                            </button>
                          )}
                        </span>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* 4. Số vốn hiện có */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                4. Số vốn khởi nghiệp hiện có (VNĐ) <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <DollarSign className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="number"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  placeholder="Ví dụ: 150000000"
                  step="5000000"
                  min="10000000"
                  className="w-full pl-9 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none transition"
                  required
                />
              </div>
              {budget && Number(budget) > 0 ? (
                <div className="text-[11px] text-slate-500 mt-1 font-medium">
                  Tương đương: <span className="text-blue-700 font-bold">{formatVND(budget)}</span>
                </div>
              ) : null}
            </div>

            {/* 5. Giá thuê mặt bằng (Bắt buộc, cho phép nhập 0) */}
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                5. Tiền thuê mặt bằng dự kiến (VNĐ/tháng) <span className="text-red-500">*</span>
              </label>
              <div className="relative">
                <DollarSign className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
                <input
                  type="number"
                  value={rent}
                  onChange={(e) => setRent(e.target.value)}
                  placeholder="VD: 10000000 (Nhập 0 nếu có sẵn mặt bằng)"
                  step="500000"
                  min="0"
                  className="w-full pl-9 pr-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm font-semibold text-slate-900 focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none transition"
                  required
                />
              </div>
              {rent !== '' && !isNaN(Number(rent)) && Number(rent) >= 0 ? (
                <div className="text-[11px] text-slate-500 mt-1 font-medium">
                  Tương đương: <span className="text-blue-700 font-bold">{Number(rent) === 0 ? '0 đ (Có sẵn mặt bằng / Bán online / Điểm bán 0 đồng)' : `${formatVND(rent)}/tháng`}</span>
                </div>
              ) : (
                <div className="text-[10px] text-slate-400 mt-1">
                  * Bắt buộc nhập (nhập 0 nếu có sẵn mặt bằng hoặc bán online)
                </div>
              )}
            </div>

            {/* Nút bấm chạy Pipeline */}
            <button
              type="submit"
              disabled={loading || isStreamingAi || !isFormValid}
              className={`w-full py-3.5 px-4 rounded-xl font-bold text-sm text-white flex items-center justify-center space-x-2 shadow-lg transition duration-200 ${
                loading || isStreamingAi || !isFormValid
                  ? 'bg-slate-300 text-slate-500 cursor-not-allowed shadow-none'
                  : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-blue-500/25 active:scale-[0.99]'
              }`}
            >
              {loading ? (
                <>
                  <RefreshCw className="w-4 h-4 animate-spin" />
                  <span>Đang tính toán dữ liệu logic...</span>
                </>
              ) : isStreamingAi ? (
                <>
                  <Sparkles className="w-4 h-4 animate-spin text-blue-200" />
                  <span>AI đang sinh kế hoạch tác chiến...</span>
                </>
              ) : (
                <>
                  <span>⚡ Quét Thẩm Định Ý Tưởng Ngay</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
            {!isFormValid && !loading && !isStreamingAi && (
              <p className="text-[11px] text-center text-slate-400">
                * Vui lòng điền đủ 5 mục (Địa chỉ, Mô hình, Món, Vốn, Tiền thuê)
              </p>
            )}

          </form>
      </div>

      {/* ============================================================= */}
      {/* CỘT PHẢI: KHÔNG GIAN HIỂN THỊ KẾ HOẠCH & BÁO CÁO (CUỘN ĐỘC LẬP) */}
      {/* ============================================================= */}
      <div className="flex-1 h-full overflow-y-auto p-4 sm:p-6 lg:p-8 bg-slate-50">
        <div className="max-w-4xl xl:max-w-5xl mx-auto space-y-5">
        
        {/* TRẠNG THÁI LOADING PIPELINE */}
        {loading && (
          <div className="bg-white rounded-2xl p-8 border border-slate-200 shadow-sm text-center space-y-6 animate-pulse">
            <div className="w-16 h-16 rounded-full bg-blue-50 border-4 border-blue-600 border-t-transparent animate-spin mx-auto flex items-center justify-center"></div>
            <div>
              <h3 className="font-bold text-slate-900 text-base">Hệ Thống Đang Phân Tích Toàn Diện...</h3>
              <p className="text-xs text-slate-500 mt-1">Đang so khớp dữ liệu thị trường thực tế và phân tích dòng tiền sinh tồn...</p>
            </div>
            
            {/* Thanh hiển thị các bước */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 text-left text-xs pt-4 border-t border-slate-100">
              <div className={`p-2 rounded-lg border ${activeStep >= 0 ? 'bg-blue-50 border-blue-200 text-blue-800' : 'bg-slate-50 border-slate-200 text-slate-400'}`}>
                <div className="font-bold">1. Thử Tải Dòng Tiền</div>
                <div className="text-[10px]">Đo Lường Runway</div>
              </div>
              <div className={`p-2 rounded-lg border ${activeStep >= 1 ? 'bg-blue-50 border-blue-200 text-blue-800' : 'bg-slate-50 border-slate-200 text-slate-400'}`}>
                <div className="font-bold">2. Quét Đối Thủ</div>
                <div className="text-[10px]">Bán Kính 1km</div>
              </div>
              <div className={`p-2 rounded-lg border ${activeStep >= 2 ? 'bg-blue-50 border-blue-200 text-blue-800' : 'bg-slate-50 border-slate-200 text-slate-400'}`}>
                <div className="font-bold">3. Mục Tiêu Tấn Công</div>
                <div className="text-[10px]">Điểm Yếu, Giá, Giờ</div>
              </div>
              <div className={`p-2 rounded-lg border ${activeStep >= 3 ? 'bg-blue-50 border-blue-200 text-blue-800' : 'bg-slate-50 border-slate-200 text-slate-400'}`}>
                <div className="font-bold">4. Vấn Đề & Bài Học</div>
                <div className="text-[10px]">Cạm Bẫy Thực Tế</div>
              </div>
              <div className={`p-2 rounded-lg border ${activeStep >= 4 ? 'bg-blue-50 border-blue-200 text-blue-800' : 'bg-slate-50 border-slate-200 text-slate-400'}`}>
                <div className="font-bold">5. Cố Vấn Chiến Lược</div>
                <div className="text-[10px]">Tổng Hợp Báo Cáo</div>
              </div>
            </div>
          </div>
        )}

        {/* LỖI NẾU CÓ */}
        {error && (
          <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-sm flex items-start space-x-3">
            <AlertTriangle className="w-5 h-5 flex-shrink-0 text-red-600 mt-0.5" />
            <div>
              <div className="font-bold">Lỗi xử lý:</div>
              <div>{error}</div>
            </div>
          </div>
        )}

        {/* TRẠNG THÁI CHỜ BAN ĐẦU (EMPTY STATE) */}
        {!loading && !result && (
          <div className="bg-white rounded-2xl p-8 sm:p-10 border border-slate-200 border-dashed text-center space-y-4">
            <div className="w-14 h-14 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mx-auto">
              <Search className="w-7 h-7" />
            </div>
            <div>
              <h3 className="font-bold text-slate-800 text-base">Chưa có dữ liệu thẩm định</h3>
              <p className="text-xs text-slate-500 max-w-md mx-auto mt-1">
                Hãy điền địa chỉ, số vốn và mô hình bên cột trái rồi bấm nút <strong>"Quét Thẩm Định Ý Tưởng Ngay"</strong> để nhận bản báo cáo 5 khối thực chiến.
              </p>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2.5 pt-4 max-w-2xl mx-auto text-left">
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                <span className="font-bold text-slate-800 block">⏱️ 1. Dòng Tiền</span>
                <span className="text-[10px] text-slate-500">Đo số tháng sinh tồn của vốn</span>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                <span className="font-bold text-slate-800 block">🏬 2. Đối Thủ 1KM</span>
                <span className="text-[10px] text-slate-500">Quét mật độ & đối thủ trực diện</span>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                <span className="font-bold text-slate-800 block">🎯 3. Tấn Công</span>
                <span className="text-[10px] text-slate-500">Tử huyệt, dải giá & giờ vàng</span>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                <span className="font-bold text-slate-800 block">💡 4. Vấn Đề & Mẹo</span>
                <span className="text-[10px] text-slate-500">4 Cạm bẫy DB3 & 4 Bài học DB4</span>
              </div>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-100 text-xs">
                <span className="font-bold text-slate-800 block">🤖 5. Báo Cáo AI</span>
                <span className="text-[10px] text-slate-500">Chiến lược thực chiến sâu</span>
              </div>
            </div>
          </div>
        )}

        {/* HIỂN THỊ KẾT QUẢ THẨM ĐỊNH */}
        {result && (() => {
          const stressList = Array.isArray(result.stress_test) 
            ? result.stress_test 
            : (result.stress_test ? [result.stress_test] : []);
          const normalScen = stressList.find(s => s.scenario === 'normal') || stressList[0] || {};
          const premiumScen = stressList.find(s => s.scenario === 'premium');
          const currentScen = scenarioTab === 'premium' && premiumScen ? premiumScen : normalScen;
          const rawRunway = currentScen.month !== undefined 
            ? Number(currentScen.month) 
            : (currentScen.runway_months !== undefined ? Number(currentScen.runway_months) : 0);
          const runwayMonths = Math.max(0, Math.floor(rawRunway));
          const isRedAlert = Number(normalScen.month || 0) <= 0;

          return (
            <div className="space-y-6">
            
            {/* 1. THÔNG BÁO NẾU ĐANG XEM CHIẾN LƯỢC ĐÃ LƯU TRƯỚC ĐÓ */}
            {savedStrategy && (
              <div className="p-4 rounded-2xl bg-gradient-to-r from-blue-50 via-indigo-50 to-blue-50 border border-blue-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 shadow-sm">
                <div className="flex items-center space-x-3">
                  <div className="p-2.5 bg-blue-600 text-white rounded-xl shadow-sm shrink-0">
                    <BookmarkCheck className="w-5 h-5" />
                  </div>
                  <div>
                    <div className="flex items-center space-x-2">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                        Kế Sách Đã Lưu Trong CSDL
                      </span>
                      {savedStrategy.updated_at && (
                        <span className="text-[11px] text-slate-500">
                          (Cập nhật: {new Date(savedStrategy.updated_at).toLocaleDateString('vi-VN')})
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-slate-700 mt-0.5 break-words">
                      Vị trí: <strong className="text-slate-900">{savedStrategy.address}</strong>
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {isCurrentReportSaved ? (
                    <span className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center space-x-1.5 shadow-2xs">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      <span>Đã lưu vào hồ sơ</span>
                    </span>
                  ) : (
                    !showSavePrompt && (
                      <button
                        type="button"
                        onClick={() => setShowSavePrompt(true)}
                        className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-white border border-blue-200 text-blue-700 hover:bg-blue-50 shadow-2xs transition"
                      >
                        Lưu / Cập nhật kế sách
                      </button>
                    )
                  )}
                  <div className="text-[10px] text-slate-400 italic">
                    Có thể nhập mức vốn / tiền thuê mới bên trái để thử tải lại.
                  </div>
                </div>
              </div>
            )}

            {/* 2. PROMPT HỎI LƯU KẾ SÁCH (KHI CÓ KẾ HOẠCH VÀ ĐÃ ĐĂNG NHẬP VÀ CHƯA LƯU) */}
            {showSavePrompt && currentUser && !isCurrentReportSaved && (
              <div className="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-amber-50 to-orange-50 border-2 border-amber-300 shadow-sm flex flex-col md:flex-row md:items-center md:justify-between gap-4 animate-fade-in">
                <div className="flex items-start space-x-3">
                  <div className="p-2 bg-amber-500 text-white rounded-xl mt-0.5 shrink-0 shadow-sm">
                    <Sparkles className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-slate-900">
                      Bạn có muốn lưu kế sách này vào hồ sơ cá nhân không?
                    </h4>
                    <p className="text-xs text-slate-600 mt-1 leading-relaxed break-words">
                      Hệ thống sẽ tự động lưu địa chỉ, tọa độ, mô hình, danh mục món và toàn bộ số liệu giả lập (vốn, mặt bằng, nhân sự, tệp khách hàng) vào tài khoản <strong>{currentUser.username}</strong> để xem lại bất cứ lúc nào và đồng bộ sang Giao diện 2 (Trợ lý) & Giao diện 3 (Hồ sơ quán).
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2 self-end md:self-center shrink-0">
                  <button
                    type="button"
                    onClick={() => setShowSavePrompt(false)}
                    className="px-3.5 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200 transition"
                  >
                    Bỏ qua
                  </button>
                  <button
                    type="button"
                    disabled={savingStrategy}
                    onClick={handleInitiateSave}
                    className="px-4 py-2 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-md shadow-blue-500/25 flex items-center space-x-1.5 transition active:scale-[0.98] disabled:opacity-50"
                  >
                    {savingStrategy ? (
                      <span>Đang lưu...</span>
                    ) : (
                      <>
                        <Bookmark className="w-4 h-4" />
                        <span>Lưu Kế Sách Ngay</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}

            {/* 3. MODAL HỎI CHỌN KỊCH BẢN KHI CÓ CẢ HAI (NORMAL & PREMIUM) */}
            {showScenarioModal && (() => {
              const currentReport = result || savedStrategy?.report_result;
              const stressList = Array.isArray(currentReport?.stress_test) ? currentReport.stress_test : [];
              const normalScen = stressList.find(s => s.scenario === 'normal') || stressList[0] || {};
              const premiumScen = stressList.find(s => s.scenario === 'premium') || {};

              return (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-5 bg-slate-900/60 backdrop-blur-xs animate-fade-in">
                  <div 
                    className="bg-white w-full max-w-xl rounded-3xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden"
                    onClick={e => e.stopPropagation()}
                  >
                    {/* Header Modal */}
                    <div className="px-6 py-4 bg-gradient-to-r from-blue-700 via-indigo-700 to-slate-900 text-white flex items-center justify-between shrink-0 shadow-sm">
                      <div className="flex items-center space-x-2.5">
                        <div className="p-2 rounded-xl bg-white/10 text-white border border-white/15">
                          <Sparkles className="w-5 h-5 text-amber-300" />
                        </div>
                        <div>
                          <h3 className="font-extrabold text-base sm:text-lg tracking-tight">
                            Chọn Kịch Bản Lưu Vào Hồ Sơ Quán
                          </h3>
                          <p className="text-xs text-blue-100/80 font-normal mt-0.5">
                            Phát hiện 2 kịch bản khả thi. Vui lòng chọn bản bạn muốn áp dụng:
                          </p>
                        </div>
                      </div>
                      <button 
                        type="button"
                        onClick={() => setShowScenarioModal(false)}
                        className="p-1.5 rounded-lg hover:bg-white/10 text-white/70 hover:text-white transition"
                      >
                        ✕
                      </button>
                    </div>

                    {/* Nội dung 2 Thẻ kịch bản */}
                    <div className="p-5 sm:p-6 space-y-3.5 overflow-y-auto max-h-[70vh]">
                      {/* Card 1: Normal Scenario */}
                      <div 
                        onClick={() => setChosenScenarioToSave('normal')}
                        className={`p-4 rounded-2xl border-2 cursor-pointer transition-all ${
                          chosenScenarioToSave === 'normal' 
                            ? 'border-blue-600 bg-blue-50/60 shadow-md ring-2 ring-blue-500/20' 
                            : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center space-x-2.5">
                            <input 
                              type="radio"
                              name="chosenScenario"
                              value="normal"
                              checked={chosenScenarioToSave === 'normal'}
                              onChange={() => setChosenScenarioToSave('normal')}
                              className="w-4 h-4 text-blue-600 focus:ring-blue-500 cursor-pointer"
                            />
                            <div>
                              <span className="font-bold text-slate-900 text-sm">Kịch bản Thông thường (Normal)</span>
                              <span className="ml-2 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700">
                                Phổ thông & Tinh gọn
                              </span>
                            </div>
                          </div>
                        </div>
                        <p className="text-xs text-slate-500 mt-2 ml-6">
                          Vận hành chuẩn quy mô bình dân, tối ưu vốn khởi điểm và đảm bảo sinh tồn bền bỉ.
                        </p>
                        <div className="grid grid-cols-3 gap-2 mt-3 ml-6 pt-2.5 border-t border-slate-200/80 text-xs">
                          <div>
                            <span className="text-[10px] text-slate-400 block font-medium">Capex sàn:</span>
                            <span className="font-bold text-slate-800">{formatVND(normalScen.capex)}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block font-medium">Định phí/tháng:</span>
                            <span className="font-bold text-slate-800">{formatVND(normalScen.monthly_fixed_cost)}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block font-medium">Runway sinh tồn:</span>
                            <span className="font-extrabold text-blue-700">{normalScen.month || 0} tháng</span>
                          </div>
                        </div>
                        <div className="mt-2 ml-6 text-[11px] text-slate-500">
                          Nhân sự vận hành: <strong className="text-slate-700">{normalScen.staff_count ?? 1} người</strong> (đã tính cả chủ cơ sở)
                        </div>
                      </div>

                      {/* Card 2: Premium Scenario */}
                      <div 
                        onClick={() => setChosenScenarioToSave('premium')}
                        className={`p-4 rounded-2xl border-2 cursor-pointer transition-all ${
                          chosenScenarioToSave === 'premium' 
                            ? 'border-indigo-600 bg-indigo-50/60 shadow-md ring-2 ring-indigo-500/20' 
                            : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/50'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center space-x-2.5">
                            <input 
                              type="radio"
                              name="chosenScenario"
                              value="premium"
                              checked={chosenScenarioToSave === 'premium'}
                              onChange={() => setChosenScenarioToSave('premium')}
                              className="w-4 h-4 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
                            />
                            <div>
                              <span className="font-bold text-slate-900 text-sm">Kịch bản Nâng cao (Premium)</span>
                              <span className="ml-2 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-700">
                                Đầu tư mở rộng (+1 NV)
                              </span>
                            </div>
                          </div>
                        </div>
                        <p className="text-xs text-slate-500 mt-2 ml-6">
                          Đầu tư thiết bị chuyên sâu (+40% Capex), bổ sung thêm nhân sự phục vụ (+1 NV) và nâng tầm giỏ hàng.
                        </p>
                        <div className="grid grid-cols-3 gap-2 mt-3 ml-6 pt-2.5 border-t border-slate-200/80 text-xs">
                          <div>
                            <span className="text-[10px] text-slate-400 block font-medium">Capex đầu tư:</span>
                            <span className="font-bold text-slate-800">{formatVND(premiumScen.capex)}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block font-medium">Định phí/tháng:</span>
                            <span className="font-bold text-slate-800">{formatVND(premiumScen.monthly_fixed_cost)}</span>
                          </div>
                          <div>
                            <span className="text-[10px] text-slate-400 block font-medium">Runway sinh tồn:</span>
                            <span className="font-extrabold text-indigo-700">{premiumScen.month || 0} tháng</span>
                          </div>
                        </div>
                        <div className="mt-2 ml-6 text-[11px] text-slate-500">
                          Nhân sự vận hành: <strong className="text-slate-700">{premiumScen.staff_count ?? 2} người</strong> (đã tính cả chủ cơ sở)
                        </div>
                      </div>
                    </div>

                    {/* Footer Modal */}
                    <div className="px-6 py-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-end space-x-2.5 shrink-0">
                      <button
                        type="button"
                        disabled={savingStrategy}
                        onClick={() => setShowScenarioModal(false)}
                        className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-200/80 transition"
                      >
                        Hủy
                      </button>
                      <button
                        type="button"
                        disabled={savingStrategy}
                        onClick={() => executeSaveStrategy(chosenScenarioToSave)}
                        className="px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-blue-600 hover:bg-blue-700 shadow-md shadow-blue-500/25 flex items-center space-x-1.5 transition active:scale-[0.98] disabled:opacity-50"
                      >
                        {savingStrategy ? (
                          <span>Đang lưu...</span>
                        ) : (
                          <>
                            <Bookmark className="w-4 h-4" />
                            <span>Xác nhận lưu kịch bản này</span>
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* 4. THÔNG BÁO LƯU THÀNH CÔNG */}
            {saveSuccessMessage && (
              <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-semibold flex items-center justify-between shadow-xs">
                <div className="flex items-center space-x-2">
                  <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                  <span>{saveSuccessMessage}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setSaveSuccessMessage(null)}
                  className="text-emerald-700 hover:text-emerald-900 text-xs underline font-normal"
                >
                  Đóng
                </button>
              </div>
            )}

            {/* THẺ TỔNG QUAN VỊ TRÍ & DÂN CƯ (DB1) */}
            <div className="bg-gradient-to-r from-blue-900 to-indigo-950 text-white rounded-2xl p-5 shadow-sm space-y-3">
              <div className="flex items-center justify-between text-xs">
                <span className="px-2.5 py-1 rounded-md bg-white/10 text-blue-200 font-semibold uppercase tracking-wider">
                  Khảo sát địa bàn vi mô
                </span>
                <span className="text-slate-300">
                  Tọa độ: [{result.location_info?.coordinates ? result.location_info.coordinates.join(', ') : 'N/A'}]
                </span>
              </div>
              <div>
                <h3 className="text-lg font-extrabold">{result.location_info?.recognized_area || address}</h3>
                <p className="text-xs text-blue-200 mt-0.5">
                  Mật độ: <strong>{result.demographics?.population_density ? `${result.demographics.population_density.toLocaleString()} người/km²` : 'N/A'}</strong> | Khách chủ lực: <strong>{result.demographics?.dominant_age || 'N/A'}</strong> | Thu nhập: <strong>{result.demographics?.income_level || 'N/A'}</strong>
                </p>
              </div>
            </div>

            {/* KHỐI 1: KẾT QUẢ THỬ TẢI SINH TỒN & DÒNG TIỀN (ZERO-REVENUE RUNWAY) */}
            {isRedAlert ? (
              <div className="bg-gradient-to-br from-red-50 via-rose-50 to-red-100 border-2 border-red-500 rounded-2xl p-5 sm:p-6 shadow-md space-y-4 animate-fade-in">
                    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-red-200">
                      <div className="flex items-center space-x-2 text-red-700">
                        <ShieldAlert className="w-6 h-6 text-red-600 shrink-0" />
                        <h4 className="font-extrabold text-base text-red-950">
                          1. THỬ TẢI SINH TỒN: CẢNH BÁO ĐỎ TÀI CHÍNH
                        </h4>
                      </div>
                      <span className="px-3 py-1 rounded-full text-xs font-black uppercase tracking-wider bg-red-600 text-white shadow-sm self-start sm:self-auto animate-pulse">
                        🚨 CẠN VỐN NGÀY 0 (RUNWAY: 0.0 THÁNG)
                      </span>
                    </div>

                    <div className="p-4 bg-white/80 rounded-xl border border-red-200 text-xs text-red-900 leading-relaxed font-medium">
                      ⚠️ <strong>BÁO ĐỘNG ĐỎ VỀ DÒNG TIỀN:</strong> Số vốn hiện có ({formatVND(budget)}) không đủ chạm ngưỡng chi phí đầu tư thiết lập ban đầu (Capex sàn) hoặc sẽ cạn kiệt ngay trong tháng đầu tiên nếu không phát sinh doanh thu. Nguy cơ đóng cửa phá sản ngày 0 là cực cao!
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                      <div className="p-3 bg-white rounded-xl border border-red-200 shadow-2xs">
                        <span className="text-[11px] text-slate-500 block font-medium">Vốn Khởi Nghiệp</span>
                        <span className="text-sm sm:text-base font-black text-slate-900 mt-1 block">
                          {formatVND(budget)}
                        </span>
                        <span className="text-[10px] text-slate-400 font-medium">Số vốn đăng ký</span>
                      </div>

                      <div className="p-3 bg-white rounded-xl border border-red-200 shadow-2xs">
                        <span className="text-[11px] text-slate-500 block font-medium">Capex Tối Thiểu</span>
                        <span className="text-sm sm:text-base font-black text-red-600 mt-1 block">
                          {formatVND(normalScen.capex)}
                        </span>
                        <span className="text-[10px] text-red-500 font-medium">Chi phí setup sàn</span>
                      </div>

                      <div className="p-3 bg-white rounded-xl border border-red-200 shadow-2xs">
                        <span className="text-[11px] text-slate-500 block font-medium">Định Phí Tháng Đầu</span>
                        <span className="text-sm sm:text-base font-black text-red-600 mt-1 block">
                          {formatVND(normalScen.monthly_fixed_cost)}
                        </span>
                        <span className="text-[10px] text-red-500 font-medium">Mặt bằng + Lương + Điện</span>
                      </div>

                      <div className="p-3 bg-white rounded-xl border border-red-200 shadow-2xs">
                        <span className="text-[11px] text-slate-500 block font-medium">Runway Sinh Tồn</span>
                        <span className="text-base sm:text-lg font-black text-red-700 mt-0.5 block">
                          0.0 Tháng
                        </span>
                        <span className="text-[10px] text-red-500 font-medium">Zero-revenue</span>
                      </div>
                    </div>

                    <div className="p-3.5 bg-red-100/70 rounded-xl text-xs text-red-950 font-medium leading-relaxed border border-red-200">
                      💡 <strong>Khuyến nghị tái cấu trúc dòng tiền:</strong> Bạn cần chuẩn bị tối thiểu <strong>{formatVND((normalScen.capex || 0) + (normalScen.monthly_fixed_cost || 0) * 3)}</strong> để bảo đảm chi phí setup và ít nhất 3 tháng định phí dự phòng, hoặc chuyển sang mô hình có chi phí sàn thấp hơn trước khi quyết định thuê mặt bằng.
                    </div>
                  </div>
                ) : (
                <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-sm space-y-4">
                  {(() => {
                    const isPremium = scenarioTab === 'premium';
                    let badgeText = '';
                    let badgeClass = '';

                    if (isPremium) {
                      if (runwayMonths >= 3) {
                        badgeText = 'MẠO HIỂM CÓ KIỂM SOÁT';
                        badgeClass = 'bg-purple-50 text-purple-700 border-purple-200';
                      } else if (runwayMonths >= 1) {
                        badgeText = 'MẠO HIỂM';
                        badgeClass = 'bg-amber-50 text-amber-800 border-amber-300';
                      } else {
                        badgeText = 'RỦI RO CỰC CAO';
                        badgeClass = 'bg-rose-50 text-rose-700 border-rose-200';
                      }
                    } else {
                      if (runwayMonths >= 3) {
                        badgeText = 'AN TOÀN CAO';
                        badgeClass = 'bg-emerald-50 text-emerald-700 border-emerald-200';
                      } else if (runwayMonths >= 1) {
                        badgeText = 'THẬN TRỌNG';
                        badgeClass = 'bg-amber-50 text-amber-700 border-amber-200';
                      } else {
                        badgeText = 'RỦI RO CAO';
                        badgeClass = 'bg-rose-50 text-rose-700 border-rose-200';
                      }
                    }

                    return (
                      <>
                        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 pb-3 border-b border-slate-100">
                          <div className="flex items-center space-x-2">
                            <ShieldAlert className="w-5 h-5 text-indigo-600 shrink-0" />
                            <h4 className="font-bold text-slate-900 text-sm sm:text-base">
                              1. Kết Quả Thử Tải Sinh Tồn (Zero-Revenue Runway)
                            </h4>
                          </div>
                          <div className="flex items-center space-x-2">
                            {premiumScen && (
                              <div className="flex bg-slate-100 p-0.5 rounded-lg text-xs font-semibold">
                                <button
                                  type="button"
                                  onClick={() => setScenarioTab('normal')}
                                  className={`px-2.5 py-1 rounded-md transition ${scenarioTab === 'normal' ? 'bg-white shadow-xs text-blue-700 font-bold' : 'text-slate-600 hover:text-slate-900'}`}
                                >
                                  Phổ thông
                                </button>
                                <button
                                  type="button"
                                  onClick={() => setScenarioTab('premium')}
                                  className={`px-2.5 py-1 rounded-md transition ${scenarioTab === 'premium' ? 'bg-white shadow-xs text-indigo-700 font-bold' : 'text-slate-600 hover:text-slate-900'}`}
                                >
                                  Nâng cao (Mạo hiểm)
                                </button>
                              </div>
                            )}
                            <span className={`text-xs px-2.5 py-1 rounded-full font-bold border ${badgeClass}`}>
                              {badgeText}
                            </span>
                          </div>
                        </div>

                        {/* THIẾT KẾ MỚI: TÁCH RIÊNG RUNWAY CỐT LÕI VÀ BẢNG THÔNG SỐ GIẢ LẬP */}
                        <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 items-stretch">
                          {/* CỘT 1: CHỈ SỐ SỐNG CÒN QUAN TRỌNG NHẤT (RUNWAY CẦM CỰ) */}
                          <div className="lg:col-span-5 bg-gradient-to-br from-blue-50/90 via-indigo-50/50 to-white p-5 rounded-2xl border-2 border-blue-200 shadow-xs flex flex-col justify-between">
                            <div>
                              <div className="flex items-center justify-between pb-2 border-b border-blue-100">
                                <span className="text-xs font-black uppercase tracking-wider text-blue-900 flex items-center gap-1.5">
                                  <Activity className="w-4 h-4 text-blue-600 shrink-0" />
                                  Sức Cầm Cự Dòng Tiền (Runway)
                                </span>
                                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-blue-100 text-blue-800">
                                  Chỉ số cốt lõi
                                </span>
                              </div>

                              <div className="mt-4 flex items-baseline gap-2">
                                <span className="text-5xl font-black text-blue-700 tracking-tight">
                                  {runwayMonths}
                                </span>
                                <span className="text-base font-bold text-slate-700">tháng</span>
                                {rawRunway > 0 && rawRunway < 1 && (
                                  <span className="text-[10px] font-bold text-rose-600 bg-rose-50 px-2 py-0.5 rounded-md border border-rose-200 ml-1">
                                    Dưới 1 tháng
                                  </span>
                                )}
                              </div>

                              <p className="text-[11px] text-slate-600 mt-2 leading-relaxed font-medium">
                                Khả năng sống sót tối đa với <strong>0đ doanh thu</strong> sau khi đã thanh toán toàn bộ chi phí thiết lập mặt bằng (Capex) và định phí hàng tháng.
                              </p>
                            </div>

                            <div className="mt-4 pt-3 border-t border-blue-100 flex items-center justify-between text-xs">
                              <span className="text-slate-500 font-medium">Mức độ an toàn vốn:</span>
                              <span className={`px-2.5 py-0.5 rounded-full font-black text-[11px] border ${badgeClass}`}>
                                {badgeText}
                              </span>
                            </div>
                          </div>

                          {/* CỘT 2: BẢNG THÔNG SỐ MÔ PHỎNG GIẢ LẬP (Simulation Assumptions) */}
                          <div className="lg:col-span-7 bg-slate-50/80 p-4 sm:p-5 rounded-2xl border border-slate-200 flex flex-col justify-between">
                            <div>
                              <div className="flex items-center justify-between pb-2 mb-3 border-b border-slate-200">
                                <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                                  <Sliders className="w-4 h-4 text-slate-500 shrink-0" />
                                  Bảng Thông Số Mô Phỏng Giả Lập
                                </span>
                                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
                                  Thông số giả định
                                </span>
                              </div>

                              <div className="grid grid-cols-3 gap-2.5 text-center">
                                <div className="bg-white p-2.5 rounded-xl border border-slate-200/80 shadow-2xs">
                                  <span className="text-[10px] text-slate-400 block font-semibold">[Giả lập] Capex</span>
                                  <span className="text-xs sm:text-sm font-extrabold text-slate-900 block mt-0.5">
                                    {formatVND(currentScen.capex)}
                                  </span>
                                  <span className="text-[9px] text-slate-400 block mt-0.5">setup ban đầu</span>
                                </div>

                                <div className="bg-white p-2.5 rounded-xl border border-slate-200/80 shadow-2xs">
                                  <span className="text-[10px] text-slate-400 block font-semibold">[Giả lập] Định Phí</span>
                                  <span className="text-xs sm:text-sm font-extrabold text-indigo-700 block mt-0.5">
                                    {formatVND(currentScen.monthly_fixed_cost)}
                                  </span>
                                  <span className="text-[9px] text-slate-400 block mt-0.5">mặt bằng & nhân sự</span>
                                </div>

                                <div className="bg-white p-2.5 rounded-xl border border-slate-200/80 shadow-2xs">
                                  <span className="text-[10px] text-slate-400 block font-semibold">[Giả lập] Đơn AOV</span>
                                  <span className="text-xs sm:text-sm font-extrabold text-emerald-600 block mt-0.5">
                                    {formatVND(currentScen.aov)}
                                  </span>
                                  <span className="text-[9px] text-slate-400 block mt-0.5">trung bình / bill</span>
                                </div>
                              </div>
                            </div>

                            <div className="mt-3 pt-2 text-[11px] text-slate-500 flex flex-wrap items-center justify-between gap-1.5 border-t border-slate-200/80">
                              <span>Nhân sự vận hành: <strong>{currentScen.staff_count ?? 1} người</strong> (đã tính chủ cơ sở) | Điện nước: <strong>{formatVND(currentScen.utilities_cost)}</strong></span>
                              <span className="text-[10px] italic text-slate-400">* Các thông số trên là cơ sở giả định tính thử tải</span>
                            </div>
                          </div>
                        </div>
                      </>
                    );
                  })()}
                </div>
            )}

            {/* KHỐI 2: BẢN ĐỒ & PHÂN TÍCH ĐỐI THỦ 1KM (DB2) */}
            {!isRedAlert && result.competitors_summary && (() => {
              const compList = result.competitors_summary?.list || [];
              const totalComp = result.competitors_summary?.total_nearby || compList.length;
              const directIds = new Set(result.market_analysis?.direct_competitors?.ids || []);
              const directCount = compList.filter(c => 
                Boolean(c.is_direct || directIds.has(String(c._id || c.id || '')) || (c.cts_score && c.cts_score >= 65))
              ).length;
              const compLevel = result.market_analysis?.competition_level || 'Trung bình';

              return (
                <div className="bg-white rounded-2xl p-5 sm:p-6 border border-slate-200 shadow-sm space-y-4">
                  <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-3 border-b border-slate-100">
                    <div className="flex items-center space-x-2">
                      <Store className="w-5 h-5 text-amber-600 shrink-0" />
                      <h4 className="font-bold text-slate-900 text-sm sm:text-base">
                        2. Phân Tích Đối Thủ Xung Quanh 1KM
                      </h4>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-xs px-2.5 py-1 rounded-full font-bold bg-amber-50 text-amber-700 border border-amber-200">
                        {totalComp} đối thủ lân cận
                      </span>
                      <span className="text-xs px-2.5 py-1 rounded-full font-bold bg-blue-50 text-blue-700 border border-blue-200">
                        Cạnh tranh: {compLevel}
                      </span>
                    </div>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-slate-50 text-slate-600 font-semibold border-b border-slate-200">
                        <tr>
                          <th className="py-2.5 px-3">Tên Quán Đối Thủ</th>
                          <th className="py-2.5 px-3">Khoảng Cách</th>
                          <th className="py-2.5 px-3">Dải Giá</th>
                          <th className="py-2.5 px-3">Điểm Yếu Bị Khách Phàn Nàn</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {compList.map((c, idx) => {
                          const isDirect = Boolean(
                            c.is_direct || 
                            directIds.has(String(c._id || c.id || '')) || 
                            (c.cts_score && c.cts_score >= 65)
                          );

                          return (
                            <tr key={idx} className={`hover:bg-slate-50 transition ${isDirect ? 'bg-rose-50/30' : ''}`}>
                              <td className="py-2.5 px-3">
                                <div className="flex items-center flex-wrap gap-1.5">
                                  <span className="font-semibold text-slate-800">{c.name}</span>
                                  {isDirect ? (
                                    <span className="inline-flex items-center gap-1 text-[10px] bg-rose-100 text-rose-800 px-2 py-0.5 rounded-full font-black border border-rose-200 shadow-2xs">
                                      ⚡ Đối thủ trực tiếp
                                    </span>
                                  ) : (
                                    <span className="inline-flex items-center text-[9px] bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded font-medium">
                                      Gián tiếp
                                    </span>
                                  )}
                                </div>
                              </td>
                              <td className="py-2.5 px-3 text-slate-500 font-medium">{c.distance_m}m</td>
                              <td className="py-2.5 px-3 text-blue-700 font-bold">{c.price_range || 'N/A'}</td>
                              <td className="py-2.5 px-3 text-red-600 font-medium italic">{c.weakness || 'Chưa ghi nhận'}</td>
                            </tr>
                          );
                        })}
                        {compList.length === 0 && (
                          <tr>
                            <td colSpan="4" className="py-4 text-center text-slate-400 italic">
                              Không tìm thấy đối thủ trực tiếp nào trong bán kính 1km.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>

                  <div className="text-[11px] text-slate-500 bg-slate-50 p-3 rounded-xl border border-slate-100">
                    📌 <strong>Nhận định mật độ:</strong> Bán kính 1km ghi nhận <strong>{totalComp} đối thủ</strong>, trong đó có <strong>{directCount} đối thủ cạnh tranh trực tiếp</strong>. Mức độ cạnh tranh thực tế: <strong className="text-slate-800">{compLevel}</strong>.
                  </div>
                </div>
              );
            })()}

            {/* KHỐI 3: ĐỀ XUẤT TẤN CÔNG VÀO 3 MẢNG (ĐIỂM YẾU, GIÁ, THỜI GIAN) */}
            {!isRedAlert && (result.market_analysis || result.market_gaps) && (() => {
              const ma = result.market_analysis || result.market_gaps || {};
              const mw = ma.market_weakness || {};
              const againstList = ma.against_weakness || [];
              const avgPrices = ma.average_price || [];
              const recPrices = ma.recommended_price || [];
              const insights = ma.customer_insights || {};
              const recTime = ma.recommended_time || insights.time || '06:00 - 09:00';
              const secInsights = insights.secondary_insights;

              // Tra cứu tên sản phẩm/dịch vụ chủ lực và bán kèm
              const primaryPid = insights.primary_product_id || (selectedProductIds.length > 0 ? selectedProductIds[0] : null);
              const primaryProdObj = metadata?.products?.find(p => p.id === primaryPid);
              const primaryProdName = primaryProdObj?.name || (primaryPid ? `Mã ${primaryPid}` : null);

              const secPid = secInsights?.product_id || (selectedProductIds.length > 1 ? selectedProductIds[1] : null);
              const secProdObj = metadata?.products?.find(p => p.id === secPid);
              const secProdName = secProdObj?.name || (secPid ? `Mã ${secPid}` : 'Sản phẩm/dịch vụ kèm');

              return (
                <div className="bg-gradient-to-tr from-blue-50/50 via-indigo-50/30 to-purple-50/40 border border-blue-200/80 rounded-2xl p-5 sm:p-6 shadow-sm space-y-5">
                  <div className="flex items-center space-x-2 text-blue-900 pb-3 border-b border-blue-200/60">
                    <Target className="w-5 h-5 text-blue-600 shrink-0" />
                    <h4 className="font-bold text-sm sm:text-base">
                      3. Đề Xuất Tấn Công Vào 3 Mảng: Điểm Yếu, Giá & Thời Gian
                    </h4>
                  </div>

                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                    {/* Mảng 1: Điểm Yếu */}
                    <div className="bg-white p-4 rounded-xl border border-blue-100 shadow-2xs space-y-3 flex flex-col justify-between">
                      <div className="space-y-2.5">
                        <div className="flex items-center space-x-1.5 text-rose-700">
                          <ShieldAlert className="w-4 h-4 shrink-0" />
                          <span className="text-xs font-bold uppercase tracking-wider">Mảng 1: Tử Huyệt Đối Thủ</span>
                        </div>

                        {mw.important_weakness ? (
                          <div className="p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs">
                            <span className="text-[10px] font-bold text-rose-800 uppercase block">Tử huyệt lớn nhất:</span>
                            <p className="text-rose-950 font-semibold mt-0.5">{mw.important_weakness}</p>
                          </div>
                        ) : null}

                        {Array.isArray(mw.normal_weakness) && mw.normal_weakness.length > 0 && (
                          <div className="space-y-1">
                            <span className="text-[10px] font-bold text-slate-500 uppercase block">Điểm yếu hệ thống:</span>
                            {mw.normal_weakness.map((nw, i) => (
                              <div key={i} className="text-[11px] text-slate-700 bg-slate-50 p-1.5 rounded border border-slate-100 font-medium">
                                • {nw}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>

                      {againstList.length > 0 && (
                        <div className="pt-2 border-t border-slate-100 text-xs">
                          <span className="text-[10px] font-bold text-emerald-700 uppercase block">Đòn đánh hóa giải đề xuất:</span>
                          <p className="text-slate-800 font-medium text-[11px] mt-0.5 leading-relaxed">
                            {typeof againstList[0] === 'string' ? againstList[0] : (againstList[0]?.lesson || againstList[0]?.title || '')}
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Mảng 2: Giá */}
                    <div className="bg-white p-4 rounded-xl border border-blue-100 shadow-2xs space-y-3 flex flex-col justify-between">
                      <div className="space-y-2.5">
                        <div className="flex items-center space-x-1.5 text-blue-700">
                          <DollarSign className="w-4 h-4 shrink-0" />
                          <span className="text-xs font-bold uppercase tracking-wider">Mảng 2: Dải Giá Thị Trường</span>
                        </div>

                        <div className="space-y-1.5">
                          <span className="text-[10px] font-bold text-slate-500 uppercase block">Phân khúc giá khu vực (DB2):</span>
                          <div className="flex flex-wrap gap-1.5">
                            {avgPrices.map((ap, i) => (
                              <span key={i} className="text-[10px] px-2 py-0.5 rounded-md bg-slate-100 text-slate-700 font-medium border border-slate-200">
                                {ap.price}: <strong>{ap.count} địa điểm</strong>
                              </span>
                            ))}
                            {avgPrices.length === 0 && (
                              <span className="text-[11px] text-slate-400 italic">Đang cập nhật</span>
                            )}
                          </div>
                        </div>
                      </div>

                      <div className="pt-2 border-t border-slate-100 space-y-1 text-xs">
                        <span className="text-[10px] font-bold text-blue-700 uppercase block">Đề xuất giá bán tối ưu (Món chính):</span>
                        <div className="space-y-1">
                          {recPrices.map((rp, i) => (
                            <div key={i} className="flex items-center justify-between p-1.5 rounded-lg bg-blue-50/70 border border-blue-100 text-xs">
                              <span className="font-bold text-blue-900 capitalize">
                                {rp.type === 'normal' ? 'Phổ thông:' : rp.type === 'premium' ? 'Nâng cao:' : `${rp.type}:`}
                              </span>
                              <span className="font-extrabold text-blue-700">{rp.price}</span>
                            </div>
                          ))}
                          {recPrices.length === 0 && (
                            <div className="text-xs text-slate-600 font-medium">{insights.price || '25.000đ - 35.000đ'}</div>
                          )}
                        </div>
                        {secInsights?.price && (
                          <div className="pt-1.5 flex items-center justify-between text-[11px] text-slate-600 border-t border-dashed border-slate-200">
                            <span className="font-medium text-indigo-900">➕ Bán kèm ({secProdName}):</span>
                            <span className="font-bold text-indigo-700">{secInsights.price}</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Mảng 3: Thời Gian */}
                    <div className="bg-white p-4 rounded-xl border border-blue-100 shadow-2xs space-y-3 flex flex-col justify-between">
                      <div className="space-y-2.5">
                        <div className="flex items-center space-x-1.5 text-amber-700">
                          <Clock className="w-4 h-4 shrink-0" />
                          <span className="text-xs font-bold uppercase tracking-wider">Mảng 3: Thời Gian & Thói Quen</span>
                        </div>

                        <div className="space-y-1 text-xs">
                          <div className="flex items-center justify-between">
                            <span className="text-[10px] font-bold text-slate-500 uppercase block">Khung giờ khách quen (DB5):</span>
                            {primaryProdName && (
                              <span className="text-[10px] font-bold text-blue-700 bg-blue-50 px-1.5 py-0.5 rounded border border-blue-200">
                                ★ {primaryProdName}
                              </span>
                            )}
                          </div>
                          <p className="font-semibold text-slate-800 bg-amber-50/70 p-2 rounded-lg border border-amber-200/60 text-xs">
                            ⏰ {insights.time || '06:30 - 08:30'}
                          </p>
                        </div>

                        {insights.behavior && (
                          <div className="space-y-1 text-xs">
                            <span className="text-[10px] font-bold text-slate-500 uppercase block">Đặc điểm hành vi (Món chính):</span>
                            <p className="text-[11px] text-slate-600 leading-relaxed font-medium">
                              {insights.behavior}
                            </p>
                          </div>
                        )}

                        {/* Món bán kèm / bổ trợ (nếu có) */}
                        {secInsights && (
                          <div className="p-2.5 rounded-lg bg-indigo-50/80 border border-indigo-200/70 text-xs space-y-1 mt-2">
                            <div className="flex items-center justify-between">
                              <span className="text-[10px] font-bold text-indigo-900 uppercase">
                                ➕ Bán kèm ({secProdName}):
                              </span>
                              <span className="text-[10px] font-bold text-indigo-700">
                                {secInsights.price}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-800 font-semibold">
                              ⏰ Giờ cao điểm phụ: <strong>{secInsights.time}</strong>
                            </p>
                            <p className="text-[10px] text-slate-600 italic">
                              "{secInsights.behavior}"
                            </p>
                          </div>
                        )}
                      </div>

                      <div className="pt-2 border-t border-slate-100 text-xs">
                        <span className="text-[10px] font-bold text-indigo-700 uppercase block">Đề xuất giờ vàng mở bán (Món chính):</span>
                        <div className="font-black text-indigo-900 bg-indigo-50/80 p-2 rounded-lg border border-indigo-200/60 mt-1 text-xs">
                          🚀 {recTime}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* KHỐI 4: GỢI Ý VẤN ĐỀ & KINH NGHIỆM THỰC CHIẾN (DB3 & DB4) */}
            {!isRedAlert && result.tactical_playbook && (() => {
              const problems = result.tactical_playbook?.top_4_problems || [];
              const experiences = result.tactical_playbook?.top_4_experiences || [];

              if (problems.length === 0 && experiences.length === 0) return null;

              return (
                <div className="bg-white rounded-2xl p-4 sm:p-5 border border-slate-200 shadow-sm space-y-4">
                  <div className="flex items-center space-x-2 text-purple-700 pb-2.5 border-b border-slate-100">
                    <Lightbulb className="w-5 h-5 text-purple-600 shrink-0" />
                    <div>
                      <h4 className="font-bold text-slate-900 text-sm sm:text-base">
                        4. Vấn Đề Cốt Tử & Bài Học Thực Chiến
                      </h4>
                      <p className="text-[11px] text-slate-500">
                        Dữ liệu đối chiếu: Cạm bẫy vận hành (DB3) và kinh nghiệm thực chiến (DB4).
                      </p>
                    </div>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                    {/* Top 4 Vấn Đề Cốt Tử (DB3) */}
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between pb-1 border-b border-slate-100">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-rose-800 flex items-center space-x-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 text-rose-600 shrink-0" />
                          <span>4 Cạm Bẫy Cần Đề Phòng (DB3)</span>
                        </span>
                        <span className="text-[9px] text-slate-400 italic">Lường trước rủi ro</span>
                      </div>

                      <div className="space-y-2">
                        {problems.map((p, idx) => (
                          <div key={idx} className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/70 space-y-1 hover:bg-slate-100/60 transition overflow-hidden">
                            <div className="flex items-center justify-between gap-1.5">
                              <h5 className="font-bold text-xs text-slate-900 leading-snug break-words">
                                {idx + 1}. {p.title}
                              </h5>
                              <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded uppercase shrink-0 ${
                                p.severity === 3 ? 'bg-red-100 text-red-700' : p.severity === 2 ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'
                              }`}>
                                {p.severity === 3 ? 'Nghiêm trọng' : p.severity === 2 ? 'Trung bình' : 'Lưu ý'}
                              </span>
                            </div>
                            <p className="text-[11px] text-slate-600 leading-relaxed font-normal break-words">
                              {p.summary}
                            </p>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Top 4 Kinh Nghiệm Thực Chiến (DB4) */}
                    <div className="space-y-2.5">
                      <div className="flex items-center justify-between pb-1 border-b border-slate-100">
                        <span className="text-[11px] font-bold uppercase tracking-wider text-emerald-800 flex items-center space-x-1.5">
                          <Award className="w-3.5 h-3.5 text-emerald-600 shrink-0" />
                          <span>4 Bài Học Thực Chiến (DB4)</span>
                        </span>
                        <span className="text-[9px] text-slate-400 italic">Đúc kết thực tế</span>
                      </div>

                      <div className="space-y-2">
                        {experiences.map((exp, idx) => (
                          <div key={idx} className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/70 space-y-1 hover:bg-slate-100/60 transition overflow-hidden">
                            <h5 className="font-bold text-xs text-slate-900 leading-snug break-words">
                              {idx + 1}. {exp.title}
                            </h5>
                            <p className="text-[11px] text-slate-700 font-normal leading-relaxed break-words">
                              ✓ {exp.key_takeaway}
                            </p>
                            {exp.dialogue_script && (
                              <div className="p-1.5 bg-white rounded-lg border border-slate-200 text-[10px] text-slate-600 italic break-words">
                                💬 Lời thoại: "{exp.dialogue_script}"
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })()}

            {/* KHỐI KẾ HOẠCH TÁC CHIẾN CHIẾN LƯỢC TỪ AI */}
            <div className="bg-white rounded-2xl p-6 sm:p-8 border border-slate-200/90 shadow-sm space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between pb-3 border-b border-slate-200/80 gap-2">
                <div className="flex items-center space-x-2.5 text-blue-700">
                  <div className="p-2 rounded-xl bg-blue-50 text-blue-600 border border-blue-100 shrink-0">
                    <CheckCircle2 className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="font-extrabold text-base sm:text-lg text-slate-900">
                      {isRedAlert ? '2.' : '5.'} Bản Kế Hoạch Tác Chiến Chiến Lược (AI Strategic Co-pilot)
                    </h4>
                    <p className="text-xs text-slate-500 font-medium mt-0.5">
                      {isRedAlert
                        ? 'Kế hoạch khẩn cấp: Tái cấu trúc vốn & mô hình sinh tồn'
                        : 'Phân tích sâu thế đánh đổi & Lộ trình thực thi 30 - 60 - 90 ngày'}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  {result.is_streaming_ai && (
                    <span className="text-[11px] font-semibold text-blue-600 bg-blue-50 px-3 py-1 rounded-full border border-blue-200 flex items-center space-x-1.5 animate-pulse">
                      <span className="w-2 h-2 rounded-full bg-blue-600 animate-ping"></span>
                      <span>AI đang sinh kế hoạch từng từ...</span>
                    </span>
                  )}
                  <span className="text-[11px] font-semibold text-slate-500 bg-slate-50 px-3 py-1 rounded-full border border-slate-200 self-start sm:self-auto">
                    ✓ Checklist tương tác trực quan
                  </span>
                </div>
              </div>
              {result.ai_report ? (
                <div className="relative">
                  <FormattedMarkdown content={result.ai_report} />
                  {result.is_streaming_ai && (
                    <span className="inline-block w-2 h-4 ml-1 bg-blue-600 animate-pulse align-middle" />
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-center p-8 text-slate-400 space-x-2.5 bg-slate-50 rounded-xl border border-dashed border-slate-200">
                  <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
                  <span className="text-xs italic text-slate-500">
                    Đang tổng hợp dữ liệu từ 4 khối phân tích phía trên để sinh kế hoạch...
                  </span>
                </div>
              )}
            </div>

            {/* THẺ LƯU Ý PHÁP LÝ & QUYỀN TỰ QUYẾT */}
            <div className="bg-amber-50/70 rounded-2xl p-4 sm:p-5 border border-amber-200/80 shadow-2xs flex items-start space-x-3.5">
              <div className="p-2 rounded-xl bg-amber-100 text-amber-700 shrink-0 mt-0.5">
                <AlertTriangle className="w-5 h-5" />
              </div>
              <div className="space-y-1 text-xs text-amber-900 leading-relaxed">
                <h5 className="font-bold text-amber-950 uppercase tracking-wide text-[11px]">
                  Lưu ý quan trọng & Giới hạn trách nhiệm
                </h5>
                <p>
                  Đây là chiến lược gợi ý dựa trên dữ liệu địa bàn và bài toán kinh doanh thực tế, <strong>quyền quyết định hoàn toàn nằm ở bạn</strong>.
                </p>
                <p className="text-[11px] text-amber-800/90 font-normal">
                  Toàn bộ thủ tục hành chính, giấy tờ pháp lý, đăng ký kinh doanh, an toàn thực phẩm và pháp lý mặt bằng <strong>không nằm trong phạm vi nhiệm vụ của hệ thống</strong> — chủ cơ sở tự chịu trách nhiệm thực hiện theo quy định pháp luật.
                </p>
              </div>
            </div>

          </div>
          );
        })()}

        {/* Chân trang thông tin tinh gọn ở đáy vùng cuộn kết quả */}
        <footer className="pt-6 pb-4 text-center text-[11px] text-slate-400 space-y-0.5 border-t border-slate-200/60 mt-6">
          <p className="font-semibold text-slate-600">
            MLAI Decision Intelligence & Tactical Co-pilot Platform © 2026
          </p>
          <p>
            Nền tảng Thẩm định & Cố vấn Chiến lược Hộ Kinh doanh Bán lẻ & Dịch vụ Thực chiến
          </p>
        </footer>

        </div>
      </div>

    </div>
  );
}
