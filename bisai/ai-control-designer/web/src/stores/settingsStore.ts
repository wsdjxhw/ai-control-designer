import { create } from 'zustand';
import { SystemSettings } from '@/types/api';
import { getSettings, updateSettings as apiUpdateSettings } from '@/api/client';

interface SettingsStore {
  settings: SystemSettings | null;
  loading: boolean;
  error: string | null;
  fetchSettings: () => Promise<void>;
  updateSettings: (data: Partial<SystemSettings>) => Promise<void>;
}

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  settings: null,
  loading: false,
  error: null,

  fetchSettings: async () => {
    set({ loading: true, error: null });
    try {
      const settings = await getSettings();
      set({ settings, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  updateSettings: async (data) => {
    set({ loading: true, error: null });
    try {
      const updated = await apiUpdateSettings(data);
      set({ settings: updated, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  },
}));