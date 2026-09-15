import React from 'react';
import RagSearchPanel from '@/components/RagSearchPanel';

const StrategyLibrary: React.FC = () => {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-2 text-white text-glow">📚 策略库</h1>
      <p className="text-gray-400 text-sm mb-6 font-mono">通过语义检索，查找相似场景的最优控制策略</p>
      <div className="glass-card p-6">
        <RagSearchPanel />
      </div>
    </div>
  );
};

export default StrategyLibrary;