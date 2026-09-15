import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useEvolutionStore } from '@/stores/evolutionStore';
import ReactECharts from 'echarts-for-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import StrategyParser from '@/components/StrategyParser';
import {
  storeStrategy,
  listStrategies,
  listProjectVersions,
  stopEvolution,
} from '@/api/client';

const EvolutionView: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const {
    status,
    versions,
    currentVersion,
    compareData,
    isPolling,
    error,
    startPolling,
    stopPolling,
    fetchVersionDetail,
    reset,
  } = useEvolutionStore();

  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [storingRag, setStoringRag] = useState(false);
  const [storedIds, setStoredIds] = useState<Set<string>>(new Set());
  const [projectVersions, setProjectVersions] = useState<any[]>([]);
  const [stopping, setStopping] = useState(false);

  useEffect(() => {
    // 过滤 "undefined" 字符串（URL 拼接失败时的产物）
    if (taskId && taskId !== 'undefined') {
      startPolling(taskId);
      return () => {
        stopPolling();
        reset();
      };
    }
  }, [taskId]);

  useEffect(() => {
    if (selectedVersion !== null && taskId) {
      fetchVersionDetail(taskId, selectedVersion);
    }
  }, [selectedVersion, taskId]);

  // 进入页面时拉一次已存策略 id 列表
  useEffect(() => {
    listStrategies(200)
      .then((res) => {
        setStoredIds(new Set((res.results || []).map((r: any) => r.id)));
      })
      .catch(() => {});
  }, []);

  // 拿到 project_id 后，加载项目的所有历史版本
  useEffect(() => {
    const pid = (status as any)?.project_id;
    if (!pid) return;
    listProjectVersions(pid)
      .then((res) => setProjectVersions(res.versions || []))
      .catch(() => {});
  }, [(status as any)?.project_id, (status as any)?.current_version, status?.status,]);

  const handleStoreToRag = async () => {
    if (!currentVersion || !taskId || storingRag) return;
    const sid = `${taskId.slice(0, 8)}_v${currentVersion.version}`;
    setStoringRag(true);
    try {
      await storeStrategy(currentVersion.code, {
        id: sid,
        domain: 'unknown',
        cost: currentVersion.total_cost,
        version: String(currentVersion.version),
        params: currentVersion.params,
        diagnosis_summary: currentVersion.diagnostic_report?.slice(0, 500) || '',
      });
      setStoredIds((prev) => new Set(prev).add(sid));
      alert('✅ 策略已存入 RAG 库');
    } catch (err: any) {
      const msg = typeof err?.message === 'object'
        ? JSON.stringify(err.message)
        : (err?.message || String(err));
      alert('存储失败: ' + msg);
    } finally {
      setStoringRag(false);
    }
  };

  // 🆕 B-8：中断演化
  const handleStop = async () => {
    if (!taskId || stopping) return;
    if (!confirm('确定要中断当前演化吗？\n\n注意：引擎会在当前轮结束后停止，可能需要 30-60 秒。')) return;
    setStopping(true);
    try {
      const res = await stopEvolution(taskId);
      alert('⏹️ 中断请求已发送\n\n' + (res.note || '引擎会在当前轮结束后停止'));
    } catch (err: any) {
      const msg = typeof err?.message === 'object'
        ? JSON.stringify(err.message)
        : (err?.message || String(err));
      alert('中断失败: ' + msg);
    } finally {
      setStopping(false);
    }
  };

  // 科技感图表配色
  const costChartOption = {
    title: {
      text: '📉 代价收敛曲线',
      left: 'center',
      textStyle: { color: '#94a3b8', fontSize: 14, fontWeight: 500 },
    },
    tooltip: { trigger: 'axis' },
    grid: {
      top: 50,
      bottom: 30,
      left: 60,
      right: 20,
    },
    xAxis: {
      type: 'category',
      data: compareData?.versions || [],
      name: '版本',
      nameTextStyle: { color: '#64748b' },
      axisLine: { lineStyle: { color: '#1a2d4a' } },
      axisLabel: { color: '#94a3b8' },
    },
    yAxis: {
      type: 'value',
      name: '总代价',
      nameTextStyle: { color: '#64748b' },
      axisLine: { lineStyle: { color: '#1a2d4a' } },
      axisLabel: { color: '#94a3b8' },
      splitLine: { lineStyle: { color: '#1a2d4a', type: 'dashed' } },
    },
    series: [{
      data: compareData?.costs || [],
      type: 'line',
      smooth: true,
      lineStyle: { color: '#3b82f6', width: 3 },
      symbol: 'circle',
      symbolSize: 8,
      itemStyle: { color: '#3b82f6' },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0,
          y: 0,
          x2: 0,
          y2: 1,
          colorStops: [
            { offset: 0, color: 'rgba(59, 130, 246, 0.4)' },
            { offset: 1, color: 'rgba(59, 130, 246, 0.05)' },
          ],
        },
      },
      markPoint: {
        data: [{
          type: 'min',
          name: '最优',
          symbol: 'circle',
          symbolSize: 60,
          label: { formatter: (p: any) => p.value.toFixed(2), color: '#34d399' },
        }],
      },
      markLine: {
        data: [{ type: 'average', name: '平均值' }],
        label: { formatter: (p: any) => `平均: ${p.value.toFixed(2)}`, color: '#64748b' },
        lineStyle: { color: '#64748b', type: 'dashed' },
      },
    }],
  };

  if (error) {
    return (
      <div className="text-center py-10 text-red-400">
        ❌ {error}
        <button
          onClick={() => navigate('/')}
          className="block mx-auto mt-4 btn-neon"
        >
          返回首页
        </button>
      </div>
    );
  }

  // ✅ 进度：用相对轮次（iteration / max_iterations）
  const totalIterations = (status as any)?.max_iterations || 3;
  const currentIter = (status as any)?.iteration || 0;
  const currentVersionNum = (status as any)?.current_version || 0;
  const isFinished =
    status?.status === 'completed' ||
    status?.status === 'done' ||
    status?.status === 'failed';
  const progress = isFinished
    ? 100
    : Math.min(100, Math.round((currentIter / totalIterations) * 100));

  // ✅ 状态分类
  const s = status?.status || '';
  const isRunning =
    s === 'running' || s === 'optimizing' || s === 'diagnosing' || s === 'modifying';
  const isCompleted = s === 'completed' || s === 'done';
  const isFailed = s === 'failed' || s === 'error';

  const isEvolving = isRunning;

  // ✅ 当前版本的 RAG 存储 ID 及是否已存
  const currentSid = taskId && currentVersion
    ? `${taskId.slice(0, 8)}_v${currentVersion.version}`
    : '';
  const alreadyStored = currentSid !== '' && storedIds.has(currentSid);

  return (
    <div className="space-y-6">
      {/* 顶部导航 */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-white text-glow">🔄 演化监控</h1>
        <div className="flex gap-3">
          <span className={`px-3 py-1.5 rounded-xl text-sm font-mono border ${
            isPolling
              ? 'text-blue-400 border-blue-500/30 bg-blue-500/10'
              : 'text-gray-500 border-gray-500/30 bg-gray-500/10'
          }`}>
            {isPolling ? '● 实时监控中' : '○ 已停止'}
          </span>
          {/* 🆕 B-8：中断按钮，只在演化进行中显示 */}
          {isEvolving && (
            <button
              onClick={handleStop}
              disabled={stopping}
              className={`text-sm px-4 py-1.5 rounded-xl border transition ${
                stopping
                  ? 'opacity-60 cursor-not-allowed border-red-500/30 text-red-400'
                  : 'border-red-500/40 text-red-400 hover:bg-red-500/10 hover:border-red-500/60'
              }`}
              title="中断当前演化（会在当前轮结束后停止）"
            >
              {stopping ? '⏳ 请求中...' : '⏹️ 中断演化'}
            </button>
          )}
          <button
            onClick={() => navigate('/')}
            className="btn-neon-outline text-sm"
          >
            返回
          </button>
        </div>
      </div>

      {/* 状态卡片 */}
      {status && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="glass-card p-4">
            <p className="text-sm text-gray-400 font-mono flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${
                isRunning
                  ? 'bg-blue-500 animate-pulse shadow-[0_0_12px_rgba(59,130,246,0.6)]'
                  : isCompleted
                    ? 'bg-green-500 shadow-[0_0_12px_rgba(34,197,94,0.4)]'
                    : isFailed
                      ? 'bg-red-500'
                      : 'bg-gray-500'
              }`}></span>
              任务状态
            </p>
            <p className={`text-lg font-semibold mt-1 ${
              isCompleted ? 'text-green-400'
                : isRunning ? 'text-blue-400'
                : isFailed ? 'text-red-400'
                : 'text-gray-400'
            }`}>
              {isCompleted ? '✅ 已完成'
                : isRunning ? '⏳ 运行中'
                : isFailed ? '❌ 失败'
                : '⏸️ 待启动'}
            </p>
          </div>
          <div className="glass-card p-4">
            <p className="text-sm text-gray-400 font-mono">当前版本</p>
            <p className="text-lg font-semibold mt-1 text-white">
              v{currentVersionNum}
            </p>
          </div>
          <div className="glass-card p-4 border-purple-500/30">
            <p className="text-sm text-gray-400 font-mono">最佳代价</p>
            <p className="text-lg font-semibold mt-1 text-purple-400">
              {status.best_cost?.toFixed(4) || '--'}
            </p>
          </div>
          <div className="glass-card p-4">
            <p className="text-sm text-gray-400 font-mono">演化进度</p>
            <div className="flex items-center gap-3 mt-1">
              <div className="flex-1 bg-[#1a2d4a] rounded-full h-2 overflow-hidden">
                <div
                  className="h-2 rounded-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="text-sm font-bold text-blue-400 font-mono min-w-[40px]">
                {progress}%
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 演化进行中提示 */}
      {isEvolving && (
        <div className="glass-card p-4 border-blue-500/30">
          <div className="flex items-center gap-4">
            <div className="relative w-10 h-10 shrink-0">
              <div className="absolute inset-0 border-2 border-blue-500/20 rounded-full"></div>
              <div className="absolute inset-0 border-2 border-transparent border-t-blue-500 rounded-full animate-spin"></div>
            </div>

            <div className="flex-1">
              <p className="text-white font-medium">
                {s === 'optimizing' && '🔍 正在优化控制参数...'}
                {s === 'diagnosing' && '🩺 LLM 正在生成诊断报告...'}
                {s === 'modifying' && '🤖 LLM 正在修改控制律代码...'}
                {s === 'running' && '⚙️ 演化初始化中...'}
              </p>
              <p className="text-sm text-gray-400 mt-1 font-mono">
                {status?.message || `迭代 ${currentIter} / ${totalIterations}（V${currentVersionNum}）`}
              </p>
              <p className="text-xs text-gray-500 mt-1">
                演化过程中每次迭代可能需要 30-60 秒，请耐心等待
              </p>
            </div>
          </div>
        </div>
      )}

      {/* 图表 */}
      <div className="glass-card p-4">
        <ReactECharts option={costChartOption} style={{ height: 280 }} />
      </div>

      {/* 版本详情 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-4">
          <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
            <span className="w-1 h-5 bg-gradient-to-b from-blue-500 to-cyan-500 rounded-full"></span>
            📌 版本列表
          </h3>
          <select
            className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-3 py-2 text-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none mb-4 font-mono"
            value={selectedVersion || ''}
            onChange={(e) => setSelectedVersion(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">选择版本</option>
            {projectVersions.map((v: any) => (
              <option key={v.version} value={v.version}>
                版本 {v.version} - 代价 {v.cost !== null && v.cost !== undefined ? Number(v.cost).toFixed(4) : '--'}
              </option>
            ))}
          </select>

          {currentVersion && (
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400 font-mono">参数</span>
                <button
                  onClick={handleStoreToRag}
                  disabled={storingRag || alreadyStored}
                  className={`text-xs badge-tech-purple transition ${
                    alreadyStored
                      ? 'opacity-70 cursor-not-allowed'
                      : storingRag
                        ? 'opacity-60 cursor-not-allowed'
                        : 'hover:bg-purple-500/30'
                  }`}
                  title={alreadyStored ? '此版本已存入 RAG 库' : '存入当前版本到 RAG 库'}
                >
                  {alreadyStored ? (
                    <>✅ 已存入 RAG</>
                  ) : storingRag ? (
                    <>
                      <span className="inline-block animate-spin mr-1">⏳</span>
                      存入中...
                    </>
                  ) : (
                    <>💾 存入 RAG</>
                  )}
                </button>
              </div>
              <pre className="bg-[#0a0e17] p-3 rounded-xl text-xs font-mono text-gray-300 overflow-auto max-h-32 border border-[#1a2d4a]">
                {JSON.stringify(currentVersion.params, null, 2)}
              </pre>
              <div className="text-sm font-mono">
                <div className="flex flex-wrap gap-2">
                  {Object.entries(currentVersion.deviations || {}).map(([key, val]) => (
                    <span key={key} className={`text-xs px-2 py-0.5 rounded ${
                      Math.abs(val as number) < 0.1
                        ? 'text-green-400 bg-green-500/10 border border-green-500/20'
                        : 'text-yellow-400 bg-yellow-500/10 border border-yellow-500/20'
                    }`}>
                      {key}: {(val as number).toFixed(3)}
                    </span>
                  ))}
                </div>
                {currentVersion.anomalies?.length > 0 && (
                  <div className="mt-2 text-red-400 text-xs">
                    ⚠️ {currentVersion.anomalies.join('; ')}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="glass-card p-4">
          <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
            <span className="w-1 h-5 bg-gradient-to-b from-purple-500 to-pink-500 rounded-full"></span>
            🩺 诊断报告
          </h3>
          {currentVersion ? (
            <div className="bg-[#0a0e17] p-4 rounded-xl border border-[#1a2d4a] overflow-auto max-h-80 prose prose-invert prose-sm max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {currentVersion.diagnostic_report || '暂无诊断报告'}
              </ReactMarkdown>
            </div>
          ) : (
            <div className="text-center py-10 text-gray-500 font-mono">
              <p className="text-4xl mb-2">📋</p>
              <p>请选择一个版本</p>
            </div>
          )}
        </div>
      </div>

      {/* 策略解析 */}
      {currentVersion && (
        <div className="glass-card p-4">
          <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
            <span className="w-1 h-5 bg-gradient-to-b from-cyan-500 to-blue-500 rounded-full"></span>
            🧠 策略解析
          </h3>
          <StrategyParser code={currentVersion.code} params={currentVersion.params} version={currentVersion.version} />
        </div>
      )}

      {/* 底部状态 */}
      <div className="glass-card p-3 text-sm text-gray-400 font-mono flex justify-between">
        <span>⏳ 演化状态: {status?.status || '等待中'}</span>
        <span>📦 版本数: {projectVersions.length}</span>
        <span className={isPolling ? 'text-blue-400' : 'text-gray-500'}>
          {isPolling ? '● 实时' : '○ 已停止'}
        </span>
      </div>
    </div>
  );
};

export default EvolutionView;