import React, { useState } from 'react';
import MonacoEditor from '@monaco-editor/react';

export interface OptimizerConfig {
  optimizer_type: 'cmaes' | 'pso' | 'tpe' | 'random' | 'grid' | 'custom';

  // 🆕 通用参数（所有优化器共享）
  n_trials?: number;             // 优化次数（每个优化器都读这个字段）

  // CMA-ES
  popsize?: number;
  sigma0?: number;

  // PSO
  n_particles?: number;
  w?: number;
  c1?: number;
  c2?: number;
  max_iter?: number;

  // TPE
  n_startup_trials?: number;
  n_ei_candidates?: number;

  // Custom
  custom_optimizer_code?: string;
}

interface OptimizerConfigPanelProps {
  config: OptimizerConfig;
  onChange: (config: OptimizerConfig) => void;
}

const OPTIMIZER_OPTIONS = [
  { value: 'cmaes', label: 'CMA-ES (协方差矩阵自适应演化策略)', desc: '默认推荐，适合连续参数优化' },
  { value: 'pso', label: 'PSO (粒子群优化)', desc: '群体智能算法，收敛速度快' },
  { value: 'tpe', label: 'TPE (树状Parzen估计器)', desc: '贝叶斯优化，适合超参数调优' },
  { value: 'random', label: 'Random (随机搜索)', desc: '基线方法，探索性强' },
  { value: 'grid', label: 'Grid (网格搜索)', desc: '穷举离散网格，适合小参数空间' },
  { value: 'custom', label: 'Custom (自定义优化器)', desc: '用户实现自定义优化逻辑' },
];

const OptimizerConfigPanel: React.FC<OptimizerConfigPanelProps> = ({ config, onChange }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // 🆕 优化次数输入的临时草稿（避免打字时被 clamp 强制修正）
  const [nTrialsDraft, setNTrialsDraft] = useState<string>('');

  const updateConfig = (updates: Partial<OptimizerConfig>) => {
    onChange({ ...config, ...updates });
  };

  const renderCMAESParams = () => (
    <div className="space-y-4 pt-4 border-t border-[#1a2d4a]">
      <div className="text-sm font-semibold text-blue-400 mb-3">CMA-ES 参数配置</div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            种群大小 <span className="text-xs text-gray-500">(popsize)</span>
          </label>
          <input
            type="number"
            min={5}
            max={500}
            step={5}
            value={config.popsize ?? 50}
            onChange={(e) => updateConfig({ popsize: parseInt(e.target.value) })}
            className="w-full px-4 py-2.5 bg-[#0a0f1a] border border-[#1a2d4a] rounded-xl text-white focus:border-blue-500 focus:outline-none"
          />
          <p className="mt-1.5 text-xs text-gray-500">种群规模，越大探索越充分但计算越慢 (默认: 50)</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            初始步长 <span className="text-xs text-gray-500">(sigma0)</span>
          </label>
          <input
            type="number"
            min={0.01}
            max={2.0}
            step={0.05}
            value={config.sigma0 ?? 0.25}
            onChange={(e) => updateConfig({ sigma0: parseFloat(e.target.value) })}
            className="w-full px-4 py-2.5 bg-[#0a0f1a] border border-[#1a2d4a] rounded-xl text-white focus:border-blue-500 focus:outline-none"
          />
          <p className="mt-1.5 text-xs text-gray-500">初始搜索步长，影响收敛速度 (默认: 0.25)</p>
        </div>
      </div>
    </div>
  );

  const renderPSOParams = () => (
    <div className="space-y-4 pt-4 border-t border-[#1a2d4a]">
      <div className="text-sm font-semibold text-teal-400 mb-3">PSO 参数配置</div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            粒子数量 <span className="text-xs text-gray-500">(n_particles)</span>
          </label>
          <input
            type="number"
            min={5}
            max={200}
            step={5}
            value={config.n_particles ?? 30}
            onChange={(e) => updateConfig({ n_particles: parseInt(e.target.value) })}
            className="w-full px-4 py-2.5 bg-[#0a0f1a] border border-[#1a2d4a] rounded-xl text-white focus:border-teal-500 focus:outline-none"
          />
          <p className="mt-1.5 text-xs text-gray-500">群体规模，越多越稳定但越慢 (默认: 30)</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            惯性权重 <span className="text-xs text-gray-500">(w)</span>
          </label>
          <input
            type="number"
            min={0.1}
            max={1.0}
            step={0.05}
            value={config.w ?? 0.7}
            onChange={(e) => updateConfig({ w: parseFloat(e.target.value) })}
            className="w-full px-4 py-2.5 bg-[#0a0f1a] border border-[#1a2d4a] rounded-xl text-white focus:border-teal-500 focus:outline-none"
          />
          <p className="mt-1.5 text-xs text-gray-500">惯性系数，控制全局探索 (默认: 0.7)</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            个体学习因子 <span className="text-xs text-gray-500">(c1)</span>
          </label>
          <input
            type="number"
            min={0.1}
            max={4.0}
            step={0.1}
            value={config.c1 ?? 1.5}
            onChange={(e) => updateConfig({ c1: parseFloat(e.target.value) })}
            className="w-full px-4 py-2.5 bg-[#0a0f1a] border border-[#1a2d4a] rounded-xl text-white focus:border-teal-500 focus:outline-none"
          />
          <p className="mt-1.5 text-xs text-gray-500">个体认知系数 (默认: 1.5)</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            社会学习因子 <span className="text-xs text-gray-500">(c2)</span>
          </label>
          <input
            type="number"
            min={0.1}
            max={4.0}
            step={0.1}
            value={config.c2 ?? 1.5}
            onChange={(e) => updateConfig({ c2: parseFloat(e.target.value) })}
            className="w-full px-4 py-2.5 bg-[#0a0f1a] border border-[#1a2d4a] rounded-xl text-white focus:border-teal-500 focus:outline-none"
          />
          <p className="mt-1.5 text-xs text-gray-500">社会学习系数 (默认: 1.5)</p>
        </div>

        <div className="md:col-span-2">
          <label className="block text-sm font-medium text-gray-300 mb-2">
            最大迭代次数 <span className="text-xs text-gray-500">(max_iter)</span>
          </label>
          <input
            type="number"
            min={10}
            max={1000}
            step={10}
            value={config.max_iter ?? 100}
            onChange={(e) => updateConfig({ max_iter: parseInt(e.target.value) })}
            className="w-full md:w-1/2 px-4 py-2.5 bg-[#0a0f1a] border border-[#1a2d4a] rounded-xl text-white focus:border-teal-500 focus:outline-none"
          />
          <p className="mt-1.5 text-xs text-gray-500">PSO 算法最大迭代次数 (默认: 100)</p>
        </div>
      </div>
    </div>
  );

  const renderTPEParams = () => (
    <div className="space-y-4 pt-4 border-t border-[#1a2d4a]">
      <div className="text-sm font-semibold text-purple-400 mb-3">TPE 参数配置</div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            随机采样次数 <span className="text-xs text-gray-500">(n_startup_trials)</span>
          </label>
          <input
            type="number"
            min={1}
            max={100}
            step={1}
            value={config.n_startup_trials ?? 10}
            onChange={(e) => updateConfig({ n_startup_trials: parseInt(e.target.value) })}
            className="w-full px-4 py-2.5 bg-[#0a0f1a] border border-[#1a2d4a] rounded-xl text-white focus:border-purple-500 focus:outline-none"
          />
          <p className="mt-1.5 text-xs text-gray-500">初始随机采样次数，建立先验 (默认: 10)</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            EI 候选数 <span className="text-xs text-gray-500">(n_ei_candidates)</span>
          </label>
          <input
            type="number"
            min={1}
            max={100}
            step={1}
            value={config.n_ei_candidates ?? 24}
            onChange={(e) => updateConfig({ n_ei_candidates: parseInt(e.target.value) })}
            className="w-full px-4 py-2.5 bg-[#0a0f1a] border border-[#1a2d4a] rounded-xl text-white focus:border-purple-500 focus:outline-none"
          />
          <p className="mt-1.5 text-xs text-gray-500">期望改进(EI)候选样本数 (默认: 24)</p>
        </div>
      </div>
    </div>
  );

  const renderCustomParams = () => (
    <div className="pt-4 border-t border-[#1a2d4a] space-y-4">
      <div className="text-sm font-semibold text-orange-400 mb-3">自定义优化器代码</div>

      <div className="bg-[#0a0e17] border border-[#1a2d4a] rounded-xl overflow-hidden">
        <div className="px-4 py-2 bg-[#111827] border-b border-[#1a2d4a] flex items-center justify-between">
          <span className="text-xs text-gray-400 font-mono">custom_optimizer.py</span>
          <button
            onClick={() => {
              const template = getCustomOptimizerTemplate();
              updateConfig({ custom_optimizer_code: template });
            }}
            className="text-xs px-3 py-1 bg-orange-600 hover:bg-orange-700 text-white rounded transition"
          >
            📋 加载模板
          </button>
        </div>
        <MonacoEditor
          height="300px"
          defaultLanguage="python"
          value={config.custom_optimizer_code || ''}
          onChange={(val) => updateConfig({ custom_optimizer_code: val || undefined })}
          options={{
            minimap: { enabled: false },
            fontSize: 13,
            theme: 'vs-dark',
            automaticLayout: true,
            scrollBeyondLastLine: false,
            lineNumbers: 'on',
            fontFamily: 'JetBrains Mono, monospace',
          }}
        />
      </div>

      <div className="text-xs text-gray-500 bg-[#0a0e17] p-3 rounded-lg border border-[#1a2d4a]">
        💡 <strong>提示：</strong>自定义优化器必须继承 <code className="text-orange-400">BaseOptimizer</code> 并实现 <code className="text-orange-400">optimize()</code> 方法。
        代码将保存到项目配置中，演化服务会动态加载执行。
      </div>
    </div>
  );

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

  const renderNoParams = (message: string) => (
    <div className="pt-4 border-t border-[#1a2d4a]">
      <p className="text-sm text-gray-500 italic">{message}</p>
    </div>
  );

  const renderParams = () => {
    switch (config.optimizer_type) {
      case 'cmaes':
        return renderCMAESParams();
      case 'pso':
        return renderPSOParams();
      case 'tpe':
        return renderTPEParams();
      case 'random':
        return renderNoParams('随机搜索无需额外参数配置');
      case 'grid':
        return renderNoParams('网格搜索无需额外参数配置');
      case 'custom':
        return renderCustomParams();
      default:
        return null;
    }
  };

  return (
    <div className="glass-card p-6">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center justify-between mb-2 group"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-orange-500/20 to-orange-600/20 flex items-center justify-center border border-orange-500/30">
            <span className="text-xl">⚙️</span>
          </div>
          <div className="text-left">
            <h3 className="text-xl font-bold text-white tracking-tight">优化器配置</h3>
            <p className="text-sm text-gray-400">选择算法并调整超参数</p>
          </div>
        </div>
        <div className={`transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}>
          <svg className="w-5 h-5 text-gray-400 group-hover:text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {isExpanded && (
        <div className="mt-6 space-y-6">
          {/* 优化器类型选择 */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-3">优化器类型</label>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {OPTIMIZER_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => updateConfig({ optimizer_type: opt.value as any })}
                  className={`p-4 rounded-xl border-2 text-left transition-all ${
                    config.optimizer_type === opt.value
                      ? 'border-orange-500 bg-orange-500/10'
                      : 'border-[#1a2d4a] hover:border-[#2a3d5a] bg-[#0a0f1a]/50'
                  }`}
                >
                  <div className="font-semibold text-white mb-1">{opt.label}</div>
                  <div className="text-xs text-gray-400">{opt.desc}</div>
                </button>
              ))}
            </div>
          </div>

          {/* 🆕 通用参数：优化次数（所有优化器共享）*/}
          <div className="pt-4 border-t border-[#1a2d4a]">
            <div className="text-sm font-semibold text-orange-400 mb-3">通用参数（所有优化器共享）</div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  优化次数 <span className="text-xs text-gray-500">(n_trials)</span>
                </label>
                <input
                  type="number"
                  min={20}
                  max={5000}
                  step={50}
                  value={nTrialsDraft !== '' ? nTrialsDraft : String(config.n_trials ?? 500)}
                  onChange={(e) => {
                    // 🆕 打字时只更新草稿，不 clamp
                    setNTrialsDraft(e.target.value);
                  }}
                  onBlur={() => {
                    // 🆕 失焦时才解析 + clamp
                    const raw = nTrialsDraft;
                    if (raw === '') {
                      // 空值，恢复显示 state 值
                      setNTrialsDraft('');
                      return;
                    }
                    const v = parseInt(raw);
                    const clamped = isNaN(v) ? 500 : Math.max(20, Math.min(5000, v));
                    updateConfig({ n_trials: clamped });
                    setNTrialsDraft(''); // 清空草稿，让 input 显示 state 值
                  }}
                  onKeyDown={(e) => {
                    // 🆕 回车触发失焦，等同保存
                    if (e.key === 'Enter') {
                      (e.target as HTMLInputElement).blur();
                    }
                  }}
                  className="w-full px-4 py-2.5 bg-[#0a0f1a] border border-[#1a2d4a] rounded-xl text-white focus:border-orange-500 focus:outline-none"
                />
                <p className="mt-1.5 text-xs text-gray-500">
                  每个参数组合的评估次数。越大搜索越充分但耗时越长 (默认: 500，演示建议 100-300)
                </p>
              </div>

              <div className="flex items-end">
                <div className="w-full p-3 bg-[#0a0f1a] border border-[#1a2d4a] rounded-xl text-xs text-gray-400">
                  <div className="font-mono mb-1">
                    <span className="text-gray-500">预计耗时 ≈ </span>
                    <span className="text-orange-400 font-bold">
                      {Math.round((config.n_trials ?? 500) * 0.1)}s
                    </span>
                  </div>
                  <div className="text-gray-500">基于每轮约 0.1s / trial 估算</div>
                </div>
              </div>
            </div>
          </div>

          {/* 动态参数配置区 */}
          {renderParams()}
        </div>
      )}
    </div>
  );
};

export default OptimizerConfigPanel;