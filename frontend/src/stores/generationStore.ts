/** 试卷生成状态管理 */

import { create } from 'zustand';
import type { GenerationTaskStatus, GenerationWsMessage, GenerationCustomParams } from '@/types/generation';
import { connectGenerationWs } from '@/api/ws';
import * as api from '@/api/generation';

interface GenerationState {
  currentTask: GenerationTaskStatus | null;
  wsMessages: GenerationWsMessage[];
  loading: boolean;
  ws: WebSocket | null;

  startGeneration: (templateId: number, params?: GenerationCustomParams) => Promise<string>;
  fetchTaskStatus: (taskId: string | number) => Promise<void>;
  connectWs: (taskId: string | number) => void;
  disconnectWs: () => void;
  clearMessages: () => void;
}

export const useGenerationStore = create<GenerationState>((set, get) => ({
  currentTask: null,
  wsMessages: [],
  loading: false,
  ws: null,

  startGeneration: async (templateId: number, params?: GenerationCustomParams) => {
    set({ loading: true });
    try {
      const task = await api.startGeneration({
        template_id: templateId,
        custom_params: params,
      });
      set({ currentTask: task });
      return task.task_id;
    } finally {
      set({ loading: false });
    }
  },

  fetchTaskStatus: async (taskId: string | number) => {
    const task = await api.getTaskStatus(taskId);
    set({ currentTask: task });
  },

  connectWs: (taskId: string | number) => {
    const existing = get().ws;
    if (existing) {
      existing.close();
    }

    const ws = connectGenerationWs(taskId, (message) => {
      set((s) => ({
        wsMessages: [...s.wsMessages.slice(-49), message],
        currentTask: s.currentTask
          ? { ...s.currentTask, status: message.status, progress_pct: message.progress_pct, current_step: message.current_step }
          : null,
      }));
    });

    set({ ws });
  },

  disconnectWs: () => {
    const ws = get().ws;
    if (ws) {
      ws.close();
      set({ ws: null });
    }
  },

  clearMessages: () => set({ wsMessages: [] }),
}));
