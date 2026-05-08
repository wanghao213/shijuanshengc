/** OCR 识别状态管理 */

import { create } from 'zustand';
import type { OCRResultData, OCRProcessRequest } from '@/api/ocr';
import * as api from '@/api/ocr';

interface OCRUploadMetadata {
  source?: string;
  source_year?: number;
  region?: string;
  exam_type?: string;
  auto_tag?: boolean;
}

interface OCRState {
  result: OCRResultData | null;
  loading: boolean;
  mode: 'text' | 'file';

  setMode: (mode: 'text' | 'file') => void;
  processText: (data: OCRProcessRequest) => Promise<OCRResultData>;
  uploadDocument: (file: File, metadata?: OCRUploadMetadata) => Promise<OCRResultData>;
  clearResult: () => void;
}

export const useOcrStore = create<OCRState>((set) => ({
  result: null,
  loading: false,
  mode: 'text',

  setMode: (mode) => set({ mode }),

  processText: async (data) => {
    set({ loading: true, result: null });
    try {
      const result = await api.processText(data);
      set({ result });
      return result;
    } finally {
      set({ loading: false });
    }
  },

  uploadDocument: async (file: File, metadata?: OCRUploadMetadata) => {
    set({ loading: true, result: null });
    try {
      const result = await api.uploadDocument(file, metadata);
      set({ result });
      return result;
    } finally {
      set({ loading: false });
    }
  },

  clearResult: () => set({ result: null }),
}));
