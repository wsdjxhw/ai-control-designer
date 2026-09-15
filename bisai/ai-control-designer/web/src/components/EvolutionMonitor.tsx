import React from 'react';
import { useEvolutionStore } from '@/stores/evolutionStore';
import ProgressBar from './ProgressBar';
import CostCurveChart from './CostCurveChart';
import DiagnosisReport from './DiagnosisReport';

interface EvolutionMonitorProps {
  taskId: string;
  className?: string;
}

const EvolutionMonitor: React.FC<EvolutionMonitorProps> = ({ taskId, className = '' }) => {
  const {
    status,
    versions,
    currentVersion,
    compareData,
    isPolling,
    error,
  } = useEvolutionStore();

  if (error) {
    return (
      <div className="text-center py-10 text-red-400">
        ❌ {error}
      </div>
    );
  }

  return (
    <div className={`space-y-6 ${className}`}>
      {/* 状态卡片 */}
      {status && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="glass-card p-4">
            <p className="text-sm text-gray-400 font-mono flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${
                status.status === 'running' ? 'bg-blue-500 animate-pulse shadow-[0_0_12px_rgba(59,130,246,0.6)]' :
                status.status === 'completed' ? 'bg-green-500 shadow-[0_0_12px_rgba(34,197,94,0.4)]' :
                status.status === 'failed' ? 'bg-red-500' : 'bg-gray-500'
              }`}></span>
              任务状态
            </p>
            <p className={`text-lg font-semibold mt-1 ${
              status.status === 'completed' ? 'text-green-400' :
              status.status === 'running' ? 'text-blue-400' :
              status.status === 'failed' ? 'text-red-400' :
              'text-gray-400'
            }`}>
              {status.status === 'running' ? '⏳ 运行中' :
               status.status === 'completed' ? '✅ 已完成' :
               status.status === 'failed' ? '❌ 失败' : '⏸️ 待启动'}
            </p>
          </div>
          <div className="glass-card p-4">
            <p className="text-sm text-gray-400 font-mono">当前版本</p>
            <p className="text-lg font-semibold mt-1 text-white">
              v{status.current_version}
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
                  style={{ width: `${status.progress || 0}%` }}
                />
              </div>
              <span className="text-sm font-bold text-blue-400 font-mono min-w-[40px]">
                {status.progress || 0}%
              </span>
            </div>
          </div>
        </div>
      )}

      {/* 图表 */}
      {compareData && compareData.versions.length > 0 && (
        <div className="glass-card p-4">
          <CostCurveChart
            versions={compareData.versions}
            costs={compareData.costs}
            height={280}
          />
        </div>
      )}

      {/* 版本信息和诊断报告 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-4">
          <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
            <span className="w-1 h-5 bg-gradient-to-b from-blue-500 to-cyan-500 rounded-full"></span>
            📌 版本列表
          </h3>
          <select
            className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-xl px-3 py-2 text-gray-300 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none mb-4 font-mono"
            value={currentVersion?.version || ''}
            onChange={(e) => {
              const version = Number(e.target.value);
              if (version) {
                // 触发版本切换
              }
            }}
          >
            <option value="">选择版本</option>
            {versions.map((v) => (
              <option key={v.version} value={v.version}>
                版本 {v.version} - 代价 {v.total_cost?.toFixed(4) || '--'}
              </option>
            ))}
          </select>

          {currentVersion && (
            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-400 font-mono">参数</span>
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
          <DiagnosisReport
            content={currentVersion?.diagnostic_report || ''}
            title="🩺 诊断报告"
          />
        </div>
      </div>

      {/* 状态指示 */}
      <div className="glass-card p-3 text-sm text-gray-400 font-mono flex justify-between">
        <span>⏳ 演化状态: {status?.status || '等待中'}</span>
        <span>📦 版本数: {versions.length}</span>
        <span className={isPolling ? 'text-blue-400' : 'text-gray-500'}>
          {isPolling ? '● 实时监控中' : '○ 已停止'}
        </span>
      </div>
    </div>
  );
};

export default EvolutionMonitor;
