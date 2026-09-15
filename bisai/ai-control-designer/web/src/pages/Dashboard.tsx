import React, { useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import ReactECharts from 'echarts-for-react';
import { useProjectStore } from '@/stores/projectStore';

const Dashboard: React.FC = () => {
  const { projects, fetchProjects, loading, error, deleteProject } = useProjectStore();

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleDelete = async (projectId: string, projectName: string) => {
    if (!confirm(`确定要删除项目「${projectName}」吗？此操作不可恢复！`)) return;
    try {
      await deleteProject(projectId);
      await fetchProjects();
    } catch (err: any) {
      alert('删除失败: ' + err.message);
    }
  };

  // ✅ 演化总览数据（只统计有 best_cost 的项目）
  const overviewData = useMemo(() => {
    const withCost = projects
      .filter((p) => p.best_cost !== null && p.best_cost !== undefined)
      .sort((a, b) => (a.best_cost as number) - (b.best_cost as number));
    return {
      names: withCost.map((p) => p.name.length > 12 ? p.name.slice(0, 12) + '…' : p.name),
      costs: withCost.map((p) => p.best_cost as number),
      ids: withCost.map((p) => p.project_id),
    };
  }, [projects]);

  // ✅ 演化概览图表配置（横向柱状图）
  const overviewOption = useMemo(() => {
    if (overviewData.names.length === 0) return null;

    return {
      title: {
        text: '',
        left: 'center',
      },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        backgroundColor: 'rgba(15, 23, 41, 0.95)',
        borderColor: '#1e3a5f',
        textStyle: { color: '#e2e8f0', fontSize: 12 },
        formatter: (params: any) => {
          const p = params[0];
          return `<b>${p.name}</b><br/>最佳代价: <span style="color:#a78bfa">${p.value.toFixed(6)}</span>`;
        },
      },
      grid: {
        left: 120,
        right: 80,
        top: 20,
        bottom: 30,
      },
      xAxis: {
        type: 'value',
        name: '最佳代价',
        nameTextStyle: { color: '#64748b', fontSize: 11 },
        axisLine: { lineStyle: { color: '#1a2d4a' } },
        axisLabel: { color: '#94a3b8', fontSize: 10 },
        splitLine: { lineStyle: { color: '#1a2d4a', type: 'dashed' } },
      },
      yAxis: {
        type: 'category',
        data: overviewData.names,
        axisLine: { lineStyle: { color: '#1a2d4a' } },
        axisLabel: { color: '#94a3b8', fontSize: 11, fontFamily: 'monospace' },
        axisTick: { show: false },
      },
      series: [
        {
          name: '最佳代价',
          type: 'bar',
          data: overviewData.costs,
          barWidth: '60%',
          itemStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 1,
              y2: 0,
              colorStops: [
                { offset: 0, color: '#3b82f6' },
                { offset: 1, color: '#8b5cf6' },
              ],
            },
            borderRadius: [0, 8, 8, 0],
          },
          label: {
            show: true,
            position: 'right',
            formatter: (p: any) => p.value.toFixed(4),
            color: '#a78bfa',
            fontSize: 11,
            fontFamily: 'monospace',
          },
        },
      ],
    };
  }, [overviewData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto shadow-[0_0_30px_rgba(59,130,246,0.3)]"></div>
          <p className="mt-4 text-blue-400/60 font-mono text-sm">加载中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-16 glass-card p-12">
        <div className="text-5xl mb-4">🔌</div>
        <div className="text-red-400 font-medium">{error}</div>
        <p className="text-gray-500 text-sm mt-2 font-mono">请确保后端服务已启动</p>
      </div>
    );
  }

  return (
    <div>
      {/* 页面头部 */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight text-glow">
            📊 项目控制台
          </h1>
          <p className="text-gray-400 text-sm mt-1 font-mono">管理所有控制律演化项目</p>
        </div>
        <Link
          to="/projects/new"
          className="btn-neon flex items-center gap-2"
        >
          <span className="text-xl leading-none">+</span>
          新建项目
        </Link>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <div className="glass-card p-4">
          <p className="text-sm text-gray-400 font-mono">总项目</p>
          <p className="text-2xl font-bold text-white">{projects.length}</p>
        </div>
        <div className="glass-card p-4 border-blue-500/30">
          <p className="text-sm text-gray-400 font-mono">运行中</p>
          <p className="text-2xl font-bold text-blue-400">
            {projects.filter(p => p.status === 'running').length}
          </p>
        </div>
        <div className="glass-card p-4 border-green-500/30">
          <p className="text-sm text-gray-400 font-mono">已完成</p>
          <p className="text-2xl font-bold text-green-400">
            {projects.filter(p => p.status === 'completed').length}
          </p>
        </div>
        <div className="glass-card p-4 border-purple-500/30">
          <p className="text-sm text-gray-400 font-mono">最佳代价</p>
          <p className="text-2xl font-bold text-purple-400">
            {projects.some(p => p.best_cost !== null)
              ? Math.min(...projects.filter(p => p.best_cost !== null).map(p => p.best_cost!)).toFixed(2)
              : '--'}
          </p>
        </div>
      </div>

      {/* ✅ 演化总览图表 */}
      {overviewOption && (
        <div className="glass-card p-4 mb-8">
          <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
            <span className="w-1 h-5 bg-gradient-to-b from-purple-500 to-pink-500 rounded-full"></span>
            📈 各项目最佳代价对比
            <span className="text-xs text-gray-500 font-mono font-normal ml-auto">
              (条形越短越好，共 {overviewData.names.length} 个项目)
            </span>
          </h3>
          <ReactECharts option={overviewOption} style={{ height: Math.max(200, overviewData.names.length * 40) }} />
        </div>
      )}

      {/* 项目列表 */}
      {projects.length === 0 ? (
        <div className="glass-card p-16 text-center">
          <div className="text-6xl mb-4">🚀</div>
          <p className="text-xl text-gray-400">还没有项目</p>
          <p className="text-sm text-gray-500 mt-1 font-mono">点击「新建项目」开始你的第一个控制律设计</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {projects.map((p) => (
            <div
              key={p.project_id}
              className="glass-card-hover p-5 group relative cursor-pointer"
            >
              {/* 删除按钮 */}
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  handleDelete(p.project_id, p.name);
                }}
                className="absolute top-3 right-3 p-1.5 text-gray-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg opacity-0 group-hover:opacity-100 transition-all"
                title="删除项目"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>

              <Link to={`/projects/${p.project_id}`} className="block">
                <h3 className="font-semibold text-white text-lg truncate pr-8">{p.name}</h3>
                <p className="text-sm text-gray-400 mt-1 line-clamp-2 min-h-[2.5rem]">
                  {p.description || '暂无描述'}
                </p>

                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                  <span className="badge-tech-blue">
                    {p.mode === 'expert' ? '👨‍💻 专家' : '👶 新手'}
                  </span>
                  <span className={`badge-tech ${
                    p.status === 'completed' ? 'badge-tech-green' :
                    p.status === 'running' ? 'badge-tech-blue' :
                    p.status === 'failed' ? 'bg-red-500/20 text-red-300 border-red-500/30' :
                    'badge-tech-gray'
                  }`}>
                    {p.status === 'running' ? '⏳ 运行中' :
                     p.status === 'completed' ? '✅ 已完成' :
                     p.status === 'failed' ? '❌ 失败' :
                     '⏸️ 待启动'}
                  </span>
                  {p.best_cost !== null && (
                    <span className="badge-tech-purple">
                      🎯 {p.best_cost.toFixed(3)}
                    </span>
                  )}
                  <span className="text-gray-500 text-xs font-mono">v{p.current_version}</span>
                </div>

                <div className="mt-3 pt-3 border-t border-[#1a2d4a] flex justify-between text-xs text-gray-500 font-mono">
                  <span>{new Date(p.updated_at).toLocaleDateString()}</span>
                  <span className="flex items-center gap-1">
                    <span className={`w-1.5 h-1.5 rounded-full ${
                      p.status === 'running' ? 'bg-blue-500 animate-pulse' : 'bg-gray-600'
                    }`}></span>
                    {p.status === 'running' ? '实时监控中' : '已就绪'}
                  </span>
                </div>
              </Link>
            </div>
          ))}

          {/* 新建卡片 */}
          <Link
            to="/projects/new"
            className="glass-card p-5 flex flex-col items-center justify-center border-dashed border-[#1a2d4a] hover:border-blue-500/50 hover:bg-blue-500/5 transition-all min-h-[220px]"
          >
            <div className="text-4xl text-gray-600 group-hover:text-blue-400 transition">＋</div>
            <p className="text-gray-500 mt-2 font-medium">新建项目</p>
            <p className="text-xs text-gray-600 font-mono">点击开始创建</p>
          </Link>
        </div>
      )}
    </div>
  );
};

export default Dashboard;