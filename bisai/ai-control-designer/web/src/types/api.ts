// ========================================
// ⚠️ 重要：以下字段名基于标准 RESTful 设计猜测
// 请与后端成员（B）确认实际返回的 JSON 字段名
// 如后端使用 snake_case（如 project_id），请保持一致
// ========================================

export interface SceneConfig {
  domain: string;
  state_names: string[];
  control_names: string[];
  target_values: Record<string, number>;
  cost_weights: Record<string, number>;
  solver_type: 'rk4' | 'scipy_ode' | 'euler';
  enforce_nonnegative?: boolean;  // 🆕 是否强制状态非负
  [key: string]: any;
}

export interface Project {
  project_id: string;
  name: string;
  description: string;
  mode: 'expert' | 'newbie';
  status: 'idle' | 'running' | 'completed' | 'failed';
  current_version: number;
  best_cost: number | null;
  scene_config: SceneConfig;
  created_at: string;
  updated_at: string;
  work_dir?: string;
}

export interface EvolutionVersion {
  run_id?: string;
  project_id?: string;
  version: number;
  status?: string;
  total_cost: number | null;
  best_params?: Record<string, number>;
  params?: Record<string, number>;        // 前端兼容字段
  diagnosis?: string;
  diagnostic_report?: string;             // 前端兼容字段
  deviations?: Record<string, number>;
  anomalies?: string[];
  code?: string;
  started_at?: string;
  completed_at?: string;
  timestamp?: string;
}

export interface TaskStatus {
  run_id: string;
  project_id: string;
  /** 后端状态机：idle / running / optimizing / diagnosing / modifying / completed / failed */
  status: 'idle' | 'running' | 'optimizing' | 'diagnosing'
        | 'modifying' | 'completed' | 'failed';
  current_version: number;
  best_cost: number | null;
  message?: string;
  /** ✅ 关键字段：判断演化是否还在跑 */
  is_running: boolean;
  /** 数据库里的 run 版本号，与 current_version 可能相同 */
  version?: number;
}

export interface SystemSettings {
  llm_model: string;
  llm_base_url: string;
  llm_api_key: string;
  llm_temperature: number;
  llm_timeout: number;
  optimizer_type: 'cmaes' | 'pso' | 'tpe' | 'random' | 'grid' | 'custom';
  max_iterations: number;
}

export interface CreateProjectPayload {
  name: string;
  description: string;
  mode: 'expert' | 'newbie';
  scene_config?: SceneConfig;
  model_code?: string;
  control_v1_code?: string;
  optimizer_config?: {
    optimizer_type: string;
    popsize?: number;
    sigma0?: number;
    n_particles?: number;
    w?: number;
    c1?: number;
    c2?: number;
    max_iter?: number;
    n_startup_trials?: number;
    n_ei_candidates?: number;
    custom_optimizer_code?: string;
  };
}

export interface RagSearchResult {
  id: string;
  code: string;
  metadata: {
    domain: string;
    cost: number;
    version: string;
    [key: string]: any;
  };
  similarity: number;
}