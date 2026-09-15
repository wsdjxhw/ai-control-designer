import React, { useEffect, useState } from 'react';
import { useSettingsStore } from '@/stores/settingsStore';

interface SystemSettingsProps {
  className?: string;
}

const SystemSettings: React.FC<SystemSettingsProps> = ({ className = '' }) => {
  const { settings, fetchSettings, updateSettings, loading, error } = useSettingsStore();
  const [form, setForm] = useState({
    llm_model: '',
    llm_base_url: '',
    llm_api_key: '',
    optimizer_type: 'cmaes' as const,
    max_iterations: 20,
  });
  const [showApiKey, setShowApiKey] = useState(false);

  useEffect(() => {
    fetchSettings();
  }, []);

  useEffect(() => {
    if (settings) {
      setForm({
        llm_model: settings.llm_model || '',
        llm_base_url: settings.llm_base_url || '',
        llm_api_key: settings.llm_api_key || '',
        optimizer_type: settings.optimizer_type || 'cmaes',
        max_iterations: settings.max_iterations || 20,
      });
    }
  }, [settings]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await updateSettings(form);
      alert('✅ 设置已保存');
    } catch (err: any) {
      alert('保存失败: ' + err.message);
    }
  };

  if (loading) {
    return <div className="text-center py-10 text-gray-500">加载设置中...</div>;
  }

  if (error) {
    return <div className="text-center py-10 text-red-500">❌ {error}</div>;
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* LLM 配置 */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <span className="w-1 h-6 bg-blue-600 rounded-full"></span>
          LLM 配置
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">模型名称</label>
            <input
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              placeholder="moonshotai/Kimi-K2.5"
              value={form.llm_model}
              onChange={(e) => setForm({ ...form, llm_model: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Base URL</label>
            <input
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              placeholder="https://api-inference.modelscope.cn/v1"
              value={form.llm_base_url}
              onChange={(e) => setForm({ ...form, llm_base_url: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">API Key</label>
            <div className="relative">
              <input
                className="w-full border border-gray-300 rounded-lg px-3 py-2 pr-10 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
                type={showApiKey ? "text" : "password"}
                placeholder="sk-..."
                value={form.llm_api_key}
                onChange={(e) => setForm({ ...form, llm_api_key: e.target.value })}
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 transition"
                tabIndex={-1}
              >
                {showApiKey ? (
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                  </svg>
                ) : (
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                  </svg>
                )}
              </button>
            </div>
          </div>
          <button
            type="submit"
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition shadow-md hover:shadow-lg"
          >
            💾 保存 LLM 设置
          </button>
        </form>
      </div>

      {/* 优化器配置 */}
      <div className="bg-white p-6 rounded-2xl shadow-sm border border-gray-100">
        <h2 className="text-lg font-semibold text-gray-800 mb-4 flex items-center gap-2">
          <span className="w-1 h-6 bg-indigo-600 rounded-full"></span>
          优化器配置
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">优化器类型</label>
            <select
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              value={form.optimizer_type}
              onChange={(e) =>
                setForm({
                  ...form,
                  optimizer_type: e.target.value as any,
                })
              }
            >
              <option value="cmaes">CMA-ES (协方差矩阵自适应演化策略)</option>
              <option value="pso">PSO (粒子群优化)</option>
              <option value="tpe">TPE (树状Parzen估计器)</option>
              <option value="random">Random (随机搜索)</option>
              <option value="grid">Grid (网格搜索)</option>
              <option value="custom">Custom (自定义优化器)</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">最大迭代次数</label>
            <input
              className="w-full border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-blue-500 focus:border-transparent outline-none"
              type="number"
              min={1}
              max={100}
              value={form.max_iterations}
              onChange={(e) =>
                setForm({ ...form, max_iterations: Number(e.target.value) })
              }
            />
          </div>
          <button
            onClick={handleSubmit}
            className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700 transition shadow-md hover:shadow-lg"
          >
            💾 保存优化器设置
          </button>
        </div>
      </div>
    </div>
  );
};

export default SystemSettings;