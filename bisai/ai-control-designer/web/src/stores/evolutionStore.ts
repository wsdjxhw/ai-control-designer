import { create } from 'zustand';
import { TaskStatus, EvolutionVersion } from '@/types/api';
import {
  getTaskStatus,
  getVersions,
  getVersionDetail,
  getCompareData,
} from '@/api/client';

// ✅ 模块级计数器：每次 startPolling/stopPolling 都会 +1，
//    旧的回调检查自己的代号是否还等于当前代号，不等就直接退出
let pollingGeneration = 0;

interface EvolutionStore {
  taskId: string | null;
  status: TaskStatus | null;
  versions: EvolutionVersion[];
  currentVersion: EvolutionVersion | null;
  compareData: {
    versions: number[];
    costs: number[];
    deviations: Record<string, number[]>;
  } | null;
  pollingInterval: NodeJS.Timeout | null;
  isPolling: boolean;
  error: string | null;

  startPolling: (taskId: string) => void;
  stopPolling: () => void;
  fetchVersions: (taskId: string) => Promise<void>;
  fetchVersionDetail: (taskId: string, version: number) => Promise<void>;
  fetchCompareData: (taskId: string) => Promise<void>;
  setCurrentVersion: (version: EvolutionVersion) => void;
  clearError: () => void;
  reset: () => void;
}

export const useEvolutionStore = create<EvolutionStore>((set, get) => ({
  taskId: null,
  status: null,
  versions: [],
  currentVersion: null,
  compareData: null,
  pollingInterval: null,
  isPolling: false,
  error: null,

  startPolling: (taskId: string) => {
    // 让所有旧回调失效
    get().stopPolling();

    const myGen = ++pollingGeneration;   // 当前代号

    set({ taskId, isPolling: true, error: null });

    let hasFinished = false;

    const fetchStatus = async () => {
      // ✅ 双重防护：本地终态标志 + 全局代号校验
      if (hasFinished) return;
      if (myGen !== pollingGeneration) return;

      try {
        const status = await getTaskStatus(taskId);
        if (myGen !== pollingGeneration) return;  // 请求返回后再次检查

        // 🆕 检测 current_version 是否变化，变化时刷新 compare
        const prevVersion = get().status?.current_version ?? 0;
        const newVersion = status.current_version ?? 0;

        set({ status });

        // 🆕 演化过程中也刷新 compare，让代价曲线实时更新
        if (newVersion > 0 && newVersion !== prevVersion) {
          get().fetchCompareData(taskId).catch(() => {});
        }

        const isTerminal =
          status.is_running === false && status.status !== 'idle';

        if (isTerminal) {
          hasFinished = true;
          get().stopPolling();
          await get().fetchVersions(taskId);
          await get().fetchCompareData(taskId);
          const dbVersion = (status as any).version ?? status.current_version;
          if (dbVersion > 0) {
            await get().fetchVersionDetail(taskId, dbVersion);
          }
        }
      } catch (err: any) {
        hasFinished = true;
        set({ error: err.message });
        get().stopPolling();
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 2000);
    set({ pollingInterval: interval });
  },

  stopPolling: () => {
    pollingGeneration++;   // ✅ 让所有旧回调失效
    const { pollingInterval } = get();
    if (pollingInterval) {
      clearInterval(pollingInterval);
      set({ pollingInterval: null, isPolling: false });
    }
  },

  fetchVersions: async (taskId) => {
    try {
      const versions = await getVersions(taskId);
      set({ versions });
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  fetchVersionDetail: async (taskId, version) => {
    try {
      const detail = await getVersionDetail(taskId, version);
      set({ currentVersion: detail });
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  fetchCompareData: async (taskId) => {
    try {
      const data = await getCompareData(taskId);
      set({ compareData: data });
    } catch (err: any) {
      set({ error: err.message });
    }
  },

  setCurrentVersion: (version) => set({ currentVersion: version }),
  clearError: () => set({ error: null }),

  reset: () => {
    get().stopPolling();
    set({
      taskId: null,
      status: null,
      versions: [],
      currentVersion: null,
      compareData: null,
      isPolling: false,
      error: null,
    });
  },
}));