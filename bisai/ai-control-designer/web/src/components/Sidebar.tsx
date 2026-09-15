import React from 'react';
import { Link, useLocation } from 'react-router-dom';

interface SidebarProps {
  collapsed?: boolean;
  onToggle?: () => void;
}

const navItems = [
  { label: '项目', path: '/', icon: '📊' },
  { label: '策略库', path: '/library', icon: '📚' },
  { label: '设置', path: '/settings', icon: '⚙️' },
];

const Sidebar: React.FC<SidebarProps> = ({ collapsed = false }) => {
  const location = useLocation();

  return (
    <aside
      className={`bg-white border-r border-gray-200 p-4 shrink-0 flex flex-col transition-all duration-300 ${
        collapsed ? 'w-20' : 'w-64'
      }`}
    >
      {/* Logo 区域 */}
      <div className={`flex items-center gap-3 mb-8 pb-4 border-b border-gray-100 ${collapsed ? 'justify-center' : ''}`}>
        <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center text-white text-xl font-bold shadow-md shrink-0">
          AI
        </div>
        {!collapsed && (
          <div>
            <div className="text-lg font-bold text-gray-800">控制设计器</div>
            <div className="text-xs text-gray-400">v2.0 · 智能体</div>
          </div>
        )}
      </div>

      {/* 导航菜单 */}
      <nav className="space-y-1 flex-1">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-xl transition-all duration-200 ${
                isActive
                  ? 'bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 font-medium shadow-sm'
                  : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
              } ${collapsed ? 'justify-center' : ''}`}
              title={collapsed ? item.label : undefined}
            >
              <span className="text-lg shrink-0">{item.icon}</span>
              {!collapsed && item.label}
              {isActive && !collapsed && (
                <span className="ml-auto w-1.5 h-6 bg-blue-600 rounded-full"></span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* 底部状态 */}
      {!collapsed && (
        <div className="mt-auto pt-4 border-t border-gray-100">
          <div className="p-3 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl">
            <div className="flex items-center gap-2 text-sm">
              <span className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></span>
              <span className="text-gray-700 font-medium">系统就绪</span>
            </div>
            <div className="text-xs text-gray-400 mt-1">等待启动演化任务</div>
          </div>
        </div>
      )}
    </aside>
  );
};

export default Sidebar;