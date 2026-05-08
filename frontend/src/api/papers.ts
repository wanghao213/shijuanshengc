/** 试卷管理 API */

import client from './client';
import type { UnifiedResponse, ResponseMeta } from '@/types/common';
import type { Paper, PaperDetail, PaperReviewRequest } from '@/types/paper';

export async function listPapers(page: number = 1, pageSize: number = 20): Promise<{ data: Paper[]; meta: ResponseMeta }> {
  const res = await client.get<UnifiedResponse<Paper[]>>('/papers/', {
    params: { page, page_size: pageSize },
  });
  return { data: res.data.data ?? [], meta: res.data.meta ?? { page, page_size: pageSize, total: 0 } };
}

export async function getPaper(id: number): Promise<Paper> {
  const res = await client.get<UnifiedResponse<Paper>>(`/papers/${id}`);
  if (!res.data.data) throw new Error('获取试卷失败：服务器未返回数据');
  return res.data.data;
}

export async function getPaperDetail(id: number): Promise<PaperDetail> {
  const res = await client.get<UnifiedResponse<PaperDetail>>(`/papers/${id}/detail`);
  if (!res.data.data) throw new Error('获取试卷详情失败：服务器未返回数据');
  return res.data.data;
}

export async function reviewPaper(id: number, data: PaperReviewRequest): Promise<void> {
  await client.put(`/papers/${id}/review`, data);
}

export async function exportPaperLatex(id: number, includeAnswers: boolean = false): Promise<string> {
  const res = await client.post<UnifiedResponse<{ latex: string }>>(
    `/papers/${id}/export`,
    null,
    { params: { format: 'latex', include_answers: includeAnswers } }
  );
  return res.data.data?.latex ?? '';
}

export async function exportPaperPdf(id: number, includeAnswers: boolean = false): Promise<Blob> {
  const res = await client.post(
    `/papers/${id}/export`,
    null,
    {
      params: { format: 'pdf', include_answers: includeAnswers },
      responseType: 'blob',
    }
  );
  return res.data;
}

export async function exportPaperDocx(id: number, includeAnswers: boolean = false): Promise<Blob> {
  const res = await client.post(
    `/papers/${id}/export`,
    null,
    {
      params: { format: 'docx', include_answers: includeAnswers },
      responseType: 'blob',
    }
  );
  return res.data;
}

export async function deletePaper(id: number): Promise<void> {
  await client.delete(`/papers/${id}`);
}
