/** 知识点状态管理 */

import { create } from 'zustand';
import type { KnowledgeNode } from '@/types/knowledge';
import * as api from '@/api/knowledge';

interface KnowledgeState {
  tree: KnowledgeNode[];
  loading: boolean;
  fetchTree: (stage?: string) => Promise<void>;
  deleteNode: (id: number) => Promise<void>;
}

export const useKnowledgeStore = create<KnowledgeState>((set) => ({
  tree: [],
  loading: false,

  fetchTree: async (stage?: string) => {
    set({ loading: true });
    try {
      const tree = await api.getKnowledgeTree(stage);
      set({ tree });
    } finally {
      set({ loading: false });
    }
  },

  deleteNode: async (id: number) => {
    await api.deleteKnowledgeNode(id);
    set((s) => ({
      tree: removeNodeFromTree(s.tree, id),
    }));
  },
}));

function removeNodeFromTree(nodes: KnowledgeNode[], id: number): KnowledgeNode[] {
  return nodes
    .filter((n) => n.id !== id)
    .map((n) => ({
      ...n,
      children: n.children ? removeNodeFromTree(n.children, id) : [],
    }));
}
