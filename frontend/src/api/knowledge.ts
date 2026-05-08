/** 知识点 API */

import client from './client';
import type { UnifiedResponse } from '@/types/common';
import type { KnowledgeNode, KnowledgeNodeCreate, KnowledgeNodeUpdate } from '@/types/knowledge';

export async function getKnowledgeTree(stage?: string): Promise<KnowledgeNode[]> {
  const params = stage ? { stage } : undefined;
  const res = await client.get<UnifiedResponse<KnowledgeNode[]>>('/knowledge/tree', { params });
  return res.data.data ?? [];
}

export async function getSubtree(nodeId: number): Promise<{ node: KnowledgeNode; children: KnowledgeNode[] }> {
  const res = await client.get<UnifiedResponse<{ node: KnowledgeNode; children: KnowledgeNode[] }>>(
    `/knowledge/tree/${nodeId}`
  );
  return res.data.data ?? { node: {} as KnowledgeNode, children: [] };
}

export async function createKnowledgeNode(data: KnowledgeNodeCreate): Promise<KnowledgeNode> {
  const res = await client.post<UnifiedResponse<KnowledgeNode>>('/knowledge/', data);
  if (!res.data.data) throw new Error('创建知识点失败：服务器未返回数据');
  return res.data.data;
}

export async function updateKnowledgeNode(id: number, data: KnowledgeNodeUpdate): Promise<KnowledgeNode> {
  const res = await client.put<UnifiedResponse<KnowledgeNode>>(`/knowledge/${id}`, data);
  if (!res.data.data) throw new Error('更新知识点失败：服务器未返回数据');
  return res.data.data;
}

export async function deleteKnowledgeNode(id: number): Promise<void> {
  await client.delete(`/knowledge/${id}`);
}
