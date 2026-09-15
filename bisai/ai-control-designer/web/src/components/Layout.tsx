import React from 'react';
import { Link, useLocation } from 'react-router-dom';

const navItems = [
  { label: '项目', path: '/', icon: '📊' },
  { label: '策略库', path: '/library', icon: '📚' },
  { label: '设置', path: '/settings', icon: '⚙️' },
];

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();

  return (
    <div className="min-h-screen flex relative">
      {/* 背景装饰 - 网格线 */}
      <div className="fixed inset-0 pointer-events-none opacity-[0.03]"
        style={{
          backgroundImage: `
            linear-gradient(rgba(59, 130, 246, 0.3) 1px, transparent 1px),
            linear-gradient(90deg, rgba(59, 130, 246, 0.3) 1px, transparent 1px)
          `,
          backgroundSize: '40px 40px',
        }}
      />

      {/* 侧边栏 - 深色玻璃态 */}
      <aside className="w-64 bg-[#0d1524]/90 backdrop-blur-xl border-r border-[#1a2d4a] p-4 shrink-0 flex flex-col relative z-10">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8 pb-4 border-b border-[#1a2d4a]">
          <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-white text-xl font-bold shadow-lg shadow-blue-500/25">
            AI
          </div>
          <div>
            <div className="text-lg font-bold text-white tracking-tight">控制设计器</div>
            <div className="text-xs text-blue-400/60">v2.0 · 智能体</div>
          </div>
        </div>

        {/* 导航 */}
        <nav className="space-y-1 flex-1">
          {navItems.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-300 ${
                  isActive
                    ? 'bg-blue-500/10 text-blue-400 border border-blue-500/30'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                <span className="text-lg">{item.icon}</span>
                {item.label}
                {isActive && (
                  <span className="ml-auto w-1 h-5 bg-gradient-to-b from-blue-500 to-purple-500 rounded-full shadow-[0_0_12px_rgba(59,130,246,0.5)]"></span>
                )}
              </Link>
            );
          })}
        </nav>

        {/* 底部状态 */}
        <div className="mt-auto pt-4 border-t border-[#1a2d4a]">
          <div className="p-3 bg-blue-500/5 rounded-xl border border-blue-500/20">
            <div className="flex items-center gap-2 text-sm">
              <span className="status-dot-online"></span>
              <span className="text-gray-300 font-medium">系统就绪</span>
            </div>
            <div className="text-xs text-gray-500 mt-1 font-mono">⚡ 等待启动演化</div>
          </div>
        </div>
      </aside>

      {/* 主内容 */}
      <main className="flex-1 p-6 overflow-auto relative z-10">
        {/* 顶部装饰光效 */}
        <div className="absolute top-0 right-0 w-96 h-96 bg-blue-500/5 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute bottom-0 left-0 w-96 h-96 bg-purple-500/5 rounded-full blur-3xl pointer-events-none"></div>
        {children}
      </main>
    </div>
  );
};

export default Layout;