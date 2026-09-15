import React, { useState } from 'react';
import MonacoEditor from '@monaco-editor/react';
import { generateControlLaw, parseExpertFiles, parseSingleModel, validateModel } from '@/api/client';
import OptimizerConfigPanel, { OptimizerConfig } from './OptimizerConfigPanel';
import SolverSelector, { SolverConfig } from './SolverSelector';
import SceneConfigPanel from './SceneConfigPanel';

interface ExpertEditorProps {
  onSubmit: (data: {
    name: string;
    description: string;
    scene_config: any;
    model_code: string;
    control_v1_code: string;
  }) => void;
  initialData?: {
    name?: string;
    description?: string;
    scene_config?: string;
    model_code?: string;
    control_v1_code?: string;
  };
}

const ExpertEditor: React.FC<ExpertEditorProps> = ({ onSubmit, initialData }) => {
  const [name, setName] = useState(initialData?.name || '');
  const [description, setDescription] = useState(initialData?.description || '');

  // 单一文件上传模式（唯一支持的模式）
  const [modelCode, setModelCode] = useState(
    initialData?.model_code ||
      `# 示例：单摆系统 (Pendulum)
# 继承 BaseModel 并实现必需的方法
# 硬编码参数 (self.xxx = ...) 会被 LLM 自动提取

from core.base.base_model import BaseModel
import numpy as np

class Pendulum(BaseModel):
    """单摆系统"""

    def __init__(self, scene_config=None):
        if scene_config is None:
            scene_config = {}
        params = scene_config.get("model_params", {})
        self.length = params.get("length", 1.0)      # 摆长 (m)
        self.mass = params.get("mass", 1.0)          # 摆锤质量 (kg)
        self.g = params.get("g", 9.81)               # 重力加速度 (m/s²)

    def get_initial_state(self, x_grid=None):
        """返回初始状态 [θ, ω]"""
        # 默认初始状态: θ=0.5 rad, ω=0
        return np.array([0.5, 0.0])

    def rhs(self, t, x, u):
        """状态方程: dx/dt = f(x, u)"""
        theta, omega = x[0], x[1]
        torque = u[0] if len(u) > 0 else 0.0

        # 单摆动力学
        dtheta_dt = omega
        domega_dt = -(self.g / self.length) * np.sin(theta) + torque / (self.mass * self.length**2)

        return np.array([dtheta_dt, domega_dt])

    def validate_state(self, state):
        """验证状态是否有效"""
        # 单摆状态通常没有硬性约束,返回 True 表示总是有效
        return True
`
  );

  // scene_config 状态
  const [sceneConfig, setSceneConfig] = useState(
    initialData?.scene_config ||
      JSON.stringify(
        {
          domain: 'custom',
          state_names: ['x1', 'x2'],
          control_names: ['u1'],
          target_values: { x1: 1.0, x2: 0.5 },
          cost_weights: { x1: 1.0, x2: 1.0, u1: 0.1 },
          solver: {
            solver_type: 'auto',
          },
        },
        null,
        2
      )
  );

  // 新增状态
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateError, setGenerateError] = useState<string | null>(null);

  // 优化器配置状态
  const [optimizerConfig, setOptimizerConfig] = useState<OptimizerConfig>({
    optimizer_type: 'cmaes',
    popsize: 50,
    sigma0: 0.25,
    n_particles: 30,
    w: 0.7,
    c1: 1.5,
    c2: 1.5,
    max_iter: 100,
    n_startup_trials: 10,
    n_ei_candidates: 24,
  });

  // 求解器配置状态
  const [solverConfig, setSolverConfig] = useState<SolverConfig>({
    solver_type: 'auto',
    solver_params: {},
  });

  // 模型代码验证状态
  const [modelValidation, setModelValidation] = useState<{
    valid: boolean;
    errors: string[];
    warnings: string[];
  }>({ valid: true, errors: [], warnings: [] });

  // 解析日志 (单文件模式)
  const [extractionLog, setExtractionLog] = useState<string[]>([]);
  const [parseWarnings, setParseWarnings] = useState<string[]>([]);
  const [typeDetection, setTypeDetection] = useState<{
    model_type: 'ode' | 'pde' | 'unknown';
    confidence: number;
    evidence: string[];
    user_can_override: boolean;
  } | undefined>(undefined);

  // 🆕 保存 LLM 生成的控制律代码
  const [controlLawCode, setControlLawCode] = useState('');

  // 验证 model.py 代码格式（混合方案：前端快速检查 + 后端 AST 深度验证）
  const validateModelCode = async (code: string) => {
    // 前端快速检查（实时反馈）
    const frontendErrors: string[] = [];
    const frontendWarnings: string[] = [];

    // 检查 1: 是否定义了类
    if (!/class\s+\w+\s*\([^)]*BaseModel[^)]*\)/.test(code) && !/class\s+\w+\s*\(/.test(code)) {
      frontendErrors.push('未检测到继承 BaseModel 的类定义');
    }

    // 检查 2: 是否实现了 rhs 方法
    if (!/def\s+rhs\s*\(self/.test(code)) {
      frontendErrors.push('未找到 rhs(self, t, x, u) 方法定义');
    }

    // 检查 2b: 是否实现了 get_initial_state 方法
    if (!/def\s+get_initial_state\s*\(self/.test(code)) {
      frontendErrors.push('未找到 get_initial_state(self, x_grid=None) 方法定义（必需的抽象方法）');
    }

    // 检查 3: 是否有 self.xxx = ... 硬编码参数
    if (!/self\.\w+\s*=/.test(code)) {
      frontendWarnings.push('未检测到硬编码参数赋值（self.xxx = ...），LLM 可能无法提取物理参数');
    }

    // 检查 4: 是否导入了 BaseModel
    if (!/from\s+core\.base\.base_model|import\s+.*BaseModel/.test(code)) {
      frontendWarnings.push('建议显式导入 BaseModel: from core.base.base_model import BaseModel');
    }

    // 检查 5: 是否有 __init__ 方法
    if (!/def\s+__init__\s*\(self/.test(code)) {
      frontendErrors.push('未找到 __init__ 方法定义（用于初始化硬编码参数）');
    }

    // 检查 6: rhs 方法签名是否正确
    if (/def\s+rhs\s*\(self,\s*\w+,\s*\w+,\s*\w+\)/.test(code) === false &&
        /def\s+rhs\s*\(self/.test(code)) {
      frontendWarnings.push('rhs 方法建议使用标准签名: def rhs(self, t, x, u):');
    }

    // 检查 7: return np.array([...])
    if (!/return\s+np\.array\s*\(/.test(code)) {
      frontendErrors.push('rhs 方法必须包含 return np.array([...]) 语句');
    }

    // 检查 8: 常见拼写错误
    if (/np\.aay|np\.arra[^y]|np\.aray/.test(code)) {
      frontendErrors.push('检测到 np.array 拼写错误，应为 return np.array([...])');
    }

    // 如果前端快速检查就失败，直接返回
    if (frontendErrors.length > 0) {
      setModelValidation({ valid: false, errors: frontendErrors, warnings: frontendWarnings });
      return;
    }

    // 调用后端 AST 深度验证
    try {
      const result = await validateModel(code);
      // 合并前端警告和后端结果
      const mergedWarnings = [...frontendWarnings, ...result.warnings];
      setModelValidation({
        valid: result.valid,
        errors: result.errors,
        warnings: mergedWarnings,
      });
    } catch (err) {
      // 后端验证失败时，降级使用前端结果
      console.warn('[validateModel] 后端验证失败，降级使用前端验证:', err);
      setModelValidation({
        valid: frontendErrors.length === 0,
        errors: frontendErrors,
        warnings: frontendWarnings,
      });
    }
  };

  // 当 modelCode 变化时自动验证（防抖处理）
  React.useEffect(() => {
    if (modelCode.trim()) {
      const timer = setTimeout(() => {
        validateModelCode(modelCode);
      }, 500); // 500ms 防抖
      return () => clearTimeout(timer);
    }
  }, [modelCode]);

  // 调用 LLM 解析单一文件
  const handleLLMGenerateSingle = async () => {
    setIsGenerating(true);
    setGenerateError(null);
    setExtractionLog([]);
    setParseWarnings([]);

    try {
      const response = await parseSingleModel({
        model_code: modelCode,
        description: description || undefined,
      });

      if (response.scene_config_extracted) {
        setSceneConfig(JSON.stringify(response.scene_config_extracted, null, 2));
      }
      if (response.extraction_log) {
        setExtractionLog(response.extraction_log);
      }
      if (response.warnings && response.warnings.length > 0) {
        setParseWarnings(response.warnings);
      }
      if (response.type_detection) {
        setTypeDetection(response.type_detection);
      }
      // 🆕 如果解析时 LLM 顺带返回了控制律，也存起来
      if ((response as any).control_law_code) {
        setControlLawCode((response as any).control_law_code);
      }

      alert('✅ LLM 已从单一文件提取 scene_config！请检查并确认配置，然后点击下方按钮生成控制律。');
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || '解析失败';
      setGenerateError(msg);
      alert('❌ 解析失败: ' + msg);
    } finally {
      setIsGenerating(false);
    }
  };

  // 独立步骤：生成初始控制律
  const handleGenerateControlLaw = async () => {
    setIsGenerating(true);
    setGenerateError(null);

    try {
      const sceneConfigParsed = JSON.parse(sceneConfig);

      // 调用独立的控制律生成 API
      const response = await generateControlLaw({
        model_code: modelCode,
        scene_config: sceneConfigParsed,
        description: description || undefined,
      });

      if (response.control_law_code) {
        setControlLawCode(response.control_law_code);   // 🆕 存到 state
        alert('✅ 控制律已生成！点击下方"创建项目"提交。');
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || '生成失败';
      setGenerateError(msg);
      alert('❌ 生成失败: ' + msg);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSubmit = () => {
    try {
      const parsedConfig = JSON.parse(sceneConfig);
      onSubmit({
        name,
        description,
        scene_config: {
          ...parsedConfig,
          solver: solverConfig,  // 注入求解器配置
        },
        model_code: modelCode,
        control_v1_code: controlLawCode,
        optimizer_config: optimizerConfig,
      });
    } catch (e) {
      alert('提交失败: ' + (e instanceof Error ? e.message : String(e)));
    }
  };

  return (
    <div className="space-y-4">
      {/* 基本信息输入 */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">项目名称 *</label>
          <input
            className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition"
            placeholder="输入项目名称"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">项目描述</label>
          <input
            className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition"
            placeholder="简要描述项目目的"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      </div>

      {/* 单一文件上传模式（唯一支持的模式） */}
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">
            📄 完整代码文件 model.py <span className="text-red-400">*</span>
          </label>

          {/* 格式要求提示 */}
          <div className="mb-2 p-3 bg-[#0a0e17] border border-[#1a2d4a] rounded-lg text-xs">
            <div className="text-gray-400 font-medium mb-1.5">📋 model.py 格式要求：</div>
            <ul className="text-gray-500 space-y-0.5 ml-4 list-disc">
              <li>继承 <code className="text-blue-400">BaseModel</code> 并实现 <code className="text-blue-400">rhs(self, t, x, u)</code> 方法</li>
              <li>使用硬编码参数（如 <code className="text-purple-400">self.mass = 1.0</code>）会被 LLM 自动提取</li>
              <li>建议命名：state 变量用 <code className="text-green-400">x1, x2</code>，控制输入用 <code className="text-green-400">u1, u2</code></li>
              <li>示例：<code className="text-orange-400">class Pendulum(BaseModel): ...</code></li>
            </ul>
          </div>

          {/* 验证状态指示器 */}
          {modelCode.trim() && (
            <div className={`mb-2 px-3 py-2 rounded-lg text-xs flex items-start gap-2 ${
              modelValidation.valid
                ? modelValidation.warnings.length > 0
                  ? 'bg-yellow-500/10 border border-yellow-500/30 text-yellow-400'
                  : 'bg-green-500/10 border border-green-500/30 text-green-400'
                : 'bg-red-500/10 border border-red-500/30 text-red-400'
            }`}>
              <span className="mt-0.5">
                {modelValidation.valid
                  ? modelValidation.warnings.length > 0 ? '⚠️' : '✅'
                  : '❌'}
              </span>
              <div className="flex-1">
                {modelValidation.valid ? (
                  modelValidation.warnings.length > 0 ? (
                    <>
                      <div className="font-medium">代码基本符合要求，但有以下建议：</div>
                      <ul className="mt-1 ml-4 list-disc text-yellow-500/80">
                        {modelValidation.warnings.map((w, i) => (
                          <li key={i}>{w}</li>
                        ))}
                      </ul>
                    </>
                  ) : (
                    <span className="font-medium">✅ 代码格式验证通过</span>
                  )
                ) : (
                  <>
                    <div className="font-medium">代码格式不符合要求：</div>
                    <ul className="mt-1 ml-4 list-disc">
                      {modelValidation.errors.map((e, i) => (
                        <li key={i}>{e}</li>
                      ))}
                    </ul>
                  </>
                )}
              </div>
            </div>
          )}

          <div className="border border-[#1a2d4a] rounded-xl overflow-hidden bg-[#0a0e17]">
            <MonacoEditor
              height="420px"
              defaultLanguage="python"
              value={modelCode}
              onChange={(val) => setModelCode(val || '')}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                theme: 'vs-dark',
                automaticLayout: true,
                scrollBeyondLastLine: false,
                lineNumbers: 'on',
                renderWhitespace: 'selection',
                fontFamily: 'JetBrains Mono, monospace',
              }}
            />
          </div>
          <p className="text-xs text-gray-500 mt-1.5">
            💡 LLM 将自动解析代码中的硬编码参数 (self.mass, self.T, self.initial_state 等)
          </p>
        </div>

        {/* LLM 生成按钮 - 单文件模式 */}
        <button
          onClick={handleLLMGenerateSingle}
          disabled={isGenerating || !modelCode.trim()}
          className="w-full px-6 py-3 text-sm bg-purple-600 hover:bg-purple-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-xl transition flex items-center justify-center gap-2"
        >
          {isGenerating ? (
            <>
              <span className="animate-spin">⏳</span>
              LLM 正在提取 scene_config...
            </>
          ) : (
            <>🤖 LLM 解析并提取 scene_config（不生成控制律）</>
          )}
        </button>

        {/* 独立生成控制律按钮 - 仅在 scene_config 已解析后显示 */}
        {sceneConfig && sceneConfig !== JSON.stringify({ domain: 'custom', state_names: ['x1', 'x2'], control_names: ['u1'] }, null, 2) && (
          <button
            onClick={handleGenerateControlLaw}
            disabled={isGenerating}
            className="w-full px-6 py-3 text-sm bg-teal-600 hover:bg-teal-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-xl transition flex items-center justify-center gap-2 mt-2"
          >
            {isGenerating ? (
              <>
                <span className="animate-spin">⏳</span>
                正在生成控制律...
              </>
            ) : (
              <>🎮 生成初始控制律</>
            )}
          </button>
        )}

        {/* 提取日志显示 */}
        {extractionLog.length > 0 && (
          <div className="glass-card p-4 bg-purple-500/5 border-purple-500/30">
            <div className="text-sm font-medium text-purple-400 mb-2">📋 参数提取日志</div>
            <div className="space-y-1 text-xs font-mono">
              {extractionLog.map((log, idx) => (
                <div key={idx} className="text-gray-400">
                  ✓ {log}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 场景配置参数面板 - LLM 解析成功后显示 */}
        {sceneConfig && sceneConfig !== JSON.stringify({ domain: 'custom', state_names: ['x1', 'x2'], control_names: ['u1'] }, null, 2) && (
          <SceneConfigPanel
        config={sceneConfig}
        onChange={setSceneConfig}
        typeDetection={typeDetection}
      />
        )}
      </div>

      {/* 求解器配置面板 */}
      <SolverSelector config={solverConfig} onChange={setSolverConfig} />

      {/* 优化器配置面板 */}
      <OptimizerConfigPanel config={optimizerConfig} onChange={setOptimizerConfig} />

      {/* 提交按钮 */}
      <button
        onClick={handleSubmit}
        className="btn-neon w-full sm:w-auto"
      >
        🚀 创建项目
      </button>
    </div>
  );
};

export default ExpertEditor;