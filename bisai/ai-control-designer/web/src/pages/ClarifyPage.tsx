import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useProjectStore } from '@/stores/projectStore';

interface ClarifyResponse {
  session_id: string;
  stage: string;
  message: string;
  collected: Record<string, any>;
  missing_items: string[];
  draft_config: Record<string, any>;
  missing_fields: string[];
  ready_to_create: boolean;
  scene_config?: any;
  model_code?: string;
  cost_function?: any;
}

const ClarifyPage: React.FC = () => {
  const navigate = useNavigate();
  const { createProject } = useProjectStore();

  const [sessionId, setSessionId] = useState<string | null>(null);
  const [description, setDescription] = useState('');
  const [stage, setStage] = useState<string>('init');
  const [message, setMessage] = useState('');
  const [collected, setCollected] = useState<Record<string, any>>({});
  const [missingItems, setMissingItems] = useState<string[]>([]);
  const [draftConfig, setDraftConfig] = useState<Record<string, any>>({});
  const [missingFields, setMissingFields] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [started, setStarted] = useState(false);
  const [editMode, setEditMode] = useState(false);

  // Checklist 项定义（已废弃，保留仅为兼容）
  const checklistLabels: Record<string, string> = {};

  // 启动澄清会话
  const startClarify = async () => {
    if (!description.trim()) return alert('请输入问题描述');

    setLoading(true);
    try {
      const resp = await fetch('/api/v1/clarify/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: description.trim() }),
      });

      if (!resp.ok) throw new Error(await resp.text());

      const data: ClarifyResponse = await resp.json();

      setSessionId(data.session_id);
      setStage(data.stage);
      setMessage(data.message);
      setCollected(data.collected || {});
      setMissingItems(data.missing_items || []);
      setDraftConfig(data.draft_config || {});
      setMissingFields(data.missing_fields || []);
      setStarted(true);
    } catch (err: any) {
      alert('启动失败: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // 发送用户消息
  const sendMessage = async (userMsg: string) => {
    if (!sessionId || loading || !userMsg.trim()) return;

    setLoading(true);
    try {
      const resp = await fetch('/api/v1/clarify/turn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: userMsg.trim(),
        }),
      });

      if (!resp.ok) throw new Error(await resp.text());

      const data: ClarifyResponse = await resp.json();

      setStage(data.stage);
      setMessage(data.message);
      setCollected(data.collected || {});
      setMissingItems(data.missing_items || []);
      setDraftConfig(data.draft_config || {});
      setMissingFields(data.missing_fields || []);

      // 如果进入 draft 阶段，自动切换到编辑模式
      if (data.stage === 'draft' || data.stage === 'editing') {
        setEditMode(true);
      }

      // 如果已准备好创建
      if (data.ready_to_create && data.scene_config && data.model_code) {
        setTimeout(async () => {
          try {
            const project = await createProject({
              name: '新手项目',
              description: description.slice(0, 100),
              scene_config: data.scene_config,
              model_code: data.model_code,
              mode: 'newbie',
            });
            navigate(`/projects/${project.project_id}`);
          } catch (err: any) {
            alert('创建项目失败: ' + err.message);
          }
        }, 1500);
      }
    } catch (err: any) {
      alert('发送失败: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // 更新 draft_config 字段
  const updateDraftField = (field: string, value: any) => {
    setDraftConfig(prev => ({ ...prev, [field]: value }));
  };

  // 提交编辑后的 draft
  const submitDraft = () => {
    const updateMsg = `我已编辑配置：${JSON.stringify(draftConfig)}`;
    sendMessage(updateMsg);
  };

  // 确认配置
  const confirmConfig = () => {
    sendMessage("配置已确认，请生成最终的 scene_config、model_code 和 cost_function");
  };

  // 取消
  const handleCancel = async () => {
    if (sessionId) {
      try {
        await fetch('/api/v1/clarify/cancel', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId }),
        });
      } catch (e) {}
    }
    navigate('/projects/new');
  };

  // 渲染纯对话收集界面（无固定清单）
  const renderCollecting = () => (
    <div className="glass-card p-4">
      <p className="text-sm text-gray-400 mb-2">💬 请按 LLM 提示逐条回复（可一次发送多条信息）：</p>
      <div className="flex gap-3">
        <input
          type="text"
          className="flex-1 bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-3 text-gray-200 placeholder-gray-500 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/30 outline-none transition"
          placeholder="例如：状态有 S,I,R，S代表易感者，初始值 S=990,I=10,R=0..."
          onKeyDown={(e) => {
            if (e.key === 'Enter' && e.currentTarget.value.trim()) {
              sendMessage(e.currentTarget.value.trim());
              e.currentTarget.value = '';
            }
          }}
          disabled={loading}
        />
        <button onClick={() => { /* 由 onKeyDown 处理 */ }} disabled={loading} className="btn-neon px-6">发送</button>
      </div>
      <p className="text-xs text-gray-500 mt-2">提示：LLM 会智能解析你的回复并检查是否足够生成配置清单</p>
    </div>
  );

  // 渲染 Draft 编辑界面
  const renderDraftEditor = () => {
    const fields = [
      { key: 'state_names', label: '状态变量 (state_names)', type: 'array' },
      { key: 'state_meanings', label: '状态含义 (state_meanings)', type: 'object' },
      { key: 'state_ranges', label: '状态范围 (state_ranges)', type: 'object' },
      { key: 'control_names', label: '控制动作 (control_names)', type: 'array' },
      { key: 'control_meanings', label: '动作含义 (control_meanings)', type: 'object' },
      { key: 'control_ranges', label: '动作范围 (control_ranges)', type: 'object' },
      { key: 'cost_objective', label: '代价/目标函数 (cost_objective)', type: 'string' },
      { key: 'solver', label: '求解器 (solver)', type: 'string' },
    ];

    return (
      <div className="glass-card p-6 mb-4">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-white">📋 配置清单确认（8 项）</h2>
          <div className="flex gap-2">
            {!editMode && (
              <button onClick={() => setEditMode(true)} className="px-4 py-1.5 text-sm bg-[#1a2d4a] hover:bg-[#2a3f5a] rounded-lg transition">✏️ 编辑</button>
            )}
            {editMode && (
              <>
                <button onClick={submitDraft} disabled={loading} className="px-4 py-1.5 text-sm btn-neon">💾 保存</button>
                <button onClick={() => setEditMode(false)} className="px-4 py-1.5 text-sm bg-[#1a2d4a] hover:bg-[#2a3f5a] rounded-lg transition">取消</button>
              </>
            )}
            {stage === 'confirm' && (
              <button onClick={confirmConfig} disabled={loading} className="px-6 py-1.5 text-sm btn-neon">✅ 确认生成项目</button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {fields.map(({ key, label, type }) => {
            const value = draftConfig[key];

            if (type === 'array') {
              return (
                <div key={key} className="bg-[#0a0e17] rounded-lg p-4 border border-[#1a2d4a]">
                  <label className="text-sm font-medium text-teal-400 mb-2 block">{label}</label>
                  {editMode ? (
                    <input
                      type="text"
                      className="w-full bg-[#05080f] border border-[#2a3f5a] rounded px-3 py-2 text-sm text-gray-200"
                      placeholder="逗号分隔"
                      value={Array.isArray(value) ? value.join(',') : ''}
                      onChange={(e) => updateDraftField(key, e.target.value.split(',').map(s => s.trim()).filter(Boolean))}
                    />
                  ) : (
                    <div className="text-gray-200 text-sm">{Array.isArray(value) ? value.join(', ') : <span className="text-gray-500 italic">未设置</span>}</div>
                  )}
                </div>
              );
            }

            if (type === 'object') {
              const objValue = value || {};
              return (
                <div key={key} className="bg-[#0a0e17] rounded-lg p-4 border border-[#1a2d4a]">
                  <label className="text-sm font-medium text-teal-400 mb-2 block">{label}</label>
                  <div className="space-y-1 text-sm">
                    {Object.keys(objValue).length > 0 ? (
                      Object.entries(objValue).map(([k, v]) => (
                        <div key={k} className="flex gap-2">
                          <span className="text-gray-400 w-20">{k}:</span>
                          <span className="text-gray-200">{String(v)}</span>
                        </div>
                      ))
                    ) : (
                      <span className="text-gray-500 italic">未设置</span>
                    )}
                  </div>
                </div>
              );
            }

            return (
              <div key={key} className="bg-[#0a0e17] rounded-lg p-4 border border-[#1a2d4a]">
                <label className="text-sm font-medium text-teal-400 mb-2 block">{label}</label>
                {editMode ? (
                  <input
                    type="text"
                    className="w-full bg-[#05080f] border border-[#2a3f5a] rounded px-3 py-2 text-sm text-gray-200"
                    value={value || ''}
                    onChange={(e) => updateDraftField(key, e.target.value)}
                  />
                ) : (
                  <div className="text-gray-200 text-sm">{value || <span className="text-gray-500 italic">未设置</span>}</div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  // 初始输入界面
  if (!started) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <button onClick={() => navigate('/projects/new')} className="text-gray-400 hover:text-white flex items-center gap-2 mb-4 transition">← 返回新建项目</button>
          <h1 className="text-4xl font-bold text-white tracking-tight">🤖 需求澄清对话</h1>
          <p className="text-gray-400 mt-2 text-lg">先按清单收集信息，再生成配置清单确认</p>
        </div>

        <div className="glass-card p-8">
          <label className="block text-sm font-medium text-gray-300 mb-3">📝 请用自然语言描述你的控制问题</label>
          <textarea
            className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-3 text-gray-200 placeholder-gray-500 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/30 outline-none transition resize-none"
            placeholder="例如：我想建立一个水下的 SIR 传播模型，控制疫苗接种率来最小化感染峰值..."
            rows={6}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />

          <div className="flex gap-4 mt-6">
            <button onClick={startClarify} disabled={loading || !description.trim()} className="btn-neon flex-1 disabled:opacity-50 py-3 text-lg">
              {loading ? '⏳ 启动中...' : '🚀 开始需求澄清'}
            </button>
            <button onClick={handleCancel} className="px-8 py-3 bg-[#1a2d4a] hover:bg-[#2a3f5a] text-gray-200 rounded-xl border border-[#2a3f5a] transition">取消</button>
          </div>
        </div>

        <div className="mt-6 text-center text-xs text-gray-500">
          💡 第一阶段：LLM 输出需求清单 → 你按清单提供信息 → LLM 检查缺失<br />
          💡 第二阶段：信息齐全后生成配置清单 → 你最后编辑确认 → 创建项目
        </div>
      </div>
    );
  }

  // 对话界面
  return (
    <div className="max-w-5xl mx-auto">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <button onClick={handleCancel} className="text-gray-400 hover:text-white flex items-center gap-2 mb-2 transition">← 取消并返回</button>
          <h1 className="text-2xl font-bold text-white">🤖 需求澄清对话</h1>
          <p className="text-sm text-gray-500">阶段: {stage} | 缺失: {missingItems.length + missingFields.length} 项</p>
        </div>
        <div className="text-right">
          <p className="text-xs text-gray-500">初始描述</p>
          <p className="text-sm text-gray-400 max-w-xs truncate">{description}</p>
        </div>
      </div>

      {/* LLM 消息 */}
      {message && (
        <div className="glass-card p-4 mb-4 bg-[#1a2d4a]/50">
          <p className="text-sm text-gray-200 whitespace-pre-wrap">{message}</p>
        </div>
      )}

      {/* 阶段 1: 纯对话收集（无固定清单） */}
      {(stage === 'collecting' || stage === 'init') && renderCollecting()}

      {/* 阶段 2: Draft */}
      {(stage === 'draft' || stage === 'editing' || stage === 'confirm') && renderDraftEditor()}

      {/* 加载状态 */}
      {loading && (
        <div className="text-center py-4 text-gray-400">
          <span className="animate-pulse">⏳ LLM 处理中...</span>
        </div>
      )}
    </div>
  );
};

export default ClarifyPage;
