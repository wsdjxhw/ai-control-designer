import React from 'react';

export interface SceneConfig {
  domain_name?: string;
  state_names: string[];
  control_names: string[];
  temporal: {
    T: number;
    dt: number;
    n_steps?: number;
  };
  // 🆕 空间参数（仅 PDE 模型需要）
  spatial?: {
    X: number;  // 空间总长度 (m)
    dx: number; // 空间步长 (m)
  };
  initial_state: Record<string, number>;
  physical_params: Record<string, number>;
  target_values: Record<string, number>;
  cost_weights?: Record<string, number>;
  control_limits?: Record<string, [number, number]>;
  control_type?: 'continuous' | 'bang_bang';
  [key: string]: any;
}

interface SceneConfigPanelProps {
  config: string; // JSON string
  onChange: (config: string) => void;
  typeDetection?: {
    model_type: 'ode' | 'pde' | 'unknown';
    confidence: number;
    evidence: string[];
    user_can_override: boolean;
  };
}

const SceneConfigPanel: React.FC<SceneConfigPanelProps> = ({ config, onChange, typeDetection }) => {
  let parsedConfig: SceneConfig;
  try {
    parsedConfig = JSON.parse(config);
  } catch {
    parsedConfig = {
      state_names: [],
      control_names: [],
      temporal: { T: 10.0, dt: 0.01 },
      initial_state: {},
      physical_params: {},
      target_values: {},
      control_type: 'continuous',
    };
  }

  // 模型类型状态（优先使用用户配置，其次使用 LLM 检测结果，默认 ODE）
  const [modelType, setModelType] = React.useState<'ode' | 'pde'>(
    parsedConfig.model_type || typeDetection?.model_type || 'ode'
  );

  // 当 LLM 检测结果变化时，同步更新（仅当用户未手动设置时）
  React.useEffect(() => {
    if (!typeDetection) return;
    const inferred = typeDetection.model_type === 'pde' ? 'pde' : 'ode';
    setModelType(inferred);
    updateConfig({ model_type: inferred, detected_type: inferred });
  }, [typeDetection]);

  // 更新模型类型
  const updateModelType = (newType: 'ode' | 'pde') => {
    setModelType(newType);
    // 🆕 同时更新 model_type 和 detected_type，确保前端选择和后端判断一致
    updateConfig({ model_type: newType, detected_type: newType });
  };

  const updateConfig = (updates: Partial<SceneConfig>) => {
    const newConfig = { ...parsedConfig, ...updates };
    onChange(JSON.stringify(newConfig, null, 2));
  };

  const updateTemporal = (key: string, value: number) => {
    const newTemporal = { ...parsedConfig.temporal, [key]: value };
    updateConfig({ temporal: newTemporal });
  };

  const updateRecord = (
    recordKey: 'initial_state' | 'physical_params' | 'target_values',
    field: string,
    value: number
  ) => {
    if (isNaN(value)) return; // 跳过 NaN
    const currentRecord = parsedConfig[recordKey] || {};
    const newRecord = { ...currentRecord, [field]: value };
    updateConfig({ [recordKey]: newRecord } as any);
  };

  const updateArray = (arrayKey: 'state_names' | 'control_names', index: number, value: string) => {
    const newArray = [...parsedConfig[arrayKey]];
    newArray[index] = value;
    updateConfig({ [arrayKey]: newArray });
  };

  const addField = (recordKey: 'initial_state' | 'physical_params' | 'target_values') => {
    const existingKeys = Object.keys(parsedConfig[recordKey] || {});
    let newKey = 'new_target';
    let counter = 1;
    while (existingKeys.includes(newKey)) {
      newKey = `new_target_${counter}`;
      counter++;
    }
    const newRecord = { ...parsedConfig[recordKey], [newKey]: 0 };
    updateConfig({ [recordKey]: newRecord });
  };

  const removeField = (recordKey: 'initial_state' | 'physical_params' | 'target_values', field: string) => {
    const newRecord = { ...parsedConfig[recordKey] };
    delete newRecord[field];
    updateConfig({ [recordKey]: newRecord });
  };

  const addArrayItem = (arrayKey: 'state_names' | 'control_names') => {
    const newArray = [...parsedConfig[arrayKey], `new_${arrayKey === 'state_names' ? 'state' : 'control'}`];
    updateConfig({ [arrayKey]: newArray });
  };

  const removeArrayItem = (arrayKey: 'state_names' | 'control_names', index: number) => {
    const newArray = parsedConfig[arrayKey].filter((_, i) => i !== index);
    updateConfig({ [arrayKey]: newArray });
  };

  return (
    <div className="glass-card p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xl font-bold text-white tracking-tight">📋 场景配置参数</h3>
          <p className="text-sm text-gray-400">编辑 LLM 提取的参数（支持实时修改，自动保存）</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="text-xs px-3 py-1 bg-green-500/20 border border-green-500/50 rounded text-green-400">
            ✓ 已自动保存
          </div>
          <div className="text-xs px-3 py-1 bg-purple-500/20 border border-purple-500/50 rounded text-purple-400">
            {parsedConfig.domain_name || 'custom'}
          </div>
        </div>
      </div>

      {/* 模型类型选择器 */}
      <div className="p-4 bg-[#0a0e17] border border-[#1a2d4a] rounded-lg">
        <div className="flex items-center justify-between mb-3">
          <label className="text-sm font-medium text-gray-300">🔬 模型类型</label>
          {typeDetection && (
            <span className="text-xs text-gray-500">
              LLM 检测: {typeDetection.model_type.toUpperCase()} (置信度: {(typeDetection.confidence * 100).toFixed(0)}%)
            </span>
          )}
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => updateModelType('ode')}
            className={`flex-1 px-4 py-2 rounded-lg border transition-all ${
              modelType === 'ode'
                ? 'bg-blue-600 border-blue-500 text-white'
                : 'bg-[#111827] border-[#2a3d5a] text-gray-400 hover:bg-[#1a2d4a]'
            }`}
          >
            <div className="font-medium">ODE</div>
            <div className="text-xs opacity-70">常微分方程</div>
          </button>
          <button
            onClick={() => updateModelType('pde')}
            className={`flex-1 px-4 py-2 rounded-lg border transition-all ${
              modelType === 'pde'
                ? 'bg-purple-600 border-purple-500 text-white'
                : 'bg-[#111827] border-[#2a3d5a] text-gray-400 hover:bg-[#1a2d4a]'
            }`}
          >
            <div className="font-medium">PDE</div>
            <div className="text-xs opacity-70">偏微分方程</div>
          </button>
        </div>
        {typeDetection && typeDetection.evidence.length > 0 && (
          <p className="text-xs text-gray-500 mt-2">💡 检测依据: {typeDetection.evidence[0]}</p>
        )}
      </div>

      {/* 控制类型选择器 */}
      <div className="p-4 bg-[#0a0e17] border border-[#1a2d4a] rounded-lg">
        <div className="flex items-center justify-between mb-3">
          <label className="text-sm font-medium text-gray-300">🎮 控制类型 (Control Type)</label>
          <span className="text-xs text-gray-500">影响控制律生成和代价校验</span>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => updateConfig({ control_type: 'continuous' })}
            className={`flex-1 px-4 py-2 rounded-lg border transition-all ${
              parsedConfig.control_type === 'continuous'
                ? 'bg-green-600 border-green-500 text-white'
                : 'bg-[#111827] border-[#2a3d5a] text-gray-400 hover:bg-[#1a2d4a]'
            }`}
          >
            <div className="font-medium">Continuous</div>
            <div className="text-xs opacity-70">连续控制 (PID/反馈)</div>
          </button>
          <button
            onClick={() => updateConfig({ control_type: 'bang_bang' })}
            className={`flex-1 px-4 py-2 rounded-lg border transition-all ${
              parsedConfig.control_type === 'bang_bang'
                ? 'bg-orange-600 border-orange-500 text-white'
                : 'bg-[#111827] border-[#2a3d5a] text-gray-400 hover:bg-[#1a2d4a]'
            }`}
          >
            <div className="font-medium">Bang-Bang</div>
            <div className="text-xs opacity-70">离散控制 (开关/阈值)</div>
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          💡 Continuous: 连续值控制，适用于力矩、电压等；Bang-Bang: 离散开关控制，适用于阀门、继电器等
        </p>
      </div>

      {/* State Variables */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-300">📍 状态变量 (State Names)</label>
          <button
            onClick={() => addArrayItem('state_names')}
            className="text-xs px-2 py-1 bg-blue-600/20 border border-blue-500/50 text-blue-400 rounded hover:bg-blue-600/40"
          >
            + 添加
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {parsedConfig.state_names.map((name, index) => (
            <div key={index} className="flex items-center gap-1 bg-[#0a0e17] border border-[#1a2d4a] rounded px-2 py-1">
              <input
                type="text"
                value={name}
                onChange={(e) => updateArray('state_names', index, e.target.value)}
                className="bg-transparent text-sm text-white w-24 focus:outline-none"
              />
              <button
                onClick={() => removeArrayItem('state_names', index)}
                className="text-red-400 hover:text-red-300 text-xs"
              >
                ✕
              </button>
            </div>
          ))}
          {parsedConfig.state_names.length === 0 && (
            <span className="text-xs text-gray-500">无状态变量</span>
          )}
        </div>
      </div>

      {/* Control Variables */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-300">🎮 控制输入 (Control Names)</label>
          <button
            onClick={() => addArrayItem('control_names')}
            className="text-xs px-2 py-1 bg-blue-600/20 border border-blue-500/50 text-blue-400 rounded hover:bg-blue-600/40"
          >
            + 添加
          </button>
        </div>
        <div className="flex flex-wrap gap-2">
          {parsedConfig.control_names.map((name, index) => (
            <div key={index} className="flex items-center gap-1 bg-[#0a0e17] border border-[#1a2d4a] rounded px-2 py-1">
              <input
                type="text"
                value={name}
                onChange={(e) => updateArray('control_names', index, e.target.value)}
                className="bg-transparent text-sm text-white w-24 focus:outline-none"
              />
              <button
                onClick={() => removeArrayItem('control_names', index)}
                className="text-red-400 hover:text-red-300 text-xs"
              >
                ✕
              </button>
            </div>
          ))}
          {parsedConfig.control_names.length === 0 && (
            <span className="text-xs text-gray-500">无控制输入</span>
          )}
        </div>
      </div>

      {/* 🆕 空间参数 (Spatial) — 仅 PDE 时显示 */}
      {modelType === 'pde' && (
        <div className="space-y-3 pt-3 border-t border-[#1a2d4a]">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-300">🌐 空间参数 (Spatial)</label>
            <span className="text-xs text-gray-500">仅 PDE 模型需要</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">X (空间总长度, m)</label>
              <input
                type="number"
                step="0.1"
                value={parsedConfig.spatial?.X ?? 2.0}
                onChange={(e) => {
                  const v = parseFloat(e.target.value);
                  if (isNaN(v)) return;
                  updateConfig({
                    spatial: { ...parsedConfig.spatial, X: v },
                  });
                }}
                className="w-full px-3 py-2 bg-[#0a0e17] border border-[#1a2d4a] rounded text-white text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">dx (空间步长, m)</label>
              <input
                type="number"
                step="0.01"
                value={parsedConfig.spatial?.dx ?? 0.1}
                onChange={(e) => {
                  const v = parseFloat(e.target.value);
                  if (isNaN(v)) return;
                  updateConfig({
                    spatial: { ...parsedConfig.spatial, dx: v },
                  });
                }}
                className="w-full px-3 py-2 bg-[#0a0e17] border border-[#1a2d4a] rounded text-white text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">M+1 (网格数, 自动计算)</label>
              <input
                type="text"
                value={Math.floor((parsedConfig.spatial?.X ?? 2.0) / (parsedConfig.spatial?.dx ?? 0.1)) + 1}
                disabled
                className="w-full px-3 py-2 bg-[#0a0e17] border border-[#1a2d4a] rounded text-gray-500 text-sm"
              />
            </div>
          </div>
          <p className="text-xs text-gray-500">
            💡 M+1 = X/dx + 1；建议 dx 使得 M+1 在 20-200 之间（仿真速度与精度平衡）
          </p>
        </div>
      )}

      {/* Temporal Parameters */}
      <div className="space-y-3 pt-3 border-t border-[#1a2d4a]">
        <label className="text-sm font-medium text-gray-300">⏱️ 时间参数 (Temporal)</label>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs text-gray-500 mb-1">T (总时间, s)</label>
            <input
              type="number"
              step="0.1"
              value={parsedConfig.temporal?.T ?? 10.0}
              onChange={(e) => updateTemporal('T', parseFloat(e.target.value))}
              className="w-full px-3 py-2 bg-[#0a0e17] border border-[#1a2d4a] rounded text-white text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">dt (时间步长, s)</label>
            <input
              type="number"
              step="0.001"
              value={parsedConfig.temporal?.dt ?? 0.01}
              onChange={(e) => updateTemporal('dt', parseFloat(e.target.value))}
              className="w-full px-3 py-2 bg-[#0a0e17] border border-[#1a2d4a] rounded text-white text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs text-gray-500 mb-1">n_steps (自动计算)</label>
            <input
              type="text"
              value={Math.floor((parsedConfig.temporal?.T ?? 10) / (parsedConfig.temporal?.dt ?? 0.01))}
              disabled
              className="w-full px-3 py-2 bg-[#0a0e17] border border-[#1a2d4a] rounded text-gray-500 text-sm"
            />
          </div>
        </div>
      </div>

      {/* Physical Parameters */}
      <div className="space-y-3 pt-3 border-t border-[#1a2d4a]">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-300">⚙️ 物理参数 (Physical Params)</label>
          <button
            onClick={() => addField('physical_params')}
            className="text-xs px-2 py-1 bg-purple-600/20 border border-purple-500/50 text-purple-400 rounded hover:bg-purple-600/40"
          >
            + 添加参数
          </button>
        </div>
        {Object.keys(parsedConfig.physical_params || {}).length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(parsedConfig.physical_params).map(([key, value]) => (
              <div key={key} className="flex items-center gap-2 bg-[#0a0e17] border border-[#1a2d4a] rounded px-3 py-2">
                <input
                  type="text"
                  value={key}
                  onChange={(e) => {
                    const newParams = { ...parsedConfig.physical_params };
                    const val = newParams[key];
                    delete newParams[key];
                    newParams[e.target.value] = val;
                    updateConfig({ physical_params: newParams });
                  }}
                  className="flex-1 bg-transparent text-sm text-purple-400 font-mono focus:outline-none"
                />
                <input
                  type="number"
                  step="0.01"
                  value={value}
                  onChange={(e) => updateRecord('physical_params', key, parseFloat(e.target.value))}
                  className="w-24 px-2 py-1 bg-[#111827] border border-[#2a3d5a] rounded text-white text-sm focus:border-purple-500 focus:outline-none"
                />
                <button
                  onClick={() => removeField('physical_params', key)}
                  className="text-red-400 hover:text-red-300 text-xs px-1"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-gray-500 italic">无物理参数（LLM 未从代码中提取）</p>
        )}
      </div>

      {/* Initial State - 自动从 state_names 同步 */}
      <div className="space-y-3 pt-3 border-t border-[#1a2d4a]">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-300">📍 初始状态 (Initial State)</label>
          <span className="text-xs text-gray-500">自动同步状态变量</span>
        </div>
        {parsedConfig.state_names && parsedConfig.state_names.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {parsedConfig.state_names.map((stateName, index) => {
              const currentValue = parsedConfig.initial_state?.[stateName] ?? 0;
              return (
                <div key={index} className="flex items-center gap-2 bg-[#0a0e17] border border-[#1a2d4a] rounded px-3 py-2">
                  <span className="text-sm text-teal-400 font-mono flex-1">{stateName}</span>
                  <input
                    type="number"
                    step="0.1"
                    value={currentValue}
                    onChange={(e) => updateRecord('initial_state', stateName, parseFloat(e.target.value))}
                    className="w-24 px-2 py-1 bg-[#111827] border border-[#2a3d5a] rounded text-white text-sm focus:border-teal-500 focus:outline-none"
                  />
                </div>
              );
            })}
          </div>
        ) : (
          <p className="text-xs text-gray-500 italic">请先添加状态变量</p>
        )}
        <p className="text-xs text-gray-500">💡 初始状态变量名自动从上方"状态变量"同步，修改状态变量名会自动更新此处</p>
      </div>

      {/* Target Values - 手动配置，不强制同步状态变量 */}
      <div className="space-y-3 pt-3 border-t border-[#1a2d4a]">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-gray-300">🎯 目标值 (Target Values)</label>
          <button
            onClick={() => addField('target_values')}
            className="text-xs px-2 py-1 bg-orange-600/20 border border-orange-500/50 text-orange-400 rounded hover:bg-orange-600/40"
          >
            + 添加目标
          </button>
        </div>
        <p className="text-xs text-gray-500">💡 仅添加需要跟踪的目标状态，某些状态（如中间变量）可能不需要目标值</p>
        {Object.keys(parsedConfig.target_values || {}).length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(parsedConfig.target_values).map(([key, value]) => (
              <div key={key} className="flex items-center gap-2 bg-[#0a0e17] border border-[#1a2d4a] rounded px-3 py-2">
                <input
                  type="text"
                  value={key}
                  onChange={(e) => {
                    const newTargets = { ...parsedConfig.target_values };
                    const val = newTargets[key];
                    delete newTargets[key];
                    newTargets[e.target.value] = val;
                    updateConfig({ target_values: newTargets });
                  }}
                  className="flex-1 bg-transparent text-sm text-orange-400 font-mono focus:outline-none"
                />
                <input
                  type="number"
                  step="0.1"
                  value={value}
                  onChange={(e) => {
                    const numValue = parseFloat(e.target.value);
                    if (!isNaN(numValue)) {
                      updateRecord('target_values', key, numValue);
                    }
                  }}
                  className="w-24 px-2 py-1 bg-[#111827] border border-[#2a3d5a] rounded text-white text-sm focus:border-orange-500 focus:outline-none"
                />
                <button
                  onClick={() => removeField('target_values', key)}
                  className="text-red-400 hover:text-red-300 text-xs px-1"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-gray-500 italic">无目标值（点击"+ 添加目标"手动添加）</p>
        )}
      </div>

      {/* Cost Function Configuration */}
      <div className="space-y-3 pt-3 border-t border-[#1a2d4a]">
        <label className="text-sm font-medium text-gray-300">💰 代价函数配置 (Cost Function)</label>

        {/* Cost Function Type */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">代价函数类型</label>
          <select
            value={parsedConfig.cost_function_type || 'quadratic'}
            onChange={(e) => updateConfig({ cost_function_type: e.target.value })}
            className="w-full px-3 py-2 bg-[#0a0e17] border border-[#1a2d4a] rounded text-white text-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="quadratic">Quadratic (二次型) - 默认推荐</option>
            <option value="lqr">LQR (线性二次调节器)</option>
            <option value="custom">Custom (自定义表达式)</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">Quadratic: Σ(w_i * (x_i - target_i)²) + Σ(w_u * u²)</p>
        </div>

        {/* Cost Computation Mode - 代价计算方式 */}
        <div>
          <label className="block text-xs text-gray-500 mb-1">代价计算方式</label>
          <select
            value={parsedConfig.cost_computation || 'discrete'}
            onChange={(e) => updateConfig({ cost_computation: e.target.value })}
            className="w-full px-3 py-2 bg-[#0a0e17] border border-[#1a2d4a] rounded text-white text-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="discrete">离散求和 (Σ) - 适用于离散时间系统</option>
            <option value="integral">连续积分 (∫) - 适用于连续时间系统</option>
            <option value="both">两者都有 (∫ + 终端代价 Φ(x(T)))</option>
          </select>
          <p className="text-xs text-gray-500 mt-1">
            {parsedConfig.cost_computation === 'discrete' && 'J = Σ(cost_t) - 每步代价累加'}
            {parsedConfig.cost_computation === 'integral' && 'J = ∫cost(t)dt - 连续时间积分'}
            {parsedConfig.cost_computation === 'both' && 'J = ∫cost(t)dt + Φ(x(T)) - 积分 + 终端代价'}
          </p>
        </div>

        {/* Integration Method (仅当选择 integral 或 both 时显示) */}
        {(parsedConfig.cost_computation === 'integral' || parsedConfig.cost_computation === 'both') && (
          <div>
            <label className="block text-xs text-gray-500 mb-1">积分数值方法</label>
            <select
              value={parsedConfig.integration_method || 'trapezoidal'}
              onChange={(e) => updateConfig({ integration_method: e.target.value })}
              className="w-full px-3 py-2 bg-[#0a0e17] border border-[#1a2d4a] rounded text-white text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="trapezoidal">梯形法则 (推荐，精度高)</option>
              <option value="simpson">Simpson 法则 (更高精度)</option>
              <option value="rectangular">矩形法则 (最简单)</option>
            </select>
            <p className="text-xs text-gray-500 mt-1">积分步长自动使用 temporal.dt = {parsedConfig.temporal?.dt ?? 0.01}</p>
          </div>
        )}

        {/* Terminal Cost Expression (仅当选择 both 时显示) */}
        {parsedConfig.cost_computation === 'both' && (
          <div>
            <label className="block text-xs text-gray-500 mb-1">终端代价 Φ(x(T))</label>
            <input
              type="text"
              value={parsedConfig.terminal_cost_expression || ''}
              onChange={(e) => updateConfig({ terminal_cost_expression: e.target.value })}
              placeholder="例如: 100*(x1 - target)**2 + 10*x2**2"
              className="w-full px-3 py-2 bg-[#0a0e17] border border-[#1a2d4a] rounded text-sm font-mono text-white focus:border-blue-500 focus:outline-none"
            />
            <p className="text-xs text-gray-500 mt-1">💡 终端代价在 t=T 时刻额外添加，通常用于强调终值约束</p>
          </div>
        )}

        {/* Cost Weights - 自动从 state_names + control_names 同步 */}
        <div>
          <label className="block text-xs text-gray-500 mb-2">代价权重 (Cost Weights)</label>
          <p className="text-xs text-gray-500 mb-2">自动同步所有状态变量和控制输入，调整权重以平衡控制目标</p>

          {/* State cost weights */}
          {parsedConfig.state_names && parsedConfig.state_names.length > 0 && (
            <div className="mb-3">
              <div className="text-xs text-gray-400 mb-2">状态权重 (State Weights)</div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {parsedConfig.state_names.map((stateName, index) => {
                  const currentWeight = parsedConfig.cost_weights?.[stateName] ?? 1.0;
                  return (
                    <div key={index} className="flex items-center gap-2 bg-[#0a0e17] border border-[#1a2d4a] rounded px-3 py-2">
                      <span className="text-sm text-yellow-400 font-mono flex-1">{stateName}</span>
                      <input
                        type="number"
                        step="0.1"
                        value={currentWeight}
                        onChange={(e) => updateRecord('cost_weights', stateName, parseFloat(e.target.value))}
                        className="w-24 px-2 py-1 bg-[#111827] border border-[#2a3d5a] rounded text-white text-sm focus:border-yellow-500 focus:outline-none"
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Control cost weights */}
          {parsedConfig.control_names && parsedConfig.control_names.length > 0 && (
            <div>
              <div className="text-xs text-gray-400 mb-2">控制权重 (Control Weights) - 越小控制越激进</div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {parsedConfig.control_names.map((controlName, index) => {
                  const currentWeight = parsedConfig.cost_weights?.[controlName] ?? 0.1;
                  return (
                    <div key={index} className="flex items-center gap-2 bg-[#0a0e17] border border-[#1a2d4a] rounded px-3 py-2">
                      <span className="text-sm text-yellow-400 font-mono flex-1">{controlName}</span>
                      <input
                        type="number"
                        step="0.01"
                        value={currentWeight}
                        onChange={(e) => updateRecord('cost_weights', controlName, parseFloat(e.target.value))}
                        className="w-24 px-2 py-1 bg-[#111827] border border-[#2a3d5a] rounded text-white text-sm focus:border-yellow-500 focus:outline-none"
                      />
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {(!parsedConfig.state_names || parsedConfig.state_names.length === 0) && (
            <p className="text-xs text-gray-500 italic">请先添加状态变量</p>
          )}
        </div>

        {/* Custom Cost Expression (仅当选择 custom 类型时显示) */}
        {parsedConfig.cost_function_type === 'custom' && (
          <div>
            <label className="block text-xs text-gray-500 mb-1">自定义代价表达式</label>
            <textarea
              value={parsedConfig.cost_function_expression || ''}
              onChange={(e) => updateConfig({ cost_function_expression: e.target.value })}
              placeholder="例如: cost = 10*(x1 - target)**2 + 0.1*u1**2"
              className="w-full h-20 px-3 py-2 bg-[#0a0e17] border border-[#1a2d4a] rounded text-xs font-mono text-white focus:border-blue-500 focus:outline-none"
              spellCheck={false}
            />
            <p className="text-xs text-gray-500 mt-1">💡 表达式中可使用 state_names, control_names, target_values 中的变量</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default SceneConfigPanel;