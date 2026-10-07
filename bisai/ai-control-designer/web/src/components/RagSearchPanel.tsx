import React, { useState, useEffect } from 'react';
import { searchStrategies, deleteStrategy, listStrategies, RagSearchResult } from '@/api/client';

const RagSearchPanel: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<RagSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [mode, setMode] = useState<'browse' | 'search'>('browse');
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // 展开/收起状态
  const [expandedCode, setExpandedCode] = useState<Set<number>>(new Set());
  const [expandedParams, setExpandedParams] = useState<Set<number>>(new Set());

  const toggleCode = (idx: number) => {
    setExpandedCode(prev => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  };

  const toggleParams = (idx: number) => {
    setExpandedParams(prev => {
      const next = new Set(prev);
      next.has(idx) ? next.delete(idx) : next.add(idx);
      return next;
    });
  };

  // 🆕 加载全部策略（浏览模式）
  const loadAllStrategies = async () => {
    setInitialLoading(true);
    try {
      const res = await listStrategies(200);
      setResults(res.results || []);
      setMode('browse');
    } catch (err: any) {
      console.error('加载策略库失败', err);
      setResults([]);
    } finally {
      setInitialLoading(false);
    }
  };

  // 🆕 首次挂载 → 拉全量
  useEffect(() => {
    loadAllStrategies();
  }, []);

  // 搜索
  const handleSearch = async () => {
    if (!query.trim() || loading) return;
    setLoading(true);
    setMode('search');
    setExpandedCode(new Set());
    setExpandedParams(new Set());
    try {
      const res = await searchStrategies(query, 5);
      setResults(res.strategies || []);
    } catch (err: any) {
      const msg = typeof err?.message === 'object'
        ? JSON.stringify(err.message)
        : (err?.message || String(err));
      alert('搜索失败: ' + msg);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  // 🆕 清空搜索 → 回到浏览模式
  const handleClearSearch = () => {
    setQuery('');
    setExpandedCode(new Set());
    setExpandedParams(new Set());
    loadAllStrategies();
  };

  const handleDelete = async (id: string, idx: number) => {
    if (!confirm(`确定要从策略库删除「${id}」吗？\n此操作不可恢复！`)) return;
    setDeletingId(id);
    try {
      const res = await deleteStrategy(id);
      if (res.success) {
        setResults(prev => prev.filter((_, i) => i !== idx));
      } else {
        alert('删除失败: ' + res.message);
      }
    } catch (err: any) {
      alert('删除失败: ' + (err?.message || String(err)));
    } finally {
      setDeletingId(null);
    }
  };

  const parseParams = (params: any): Record<string, number> => {
    if (!params) return {};
    if (typeof params === 'string') {
      try { return JSON.parse(params); } catch { return {}; }
    }
    if (typeof params === 'object') return params;
    return {};
  };

  return (
    <div className="space-y-4">
      {/* 搜索框 */}
      <div className="flex gap-2">
        <input
          className="flex-1 bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-4 py-2.5 text-gray-200 placeholder-gray-500 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/30 outline-none transition font-mono"
          placeholder="输入场景描述，检索相似控制策略...（如 kp kd、pendulum、torque）"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          disabled={loading}
        />
        <button
          onClick={handleSearch}
          disabled={loading || !query.trim()}
          className="btn-neon px-6 whitespace-nowrap disabled:opacity-50"
        >
          {loading ? '⏳ 检索中...' : '🔍 检索'}
        </button>
        {/* 🆕 清空按钮 */}
        {mode === 'search' && (
          <button
            onClick={handleClearSearch}
            disabled={loading}
            className="px-4 py-2.5 bg-[#1a2d4a] hover:bg-[#2a3f5a] text-gray-300 rounded-xl border border-[#2a3f5a] transition whitespace-nowrap"
            title="清空搜索，返回全部策略"
          >
            ✕ 清空
          </button>
        )}
      </div>

      {/* 🆕 状态栏 */}
      <div className="flex items-center justify-between text-sm">
        <div className="flex items-center gap-2">
          {mode === 'browse' ? (
            <span className="text-gray-400 font-mono">
              📚 策略库全部策略
              <span className="ml-2 text-blue-400 font-bold">{results.length}</span>
              <span className="text-gray-500">条</span>
            </span>
          ) : (
            <span className="text-gray-400 font-mono">
              🔍 检索「<span className="text-blue-400">{query}</span>」
              <span className="ml-2 text-blue-400 font-bold">{results.length}</span>
              <span className="text-gray-500">条命中</span>
            </span>
          )}
        </div>
        {initialLoading && (
          <span className="text-xs text-gray-500 font-mono">加载中...</span>
        )}
      </div>

      {/* 首次加载状态 */}
      {initialLoading && (
        <div className="text-center py-8 text-blue-400 font-mono">
          <div className="inline-block w-8 h-8 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin mb-2"></div>
          <p>正在加载策略库...</p>
        </div>
      )}

      {/* 搜索加载中 */}
      {loading && (
        <div className="text-center py-8 text-blue-400 font-mono">
          <div className="inline-block w-8 h-8 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin mb-2"></div>
          <p>正在加载 embedding 模型并检索...</p>
          <p className="text-xs text-gray-500 mt-1">首次检索可能需要 5-10 秒</p>
        </div>
      )}

      {/* 空结果 */}
      {!initialLoading && !loading && results.length === 0 && (
        <div className="text-center py-12 glass-card">
          <div className="text-4xl mb-3">{mode === 'browse' ? '📭' : '🔍'}</div>
          <p className="text-gray-400">
            {mode === 'browse' ? '策略库暂无数据' : '未找到匹配的策略'}
          </p>
          <p className="text-xs text-gray-500 mt-2">
            {mode === 'browse'
              ? '在项目演化过程中点"存入 RAG"，即可积累策略'
              : '试试更具体的查询，或点"清空"返回全部策略'}
          </p>
        </div>
      )}

      {/* 结果列表 */}
      {!initialLoading && !loading && results.length > 0 && (
        <div className="space-y-3">
          {results.map((r, idx) => {
            const codeExpanded = expandedCode.has(idx);
            const paramsExpanded = expandedParams.has(idx);
            const params = parseParams(r.metadata?.params);
            const paramCount = Object.keys(params).length;
            const codePreview = codeExpanded ? r.code : r.code.slice(0, 500);
            const codeTruncated = r.code.length > 500 && !codeExpanded;
            const isDeleting = deletingId === r.id;

            return (
              <div key={idx} className="glass-card p-4 hover:border-blue-500/30 transition">
                {/* 头部信息 */}
                <div className="flex justify-between items-start mb-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    {/* 🆕 浏览模式下不显示相似度（无意义） */}
                    {mode === 'search' && typeof r.similarity === 'number' && (
                      <span className="badge-tech-blue text-xs">
                        {(r.similarity * 100).toFixed(1)}% 相似
                      </span>
                    )}
                    <span className="badge-tech-purple text-xs">
                      领域: {r.metadata?.domain || '未知'}
                    </span>
                    {r.metadata?.cost !== undefined && r.metadata?.cost !== null && (
                      <span className="badge-tech-green text-xs">
                        代价: {Number(r.metadata.cost).toFixed(4)}
                      </span>
                    )}
                    {r.metadata?.version !== undefined && (
                      <span className="badge-tech-gray text-xs">
                        v{r.metadata.version}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-500 font-mono">
                      #{idx + 1} · {r.id}
                    </span>
                    <button
                      onClick={() => handleDelete(r.id, idx)}
                      disabled={isDeleting}
                      className={`text-xs px-2 py-1 rounded border transition ${
                        isDeleting
                          ? 'opacity-50 cursor-not-allowed border-red-500/30 text-red-400'
                          : 'border-red-500/30 text-red-400 hover:bg-red-500/10 hover:border-red-500/60'
                      }`}
                      title="从策略库删除"
                    >
                      {isDeleting ? '⏳' : '🗑️'}
                    </button>
                  </div>
                </div>

                {/* 操作按钮 */}
                <div className="flex gap-2 mb-3">
                  <button
                    onClick={() => toggleCode(idx)}
                    className={`text-xs px-3 py-1 rounded-lg border transition ${
                      codeExpanded
                        ? 'bg-blue-500/20 border-blue-500/50 text-blue-300'
                        : 'bg-[#0a0e17] border-[#1a2d4a] text-gray-400 hover:border-blue-500/50 hover:text-blue-300'
                    }`}
                  >
                    {codeExpanded ? '📕 收起代码' : '📖 展开完整代码'}
                  </button>
                  <button
                    onClick={() => toggleParams(idx)}
                    disabled={paramCount === 0}
                    className={`text-xs px-3 py-1 rounded-lg border transition ${
                      paramCount === 0
                        ? 'bg-[#0a0e17] border-[#1a2d4a] text-gray-600 cursor-not-allowed'
                        : paramsExpanded
                          ? 'bg-purple-500/20 border-purple-500/50 text-purple-300'
                          : 'bg-[#0a0e17] border-[#1a2d4a] text-gray-400 hover:border-purple-500/50 hover:text-purple-300'
                    }`}
                  >
                    📊 {paramsExpanded ? '收起参数' : `查看参数 (${paramCount})`}
                  </button>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(r.code);
                      alert('✅ 代码已复制到剪贴板');
                    }}
                    className="text-xs px-3 py-1 rounded-lg border bg-[#0a0e17] border-[#1a2d4a] text-gray-400 hover:border-teal-500/50 hover:text-teal-300 transition"
                  >
                    📋 复制代码
                  </button>
                </div>

                {/* 参数面板 */}
                {paramsExpanded && paramCount > 0 && (
                  <div className="mb-3 bg-[#0a0e17] border border-purple-500/30 rounded-xl p-3">
                    <p className="text-xs text-purple-400 font-medium mb-2">
                      ⚙️ 最优参数 ({paramCount} 个)
                    </p>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      {Object.entries(params).map(([key, val]) => (
                        <div
                          key={key}
                          className="flex items-center justify-between bg-[#05080f] border border-[#1a2d4a] rounded-lg px-3 py-1.5 text-xs"
                        >
                          <span className="text-purple-300 font-mono truncate mr-2">
                            {key}
                          </span>
                          <span className="text-gray-200 font-mono shrink-0">
                            {typeof val === 'number' ? val.toFixed(4) : String(val)}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* 代码预览 */}
                <pre className={`bg-[#0a0e17] p-3 rounded-xl text-xs font-mono text-gray-300 border border-[#1a2d4a] ${
                  codeExpanded ? 'overflow-auto max-h-[600px]' : 'overflow-auto max-h-40'
                }`}>
                  {codePreview}
                  {codeTruncated && (
                    <span className="text-gray-500">
                      {'\n\n'}... (还有 {r.code.length - 500} 字符，点击上方"展开完整代码"查看)
                    </span>
                  )}
                </pre>

                {/* 诊断摘要 */}
                {r.metadata?.diagnosis_summary && (
                  <details className="mt-2">
                    <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-300">
                      📋 诊断摘要
                    </summary>
                    <p className="text-xs text-gray-400 mt-2 pl-4 border-l-2 border-[#1a2d4a]">
                      {r.metadata.diagnosis_summary}
                    </p>
                  </details>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};

export default RagSearchPanel;