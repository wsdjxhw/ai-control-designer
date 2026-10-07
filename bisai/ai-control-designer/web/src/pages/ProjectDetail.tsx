import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProjectStore } from '@/stores/projectStore';
import {
  startEvolution,
  listProjectVersions,
  ProjectVersion,
  getProjectVersionDetail,
  ProjectVersionDetail,
  getActiveRun,
  getLatestRun,
  reevaluateBaseline,
} from '@/api/client';

const ProjectDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentProject, fetchProject, loading, error, deleteProject } = useProjectStore();

  const [evolving, setEvolving] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [maxIterations, setMaxIterations] = useState(3);
  const [versions, setVersions] = useState<ProjectVersion[]>([]);
  const [versionsLoading, setVersionsLoading] = useState(false);

  // 🆕 版本详情弹窗 state
  const [viewingVersion, setViewingVersion] = useState<number | null>(null);
  const [versionDetail, setVersionDetail] = useState<ProjectVersionDetail | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);

  // 🆕 当前正在运行的演化 run_id（用于"进入实时监控"按钮）
  const [activeRunId, setActiveRunId] = useState<string | null>(null);

  // 🆕 最近一次演化 run_id（用于"查看演化记录"按钮）
  const [latestRunId, setLatestRunId] = useState<string | null>(null);

  // 🆕 基线参数编辑 state
  const [editingBaseline, setEditingBaseline] = useState(false);
  const [baselineParams, setBaselineParams] = useState<Record<string, number>>({});
  const [reevaluating, setReevaluating] = useState(false);

  // 🆕 查看版本详情
  const handleViewVersion = async (version: number) => {
    if (!id) return;
    setViewingVersion(version);
    setVersionDetail(null);
    setLoadingDetail(true);
    try {
      const detail = await getProjectVersionDetail(id, version);
      setVersionDetail(detail);
    } catch (err: any) {
      alert('加载版本详情失败: ' + err.message);
      setViewingVersion(null);
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    if (id) {
      fetchProject(id);
      loadVersions();
    }
  }, [id]);

  // 🆕 每 3 秒查询一次是否有正在跑的演化
  useEffect(() => {
    if (!id) return;

    const checkActive = () => {
      getActiveRun(id)
        .then((res) => setActiveRunId(res.run_id))
        .catch(() => setActiveRunId(null));
    };

    checkActive();
    const timer = setInterval(checkActive, 3000);
    return () => clearInterval(timer);
  }, [id]);

  // 🆕 加载最近一次演化 run_id（不管是否在运行）
  useEffect(() => {
    if (!id) return;
    getLatestRun(id)
      .then((res) => setLatestRunId(res.has_run ? res.run_id : null))
      .catch(() => setLatestRunId(null));
  }, [id, currentProject?.status, currentProject?.current_version]);

  const loadVersions = async () => {
    if (!id) return;
    setVersionsLoading(true);
    try {
      const res = await listProjectVersions(id);
      setVersions(res.versions || []);
    } catch (err) {
      console.warn('[ProjectDetail] 加载版本列表失败', err);
    } finally {
      setVersionsLoading(false);
    }
  };

  const handleStartEvolution = async () => {
    if (!id) return;
    setEvolving(true);
    try {
      const { run_id } = await startEvolution(id, maxIterations);
      navigate(`/evolution/${run_id}`);
    } catch (err: any) {
      alert('启动演化失败: ' + err.message);
      setEvolving(false);
    }
  };

  const handleDelete = async () => {
    if (!currentProject) return;
    if (!confirm(`确定要删除项目「${currentProject.name}」吗？此操作不可恢复！`)) return;
    setDeleting(true);
    try {
      await deleteProject(currentProject.project_id);
      navigate('/');
    } catch (err: any) {
      alert('删除失败: ' + err.message);
      setDeleting(false);
    }
  };

  const handleContinueFromVersion = async (version: number) => {
    if (!confirm(
      `确定要从 v${version} 继续迭代吗？\n\n` +
      `注意：这会在该版本基础上生成新代码，可能覆盖后续版本的 control_v*.py 文件。`
    )) return;

    if (!id) return;
    setEvolving(true);
    try {
      const { run_id } = await startEvolution(id, maxIterations, version);
      navigate(`/evolution/${run_id}`);
    } catch (err: any) {
      alert('启动演化失败: ' + err.message);
      setEvolving(false);
    }
  };

  // 🆕 重新评估基线
  const handleReevaluateBaseline = async () => {
    if (!id) return;
    setReevaluating(true);
    try {
      const res = await reevaluateBaseline(id, baselineParams);
      // 刷新项目数据
      await fetchProject(id);
      setEditingBaseline(false);
      alert(`✅ 基线已重新评估：cost = ${res.baseline.cost.toFixed(2)}`);
    } catch (err: any) {
      alert('重新评估失败: ' + err.message);
    } finally {
      setReevaluating(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-12 h-12 border-2 border-blue-500 border-t-transparent rounded-full animate-spin shadow-[0_0_30px_rgba(59,130,246,0.3)]"></div>
      </div>
    );
  }
  if (error) return <div className="text-red-400">❌ {error}</div>;
  if (!currentProject) return <div className="text-center py-10 text-gray-400">项目不存在</div>;

  const latestVersion = versions.length > 0 ? Math.max(...versions.map(v => v.version)) : 0;
  const baseline = currentProject.scene_config?.baseline;

  return (
    <div className="space-y-6">
      {/* 顶部项目信息 */}
      <div className="glass-card p-6">
        <div className="flex justify-between items-start mb-4">
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-bold text-white text-glow truncate">{currentProject.name}</h1>
            <p className="text-gray-400 mt-1">{currentProject.description || '暂无描述'}</p>
            <div className="flex gap-2 mt-3 text-sm flex-wrap">
              <span className="badge-tech-blue">
                模式: {currentProject.mode}
              </span>
              <span className={`badge-tech ${
                currentProject.status === 'completed' ? 'badge-tech-green' :
                currentProject.status === 'running' ? 'badge-tech-blue' :
                currentProject.status === 'failed' ? 'bg-red-500/20 text-red-300 border-red-500/30' :
                'badge-tech-gray'
              }`}>
                状态: {currentProject.status === 'running' ? '⏳ 运行中' :
                       currentProject.status === 'completed' ? '✅ 已完成' :
                       currentProject.status === 'failed' ? '❌ 失败' :
                       '⏸️ 待启动'}
              </span>
              <span className="badge-tech-purple">最新版本 v{latestVersion || currentProject.current_version}</span>
              {typeof currentProject.best_cost === 'number' && (
                <span className="badge-tech bg-yellow-500/20 text-yellow-300 border-yellow-500/30">
                  最佳代价: {currentProject.best_cost.toFixed(4)}
                </span>
              )}
            </div>
          </div>
          <div className="flex gap-2 shrink-0 ml-4">
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="btn-neon-outline border-red-500/30 text-red-400 hover:border-red-400 hover:bg-red-500/10"
            >
              {deleting ? '删除中...' : '🗑️ 删除'}
            </button>
          </div>
        </div>

        {/* 启动演化控制区 */}
        <div className="pt-4 border-t border-[#1a2d4a]">
          <div className="flex items-end gap-3 flex-wrap">
            <div>
              <label className="block text-xs text-gray-400 mb-1 font-mono">
                本次迭代轮数
              </label>
              <input
                type="number"
                min={1}
                max={50}
                value={maxIterations}
                onChange={(e) => {
                  const v = parseInt(e.target.value);
                  setMaxIterations(isNaN(v) ? 1 : Math.max(1, Math.min(50, v)));
                }}
                className="w-24 px-3 py-2 bg-[#0a0e17] border border-[#1a2d4a] rounded-xl text-white text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none"
              />
            </div>
            <button
              onClick={handleStartEvolution}
              disabled={evolving || currentProject.status === 'running'}
              className="btn-neon disabled:opacity-60 disabled:cursor-not-allowed"
              title={latestVersion > 0 ? `将从 v${latestVersion} 继续迭代 ${maxIterations} 轮` : `将从初始版本开始迭代 ${maxIterations} 轮`}
            >
              {evolving ? '⏳ 启动中...' : `▶️ 从最新版 v${latestVersion || 1} 继续`}
            </button>

            {/* 🆕 进入实时监控按钮（仅运行中显示） */}
            {activeRunId && (
              <button
                onClick={() => navigate(`/evolution/${activeRunId}`)}
                className="px-6 py-2.5 rounded-2xl font-semibold text-white bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-400 hover:to-teal-400 transition-all shadow-[0_0_30px_rgba(16,185,129,0.4)]"
                title="进入演化监控页，实时查看进度"
              >
                📊 进入实时监控
              </button>
            )}

            {/* 🆕 查看演化记录按钮（非运行中且已有历史 run 时显示） */}
            {!activeRunId && latestRunId && (
              <button
                onClick={() => navigate(`/evolution/${latestRunId}`)}
                className="px-6 py-2.5 rounded-2xl font-semibold text-blue-400 bg-[#0a0e17] border border-blue-500/50 hover:bg-blue-500/10 hover:border-blue-400 transition-all"
                title="查看历史演化记录（曲线、诊断、版本详情）"
              >
                📊 查看演化记录
              </button>
            )}

            {currentProject.status === 'running' && (
              <span className="text-sm text-blue-400 font-mono animate-pulse">
                ● 演化进行中
              </span>
            )}
          </div>
          <p className="text-xs text-gray-500 mt-2">
            💡 不选版本则从**最新版**继续；如需从某个历史版本分支，点下方版本列表里的「从此版继续」
          </p>
        </div>
      </div>

      {/* 历史版本列表 */}
      <div className="glass-card p-4">
        <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
          <span className="w-1 h-5 bg-gradient-to-b from-purple-500 to-pink-500 rounded-full"></span>
          📌 历史版本 ({versions.length})
          {versionsLoading && <span className="text-xs text-gray-500">加载中...</span>}
        </h3>
        {versions.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-6">暂无历史版本（还没启动过演化）</p>
        ) : (
          <div className="space-y-2">
            {versions.map((v) => (
              <div
                key={v.version}
                className="flex items-center gap-3 p-3 bg-[#0a0e17] border border-[#1a2d4a] rounded-xl hover:border-blue-500/40 transition"
              >
                <div className="w-12 h-12 shrink-0 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/30 flex items-center justify-center">
                  <span className="text-sm font-bold text-white font-mono">v{v.version}</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 text-sm flex-wrap">
                    <span className="text-white font-medium">版本 {v.version}</span>
                    {v.version === latestVersion && (
                      <span className="badge-tech-green text-xs">最新</span>
                    )}
                    {typeof v.cost === 'number' && (
                      <span className="badge-tech-purple text-xs">
                        🎯 代价 {v.cost.toFixed(4)}
                      </span>
                    )}
                    {v.has_params && (
                      <span className="text-xs text-gray-500">📊 有参数</span>
                    )}
                    {v.has_diagnosis && (
                      <span className="text-xs text-gray-500">🩺 有诊断</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-1 font-mono">
                    data/projects/{id?.slice(0, 8)}.../control_v{v.version}.py
                  </p>
                </div>
                <div className="flex gap-2 shrink-0">
                  <button
                    onClick={() => handleViewVersion(v.version)}
                    className="text-xs px-3 py-1 rounded-lg border bg-[#0a0e17] border-[#1a2d4a] text-gray-400 hover:border-teal-500/50 hover:text-teal-300 transition"
                    title="查看此版本详情"
                  >
                    查看
                  </button>
                  <button
                    onClick={() => handleContinueFromVersion(v.version)}
                    disabled={evolving || currentProject.status === 'running'}
                    className="text-xs px-3 py-1 rounded-lg border bg-[#0a0e17] border-[#1a2d4a] text-gray-400 hover:border-blue-500/50 hover:text-blue-300 disabled:opacity-40 disabled:cursor-not-allowed transition"
                    title={`从 v${v.version} 继续迭代（注意：可能覆盖后续版本）`}
                  >
                    从此版继续
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 🆕 基线对比（AI 设计器 vs PID/经典方法） */}
      {baseline && typeof baseline.cost === 'number' && (
        <div className="glass-card p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-white flex items-center gap-2">
              <span className="w-1 h-5 bg-gradient-to-b from-orange-500 to-red-500 rounded-full"></span>
              📊 AI 设计器 vs 基线对比
            </h3>
            <div className="flex gap-2">
              {!editingBaseline && (
                <button
                  onClick={() => {
                    setBaselineParams(baseline.params || { kp: 5.0, ki: 2.0, kd: 0.5 });
                    setEditingBaseline(true);
                  }}
                  className="text-xs px-3 py-1.5 bg-orange-600/20 border border-orange-500/50 text-orange-400 rounded-lg hover:bg-orange-600/40 transition"
                >
                  ⚙️ 调整参数
                </button>
              )}
              {editingBaseline && (
                <>
                  <button
                    onClick={handleReevaluateBaseline}
                    disabled={reevaluating}
                    className="text-xs px-3 py-1.5 bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white rounded-lg transition"
                  >
                    {reevaluating ? '⏳ 评估中...' : '✓ 重新评估'}
                  </button>
                  <button
                    onClick={() => setEditingBaseline(false)}
                    disabled={reevaluating}
                    className="text-xs px-3 py-1.5 bg-[#1a2d4a] hover:bg-[#2a3f5a] text-gray-300 rounded-lg transition"
                  >
                    取消
                  </button>
                </>
              )}
            </div>
          </div>

          {/* 参数编辑区（编辑模式下显示） */}
          {editingBaseline && (
            <div className="mb-4 p-4 bg-[#0a0e17] border border-orange-500/30 rounded-xl">
              <div className="text-xs text-orange-400 mb-3 font-mono">PID 参数调整</div>
              <div className="grid grid-cols-3 gap-3">
                {['kp', 'ki', 'kd'].map((key) => (
                  <div key={key}>
                    <label className="block text-xs text-gray-500 mb-1 font-mono">{key.toUpperCase()}</label>
                    <input
                      type="number"
                      step="0.1"
                      value={baselineParams[key] ?? 0}
                      onChange={(e) => {
                        const v = parseFloat(e.target.value);
                        setBaselineParams((prev) => ({ ...prev, [key]: isNaN(v) ? 0 : v }));
                      }}
                      className="w-full px-3 py-2 bg-[#111827] border border-[#2a3d5a] rounded text-white text-sm focus:border-orange-500 focus:outline-none font-mono"
                    />
                  </div>
                ))}
              </div>
              <p className="text-xs text-gray-500 mt-3">
                💡 修改后点"重新评估"，系统会用新参数跑一次仿真，更新基线代价。
              </p>
            </div>
          )}

          <div className="grid grid-cols-3 gap-4">
            {/* AI 设计器 */}
            <div className="bg-[#0a0e17] border border-purple-500/30 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">🤖</span>
                <span className="text-sm text-purple-400 font-mono">AI 设计器</span>
              </div>
              <div className="text-2xl font-bold text-purple-300 font-mono">
                {typeof currentProject.best_cost === 'number'
                  ? currentProject.best_cost.toFixed(2)
                  : '--'}
              </div>
              <div className="text-xs text-gray-500 mt-1">
                演化 {currentProject.current_version} 轮
              </div>
            </div>

            {/* 基线 */}
            <div className="bg-[#0a0e17] border border-orange-500/30 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">📐</span>
                <span className="text-sm text-orange-400 font-mono">
                  {baseline.type === 'pid' ? 'PID 基线' : '基线'}
                </span>
              </div>
              <div className="text-2xl font-bold text-orange-300 font-mono">
                {baseline.cost.toFixed(2)}
              </div>
              <div className="text-xs text-gray-500 mt-1 font-mono">
                {baseline.params
                  ? `kp=${baseline.params.kp ?? '-'} ki=${baseline.params.ki ?? '-'} kd=${baseline.params.kd ?? '-'}`
                  : '经典方法'}
              </div>
            </div>

            {/* 改进 */}
            <div className="bg-[#0a0e17] border border-green-500/30 rounded-xl p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-lg">📈</span>
                <span className="text-sm text-green-400 font-mono">改进</span>
              </div>
              {typeof currentProject.best_cost === 'number' && baseline.cost > 0 ? (
                <>
                  <div className="text-2xl font-bold text-green-300 font-mono">
                    {((1 - currentProject.best_cost / baseline.cost) * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {currentProject.best_cost < baseline.cost ? '代价降低' : '代价增加'}
                  </div>
                </>
              ) : (
                <div className="text-2xl font-bold text-gray-600 font-mono">--</div>
              )}
            </div>
          </div>

          <p className="text-xs text-gray-500 mt-3">
            💡 基线使用系统自动生成的经典控制律，AI 设计器通过演化优化达到更低的代价。
          </p>
        </div>
      )}

      {/* 场景配置 + 统计信息 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass-card p-4">
          <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
            <span className="w-1 h-5 bg-gradient-to-b from-blue-500 to-purple-500 rounded-full"></span>
            ⚙️ 场景配置
          </h3>
          <pre className="bg-[#0a0e17]/60 p-3 rounded-xl text-xs font-mono text-gray-300 overflow-auto max-h-60 border border-[#1a2d4a]">
            {JSON.stringify(currentProject.scene_config, null, 2)}
          </pre>
        </div>
        <div className="glass-card p-4">
          <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
            <span className="w-1 h-5 bg-gradient-to-b from-purple-500 to-pink-500 rounded-full"></span>
            📊 统计信息
          </h3>
          <div className="space-y-2 text-sm font-mono">
            <div className="flex justify-between py-1.5 border-b border-[#1a2d4a]">
              <span className="text-gray-400">创建时间</span>
              <span className="text-gray-300">{new Date(currentProject.created_at).toLocaleString()}</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-[#1a2d4a]">
              <span className="text-gray-400">更新时间</span>
              <span className="text-gray-300">{new Date(currentProject.updated_at).toLocaleString()}</span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-gray-400">工作目录</span>
              <span className="text-blue-400 truncate ml-2">{currentProject.work_dir || '默认'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 🆕 版本详情弹窗 */}
      {viewingVersion !== null && (
        <div
          className="fixed inset-0 bg-black/70 flex items-center justify-center z-50 p-4"
          onClick={() => setViewingVersion(null)}
        >
          <div
            className="glass-card w-full max-w-4xl max-h-[90vh] flex flex-col"
            onClick={(e) => e.stopPropagation()}
          >
            {/* 头部 */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#1a2d4a]">
              <div>
                <h2 className="text-lg font-bold text-white">
                  📌 版本 v{viewingVersion} 详情
                </h2>
                {versionDetail && (
                  <p className="text-xs text-gray-500 mt-1 font-mono">
                    代价: {typeof versionDetail.total_cost === 'number' ? versionDetail.total_cost.toFixed(4) : '--'}
                  </p>
                )}
              </div>
              <button
                onClick={() => setViewingVersion(null)}
                className="text-gray-400 hover:text-red-400 transition text-xl leading-none"
              >
                ✕
              </button>
            </div>

            {/* 内容 */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {loadingDetail ? (
                <div className="text-center py-10 text-blue-400 font-mono">
                  <div className="inline-block w-8 h-8 border-2 border-blue-500/20 border-t-blue-500 rounded-full animate-spin mb-3"></div>
                  <p>加载中...</p>
                </div>
              ) : versionDetail ? (
                <>
                  {/* 控制律代码 */}
                  <div>
                    <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                      <span className="w-1 h-4 bg-gradient-to-b from-blue-500 to-cyan-500 rounded-full"></span>
                      control_v{viewingVersion}.py
                    </h3>
                    <pre className="bg-[#0a0e17] p-4 rounded-xl text-xs font-mono text-gray-300 overflow-auto max-h-80 border border-[#1a2d4a]">
                      {versionDetail.code || '（无代码）'}
                    </pre>
                  </div>

                  {/* 最优参数 */}
                  <div>
                    <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                      <span className="w-1 h-4 bg-gradient-to-b from-purple-500 to-pink-500 rounded-full"></span>
                      最优参数
                    </h3>
                    <pre className="bg-[#0a0e17] p-4 rounded-xl text-xs font-mono text-gray-300 overflow-auto max-h-40 border border-[#1a2d4a]">
                      {JSON.stringify(versionDetail.best_params || {}, null, 2)}
                    </pre>
                  </div>

                  {/* 诊断报告 */}
                  <div>
                    <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
                      <span className="w-1 h-4 bg-gradient-to-b from-teal-500 to-emerald-500 rounded-full"></span>
                      诊断报告
                    </h3>
                    <pre className="bg-[#0a0e17] p-4 rounded-xl text-xs font-mono text-gray-300 overflow-auto max-h-60 whitespace-pre-wrap border border-[#1a2d4a]">
                      {versionDetail.diagnosis || '（无诊断报告）'}
                    </pre>
                  </div>
                </>
              ) : (
                <div className="text-center py-10 text-gray-500 font-mono">
                  <p>加载失败</p>
                </div>
              )}
            </div>

            {/* 底部按钮 */}
            <div className="flex justify-end gap-3 px-6 py-4 border-t border-[#1a2d4a]">
              <button
                onClick={() => setViewingVersion(null)}
                className="px-6 py-2 text-sm bg-[#1a2d4a] hover:bg-[#2a3f5a] text-gray-200 rounded-xl border border-[#2a3f5a] transition"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProjectDetail;