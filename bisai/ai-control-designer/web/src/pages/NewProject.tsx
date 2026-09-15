import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useProjectStore } from '@/stores/projectStore';
import ExpertEditor from '@/components/ExpertEditor';

const NewProject: React.FC = () => {
  const navigate = useNavigate();
  const { createProject } = useProjectStore();

  const handleSubmit = async (data: any) => {
    try {
      const project = await createProject({ ...data, mode: 'expert' });
      navigate(`/projects/${project.project_id}`);
    } catch (err: any) {
      alert('创建失败: ' + err.message);
    }
  };

  return (
    <div className="max-w-5xl mx-auto">
      {/* 页面标题 - 增强版 */}
      <div className="mb-10 text-center">
        <div className="inline-flex items-center gap-3 mb-4">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 via-purple-500 to-teal-500 flex items-center justify-center">
            <span className="text-2xl">🚀</span>
          </div>
          <h1 className="text-5xl font-bold text-white tracking-tight text-glow">
            新建项目
          </h1>
        </div>
        <p className="text-gray-400 text-lg font-mono tracking-[2px]">
          上传模型代码 · 开启智能控制律设计之旅
        </p>
        <div className="mt-4 flex justify-center gap-2">
          <div className="h-px w-20 bg-gradient-to-r from-transparent via-blue-500/50 to-transparent mt-3" />
          <div className="badge-tech-blue">AI POWERED</div>
          <div className="h-px w-20 bg-gradient-to-l from-transparent via-purple-500/50 to-transparent mt-3" />
        </div>
      </div>

      {/* 专家模式卡片（全宽） */}
      <div className="mb-8">
        <div className="mode-card mode-card-expert text-left group ring-2 ring-blue-500/60">
          <div className="flex items-start justify-between mb-6">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/20 to-blue-600/20 flex items-center justify-center border border-blue-500/30">
              <span className="text-4xl">👨‍💻</span>
            </div>
            <div className="badge-tech-blue flex items-center gap-1.5">
              <div className="status-dot-online" />
              已选择
            </div>
          </div>

          <div className="space-y-3">
            <h3 className="text-2xl font-bold text-white tracking-tight">专家模式</h3>
            <p className="text-gray-400 text-[15px] leading-relaxed">
              直接上传模型代码和配置文件 · 完全掌控 · 精细调优
            </p>
          </div>

          <div className="mt-6 pt-6 border-t border-[#1a2d4a] flex items-center gap-2 text-sm text-blue-400/80">
            <span>上传 model_code.py + scene_config.json</span>
            <span>→</span>
          </div>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="glass-card p-8">
        <div className="mb-6 flex items-center gap-3">
          <div className="badge-tech-purple">EXPERT MODE</div>
          <div className="h-px flex-1 bg-gradient-to-r from-[#1a2d4a] to-transparent" />
        </div>

        <ExpertEditor onSubmit={handleSubmit} />
      </div>

      {/* 底部提示 */}
      <div className="mt-6 text-center">
        <p className="text-xs text-gray-500 font-mono tracking-widest">
          POWERED BY EVOLUTIONARY AI + LLM
        </p>
      </div>
    </div>
  );
};

export default NewProject;