import React, { useState, useEffect } from 'react';
import { Key, Cpu, Cloud, CheckCircle2, AlertTriangle, X, Eye, EyeOff, RefreshCw } from 'lucide-react';

const PROVIDERS = [
  {
    id: 'gemini',
    name: 'Google Gemini',
    defaultModel: 'gemini-3.8-flash',
    models: ['gemini-3.8-flash', 'gemini-3.7-flash', 'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-2.0-flash'],
    placeholderKey: 'AIzaSy...'
  },
  {
    id: 'openai',
    name: 'OpenAI',
    defaultModel: 'gpt-4o-mini',
    models: ['gpt-4o-mini', 'gpt-4o', 'gpt-4.1-mini'],
    placeholderKey: 'sk-...'
  },
  {
    id: 'groq',
    name: 'Groq Cloud',
    defaultModel: 'llama-3.3-70b-versatile',
    models: ['llama-3.3-70b-versatile', 'qwen-qwq-32b', 'gemma2-9b-it'],
    placeholderKey: 'gsk_...'
  },
  {
    id: 'deepseek',
    name: 'DeepSeek',
    defaultModel: 'deepseek-chat',
    models: ['deepseek-chat', 'deepseek-reasoner'],
    placeholderKey: 'sk-...'
  },
  {
    id: 'openrouter',
    name: 'OpenRouter',
    defaultModel: 'google/gemini-2.5-flash',
    models: ['google/gemini-2.5-flash', 'openai/gpt-4o-mini', 'anthropic/claude-3.5-sonnet'],
    placeholderKey: 'sk-or-v1-...'
  }
];

/**
 * ApiKeyModal - Hộp thoại chuyển đổi luồng sinh văn bản (Local Ollama <-> Cloud API Key)
 */
export default function ApiKeyModal({ isOpen, onClose, llmConfig, onSaveConfig, localModelName }) {
  const [mode, setMode] = useState('local');
  const [provider, setProvider] = useState('gemini');
  const [apiKey, setApiKey] = useState('');
  const [model, setModel] = useState('gemini-3.8-flash');
  const [showKey, setShowKey] = useState(false);

  const [verifying, setVerifying] = useState(false);
  const [verifyStatus, setVerifyStatus] = useState(null); // { ok: boolean, message: string }

  useEffect(() => {
    if (isOpen && llmConfig) {
      setMode(llmConfig.mode || 'local');
      setProvider(llmConfig.provider || 'gemini');
      setApiKey(llmConfig.api_key || '');
      setModel(llmConfig.model || 'gemini-3.8-flash');
      setVerifyStatus(null);
    }
  }, [isOpen, llmConfig]);

  if (!isOpen) return null;

  const activeProviderObj = PROVIDERS.find((p) => p.id === provider) || PROVIDERS[0];

  const handleProviderChange = (newProviderId) => {
    setProvider(newProviderId);
    const found = PROVIDERS.find((p) => p.id === newProviderId);
    if (found) {
      setModel(found.defaultModel);
    }
    setVerifyStatus(null);
  };

  const handleVerifyKey = async () => {
    if (!apiKey.trim()) {
      setVerifyStatus({ ok: false, message: 'Vui lòng nhập API Key trước khi kiểm tra!' });
      return;
    }
    setVerifying(true);
    setVerifyStatus(null);
    try {
      const res = await fetch('/api/llm/verify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          mode: 'cloud',
          provider,
          api_key: apiKey.trim(),
          model: model.trim() || activeProviderObj.defaultModel
        })
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || 'Không thể xác thực API Key');
      }
      setVerifyStatus({ ok: true, message: data.message || 'Kết nối API Key thành công!' });
    } catch (err) {
      setVerifyStatus({ ok: false, message: err.message });
    } finally {
      setVerifying(false);
    }
  };

  const handleSave = (e) => {
    e.preventDefault();
    if (mode === 'cloud' && !apiKey.trim()) {
      setVerifyStatus({ ok: false, message: 'Vui lòng nhập API Key hoặc chuyển về chế độ Local!' });
      return;
    }
    const newConfig = {
      mode,
      provider,
      api_key: apiKey.trim(),
      model: model.trim() || activeProviderObj.defaultModel
    };
    onSaveConfig(newConfig);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/80">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-indigo-600 text-white rounded-xl shadow-sm">
              <Key className="w-4 h-4" />
            </div>
            <div>
              <h3 className="font-bold text-slate-900 text-sm sm:text-base">
                Cấu Hình Nguồn AI (Local / Cloud API)
              </h3>
              <p className="text-[11px] text-slate-500">
                Chuyển luồng sinh báo cáo giữa máy chủ nội bộ và API Key của bạn
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg hover:bg-slate-200 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <form onSubmit={handleSave} className="p-6 space-y-5">
          {/* Chuyển chế độ Local vs Cloud */}
          <div className="grid grid-cols-2 gap-3">
            <button
              type="button"
              onClick={() => {
                setMode('local');
                setVerifyStatus(null);
              }}
              className={`flex items-center space-x-3 p-3.5 rounded-xl border text-left transition ${
                mode === 'local'
                  ? 'bg-blue-50/80 border-blue-500 ring-2 ring-blue-500/20 text-blue-900'
                  : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Cpu className={`w-5 h-5 shrink-0 ${mode === 'local' ? 'text-blue-600' : 'text-slate-400'}`} />
              <div>
                <div className="text-xs font-bold">Local AI (Mặc định)</div>
                <div className="text-[10px] opacity-80 truncate">
                  Ollama ({localModelName || 'qwen3.5:4b'})
                </div>
              </div>
            </button>

            <button
              type="button"
              onClick={() => {
                setMode('cloud');
                setVerifyStatus(null);
              }}
              className={`flex items-center space-x-3 p-3.5 rounded-xl border text-left transition ${
                mode === 'cloud'
                  ? 'bg-indigo-50/80 border-indigo-500 ring-2 ring-indigo-500/20 text-indigo-900'
                  : 'bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100'
              }`}
            >
              <Cloud className={`w-5 h-5 shrink-0 ${mode === 'cloud' ? 'text-indigo-600' : 'text-slate-400'}`} />
              <div>
                <div className="text-xs font-bold">Cloud API Key</div>
                <div className="text-[10px] opacity-80">Dùng Model & Key cá nhân</div>
              </div>
            </button>
          </div>

          {mode === 'local' ? (
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 space-y-2 text-xs text-slate-600">
              <div className="font-bold text-slate-800 flex items-center space-x-1.5">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Đang sử dụng Luồng Local Ollama</span>
              </div>
              <p className="leading-relaxed">
                Hệ thống sẽ gọi trực tiếp mô hình <strong>{localModelName || 'qwen3.5:4b'}</strong> trên máy chủ Ollama cục bộ mà không tốn phí API bên ngoài.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Chọn nhà cung cấp */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1.5">
                  Nhà cung cấp (Provider)
                </label>
                <div className="grid grid-cols-3 sm:grid-cols-5 gap-1.5">
                  {PROVIDERS.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => handleProviderChange(p.id)}
                      className={`py-2 px-2 rounded-lg text-[11px] font-bold border transition truncate ${
                        provider === p.id
                          ? 'bg-indigo-600 text-white border-indigo-600 shadow-sm'
                          : 'bg-slate-50 text-slate-600 border-slate-200 hover:bg-slate-100'
                      }`}
                    >
                      {p.name.replace('Google ', '').replace(' Cloud', '')}
                    </button>
                  ))}
                </div>
              </div>

              {/* Chọn hoặc nhập tên Model */}
              <div>
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                    Tên Model (Có thể tự nhập)
                  </label>
                  <div className="flex flex-wrap gap-1">
                    {activeProviderObj.models.map((m) => (
                      <button
                        key={m}
                        type="button"
                        onClick={() => setModel(m)}
                        className={`text-[10px] px-2 py-0.5 rounded-md border transition ${
                          model === m
                            ? 'bg-indigo-50 border-indigo-300 text-indigo-700 font-semibold'
                            : 'bg-slate-50 border-slate-200 text-slate-500 hover:text-slate-800'
                        }`}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                </div>
                <input
                  type="text"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  placeholder={activeProviderObj.defaultModel}
                  className="w-full px-3.5 py-2 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono focus:ring-2 focus:ring-indigo-500 focus:bg-white outline-none transition"
                />
              </div>

              {/* Nhập API Key */}
              <div>
                <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-1">
                  API Key ({activeProviderObj.name}) <span className="text-red-500">*</span>
                </label>
                <div className="relative flex items-center">
                  <input
                    type={showKey ? 'text' : 'password'}
                    value={apiKey}
                    onChange={(e) => {
                      setApiKey(e.target.value);
                      setVerifyStatus(null);
                    }}
                    placeholder={activeProviderObj.placeholderKey}
                    className="w-full pl-3.5 pr-24 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-xs font-mono focus:ring-2 focus:ring-indigo-500 focus:bg-white outline-none transition"
                  />
                  <div className="absolute right-1.5 flex items-center space-x-1">
                    <button
                      type="button"
                      onClick={() => setShowKey(!showKey)}
                      className="p-1.5 text-slate-400 hover:text-slate-700 rounded-lg"
                      title={showKey ? 'Ẩn API Key' : 'Hiện API Key'}
                    >
                      {showKey ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                    </button>
                    <button
                      type="button"
                      onClick={handleVerifyKey}
                      disabled={verifying}
                      className="px-2.5 py-1 bg-slate-200 hover:bg-slate-300 text-slate-700 font-bold text-[11px] rounded-lg transition flex items-center space-x-1 disabled:opacity-50"
                    >
                      {verifying && <RefreshCw className="w-3 h-3 animate-spin" />}
                      <span>Test Key</span>
                    </button>
                  </div>
                </div>
                <p className="text-[10px] text-slate-400 mt-1">
                  API Key chỉ lưu cục bộ trên trình duyệt của bạn và gửi trực tiếp khi gọi mô hình.
                </p>
              </div>

              {/* Thông báo kết quả kiểm tra */}
              {verifyStatus && (
                <div
                  className={`p-3 rounded-xl border text-xs flex items-start space-x-2 ${
                    verifyStatus.ok
                      ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
                      : 'bg-red-50 border-red-200 text-red-700'
                  }`}
                >
                  {verifyStatus.ok ? (
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                  ) : (
                    <AlertTriangle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                  )}
                  <span className="font-medium break-words">{verifyStatus.message}</span>
                </div>
              )}
            </div>
          )}

          {/* Footer Buttons */}
          <div className="flex items-center justify-end space-x-2.5 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100 transition"
            >
              Hủy
            </button>
            <button
              type="submit"
              className="px-5 py-2.5 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 shadow-md shadow-indigo-500/20 transition"
            >
              Áp Dụng Cấu Hình
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
