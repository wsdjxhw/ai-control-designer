import React, { useState } from 'react';
import { generateScene, validatePhysics } from '@/api/client';
import OptimizerConfigPanel, { OptimizerConfig } from './OptimizerConfigPanel';

interface NewbieWizardProps {
  onSubmit: (data: {
    name: string;
    description: string;
    scene_config: any;
    model_code: string;
    control_v1_code?: string;
  }) => void;
}

const NewbieWizard: React.FC<NewbieWizardProps> = ({ onSubmit }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [generated, setGenerated] = useState<{
    scene_config: any;
    model_code: string;
    cost_function_code: string;
  } | null>(null);
  const [validation, setValidation] = useState<{
    L1: boolean;
    L2: boolean;
    L3: boolean;
    details: string;
  } | null>(null);

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

  const handleGenerate = async () => {
    if (!prompt.trim()) return alert('请输入系统描述');
    setLoading(true);
    try {
      const result = await generateScene(prompt);
      setGenerated(result);
      const vResult = await validatePhysics(result.model_code, result.scene_config);
      setValidation(vResult);
    } catch (err: any) {
      alert('生成失败: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = () => {
    if (!generated) return alert('请先生成场景');
    if (!validation?.L1 || !validation?.L2 || !validation?.L3) {
      if (!confirm('物理验证未完全通过，确定要创建项目吗？')) return;
    }
    onSubmit({
      name: name || '新手项目',
      description: description || prompt.slice(0, 100),
      scene_config: generated.scene_config,
      model_code: generated.model_code,
      optimizer_config: optimizerConfig,
    });
  };

  return (
    <div className="space-y-4">
      {/* 基本信息 */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">项目名称</label>
          <input
            className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 placeholder-gray-500 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/30 outline-none transition"
            placeholder="输入项目名称"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1">项目描述</label>
          <input
            className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 placeholder-gray-500 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/30 outline-none transition"
            placeholder="简要描述"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>
      </div>

      {/* 自然语言输入 */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-1">📝 系统描述</label>
        <textarea
          className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 placeholder-gray-500 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/30 outline-none transition resize-none"
          placeholder="用自然语言描述你的物理系统，例如：'我想控制一个直流电机，输入电压控制转速，状态变量是角速度和电流...'"
          rows={4}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
        />
      </div>

      <button
        onClick={handleGenerate}
        disabled={loading}
        className="btn-neon w-full sm:w-auto disabled:opacity-50"
      >
        {loading ? '⏳ 生成中...' : '🤖 AI 生成场景'}
      </button>

      {/* 生成结果 */}
      {generated && (
        <div className="mt-4 p-4 glass-card border-teal-500/30">
          <h3 className="font-semibold text-white mb-2">✅ 生成完成</h3>
          <div className="text-sm space-y-1 font-mono">
            <div className="flex justify-between py-1 border-b border-[#1a2d4a]">
              <span className="text-gray-400">领域</span>
              <span className="text-teal-400">{generated.scene_config.domain}</span>
            </div>
            <div className="flex justify-between py-1 border-b border-[#1a2d4a]">
              <span className="text-gray-400">状态变量</span>
              <span className="text-gray-300">{generated.scene_config.state_names?.join(', ') || '无'}</span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-gray-400">控制变量</span>
              <span className="text-gray-300">{generated.scene_config.control_names?.join(', ') || '无'}</span>
            </div>
          </div>

          {/* 验证结果 */}
          {validation && (
            <div className="mt-3 p-3 bg-[#0a0e17] rounded-xl border border-[#1a2d4a]">
              <p className="text-sm font-medium text-gray-300 mb-2">🔍 物理验证</p>
              <div className="grid grid-cols-3 gap-2 text-xs">
                <div className={`text-center py-1.5 rounded-lg ${validation.L1 ? 'text-green-400 bg-green-500/10 border border-green-500/20' : 'text-red-400 bg-red-500/10 border border-red-500/20'}`}>
                  L1 语义 {validation.L1 ? '✅' : '❌'}
                </div>
                <div className={`text-center py-1.5 rounded-lg ${validation.L2 ? 'text-green-400 bg-green-500/10 border border-green-500/20' : 'text-red-400 bg-red-500/10 border border-red-500/20'}`}>
                  L2 符号 {validation.L2 ? '✅' : '❌'}
                </div>
                <div className={`text-center py-1.5 rounded-lg ${validation.L3 ? 'text-green-400 bg-green-500/10 border border-green-500/20' : 'text-red-400 bg-red-500/10 border border-red-500/20'}`}>
                  L3 烟雾 {validation.L3 ? '✅' : '❌'}
                </div>
              </div>
              <pre className="mt-2 text-xs text-gray-400 font-mono bg-[#0a0e17] p-2 rounded-lg overflow-auto max-h-20">
                {validation.details}
              </pre>
            </div>
          )}

          <button
            onClick={handleSubmit}
            className="btn-neon w-full sm:w-auto mt-4"
          >
            ✅ 确认创建项目
          </button>
        </div>
      )}

      {/* 优化器配置面板 */}
      <OptimizerConfigPanel config={optimizerConfig} onChange={setOptimizerConfig} />
    </div>
  );
};

export default NewbieWizard;