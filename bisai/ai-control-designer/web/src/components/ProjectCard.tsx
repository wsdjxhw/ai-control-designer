import React from 'react';
import { Link } from 'react-router-dom';
import { Project } from '@/types/api';

interface ProjectCardProps {
  project: Project;
  onDelete?: (projectId: string) => void;
  className?: string;
}

const ProjectCard: React.FC<ProjectCardProps> = ({ project, onDelete, className = '' }) => {
  const getStatusBadge = (status: string) => {
    const map: Record<string, string> = {
      idle: 'bg-gray-100 text-gray-600',
      running: 'bg-blue-100 text-blue-700 animate-pulse',
      completed: 'bg-green-100 text-green-700',
      failed: 'bg-red-100 text-red-700',
    };
    return map[status] || 'bg-gray-100 text-gray-600';
  };

  const getStatusLabel = (status: string) => {
    const map: Record<string, string> = {
      idle: '待启动',
      running: '运行中',
      completed: '已完成',
      failed: '失败',
    };
    return map[status] || status;
  };

  const handleDelete = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (onDelete) onDelete(project.project_id);
  };

  return (
    <div className={`bg-white p-5 rounded-2xl shadow-sm border border-gray-100 card-hover group ${className}`}>
      <div className="flex justify-between items-start">
        <Link to={`/projects/${project.project_id}`} className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-800 text-lg truncate">{project.name}</h3>
          <p className="text-sm text-gray-400 mt-1 line-clamp-2 min-h-[2.5rem]">
            {project.description || '暂无描述'}
          </p>
        </Link>
        {onDelete && (
          <button
            onClick={handleDelete}
            className="p-1.5 text-gray-300 hover:text-red-500 hover:bg-red-50 rounded-lg opacity-0 group-hover:opacity-100 transition-all shrink-0 ml-2"
            title="删除项目"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </button>
        )}
      </div>

      <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
        <span className={`px-2 py-1 rounded ${
          project.mode === 'expert' ? 'bg-purple-100 text-purple-700' : 'bg-teal-100 text-teal-700'
        }`}>
          {project.mode === 'expert' ? '👨‍💻 专家' : '👶 新手'}
        </span>
        <span className={`px-2 py-1 rounded ${getStatusBadge(project.status)}`}>
          {getStatusLabel(project.status)}
        </span>
        {project.best_cost !== null && (
          <span className="bg-indigo-50 text-indigo-700 px-2 py-1 rounded">
            🎯 {project.best_cost.toFixed(3)}
          </span>
        )}
        <span className="text-gray-400 px-2 py-1">v{project.current_version}</span>
      </div>

      <div className="mt-3 pt-3 border-t border-gray-50 flex justify-between text-xs text-gray-400">
        <span>🕐 {new Date(project.updated_at).toLocaleDateString()}</span>
        <span className="flex items-center gap-1">
          <span className={`w-1.5 h-1.5 rounded-full ${
            project.status === 'running' ? 'bg-blue-500 animate-pulse' : 'bg-gray-300'
          }`}></span>
          {project.status === 'running' ? '实时监控中' : '已就绪'}
        </span>
      </div>
    </div>
  );
};

export default ProjectCard;