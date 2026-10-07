import axios from 'axios';
import {
  Project,
  CreateProjectPayload,
  TaskStatus,
  EvolutionVersion,
  SystemSettings,
  SceneConfig,
  RagSearchResult,
} from '@/types/api';

// 创建 axios 实例
const api = axios.create({
  baseURL: '/api/v1', // Vite 代理会转发到 http://localhost:8000
  timeout: 6000000,   // ← 10 分钟，演化密集跑时够用
  headers: {
    'Content-Type': 'application/json',
  },
});

// 响应拦截器：统一处理错误
api.interceptors.response.use(
  (response) => response.data,
  (error) => {
    let message: string;
    const detail = error.response?.data?.detail;

    if (typeof detail === 'string') {
      message = detail;
    } else if (Array.isArray(detail)) {
      // Pydantic 422 错误：detail 是数组
      message = detail.map((e: any) => {
        const loc = Array.isArray(e.loc) ? e.loc.join('.') : '';
        return `${loc}: ${e.msg}`;
      }).join('; ');
    } else if (detail) {
      message = JSON.stringify(detail);
    } else {
      message = error.message || '请求失败';
    }

    console.error('[API Error]', message);
    return Promise.reject(new Error(message));
  }
);

// ========== 项目管理 ==========
export const createProject = (data: CreateProjectPayload): Promise<Project> =>
  api.post('/projects', data);

export const getProjects = (): Promise<Project[]> => api.get('/projects');

export const getProject = (id: string): Promise<Project> =>
  api.get(`/projects/${id}`);

export interface ProjectVersion {
  version: number;
  cost: number | null;
  has_params: boolean;
  has_diagnosis: boolean;
}

export const listProjectVersions = (
  projectId: string
): Promise<{ project_id: string; current_version: number; versions: ProjectVersion[] }> =>
  api.get(`/projects/${projectId}/versions`);

export const getActiveRun = (
  projectId: string
): Promise<{ active: boolean; run_id: string | null }> =>
  api.get(`/projects/${projectId}/active-run`);

export const getLatestRun = (
  projectId: string
): Promise<{ has_run: boolean; run_id: string | null; status: string | null }> =>
  api.get(`/projects/${projectId}/latest-run`);

// 🆕 基线评估相关
export interface BaselineInfo {
  type: string;
  control_law_code: string;
  params: Record<string, number>;
  cost: number;
}

export const reevaluateBaseline = (
  projectId: string,
  params: Record<string, number>
): Promise<{ success: boolean; baseline: BaselineInfo }> =>
  api.post(`/projects/${projectId}/baseline/reevaluate`, { params });

export interface ProjectVersionDetail {
  project_id: string;
  version: number;
  best_params: Record<string, number>;
  diagnosis: string;
  code: string;
  total_cost: number | null;
}

export const getProjectVersionDetail = (
  projectId: string,
  version: number
): Promise<ProjectVersionDetail> =>
  api.get(`/projects/${projectId}/versions/${version}`);


export const updateProject = (id: string, data: Partial<Project>): Promise<Project> =>
  api.put(`/projects/${id}`, data);

export const deleteProject = (id: string): Promise<void> =>
  api.delete(`/projects/${id}`);

// ========== 演化控制 ==========
export const startEvolution = (
  projectId: string,
  maxIterations?: number,
  startVersion?: number
): Promise<{ run_id: string }> =>
  api.post(`/projects/${projectId}/evolution/start`, {
    max_iterations: maxIterations || 3,
    start_version: startVersion ?? null,
  });

export const stopEvolution = (
  taskId: string
): Promise<{ run_id: string; message: string; note?: string }> =>
  api.post(`/evolution/${taskId}/stop`);

export const getTaskStatus = (taskId: string): Promise<TaskStatus> =>
  api.get(`/evolution/${taskId}/status`);

export const getVersions = (taskId: string): Promise<EvolutionVersion[]> =>
  api.get(`/evolution/${taskId}/versions`).then((res: any) => {
    // 后端返回 [{run_id, version, status, total_cost, started_at, completed_at}]
    // 转成 EvolutionView 期望的 EvolutionVersion 结构
    return (res || []).map((r: any) => ({
      run_id: r.run_id,
      version: r.version ?? 1,
      status: r.status,
      total_cost: r.total_cost,
      params: r.best_params || {},
      deviations: r.deviations || {},
      anomalies: r.anomalies || [],
      diagnostic_report: '',
      code: '',
      timestamp: r.started_at || r.completed_at || '',
    }));
  });

export const getVersionDetail = (
  taskId: string,
  version: number
): Promise<EvolutionVersion> =>
  api.get(`/evolution/${taskId}/versions/${version}`).then((res: any) => {
    // 后端字段：best_params / diagnosis
    // 前端字段：params / diagnostic_report
    return {
      run_id: res.run_id,
      version: res.version ?? version,
      status: res.status,
      total_cost: res.total_cost,
      params: res.best_params || {},
      deviations: res.deviations || {},
      anomalies: res.anomalies || [],
      diagnostic_report: res.diagnosis || '',
      code: res.code || '',
      timestamp: res.started_at || res.completed_at || '',
    };
  });

export const getCompareData = (
  taskId: string
): Promise<{
  versions: number[];
  costs: number[];
  deviations: Record<string, number[]>;
}> =>
  api.get(`/evolution/${taskId}/compare`).then((res: any) => {
    // 后端返回 { project_id, versions: [{version, cost, param_count}] }
    // 转成 ECharts 期望的 { versions: number[], costs: number[] }
    const raw = res?.versions ?? [];
    return {
      versions: raw.map((v: any) => v.version),
      costs: raw.map((v: any) => v.cost),
      deviations: {},
    };
  });

// ========== 诊断 & 策略解析 ==========
export const getDiagnosis = (
  taskId: string,
  version: number
): Promise<{
  run_id: string;
  project_id: string;
  version: number;
  diagnosis: string;
}> =>
  api.get(`/evolution/${taskId}/versions/${version}/diagnosis`);


export const parseStrategy = (
  code: string,
  params: Record<string, number>
): Promise<{
  description: string;
  key_mechanisms: string[];
  parameter_effects: Record<string, string>;
}> =>
  api.post('/llm/parse-strategy', { control_code: code, params });

// ========== RAG 策略库 ==========
export const searchStrategies = (
  query: string,
  top_k = 5,
  filters?: Record<string, any>
): Promise<{ strategies: RagSearchResult[] }> =>
  api.post('/rag/search', { query, top_k, filters }).then((res: any) => {
    // 后端返回 { results: [...] }，前端期望 { strategies: [...] }
    return { strategies: res?.results ?? [] };
  });

export const storeStrategy = (
  code: string,
  metadata: Record<string, any>
): Promise<void> => {
  // 自动生成策略 ID（若 metadata 里已有 id 就用，否则用 domain + timestamp）
  const id = metadata.id
    || `${metadata.domain || 'strategy'}_v${metadata.version || 0}_${Date.now()}`;
  return api.post('/rag/store', { id, code, metadata });
};

export const listStrategies = (limit: number = 100): Promise<{ results: RagSearchResult[]; count: number }> =>
  api.get(`/rag/list?limit=${limit}`);


export const deleteStrategy = (id: string): Promise<{ success: boolean; message: string }> =>
  api.post('/rag/delete', { id });

// ========== 系统设置 ==========
export const getSettings = (): Promise<SystemSettings> =>
  api.get('/system/settings');

// ========== 专家模式文件解析 ==========
export interface ParseExpertFilesRequest {
  model_code: string;
  parameters?: Record<string, any>;
  env_config?: Record<string, any>;
  description?: string;
}

export interface ParseExpertFilesResponse {
  scene_config_complete: Record<string, any>;
  control_law_code: string;
  warnings?: string[];
}

export const parseExpertFiles = (
  data: ParseExpertFilesRequest
): Promise<ParseExpertFilesResponse> => api.post('/llm/parse-expert-files', data);

export interface ParseSingleModelRequest {
  model_code: string;
  description?: string;
}

export interface ParseSingleModelResponse {
  scene_config_extracted: Record<string, any>;
  control_law_code: string;
  extraction_log?: string[];
  warnings?: string[];
  type_detection?: {
    model_type: 'ode' | 'pde' | 'unknown';
    confidence: number;
    evidence: string[];
    user_can_override: boolean;
  };
}

export const parseSingleModel = (
  data: ParseSingleModelRequest
): Promise<ParseSingleModelResponse> => api.post('/llm/parse-single-model', data);

export const updateSettings = (
  settings: Partial<SystemSettings>
): Promise<SystemSettings> => api.put('/system/settings', settings);

// ========== 新手模式 ==========
export const generateScene = (
  description: string
): Promise<{
  scene_config: SceneConfig;
  model_code: string;
  cost_function_code: string;
}> => api.post('/llm/generate-scene', { user_description: description });

// ========== 专家模式：LLM 生成初始控制律 ==========
export const generateControlLaw = (payload: {
  model_code: string;
  scene_config: any;
  description?: string;
}): Promise<{ control_law_code: string }> =>
  api.post('/llm/generate-control-law', payload);

export const validatePhysics = (
  modelCode: string,
  sceneConfig: SceneConfig
): Promise<{
  L1: boolean;
  L2: boolean;
  L3: boolean;
  details: string;
}> => api.post('/llm/validate-physics', {
  model_code: modelCode,
  scene_config: sceneConfig,
});

// ========== 专家模式：model.py 代码验证 ==========
export const validateModel = (modelCode: string): Promise<{
  valid: boolean;
  errors: string[];
  warnings: string[];
}> => api.post('/llm/validate-model', { model_code: modelCode });

// ========== 专家模式：自定义求解器验证 ==========
export const validateCustomSolver = (code: string): Promise<{
  valid: boolean;
  errors: string[];
  warnings: string[];
}> => api.post('/llm/validate-custom-solver', { code });