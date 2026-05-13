/** 题目状态管理 - 支持细粒度订阅优化 */

import { create } from 'zustand';
import { shallow } from 'zustand/shallow';
import type { Question } from '@/types/question';
import type { ResponseMeta } from '@/types/common';
import * as api from '@/api/questions';

interface QuestionStats {
  total: number;
  by_type: Record<string, number>;
  monthly_new: number;
  ai_ratio: number;
  total_papers: number;
}

interface QuestionListParams {
  page?: number;
  page_size?: number;
  stage?: string;
  grade?: string;
  question_type?: string;
  difficulty_min?: number;
  difficulty_max?: number;
  review_status?: string;
  q?: string;
  mode?: string;
}

interface QuestionState {
  questions: Question[];
  meta: ResponseMeta;
  loading: boolean;
  statsLoading: boolean;
  currentQuestion: Question | null;
  stats: QuestionStats;

  fetchQuestions: (params?: QuestionListParams) => Promise<void>;
  fetchQuestion: (id: number) => Promise<void>;
  deleteQuestion: (id: number) => Promise<void>;
  fetchStats: () => Promise<void>;
}

export const useQuestionStore = create<QuestionState>((set) => ({
  questions: [],
  meta: { page: 1, page_size: 20, total: 0 },
  loading: false,
  statsLoading: false,
  currentQuestion: null,
  stats: { total: 0, by_type: {}, monthly_new: 0, ai_ratio: 0, total_papers: 0 },

  fetchQuestions: async (params = {}) => {
    set({ loading: true });
    try {
      const { data, meta } = await api.listQuestions(params);
      set({ questions: data, meta });
    } finally {
      set({ loading: false });
    }
  },

  fetchQuestion: async (id: number) => {
    set({ loading: true });
    try {
      const question = await api.getQuestion(id);
      set({ currentQuestion: question });
    } finally {
      set({ loading: false });
    }
  },

  deleteQuestion: async (id: number) => {
    await api.deleteQuestion(id);
    set((s) => ({ questions: s.questions.filter((q) => q.id !== id) }));
  },

  fetchStats: async () => {
    set({ statsLoading: true });
    try {
      const stats = await api.getQuestionStats();
      set({ stats });
    } finally {
      set({ statsLoading: false });
    }
  },
}));

// 导出细粒度选择器，避免不必要的重渲染
export const useQuestions = () => useQuestionStore((state) => state.questions, shallow);
export const useQuestionMeta = () => useQuestionStore((state) => state.meta, shallow);
export const useQuestionLoading = () => useQuestionStore((state) => state.loading);
export const useCurrentQuestion = () => useQuestionStore((state) => state.currentQuestion, shallow);
export const useQuestionStats = () => useQuestionStore((state) => state.stats, shallow);
