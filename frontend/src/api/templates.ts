/** 试卷模板 API */

import client from './client';
import type { UnifiedResponse, ResponseMeta } from '@/types/common';
import type { PaperTemplate, TemplateCreate, TemplateUpdate } from '@/types/template';

export async function listTemplates(page: number = 1, pageSize: number = 20): Promise<{ data: PaperTemplate[]; meta: ResponseMeta }> {
  const res = await client.get<UnifiedResponse<PaperTemplate[]>>('/templates/', {
    params: { page, page_size: pageSize },
  });
  return { data: res.data.data ?? [], meta: res.data.meta ?? { page, page_size: pageSize, total: 0 } };
}

export async function getTemplate(id: number): Promise<PaperTemplate> {
  const res = await client.get<UnifiedResponse<PaperTemplate>>(`/templates/${id}`);
  if (!res.data.data) throw new Error('获取模板失败：服务器未返回数据');
  return res.data.data;
}

export async function createTemplate(data: TemplateCreate): Promise<PaperTemplate> {
  const res = await client.post<UnifiedResponse<PaperTemplate>>('/templates/', data);
  if (!res.data.data) throw new Error('创建模板失败：服务器未返回数据');
  return res.data.data;
}

export async function updateTemplate(id: number, data: TemplateUpdate): Promise<PaperTemplate> {
  const res = await client.put<UnifiedResponse<PaperTemplate>>(`/templates/${id}`, data);
  if (!res.data.data) throw new Error('更新模板失败：服务器未返回数据');
  return res.data.data;
}

export async function deleteTemplate(id: number): Promise<void> {
  await client.delete(`/templates/${id}`);
}

export async function duplicateTemplate(id: number): Promise<PaperTemplate> {
  const res = await client.post<UnifiedResponse<PaperTemplate>>(`/templates/${id}/duplicate`);
  if (!res.data.data) throw new Error('复制模板失败：服务器未返回数据');
  return res.data.data;
}
