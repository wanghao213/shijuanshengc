/** 试卷状态管理 */

import { create } from 'zustand';
import type { Paper, PaperDetail } from '@/types/paper';
import type { ResponseMeta } from '@/types/common';
import * as api from '@/api/papers';

interface PaperState {
  papers: Paper[];
  currentPaper: Paper | null;
  currentPaperDetail: PaperDetail | null;
  meta: ResponseMeta;
  loading: boolean;

  fetchPapers: (page?: number, pageSize?: number) => Promise<void>;
  fetchPaper: (id: number) => Promise<void>;
  fetchPaperDetail: (id: number) => Promise<void>;
  deletePaper: (id: number) => Promise<void>;
  exportLatex: (id: number, includeAnswers?: boolean) => Promise<string>;
  exportPdf: (id: number, includeAnswers?: boolean) => Promise<Blob>;
  exportDocx: (id: number, includeAnswers?: boolean) => Promise<Blob>;
}

export const usePaperStore = create<PaperState>((set) => ({
  papers: [],
  currentPaper: null,
  currentPaperDetail: null,
  meta: { page: 1, page_size: 20, total: 0 },
  loading: false,

  fetchPapers: async (page = 1, pageSize = 20) => {
    set({ loading: true });
    try {
      const { data, meta } = await api.listPapers(page, pageSize);
      set({ papers: data, meta });
    } finally {
      set({ loading: false });
    }
  },

  fetchPaper: async (id: number) => {
    set({ loading: true });
    try {
      const paper = await api.getPaper(id);
      set({ currentPaper: paper });
    } finally {
      set({ loading: false });
    }
  },

  fetchPaperDetail: async (id: number) => {
    set({ loading: true });
    try {
      const detail = await api.getPaperDetail(id);
      set({ currentPaperDetail: detail });
    } finally {
      set({ loading: false });
    }
  },

  deletePaper: async (id: number) => {
    await api.deletePaper(id);
    set((s) => ({ papers: s.papers.filter((p) => p.id !== id) }));
  },

  exportLatex: async (id: number, includeAnswers = false) => {
    return await api.exportPaperLatex(id, includeAnswers);
  },

  exportPdf: async (id: number, includeAnswers = false) => {
    return await api.exportPaperPdf(id, includeAnswers);
  },

  exportDocx: async (id: number, includeAnswers = false) => {
    return await api.exportPaperDocx(id, includeAnswers);
  },
}));
