import React, { useState, useEffect } from 'react';
import { parseStrategy } from '@/api/client';

interface StrategyParserProps {
  code: string;
  params: Record<string, number>;
  version?: number;      // 🆕 当前版本号，用于显示
}

const StrategyParser: React.FC<StrategyParserProps> = ({ code, params, version }) => {
  const [explanation, setExplanation] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // 🆕 版本切换时清空旧结果，避免看到过期内容
  useEffect(() => {
    setExplanation(null);
  }, [version]);

  const handleParse = async () => {
    setLoading(true);
    try {
      const result = await parseStrategy(code, params);

      // 后端返回：{ description, key_mechanisms[], parameter_effects{} }
      let text = result.description || '';

      if (result.key_mechanisms && result.key_mechanisms.length > 0) {
        text += '\n\n【关键机制】\n';
        result.key_mechanisms.forEach((m, i) => {
          text += `${i + 1}. ${m}\n`;
        });
      }

      if (
        result.parameter_effects &&
        Object.keys(result.parameter_effects).length > 0
      ) {
        text += '\n【参数作用】\n';
        Object.entries(result.parameter_effects).forEach(([k, v]) => {
          text += `  ${k}: ${v}\n`;
        });
      }

      setExplanation(text || '（LLM 未返回有效解析结果）');
    } catch (err: any) {
      alert('解析失败: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3">
      {/* 顶部：按钮 + 当前版本提示 */}
      <div className="flex items-center gap-3 flex-wrap">
        <button
          onClick={handleParse}
          disabled={loading}
          className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 text-white px-4 py-2 rounded-lg transition"
        >
          {loading ? '⏳ 解析中...' : '🧠 解析控制策略'}
        </button>

        {version !== undefined && (
          <span className="text-sm text-gray-400 font-mono">
            正在解析: <span className="text-purple-400 font-bold">v{version}</span>
          </span>
        )}
      </div>

      {/* 🆕 解析结果 - 深色主题，浅色文字 */}
      {explanation && (
        <div className="p-4 bg-[#0a0e17] border border-[#1a2d4a] rounded-xl text-sm text-gray-200 leading-relaxed whitespace-pre-wrap">
          {explanation}
        </div>
      )}
    </div>
  );
};

export default StrategyParser;