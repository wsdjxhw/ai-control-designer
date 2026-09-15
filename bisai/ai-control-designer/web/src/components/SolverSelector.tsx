import React, { useState } from 'react';
import MonacoEditor from '@monaco-editor/react';

export interface SolverConfig {
  solver_type: 'auto' | 'ode_scipy' | 'pde_rk4' | 'custom';
  custom_solver_path?: string;
  solver_params?: Record<string, any>;
  method?: string;
  rtol?: number;
  atol?: number;
}

interface SolverSelectorProps {
  config: SolverConfig;
  onChange: (config: SolverConfig) => void;
}

const SolverSelector: React.FC<SolverSelectorProps> = ({ config, onChange }) => {
  const [solverMode, setSolverMode] = useState<'builtin' | 'custom'>(
    config.solver_type === 'custom' ? 'custom' : 'builtin'
  );
  const [customFile, setCustomFile] = useState<File | null>(null);
  const [validationResult, setValidationResult] = useState<any>(null);
  const [isValidating, setIsValidating] = useState(false);
  const [showEditor, setShowEditor] = useState(false);
  const [customSolverCode, setCustomSolverCode] = useState('');

  const handleBuiltinChange = (solver_type: 'auto' | 'ode_scipy' | 'pde_rk4') => {
    onChange({
      ...config,
      solver_type,
      custom_solver_path: undefined,
    });
    setSolverMode('builtin');
    setCustomFile(null);
    setValidationResult(null);
  };

  const handleCustomUpload = async (file: File) => {
    setCustomFile(file);
    setIsValidating(true);

    // 读取文件内容进行前端验证
    const reader = new FileReader();
    reader.onload = async (e) => {
      const code = e.target?.result as string;

      // 保存代码内容（无论验证成功还是失败，都允许用户查看/编辑）
      setCustomSolverCode(code);

      // 前端快速验证
      const errors: string[] = [];
      const warnings: string[] = [];

      // 检查 1: 是否继承 BaseSolver
      if (!/class\s+\w+\s*\([^)]*BaseSolver[^)]*\)/.test(code) &&
          !/from\s+core\.solvers|import\s+.*BaseSolver/.test(code)) {
        errors.push('未检测到继承 BaseSolver 的类');
      }

      // 检查 2: 是否定义了 CustomSolver 类
      if (!/class\s+CustomSolver/.test(code)) {
        errors.push('必须定义 CustomSolver 类（固定名称）');
      }

      // 检查 3: 是否实现了 solve 方法
      if (!/def\s+solve\s*\(self/.test(code)) {
        errors.push('未找到 solve(self, rhs_func, y0, t_span, **kwargs) 方法');
      }

      // 检查 4: solve 方法签名是否正确
      if (/def\s+solve\s*\(self,\s*\w+,\s*\w+,\s*\w+/.test(code) === false &&
          /def\s+solve\s*\(self/.test(code)) {
        warnings.push('solve 方法建议使用标准签名: def solve(self, rhs_func, y0, t_span, **kwargs)');
      }

      if (errors.length > 0) {
        setValidationResult({
          valid: false,
          errors,
          warnings,
        });
        setIsValidating(false);
        return;
      }

      // 验证通过
      setValidationResult({
        valid: true,
        errors: [],
        warnings,
      });
      setIsValidating(false);

      onChange({
        ...config,
        solver_type: 'custom',
        custom_solver_path: file.name,
      });
    };
    reader.readAsText(file);
  };

  const handleParamChange = (key: string, value: any) => {
    const newParams = { ...(config.solver_params || {}), [key]: value };
    onChange({
      ...config,
      solver_params: newParams,
    });
  };

  // 自定义求解器模板
  const getCustomSolverTemplate = (): string => {
    return `# 自定义求解器模板
# 必须继承 BaseSolver 并实现 solve() 方法

from core.solvers.base_solver import BaseSolver
from typing import Callable, Any
import numpy as np


class CustomSolver(BaseSolver):
    """用户自定义求解器示例"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 初始化参数
        self.method = kwargs.get('method', 'RK45')

    def solve(
        self,
        rhs_func: Callable,
        y0: np.ndarray,
        t_span: tuple[float, float],
        **kwargs
    ) -> Any:
        """
        求解 ODE/PDE

        Args:
            rhs_func: 右端函数 f(t, y) -> dy/dt
            y0: 初始状态向量
            t_span: 时间区间 (t_start, t_end)
            **kwargs: 其他参数（如 rtol, atol, max_step 等）

        Returns:
            solution: 求解结果对象
                - solution.t: 时间点数组
                - solution.y: 状态轨迹 (shape: [n_states, n_times])
        """
        from scipy.integrate import solve_ivp

        # 调用 SciPy 的 solve_ivp（示例实现）
        solution = solve_ivp(
            fun=rhs_func,
            t_span=t_span,
            y0=y0,
            method=self.method,
            rtol=kwargs.get('rtol', 1e-6),
            atol=kwargs.get('atol', 1e-9),
            **{k: v for k, v in kwargs.items() if k not in ['rtol', 'atol']}
        )

        return solution
`;
  };

  return (
    <div className="glass-card p-4 space-y-4">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-gray-300">🔧 求解器配置</label>
        <span className="text-xs text-gray-500">Solver Type</span>
      </div>

      {/* 求解器模式选择 */}
      <div className="flex gap-2">
        <button
          onClick={() => setSolverMode('builtin')}
          className={`flex-1 px-4 py-2 rounded-lg border transition text-sm ${
            solverMode === 'builtin'
              ? 'bg-blue-500/20 border-blue-500 text-white'
              : 'bg-[#0a0e17] border-[#1a2d4a] text-gray-400 hover:border-[#2a3f5a]'
          }`}
        >
          内置求解器
        </button>
        <button
          onClick={() => setSolverMode('custom')}
          className={`flex-1 px-4 py-2 rounded-lg border transition text-sm ${
            solverMode === 'custom'
              ? 'bg-purple-500/20 border-purple-500 text-white'
              : 'bg-[#0a0e17] border-[#1a2d4a] text-gray-400 hover:border-[#2a3f5a]'
          }`}
        >
          自定义求解器
        </button>
      </div>

      {/* 内置求解器选项 */}
      {solverMode === 'builtin' && (
        <div className="space-y-3">
          <div className="grid grid-cols-2 gap-2">
            {[
              { type: 'auto' as const, label: '自动选择', desc: '根据模型类型自动选择' },
              { type: 'ode_scipy' as const, label: 'ODE (SciPy)', desc: '常微分方程求解器' },
              { type: 'pde_rk4' as const, label: 'PDE (RK4)', desc: '偏微分方程求解器' },
            ].map((opt) => (
              <button
                key={opt.type}
                onClick={() => handleBuiltinChange(opt.type)}
                className={`p-3 rounded-lg border text-left transition ${
                  config.solver_type === opt.type
                    ? 'bg-blue-500/20 border-blue-500'
                    : 'bg-[#0a0e17] border-[#1a2d4a] hover:border-[#2a3f5a]'
                }`}
              >
                <div className="font-medium text-sm text-white">{opt.label}</div>
                <div className="text-xs text-gray-500 mt-0.5">{opt.desc}</div>
              </button>
            ))}
          </div>

          {/* ODE 高级参数 */}
          {config.solver_type === 'ode_scipy' && (
            <details className="bg-[#0a0e17] border border-[#1a2d4a] rounded-lg p-3">
              <summary className="text-sm text-gray-400 cursor-pointer">⚙️ 高级参数</summary>
              <div className="mt-3 space-y-2 text-sm">
                <div>
                  <label className="text-xs text-gray-500">Method</label>
                  <select
                    className="w-full bg-[#111827] border border-[#1a2d4a] rounded px-2 py-1 text-white"
                    value={config.method || 'RK45'}
                    onChange={(e) => onChange({ ...config, method: e.target.value })}
                  >
                    <option value="RK45">RK45 (推荐)</option>
                    <option value="RK23">RK23</option>
                    <option value="DOP853">DOP853</option>
                    <option value="Radau">Radau</option>
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="text-xs text-gray-500">rtol</label>
                    <input
                      type="number"
                      step="1e-8"
                      className="w-full bg-[#111827] border border-[#1a2d4a] rounded px-2 py-1 text-white"
                      value={config.rtol || 1e-6}
                      onChange={(e) => onChange({ ...config, rtol: parseFloat(e.target.value) })}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-gray-500">atol</label>
                    <input
                      type="number"
                      step="1e-10"
                      className="w-full bg-[#111827] border border-[#1a2d4a] rounded px-2 py-1 text-white"
                      value={config.atol || 1e-9}
                      onChange={(e) => onChange({ ...config, atol: parseFloat(e.target.value) })}
                    />
                  </div>
                </div>
              </div>
            </details>
          )}
        </div>
      )}

      {/* 自定义求解器上传 */}
      {solverMode === 'custom' && (
        <div className="space-y-3">
          {/* 格式要求提示 */}
          <div className="p-3 bg-[#0a0e17] border border-[#1a2d4a] rounded-lg text-xs">
            <div className="text-gray-400 font-medium mb-1.5">📋 自定义求解器格式要求：</div>
            <ul className="text-gray-500 space-y-0.5 ml-4 list-disc">
              <li>继承 <code className="text-blue-400">BaseSolver</code> 并实现 <code className="text-blue-400">solve()</code> 方法</li>
              <li>定义 <code className="text-purple-400">CustomSolver</code> 类（固定名称）</li>
              <li>签名：<code className="text-green-400">def solve(self, rhs_func, y0, t_span, **kwargs)</code></li>
              <li>返回：求解结果（通常是 <code className="text-orange-400">scipy.integrate.solve_ivp</code> 格式）</li>
            </ul>
          </div>

          <div className="border-2 border-dashed border-[#1a2d4a] rounded-xl p-6 text-center">
            <input
              type="file"
              accept=".py"
              className="hidden"
              id="custom-solver-upload"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleCustomUpload(file);
              }}
            />
            <label
              htmlFor="custom-solver-upload"
              className="cursor-pointer flex flex-col items-center gap-2"
            >
              <div className="text-4xl">📤</div>
              <div className="text-sm text-gray-400">
                点击上传自定义求解器 (.py)
              </div>
              <div className="text-xs text-gray-500">
                必须继承 BaseSolver 并定义 CustomSolver 类
              </div>
            </label>
            <button
              onClick={() => {
                // TODO: 加载自定义求解器模板
                const template = getCustomSolverTemplate();
                // 暂时用 alert 显示模板，用户可以手动复制
                alert('模板已准备好！请复制以下代码到 .py 文件：\n\n' + template);
              }}
              className="mt-2 text-xs px-3 py-1 bg-purple-600/20 border border-purple-500/50 hover:bg-purple-600/40 text-purple-400 rounded transition"
            >
              📋 加载模板
            </button>
          </div>

          {customFile && (
            <div className="bg-[#0a0e17] border border-[#1a2d4a] rounded-lg p-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-green-400">✓</span>
                  <span className="text-white">{customFile.name}</span>
                  <span className="text-gray-500">({(customFile.size / 1024).toFixed(1)} KB)</span>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setShowEditor(true)}
                    className="text-xs px-3 py-1 bg-blue-600/20 border border-blue-500/50 hover:bg-blue-600/40 text-blue-400 rounded transition"
                  >
                    👁️ 查看/编辑代码
                  </button>
                  <button
                    onClick={() => {
                      setCustomFile(null);
                      setValidationResult(null);
                      setCustomSolverCode('');
                      onChange({ ...config, solver_type: 'auto', custom_solver_path: undefined });
                    }}
                    className="text-xs px-3 py-1 bg-gray-600/20 border border-gray-500/50 hover:bg-gray-600/40 text-gray-400 rounded transition"
                  >
                    🔄 重新上传
                  </button>
                </div>
              </div>
            </div>
          )}

          {isValidating && (
            <div className="text-sm text-yellow-400">⏳ 验证中...</div>
          )}

          {validationResult && (
            <div className={`text-sm p-2 rounded ${validationResult.valid ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'}`}>
              {validationResult.valid ? '✅ 验证通过' : '❌ 验证失败'}
              {validationResult.errors?.length > 0 && (
                <div className="mt-1 text-xs">{validationResult.errors.join(', ')}</div>
              )}
              {validationResult.warnings?.length > 0 && (
                <div className="mt-1 text-xs text-yellow-400">⚠️ {validationResult.warnings.join(', ')}</div>
              )}
            </div>
          )}

          {/* Monaco Editor 弹窗 - 查看/编辑自定义求解器代码 */}
          {showEditor && customSolverCode && (
            <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
              <div className="bg-[#0a0e17] border border-[#1a2d4a] rounded-xl w-[90%] max-w-4xl h-[80vh] flex flex-col">
                <div className="flex items-center justify-between p-4 border-b border-[#1a2d4a]">
                  <div className="text-sm font-medium text-white">编辑自定义求解器代码</div>
                  <button
                    onClick={() => setShowEditor(false)}
                    className="text-gray-400 hover:text-white"
                  >
                    ✕
                  </button>
                </div>

                <div className="flex-1 overflow-hidden p-4" style={{ minHeight: 0 }}>
                  <MonacoEditor
                    key={showEditor ? 'solver-editor-open' : 'solver-editor-closed'}
                    height="calc(100% - 20px)"
                    defaultLanguage="python"
                    value={customSolverCode}
                    onChange={(val) => setCustomSolverCode(val || '')}
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

                <div className="flex items-center justify-end gap-3 p-4 border-t border-[#1a2d4a]">
                  <button
                    onClick={() => setShowEditor(false)}
                    className="px-4 py-2 text-sm bg-gray-600 hover:bg-gray-700 text-white rounded-lg transition"
                  >
                    取消
                  </button>
                  <button
                    onClick={async () => {
                      // 重新验证修改后的代码
                      setIsValidating(true);
                      try {
                        const { validateCustomSolver } = await import('@/api/client');
                        const result = await validateCustomSolver(customSolverCode);
                        setValidationResult(result);

                        if (result.valid) {
                          alert('✅ 验证通过！修改已保存。');
                          setShowEditor(false);
                        } else {
                          alert('❌ 验证失败，请检查错误信息。');
                        }
                      } catch (err: any) {
                        alert('验证失败: ' + (err.message || '未知错误'));
                      } finally {
                        setIsValidating(false);
                      }
                    }}
                    disabled={isValidating}
                    className="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg transition"
                  >
                    {isValidating ? '验证中...' : '✅ 保存并重新验证'}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* 自定义求解器参数注入 */}
          {config.solver_type === 'custom' && (
            <details className="bg-[#0a0e17] border border-[#1a2d4a] rounded-lg p-3">
              <summary className="text-sm text-gray-400 cursor-pointer">📝 参数注入</summary>
              <div className="mt-3 text-xs text-gray-500">
                在控制律中可通过 params 访问：params.get("K1", 0.5)
              </div>
              <div className="mt-2 space-y-2">
                <button
                  onClick={() => handleParamChange('K1', 0.5)}
                  className="text-xs px-2 py-1 bg-purple-600/20 border border-purple-500/50 rounded text-purple-400"
                >
                  + 添加参数 K1
                </button>
              </div>
            </details>
          )}
        </div>
      )}
    </div>
  );
};

export default SolverSelector;
