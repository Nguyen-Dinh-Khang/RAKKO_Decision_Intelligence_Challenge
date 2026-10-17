import React, { useState } from 'react';
import { Compass, MessageSquareText, Store, User, LogIn, LogOut, X, Lock, Key, Cpu, Cloud } from 'lucide-react';
import ApiKeyModal from './ApiKeyModal';

/**
 * Navbar - Thanh điều hướng chính của Nền tảng Ra quyết định
 * Cho phép chuyển đổi mượt mà giữa:
 * - Giao diện 1: Máy quét Thẩm định Ý tưởng (Day 0)
 * - Giao diện 2: Trợ lý Chiến thuật Đồng hành (Day 1 - 365)
 * - Quản lý tài khoản người dùng: Đăng nhập / Đăng ký / Lưu kế sách
 */
export default function Navbar({ activeTab, setActiveTab, systemStatus, currentUser, onLoginSuccess, onLogout, llmConfig, onUpdateLlmConfig }) {
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [showApiKeyModal, setShowApiKeyModal] = useState(false);
  const [isRegisterMode, setIsRegisterMode] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState(null);

  const isCloudMode = llmConfig?.mode === 'cloud' && Boolean(llmConfig?.api_key);


  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password) {
      setAuthError('Vui lòng điền tên đăng nhập và mật khẩu!');
      return;
    }

    setAuthLoading(true);
    setAuthError(null);

    const endpoint = isRegisterMode ? '/api/auth/register' : '/api/auth/login';
    const payload = isRegisterMode 
      ? { username: username.trim(), password, full_name: fullName.trim() || username.trim() }
      : { username: username.trim(), password };

    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Lỗi khi xác thực tài khoản');
      }

      onLoginSuccess(data.token, data.user);
      setShowAuthModal(false);
      setUsername('');
      setPassword('');
      setFullName('');
    } catch (err) {
      setAuthError(err.message);
    } finally {
      setAuthLoading(false);
    }
  };

  return (
    <>
      <header className="sticky top-0 z-50 bg-white/95 backdrop-blur border-b border-slate-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16 gap-4">
            
            {/* Logo & Tên nền tảng tinh gọn */}
            <div className="flex items-center space-x-2.5 shrink-0">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-sm flex-shrink-0">
                <Compass className="w-5 h-5" />
              </div>
              <div>
                <span className="font-extrabold text-sm sm:text-base tracking-tight text-slate-900 block leading-tight">
                  DECISION CO-PILOT
                </span>
                <p className="text-[11px] text-slate-500 font-medium hidden sm:block leading-none mt-0.5">
                  Trợ lý Ra quyết định Kinh doanh
                </p>
              </div>
            </div>

            {/* Tab Navigation Switcher */}
            <div className="flex bg-slate-100 p-1 rounded-xl border border-slate-200 shrink-0">
              <button
                onClick={() => setActiveTab('scanner')}
                className={`flex items-center space-x-2 px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all duration-150 ${
                  activeTab === 'scanner'
                    ? 'bg-white text-blue-600 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Compass className="w-4 h-4" />
                <span>1. Máy Quét Thẩm Định</span>
                <span className="hidden md:inline text-[10px] text-slate-400 font-normal">(Day 0)</span>
              </button>

              <button
                onClick={() => setActiveTab('copilot')}
                className={`flex items-center space-x-2 px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all duration-150 ${
                  activeTab === 'copilot'
                    ? 'bg-white text-indigo-600 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <MessageSquareText className="w-4 h-4" />
                <span>2. Trợ Lý Chiến Thuật</span>
                <span className="hidden md:inline text-[10px] text-slate-400 font-normal">(Day 1 - 365)</span>
              </button>

              <button
                onClick={() => setActiveTab('profile')}
                className={`flex items-center space-x-2 px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-semibold transition-all duration-150 ${
                  activeTab === 'profile'
                    ? 'bg-white text-emerald-600 shadow-sm'
                    : 'text-slate-600 hover:text-slate-900'
                }`}
              >
                <Store className="w-4 h-4" />
                <span>3. Hồ Sơ & Sổ Sách</span>
                <span className="hidden md:inline text-[10px] text-slate-400 font-normal">(Quản trị)</span>
              </button>
            </div>

            {/* Chuyển luồng AI & Tài khoản Người dùng */}
            <div className="flex items-center space-x-2 text-xs shrink-0">
              <button
                type="button"
                onClick={() => setShowApiKeyModal(true)}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-xl border font-bold text-xs transition ${
                  isCloudMode
                    ? 'bg-indigo-50 border-indigo-200 text-indigo-700 hover:bg-indigo-100'
                    : 'bg-slate-100 border-slate-200 text-slate-700 hover:bg-slate-200'
                }`}
                title="Đổi nguồn sinh văn bản: Local Ollama hoặc Cloud API Key cá nhân"
              >
                {isCloudMode ? (
                  <Cloud className="w-3.5 h-3.5 text-indigo-600" />
                ) : (
                  <Cpu className="w-3.5 h-3.5 text-slate-600" />
                )}
                <span className="hidden lg:inline">
                  {isCloudMode
                    ? `API: ${(llmConfig?.provider || 'gemini').toUpperCase()}`
                    : 'Local AI'}
                </span>
                <Key className="w-3 h-3 opacity-60" />
              </button>

              {currentUser ? (
                <div className="flex items-center space-x-2">
                  <div className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-blue-50 border border-blue-200 text-blue-700 font-semibold text-xs">
                    <User className="w-3.5 h-3.5 text-blue-600" />
                    <span className="max-w-[120px] truncate">{currentUser.full_name || currentUser.username}</span>
                  </div>
                  <button
                    onClick={onLogout}
                    className="p-2 text-slate-400 hover:text-red-600 rounded-xl hover:bg-red-50 transition border border-transparent hover:border-red-100"
                    title="Đăng xuất"
                  >
                    <LogOut className="w-4 h-4" />
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => {
                    setAuthError(null);
                    setShowAuthModal(true);
                  }}
                  className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-bold text-xs shadow-sm shadow-blue-500/20 transition active:scale-[0.98]"
                >
                  <LogIn className="w-3.5 h-3.5" />
                  <span>Đăng nhập / Đăng ký</span>
                </button>
              )}
            </div>

          </div>
        </div>
      </header>

      {/* MODAL ĐĂNG NHẬP / ĐĂNG KÝ */}
      {showAuthModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
          <div className="bg-white rounded-2xl w-full max-w-md shadow-2xl border border-slate-200 overflow-hidden">
            
            {/* Header Modal */}
            <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/70">
              <div className="flex items-center space-x-2">
                <div className="p-1.5 bg-blue-600 text-white rounded-lg">
                  <Lock className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-slate-900 text-base">
                  {isRegisterMode ? 'Đăng Ký Tài Khoản Mới' : 'Đăng Nhập Tài Khoản'}
                </h3>
              </div>
              <button
                onClick={() => setShowAuthModal(false)}
                className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200 transition"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Switcher Đăng nhập / Đăng ký */}
            <div className="px-6 pt-5">
              <div className="flex bg-slate-100 p-1 rounded-xl">
                <button
                  type="button"
                  onClick={() => {
                    setIsRegisterMode(false);
                    setAuthError(null);
                  }}
                  className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition ${
                    !isRegisterMode ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Đăng Nhập
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsRegisterMode(true);
                    setAuthError(null);
                  }}
                  className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition ${
                    isRegisterMode ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-800'
                  }`}
                >
                  Đăng Ký Mới
                </button>
              </div>
            </div>

            {/* Form */}
            <form onSubmit={handleAuthSubmit} className="p-6 space-y-4">
              {authError && (
                <div className="p-3 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs font-medium">
                  {authError}
                </div>
              )}

              {isRegisterMode && (
                <div>
                  <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                    Tên đầy đủ hoặc Tên quán
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Ví dụ: Anh Nam - Quán Cà phê Đa Kao"
                    className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none transition"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Tên đăng nhập <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Ví dụ: chuquan_dakao"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none transition"
                  required
                />
              </div>

              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  Mật khẩu <span className="text-red-500">*</span>
                </label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Nhập mật khẩu (tối thiểu 4 ký tự)"
                  className="w-full px-3.5 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none transition"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={authLoading}
                className="w-full py-3 px-4 rounded-xl font-bold text-sm text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-md shadow-blue-500/25 transition disabled:opacity-50"
              >
                {authLoading ? 'Đang xử lý...' : (isRegisterMode ? 'Tạo Tài Khoản & Bắt Đầu' : 'Đăng Nhập Ngay')}
              </button>

              <p className="text-[11px] text-center text-slate-500 pt-1">
                {isRegisterMode ? (
                  <>Đã có tài khoản? <button type="button" onClick={() => setIsRegisterMode(false)} className="text-blue-600 font-bold hover:underline">Đăng nhập</button></>
                ) : (
                  <>Chưa có tài khoản? <button type="button" onClick={() => setIsRegisterMode(true)} className="text-blue-600 font-bold hover:underline">Đăng ký ngay</button></>
                )}
              </p>
            </form>

          </div>
        </div>
      )}

      {/* MODAL CẤU HÌNH NGUỒN AI (LOCAL OLLAMA / CLOUD API KEY) */}
      <ApiKeyModal
        isOpen={showApiKeyModal}
        onClose={() => setShowApiKeyModal(false)}
        llmConfig={llmConfig}
        onSaveConfig={onUpdateLlmConfig}
        localModelName={systemStatus?.llm_model}
      />
    </>
  );
}
