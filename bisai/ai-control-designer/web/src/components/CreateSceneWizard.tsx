import React, { useState } from 'react';
import ExpertEditor from './ExpertEditor';
import NewbieWizard from './NewbieWizard';

interface CreateSceneWizardProps {
  onSubmit: (data: {
    name: string;
    description: string;
    mode: 'expert' | 'newbie';
    scene_config: any;
    model_code: string;
    control_v1_code?: string;
  }) => void;
  initialData?: {
    name?: string;
    description?: string;
  };
}

const CreateSceneWizard: React.FC<CreateSceneWizardProps> = ({ onSubmit, initialData }) => {
  const [mode, setMode] = useState<'expert' | 'newbie'>('expert');

  const handleSubmit = (data: any) => {
    onSubmit({
      ...data,
      mode,
    });
  };

  return (
    <div className="space-y-8">
      {/* 模式选择 - 终极炫酷版 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <button
          className={`mode-card-v2 mode-card-v2-expert text-left group ${mode === 'expert' ? 'border-blue-500 scale-[1.01]' : ''}`}
          onClick={() => setMode('expert')}
        >
          <div className="flex items-start gap-4">
            <div className="text-6xl transition-transform group-hover:scale-110">👨‍💻</div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <div className="font-bold text-2xl text-white">专家模式</div>
                {mode === 'expert' && (
                  <span className="badge-tech-blue px-3 py-0.5 text-xs">当前选择</span>
                )}
              </div>
              <div className="text-gray-400 text-sm leading-relaxed">
                直接上传模型代码和配置文件，<br />完全掌控控制律生成流程
              </div>
              <div className="mt-4 flex gap-2">
                <span className="badge-tech-purple text-xs">Python</span>
                <span className="badge-tech-purple text-xs">自定义</span>
                <span className="badge-tech-purple text-xs">高级</span>
              </div>
            </div>
          </div>
        </button>

        <button
          className={`mode-card-v2 mode-card-v2-newbie text-left group ${mode === 'newbie' ? 'border-teal-500 scale-[1.01]' : ''}`}
          onClick={() => setMode('newbie')}
        >
          <div className="flex items-start gap-4">
            <div className="text-6xl transition-transform group-hover:scale-110">🤖</div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-2">
                <div className="font-bold text-2xl text-white">新手模式</div>
                {mode === 'newbie' && (
                  <span className="badge-tech-green px-3 py-0.5 text-xs">当前选择</span>
                )}
              </div>
              <div className="text-gray-400 text-sm leading-relaxed">
                AI 引导创建，用自然语言描述<br />自动生成完整控制律系统
              </div>
              <div className="mt-4 flex gap-2">
                <span className="badge-tech-teal text-xs">AI 辅助</span>
                <span className="badge-tech-teal text-xs">简单</span>
                <span className="badge-tech-teal text-xs">快速</span>
              </div>
            </div>
          </div>
        </button>
      </div>

      {/* 内容区域 - 玻璃态增强 */}
      <div className="glass-ultra p-8 rounded-3xl border border-[#1a2d4a]">
        {mode === 'expert' ? (
          <ExpertEditor
            onSubmit={handleSubmit}
            initialData={initialData}
          />
        ) : (
          <NewbieWizard
            onSubmit={handleSubmit}
          />
        )}
      </div>
    </div>
  );
};

export default CreateSceneWizard;