import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface DiagnosisReportProps {
  content: string;
  title?: string;
  className?: string;
  loading?: boolean;
}

const DiagnosisReport: React.FC<DiagnosisReportProps> = ({
  content,
  title = '🩺 诊断报告',
  className = '',
  loading = false,
}) => {
  if (loading) {
    return (
      <div className={`bg-white rounded-xl border border-gray-100 p-4 ${className}`}>
        <h3 className="font-semibold text-gray-800 mb-3">{title}</h3>
        <div className="flex items-center justify-center py-8">
          <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="ml-3 text-gray-400">生成诊断报告中...</span>
        </div>
      </div>
    );
  }

  if (!content) {
    return (
      <div className={`bg-white rounded-xl border border-gray-100 p-4 ${className}`}>
        <h3 className="font-semibold text-gray-800 mb-3">{title}</h3>
        <div className="text-center py-8 text-gray-400">
          <p className="text-4xl mb-2">📋</p>
          <p>暂无诊断报告</p>
          <p className="text-sm">完成演化后自动生成</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white rounded-xl border border-gray-100 p-4 ${className}`}>
      <h3 className="font-semibold text-gray-800 mb-3">{title}</h3>
      <div className="prose prose-sm max-w-none bg-gray-50 p-4 rounded-lg overflow-auto max-h-96">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {content}
        </ReactMarkdown>
      </div>
    </div>
  );
};

export default DiagnosisReport;