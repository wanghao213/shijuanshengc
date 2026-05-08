/** 试卷生成 API */

import client from './client';
import type { UnifiedResponse, ResponseMeta } from '@/types/common';
import type { GenerationRequest, GenerationTaskStatus } from '@/types/generation';

export async function startGeneration(request: GenerationRequest): Promise<GenerationTaskStatus> {
  const res = await client.post<UnifiedResponse<GenerationTaskStatus>>('/generation/generate', request);
  if (!res.data.data) throw new Error('生成任务创建失败：服务器未返回数据');
  return res.data.data;
}

export async function getTaskStatus(taskId: string | number): Promise<GenerationTaskStatus> {
  const res = await client.get<UnifiedResponse<GenerationTaskStatus>>(`/generation/tasks/${taskId}`);
  if (!res.data.data) throw new Error('获取任务状态失败：服务器未返回数据');
  return res.data.data;
}

export async function listTasks(page: number = 1, pageSize: number = 20): Promise<{ data: GenerationTaskStatus[]; meta: ResponseMeta }> {
  const res = await client.get<UnifiedResponse<GenerationTaskStatus[]>>('/generation/tasks', {
    params: { page, page_size: pageSize },
  });
  return { data: res.data.data ?? [], meta: res.data.meta ?? { page, page_size: pageSize, total: 0 } };
}
