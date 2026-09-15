import React, { useState, useEffect } from 'react';

interface ConfigFormProps {
  value: any;
  onChange: (config: any) => void;
  schema?: any;
  readOnly?: boolean;
}

const ConfigForm: React.FC<ConfigFormProps> = ({
  value,
  onChange,
  schema,
  readOnly = false,
}) => {
  const [config, setConfig] = useState(value);

  useEffect(() => {
    setConfig(value);
  }, [value]);

  const handleChange = (key: string, val: any) => {
    const updated = { ...config, [key]: val };
    setConfig(updated);
    onChange(updated);
  };

  // 简单渲染：如果是对象，递归展示
  const renderField = (key: string, val: any, path: string) => {
    if (typeof val === 'object' && val !== null && !Array.isArray(val)) {
      return (
        <div key={path} className="ml-4 border-l-2 border-[#1a2d4a] pl-4">
          <p className="text-sm font-medium text-gray-300 mt-2">{key}</p>
          {Object.entries(val).map(([subKey, subVal]) =>
            renderField(subKey, subVal, `${path}.${subKey}`)
          )}
        </div>
      );
    }

    if (Array.isArray(val)) {
      return (
        <div key={path} className="ml-4 border-l-2 border-[#1a2d4a] pl-4">
          <p className="text-sm font-medium text-gray-300 mt-2">{key} (数组)</p>
          <div className="text-xs text-gray-400 bg-[#0a0e17] p-2 rounded border border-[#1a2d4a]">
            [{val.join(', ')}]
          </div>
        </div>
      );
    }

    return (
      <div key={path} className="mt-2">
        <label className="block text-sm font-medium text-gray-300">{key}</label>
        {readOnly ? (
          <div className="text-sm text-gray-400 bg-[#0a0e17] p-2 rounded border border-[#1a2d4a] font-mono">
            {String(val)}
          </div>
        ) : (
          <input
            className="w-full bg-[#0a0e17] border border-[#1a2d4a] rounded-lg px-3 py-1.5 text-sm text-gray-200 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 outline-none transition font-mono"
            type={typeof val === 'number' ? 'number' : 'text'}
            value={val ?? ''}
            onChange={(e) => {
              const newVal = typeof val === 'number' ? Number(e.target.value) : e.target.value;
              const keys = path.split('.');
              const updated = { ...config };
              let current: any = updated;
              for (let i = 0; i < keys.length - 1; i++) {
                current = current[keys[i]];
              }
              current[keys[keys.length - 1]] = newVal;
              setConfig(updated);
              onChange(updated);
            }}
          />
        )}
      </div>
    );
  };

  return (
    <div className="space-y-2 max-h-96 overflow-auto">
      {Object.entries(config).map(([key, val]) =>
        renderField(key, val, key)
      )}
    </div>
  );
};

export default ConfigForm;