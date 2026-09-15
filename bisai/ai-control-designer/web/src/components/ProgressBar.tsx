import React from 'react';

interface ProgressBarProps {
  value: number; // 0-100
  label?: string;
  showPercentage?: boolean;
  color?: 'blue' | 'green' | 'red' | 'orange' | 'gradient';
  size?: 'sm' | 'md' | 'lg';
  animated?: boolean;
  className?: string;
}

const colorMap = {
  blue: 'bg-blue-600',
  green: 'bg-green-600',
  red: 'bg-red-600',
  orange: 'bg-orange-600',
  gradient: 'bg-gradient-to-r from-blue-500 to-indigo-600',
};

const sizeMap = {
  sm: 'h-1.5',
  md: 'h-2.5',
  lg: 'h-4',
};

const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  label,
  showPercentage = true,
  color = 'gradient',
  size = 'md',
  animated = true,
  className = '',
}) => {
  const clampedValue = Math.min(100, Math.max(0, value));

  return (
    <div className={className}>
      {label && (
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm font-medium text-gray-700">{label}</span>
          {showPercentage && (
            <span className="text-sm font-semibold text-gray-700">{Math.round(clampedValue)}%</span>
          )}
        </div>
      )}
      <div className={`w-full bg-gray-200 rounded-full overflow-hidden ${sizeMap[size]}`}>
        <div
          className={`${colorMap[color]} ${sizeMap[size]} rounded-full transition-all duration-500 ${
            animated ? 'transition-all' : ''
          }`}
          style={{ width: `${clampedValue}%` }}
        />
      </div>
    </div>
  );
};

export default ProgressBar;