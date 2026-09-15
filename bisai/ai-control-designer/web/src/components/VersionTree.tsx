import React from 'react';

interface VersionNode {
  version: number;
  cost: number;
  params?: Record<string, number>;
  isBest?: boolean;
  status?: 'success' | 'failed' | 'running';
}

interface VersionTreeProps {
  versions: VersionNode[];
  onSelect?: (version: number) => void;
  selectedVersion?: number;
  className?: string;
}

const VersionTree: React.FC<VersionTreeProps> = ({
  versions,
  onSelect,
  selectedVersion,
  className = '',
}) => {
  const getStatusColor = (status?: string) => {
    switch (status) {
      case 'success':
        return 'bg-green-500';
      case 'failed':
        return 'bg-red-500';
      case 'running':
        return 'bg-blue-500 animate-pulse';
      default:
        return 'bg-gray-400';
    }
  };

  const getCostColor = (cost: number, allCosts: number[]) => {
    const min = Math.min(...allCosts);
    const max = Math.max(...allCosts);
    const ratio = (cost - min) / (max - min + 0.001);
    if (ratio < 0.3) return 'text-green-600';
    if (ratio < 0.6) return 'text-yellow-600';
    return 'text-red-600';
  };

  const allCosts = versions.map(v => v.cost);

  return (
    <div className={`bg-white rounded-xl border border-gray-100 p-4 ${className}`}>
      <h3 className="font-semibold text-gray-800 mb-4">🌳 版本进化树</h3>
      <div className="relative">
        {/* 垂直连线 */}
        <div className="absolute left-5 top-0 bottom-0 w-0.5 bg-gray-200"></div>

        <div className="space-y-0">
          {versions.map((v, index) => {
            const isSelected = selectedVersion === v.version;
            const isFirst = index === 0;
            const isLast = index === versions.length - 1;

            return (
              <div
                key={v.version}
                className={`relative flex items-start gap-4 cursor-pointer hover:bg-gray-50 rounded-lg p-2 transition ${
                  isSelected ? 'bg-blue-50' : ''
                }`}
                onClick={() => onSelect?.(v.version)}
              >
                {/* 版本节点 */}
                <div className="relative z-10 flex items-center justify-center w-10 h-10 rounded-full border-2 bg-white shrink-0"
                  style={{
                    borderColor: isSelected ? '#2563eb' : '#d1d5db',
                    boxShadow: isSelected ? '0 0 0 3px rgba(37, 99, 235, 0.3)' : 'none',
                  }}
                >
                  <span className={`text-xs font-bold ${isSelected ? 'text-blue-600' : 'text-gray-600'}`}>
                    v{v.version}
                  </span>
                </div>

                {/* 版本信息 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className={`font-medium ${isSelected ? 'text-blue-600' : 'text-gray-800'}`}>
                      版本 {v.version}
                    </span>
                    <span className="w-2 h-2 rounded-full shrink-0 ${getStatusColor(v.status)}"></span>
                    {v.isBest && (
                      <span className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">
                        ★ 最优
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-sm">
                    <span className={getCostColor(v.cost, allCosts)}>
                      代价: {v.cost.toFixed(3)}
                    </span>
                    {v.params && (
                      <span className="text-gray-400 text-xs truncate max-w-[200px]">
                        {Object.entries(v.params)
                          .slice(0, 3)
                          .map(([k, val]) => `${k}=${val.toFixed(2)}`)
                          .join(', ')}
                        {Object.keys(v.params).length > 3 && '...'}
                      </span>
                    )}
                  </div>
                </div>

                {/* 连接线（非最后一个） */}
                {!isLast && (
                  <div className="absolute left-5 top-10 bottom-0 w-0.5 bg-gray-200 -z-0"></div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default VersionTree;