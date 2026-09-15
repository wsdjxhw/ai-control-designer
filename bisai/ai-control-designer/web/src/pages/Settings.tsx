import React, { useEffect, useState } from 'react';
import { useSettingsStore } from '@/stores/settingsStore';
import MonacoEditor from '@monaco-editor/react';

interface OptimizerParams {
  popsize?: number;
  sigma0?: number;
  n_particles?: number;
  w?: number;
  c1?: number;
  c2?: number;
  max_iter?: number;
  n_startup_trials?: number;
  n_ei_candidates?: number;
  custom_optimizer_code?: string;
}

const Settings: React.FC = () => {
  const { settings, fetchSettings, updateSettings, loading, error } = useSettingsStore();
  const [showApiKey, setShowApiKey] = useState(false);
  const [testingConnection, setTestingConnection] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; detail?: string; suggestion?: string; response?: string } | null>(null);
  const [form, setForm] = useState({
    llm_model: '',
    llm_base_url: '',
    llm_api_key: '',
    llm_temperature: 0.0,
    llm_timeout: 240,
    optimizer_type: 'cmaes' as const,
    max_iterations: 20,
    ...({} as OptimizerParams),
  });

  useEffect(() => {
    fetchSettings();
  }, []);

  useEffect(() => {
    if (settings) {
      setForm({
        llm_model: settings.llm_model || '',
        llm_base_url: settings.llm_base_url || '',
        llm_api_key: settings.llm_api_key || '',
        llm_temperature: settings.llm_temperature ?? 0.0,
        llm_timeout: settings.llm_timeout ?? 240,
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
    return <div className="text-center py-10 text-blue-400 font-mono">加载设置中...</div>;
  }

  if (error) {
    return <div className="text-center py-10 text-red-400">❌ {error}</div>;
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 text-white text-glow">⚙️ 系统设置</h1>

      {/* LLM 配置 */}
      <div className="glass-card p-6 mb-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className="w-1 h-6 bg-gradient-to-b from-blue-500 to-cyan-500 rounded-full"></span>
          LLM 配置
        </h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">模型名称</label>
            <div className="flex gap-3">
              <input
                className="flex-1 bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition"
                placeholder="moonshotai/Kimi-K2.5"
                value={form.llm_model}
                onChange={(e) => setForm({ ...form, llm_model: e.target.value })}
              />
              <button
                type="button"
                onClick={async () => {
                  if (!form.llm_base_url) {
                    alert('请先填写 Base URL');
                    return;
                  }
                  try {
                    const resp = await fetch('/api/v1/system/fetch-llm-models', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        base_url: form.llm_base_url,
                        api_key: form.llm_api_key,
                        limit: 100,
                      }),
                    });
                    const data = await resp.json();
                    if (data.success && data.models && data.models.length > 0) {
                      const modelList = data.models.map((m: any, i: number) => `${i + 1}. ${m.id}`).join('\n');
                      const choice = prompt(
                        `共找到 ${data.count} 个模型，请输入序号或直接粘贴模型 ID：\n\n${modelList}`,
                        data.models[0]?.id || ''
                      );
                      if (choice) {
                        const num = parseInt(choice);
                        if (!isNaN(num) && num > 0 && num <= data.models.length) {
                          setForm({ ...form, llm_model: data.models[num - 1].id });
                        } else {
                          setForm({ ...form, llm_model: choice });
                        }
                      }
                    } else {
                      alert('未获取到模型列表: ' + (data.detail || '未知错误'));
                    }
                  } catch (err: any) {
                    alert('请求失败: ' + err.message);
                  }
                }}
                className="px-4 py-2.5 bg-[#1a2d4a] hover:bg-[#2a3f5a] text-gray-200 rounded-xl border border-[#2a3f5a] transition flex items-center gap-2 text-sm whitespace-nowrap"
                title="从当前 Base URL 获取可用模型列表"
              >
                📥 获取模型列表
              </button>
              <button
                type="button"
                onClick={async () => {
                  if (!form.llm_base_url) {
                    alert('请先填写 Base URL');
                    return;
                  }
                  if (!form.llm_model) {
                    alert('请先填写模型名称');
                    return;
                  }

                  setTestingConnection(true);
                  setTestResult(null);

                  try {
                    const resp = await fetch('/api/v1/system/test-llm-connection', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        base_url: form.llm_base_url,
                        api_key: form.llm_api_key,
                        model: form.llm_model,
                      }),
                    });
                    const data = await resp.json();
                    setTestResult(data);
                  } catch (err: any) {
                    setTestResult({
                      success: false,
                      message: '❌ 检测请求失败',
                      detail: err.message
                    });
                  } finally {
                    setTestingConnection(false);
                  }
                }}
                disabled={testingConnection}
                className="px-4 py-2.5 bg-[#1a2d4a] hover:bg-[#2a3f5a] disabled:bg-[#0f1624] disabled:cursor-not-allowed text-gray-200 rounded-xl border border-[#2a3f5a] transition flex items-center gap-2 text-sm whitespace-nowrap"
                title="测试当前配置是否能正常连接到模型"
              >
                {testingConnection ? (
                  <>
                    <svg className="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    检测中...
                  </>
                ) : (
                  '🔍 检测连接'
                )}
              </button>
            </div>
            <p className="mt-1 text-xs text-gray-500">
              填写 Base URL 后可点击右侧按钮获取该平台支持的模型列表（最多 100 个），填写模型名称后可点击「检测连接」验证配置是否正确
            </p>

            {/* 连接检测结果展示 */}
            {testResult && (
              <div className={`mt-3 p-4 rounded-xl border ${testResult.success ? 'bg-green-500/10 border-green-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <p className={`font-medium ${testResult.success ? 'text-green-400' : 'text-red-400'}`}>
                      {testResult.message}
                    </p>
                    {testResult.response && (
                      <p className="mt-2 text-sm text-gray-400">
                        测试响应: {testResult.response}
                      </p>
                    )}
                    {testResult.detail && (
                      <p className="mt-2 text-sm text-gray-400">
                        详情: {testResult.detail}
                      </p>
                    )}
                    {testResult.suggestion && (
                      <div className="mt-3 pt-3 border-t border-gray-700">
                        <p className="text-sm text-yellow-400 font-medium">💡 建议:</p>
                        <p className="mt-1 text-sm text-gray-400 whitespace-pre-line">{testResult.suggestion}</p>
                      </div>
                    )}
                  </div>
                  <button
                    onClick={() => setTestResult(null)}
                    className="ml-4 text-gray-500 hover:text-gray-300 transition"
                    title="关闭"
                  >
                    ✕
                  </button>
                </div>
              </div>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">Base URL</label>
            <input
              className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition"
              placeholder="https://api-inference.modelscope.cn/v1"
              value={form.llm_base_url}
              onChange={(e) => setForm({ ...form, llm_base_url: e.target.value })}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">API Key</label>
            <div className="relative">
              <input
                className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 pr-12 text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition"
                type={showApiKey ? "text" : "password"}
                placeholder="sk-..."
                value={form.llm_api_key}
                onChange={(e) => setForm({ ...form, llm_api_key: e.target.value })}
              />
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-200 transition"
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

          {/* Temperature 和 Timeout 配置 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Temperature <span className="text-xs text-gray-500">(0.0 - 2.0)</span>
              </label>
              <input
                type="number"
                min={0}
                max={2}
                step={0.1}
                className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition"
                placeholder="0.0"
                value={form.llm_temperature}
                onChange={(e) => setForm({ ...form, llm_temperature: parseFloat(e.target.value) || 0 })}
              />
              <p className="mt-1 text-xs text-gray-500">控制输出的随机性，0=确定性，2=最大随机性</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-1">
                Timeout <span className="text-xs text-gray-500">(秒)</span>
              </label>
              <input
                type="number"
                min={10}
                max={600}
                step={10}
                className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition"
                placeholder="240"
                value={form.llm_timeout}
                onChange={(e) => setForm({ ...form, llm_timeout: parseInt(e.target.value) || 240 })}
              />
              <p className="mt-1 text-xs text-gray-500">LLM 请求超时时间（默认 240秒）</p>
            </div>
          </div>

          {/* 保存按钮 */}
          <div className="pt-4 border-t border-[#1a2d4a]">
            <button
              type="submit"
              className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-xl transition flex items-center justify-center gap-2 font-medium"
            >
              💾 保存 LLM 配置
            </button>
            <p className="mt-2 text-xs text-gray-500">点击保存后配置将持久化到 system_settings.json，刷新页面后仍显示最新配置</p>
          </div>
        </form>
      </div>

      {/* 优化器配置 */}
      <div className="glass-card p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <span className="w-1 h-6 bg-gradient-to-b from-purple-500 to-pink-500 rounded-full"></span>
          优化器配置
        </h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1">优化器类型</label>
            <select
              className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 focus:border-purple-500 focus:ring-2 focus:ring-purple-500/30 outline-none transition appearance-none"
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

          {/* 动态参数配置区 - CMA-ES */}
          {form.optimizer_type === 'cmaes' && (
            <div className="pt-4 border-t border-[#1a2d4a] space-y-4">
              <div className="text-sm font-semibold text-blue-400 mb-2">CMA-ES 参数</div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    种群大小 <span className="text-xs text-gray-500">(popsize)</span>
                  </label>
                  <input
                    type="number"
                    min={5}
                    max={500}
                    step={5}
                    value={form.popsize ?? 50}
                    onChange={(e) => setForm({ ...form, popsize: parseInt(e.target.value) })}
                    className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 focus:border-blue-500 focus:outline-none"
                  />
                  <p className="mt-1 text-xs text-gray-500">种群规模 (默认: 50)</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    初始步长 <span className="text-xs text-gray-500">(sigma0)</span>
                  </label>
                  <input
                    type="number"
                    min={0.01}
                    max={2.0}
                    step={0.05}
                    value={form.sigma0 ?? 0.25}
                    onChange={(e) => setForm({ ...form, sigma0: parseFloat(e.target.value) })}
                    className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 focus:border-blue-500 focus:outline-none"
                  />
                  <p className="mt-1 text-xs text-gray-500">初始搜索步长 (默认: 0.25)</p>
                </div>
              </div>
            </div>
          )}

          {/* 动态参数配置区 - PSO */}
          {form.optimizer_type === 'pso' && (
            <div className="pt-4 border-t border-[#1a2d4a] space-y-4">
              <div className="text-sm font-semibold text-teal-400 mb-2">PSO 参数</div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    粒子数量 <span className="text-xs text-gray-500">(n_particles)</span>
                  </label>
                  <input
                    type="number"
                    min={5}
                    max={200}
                    step={5}
                    value={form.n_particles ?? 30}
                    onChange={(e) => setForm({ ...form, n_particles: parseInt(e.target.value) })}
                    className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 focus:border-teal-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    惯性权重 <span className="text-xs text-gray-500">(w)</span>
                  </label>
                  <input
                    type="number"
                    min={0.1}
                    max={1.0}
                    step={0.05}
                    value={form.w ?? 0.7}
                    onChange={(e) => setForm({ ...form, w: parseFloat(e.target.value) })}
                    className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 focus:border-teal-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    个体学习因子 <span className="text-xs text-gray-500">(c1)</span>
                  </label>
                  <input
                    type="number"
                    min={0.1}
                    max={4.0}
                    step={0.1}
                    value={form.c1 ?? 1.5}
                    onChange={(e) => setForm({ ...form, c1: parseFloat(e.target.value) })}
                    className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 focus:border-teal-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    社会学习因子 <span className="text-xs text-gray-500">(c2)</span>
                  </label>
                  <input
                    type="number"
                    min={0.1}
                    max={4.0}
                    step={0.1}
                    value={form.c2 ?? 1.5}
                    onChange={(e) => setForm({ ...form, c2: parseFloat(e.target.value) })}
                    className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 focus:border-teal-500 focus:outline-none"
                  />
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    最大迭代次数 <span className="text-xs text-gray-500">(max_iter)</span>
                  </label>
                  <input
                    type="number"
                    min={10}
                    max={1000}
                    step={10}
                    value={form.max_iter ?? 100}
                    onChange={(e) => setForm({ ...form, max_iter: parseInt(e.target.value) })}
                    className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 focus:border-teal-500 focus:outline-none"
                  />
                </div>
              </div>
            </div>
          )}

          {/* 动态参数配置区 - TPE */}
          {form.optimizer_type === 'tpe' && (
            <div className="pt-4 border-t border-[#1a2d4a] space-y-4">
              <div className="text-sm font-semibold text-purple-400 mb-2">TPE 参数</div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    随机采样次数 <span className="text-xs text-gray-500">(n_startup_trials)</span>
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    step={1}
                    value={form.n_startup_trials ?? 10}
                    onChange={(e) => setForm({ ...form, n_startup_trials: parseInt(e.target.value) })}
                    className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 focus:border-purple-500 focus:outline-none"
                  />
                  <p className="mt-1 text-xs text-gray-500">初始随机采样次数 (默认: 10)</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    EI 候选数 <span className="text-xs text-gray-500">(n_ei_candidates)</span>
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={100}
                    step={1}
                    value={form.n_ei_candidates ?? 24}
                    onChange={(e) => setForm({ ...form, n_ei_candidates: parseInt(e.target.value) })}
                    className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 focus:border-purple-500 focus:outline-none"
                  />
                  <p className="mt-1 text-xs text-gray-500">期望改进(EI)候选样本数 (默认: 24)</p>
                </div>
              </div>
            </div>
          )}

          {/* 其他优化器提示 */}
          {(form.optimizer_type === 'random' || form.optimizer_type === 'grid') && (
            <div className="pt-4 border-t border-[#1a2d4a]">
              <p className="text-sm text-gray-500 italic">
                {form.optimizer_type === 'random' ? '随机搜索' : '网格搜索'}无需额外参数配置
              </p>
            </div>
          )}

          {form.optimizer_type === 'custom' && (
            <div className="pt-4 border-t border-[#1a2d4a] space-y-4">
              <div className="text-sm font-semibold text-orange-400 mb-2">自定义优化器代码</div>

              <div className="bg-[#0a0e17] border border-[#1a2d4a] rounded-xl overflow-hidden">
                <div className="px-4 py-2 bg-[#111827] border-b border-[#1a2d4a] flex items-center justify-between">
                  <span className="text-xs text-gray-400 font-mono">custom_optimizer.py</span>
                  <button
                    onClick={() => {
                      const template = getCustomOptimizerTemplate();
                      setForm({ ...form, custom_optimizer_code: template });
                    }}
                    className="text-xs px-3 py-1 bg-orange-600 hover:bg-orange-700 text-white rounded transition"
                  >
                    📋 加载模板
                  </button>
                </div>
                <MonacoEditor
                  height="250px"
                  defaultLanguage="python"
                  value={form.custom_optimizer_code || ''}
                  onChange={(val) => setForm({ ...form, custom_optimizer_code: val || undefined })}
                  options={{
                    minimap: { enabled: false },
                    fontSize: 12,
                    theme: 'vs-dark',
                    automaticLayout: true,
                    scrollBeyondLastLine: false,
                    lineNumbers: 'on',
                    fontFamily: 'JetBrains Mono, monospace',
                  }}
                />
              </div>

              <div className="text-xs text-gray-500 bg-[#0a0e17] p-3 rounded-lg border border-[#1a2d4a]">
                💡 自定义优化器必须继承 <code className="text-orange-400">BaseOptimizer</code> 并实现 <code className="text-orange-400">optimize()</code> 方法。
              </div>
            </div>
          )}

          <button
            onClick={handleSubmit}
            className="btn-neon w-full sm:w-auto"
          >
            💾 保存优化器设置
          </button>
        </div>
      </div>
    </div>
  );
};

const getCustomOptimizerTemplate = (): string => {
  return `# 自定义优化器模板
# 必须继承 BaseOptimizer 并实现 optimize() 方法

from typing import Callable
from core.optimizers.base_optimizer import BaseOptimizer


class CustomOptimizer(BaseOptimizer):
    """用户自定义优化器示例"""

    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def optimize(
        self,
        objective: Callable[[dict[str, float]], float],
        param_bounds: dict[str, tuple[float, float]],
        n_trials: int,
        seed: int = 42,
    ) -> tuple[dict[str, float], float, list[dict]]:
        """
        执行优化。

        Args:
            objective: 目标函数，输入参数字典，返回代价值
            param_bounds: 参数边界 {param_name: (low, high)}
            n_trials: 优化迭代次数
            seed: 随机种子

        Returns:
            (best_params, best_value, history)
            - best_params: 最优参数字典
            - best_value: 最优代价值
            - history: 每轮优化历史 [{"params": {...}, "value": float}, ...]
        """
        import random
        random.seed(seed)

        param_names = list(param_bounds.keys())
        best_params = None
        best_value = float('inf')
        history = []

        for trial in range(n_trials):
            # 随机采样参数
            params = {}
            for name, (low, high) in param_bounds.items():
                params[name] = random.uniform(low, high)

            # 评估
            value = objective(params)

            # 记录历史
            history.append({"params": params.copy(), "value": value})

            # 更新最优
            if value < best_value:
                best_value = value
                best_params = params.copy()

        return best_params or {}, best_value, history
`;
};

export default Settings;
