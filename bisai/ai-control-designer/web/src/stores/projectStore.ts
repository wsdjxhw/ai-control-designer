import { create } from 'zustand';
import { Project, CreateProjectPayload } from '@/types/api';
import {
  getProjects,
  getProject,
  createProject as apiCreateProject,
  updateProject as apiUpdateProject,
  deleteProject as apiDeleteProject,
} from '@/api/client';

interface ProjectStore {
  projects: Project[];
  currentProject: Project | null;
  loading: boolean;
  error: string | null;
  fetchProjects: () => Promise<void>;
  fetchProject: (id: string) => Promise<void>;
  createProject: (data: CreateProjectPayload) => Promise<Project>;
  updateProject: (id: string, data: Partial<Project>) => Promise<Project>;
  deleteProject: (id: string) => Promise<void>;
  setCurrentProject: (project: Project | null) => void;
  clearError: () => void;
}

export const useProjectStore = create<ProjectStore>((set, get) => ({
  projects: [],
  currentProject: null,
  loading: false,
  error: null,

  fetchProjects: async () => {
    set({ loading: true, error: null });
    try {
      const projects = await getProjects();
      set({ projects, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  fetchProject: async (id: string) => {
    set({ loading: true, error: null });
    try {
      const project = await getProject(id);
      set({ currentProject: project, loading: false });
    } catch (err: any) {
      set({ error: err.message, loading: false });
    }
  },

  createProject: async (data) => {
    set({ loading: true, error: null });
    try {
      const project = await apiCreateProject(data);
      set((state) => ({
        projects: [...state.projects, project],
        loading: false,
      }));
      return project;
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  },

  updateProject: async (id, data) => {
    set({ loading: true, error: null });
    try {
      const updated = await apiUpdateProject(id, data);
      set((state) => ({
        projects: state.projects.map((p) =>
          p.project_id === id ? updated : p
        ),
        currentProject:
          state.currentProject?.project_id === id ? updated : state.currentProject,
        loading: false,
      }));
      return updated;
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  },

  deleteProject: async (id) => {
    set({ loading: true, error: null });
    try {
      await apiDeleteProject(id);
      set((state) => ({
        projects: state.projects.filter((p) => p.project_id !== id),
        loading: false,
      }));
    } catch (err: any) {
      set({ error: err.message, loading: false });
      throw err;
    }
  },

  setCurrentProject: (project) => set({ currentProject: project }),
  clearError: () => set({ error: null }),
}));