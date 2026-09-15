import React, { useState } from 'react';

interface ClarifyDialogProps {
  onComplete: (data: {
    scene_config: any;
    model_code: string;
    cost_function: any;
  }) => void;
  onCancel: () => void;
}

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface ClarifyResponse {
  session_id: string;
  stage: string;
  message: string;
  collected: Record<string, any>;
  ready_to_create: boolean;
  scene_config?: any;
  model_code?: string;
  cost_function?: any;
}

const ClarifyDialog: React.FC<ClarifyDialogProps> = ({ onComplete, onCancel }) => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [collected, setCollected] = useState<Record<string, any>>({});
  const [stage, setStage] = useState<string>('init');

  // 启动澄清会话
  const startClarify = async (description: string) => {
    if (!description.trim()) return;

    setLoading(true);
    try {
      const resp = await fetch('/api/v1/clarify/start', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description }),
      });

      if (!resp.ok) {
        throw new Error(await resp.text());
      }

      const data: ClarifyResponse = await resp.json();

      setSessionId(data.session_id);
      setMessages([{ role: 'assistant', content: data.message }]);
      setCollected(data.collected);
      setStage(data.stage);
    } catch (err: any) {
      alert('启动澄清失败: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // 发送用户消息
  const sendMessage = async () => {
    if (!input.trim() || !sessionId || loading) return;

    const userMsg = input.trim();
    setMessages(prev => [...prev, { role: 'user', content: userMsg }]);
    setInput('');
    setLoading(true);

    try {
      const resp = await fetch('/api/v1/clarify/turn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: userMsg,
        }),
      });

      if (!resp.ok) {
        throw new Error(await resp.text());
      }

      const data: ClarifyResponse = await resp.json();

      setMessages(prev => [...prev, { role: 'assistant', content: data.message }]);
      setCollected(data.collected);
      setStage(data.stage);

      // 如果已准备好创建项目
      if (data.ready_to_create && data.scene_config && data.model_code) {
        setTimeout(() => {
          onComplete({
            scene_config: data.scene_config,
            model_code: data.model_code!,
            cost_function: data.cost_function,
          });
        }, 1500); // 延迟 1.5 秒让用户看到最终消息
      }
    } catch (err: any) {
      alert('发送失败: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  // 取消会话
  const handleCancel = async () => {
    if (sessionId) {
      try {
        await fetch('/api/v1/clarify/cancel', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId }),
        });
      } catch (e) {
        // 忽略取消错误
      }
    }
    onCancel();
  };

  // 如果还未启动，显示初始输入
  if (!sessionId) {
    return (
      <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
        <div className="glass-card w-full max-w-2xl p-6">
          <h2 className="text-xl font-bold text-white mb-4">🤖 新手模式 - 需求澄清</h2>
          <p className="text-gray-400 mb-4">
            请用自然语言描述你的控制问题，AI 将通过多轮对话帮你明确状态、动作、代价函数等关键信息。
          </p>
          <textarea
            className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-3 text-gray-200 placeholder-gray-500 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/30 outline-none transition resize-none"
            placeholder="例如：我想建立一个水下的 SIR 传播模型，控制疫苗接种率来最小化感染峰值..."
            rows={4}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                startClarify(e.currentTarget.value);
              }
            }}
            id="initial-desc"
          />
          <div className="flex gap-3 mt-4">
            <button
              onClick={() => {
                const textarea = document.getElementById('initial-desc') as HTMLTextAreaElement;
                startClarify(textarea.value);
              }}
              disabled={loading}
              className="btn-neon flex-1 disabled:opacity-50"
            >
              {loading ? '⏳ 启动中...' : '🚀 开始澄清对话'}
            </button>
            <button
              onClick={onCancel}
              className="px-6 py-2.5 bg-[#1a2d4a] hover:bg-[#2a3f5a] text-gray-200 rounded-xl border border-[#2a3f5a] transition"
            >
              取消
            </button>
          </div>
        </div>
      </div>
    );
  }

  // 对话界面
  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center z-50">
      <div className="glass-card w-full max-w-3xl h-[600px] flex flex-col">
        {/* 头部 */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#1a2d4a]">
          <div>
            <h2 className="text-lg font-bold text-white">🤖 需求澄清对话</h2>
            <p className="text-xs text-gray-500">阶段: {stage} | 已收集: {Object.keys(collected).length} 项</p>
          </div>
          <button
            onClick={handleCancel}
            className="text-gray-400 hover:text-red-400 transition"
          >
            ✕ 取消
          </button>
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-[#05080f]">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[80%] px-4 py-3 rounded-2xl ${
                  msg.role === 'user'
                    ? 'bg-teal-600 text-white rounded-br-none'
                    : 'bg-[#1a2d4a] text-gray-200 rounded-bl-none'
                }`}
              >
                <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-[#1a2d4a] text-gray-400 px-4 py-3 rounded-2xl rounded-bl-none">
                <span className="animate-pulse">⏳ AI 思考中...</span>
              </div>
            </div>
          )}
        </div>

        {/* 已收集信息摘要 */}
        {Object.keys(collected).length > 0 && (
          <div className="px-6 py-3 bg-[#0a0e17] border-t border-[#1a2d4a]">
            <p className="text-xs text-gray-500 mb-2">📋 已确认信息:</p>
            <div className="flex flex-wrap gap-2">
              {Object.entries(collected).map(([key, value]) => (
                <span
                  key={key}
                  className="text-xs px-2 py-1 bg-[#1a2d4a] text-teal-400 rounded-lg"
                >
                  {key}: {Array.isArray(value) ? value.join(', ') : String(value).slice(0, 30)}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 输入框 */}
        <div className="p-4 border-t border-[#1a2d4a] flex gap-3">
          <input
            type="text"
            className="flex-1 bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 placeholder-gray-500 focus:border-teal-500 focus:ring-2 focus:ring-teal-500/30 outline-none transition"
            placeholder="输入你的回复..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
              }
            }}
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="btn-neon px-6 disabled:opacity-50"
          >
            发送
          </button>
        </div>
      </div>
    </div>
  );
};

export default ClarifyDialog;
