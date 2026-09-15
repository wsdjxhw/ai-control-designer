import React from 'react';
import { useNavigate } from 'react-router-dom';

interface TopNavProps {
  title?: string;
  showBack?: boolean;
  rightContent?: React.ReactNode;
}

const TopNav: React.FC<TopNavProps> = ({ title, showBack = false, rightContent }) => {
  const navigate = useNavigate();

  return (
    <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between shrink-0">
      <div className="flex items-center gap-3">
        {showBack && (
          <button
            onClick={() => navigate(-1)}
            className="p-1.5 hover:bg-gray-100 rounded-lg transition"
            aria-label="返回"
          >
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
        )}
        {title && <h1 className="text-lg font-semibold text-gray-800">{title}</h1>}
      </div>
      <div className="flex items-center gap-3">
        {rightContent}
        {/* 用户信息/状态指示器 */}
        <div className="flex items-center gap-2 text-sm text-gray-500">
          <span className="w-2 h-2 bg-green-500 rounded-full"></span>
          <span className="hidden sm:inline">在线</span>
        </div>
      </div>
    </header>
  );
};

export default TopNav;