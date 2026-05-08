/** 题目 API */

import client from './client';
import type { UnifiedResponse, ResponseMeta } from '@/types/common';
import type { Question, QuestionCreate, QuestionUpdate } from '@/types/question';

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

export async function listQuestions(params: QuestionListParams = {}): Promise<{ data: Question[]; meta: ResponseMeta }> {
  const { q, mode, ...rest } = params;
  if (q && q.trim()) {
    const searchRes = await searchQuestions(q, mode || 'keyword', 100);
    return { data: searchRes, meta: { page: 1, page_size: 100, total: searchRes.length } };
  }
  const res = await client.get<UnifiedResponse<Question[]>>('/questions/', { params: rest });
  return { data: res.data.data ?? [], meta: res.data.meta ?? { page: rest.page ?? 1, page_size: rest.page_size ?? 20, total: 0 } };
}

export async function getQuestion(id: number): Promise<Question> {
  const res = await client.get<UnifiedResponse<Question>>(`/questions/${id}`);
  if (!res.data.data) throw new Error('获取题目失败：服务器未返回数据');
  return res.data.data;
}

export async function createQuestion(data: QuestionCreate): Promise<Question> {
  const res = await client.post<UnifiedResponse<Question>>('/questions/', data);
  if (!res.data.data) throw new Error('创建题目失败：服务器未返回数据');
  return res.data.data;
}

export async function updateQuestion(id: number, data: QuestionUpdate): Promise<Question> {
  const res = await client.put<UnifiedResponse<Question>>(`/questions/${id}`, data);
  if (!res.data.data) throw new Error('更新题目失败：服务器未返回数据');
  return res.data.data;
}

export async function deleteQuestion(id: number): Promise<void> {
  await client.delete(`/questions/${id}`);
}

export async function searchQuestions(q: string, mode: string = 'keyword', limit: number = 20): Promise<Question[]> {
  const res = await client.get<UnifiedResponse<Question[]>>('/questions/search', {
    params: { q, mode, limit },
  });
  return res.data.data ?? [];
}

export async function getQuestionStats(): Promise<{ total: number; by_type: Record<string, number>; monthly_new: number; ai_ratio: number; total_papers: number }> {
  const res = await client.get<UnifiedResponse<{ total: number; by_type: Record<string, number>; monthly_new: number; ai_ratio: number; total_papers: number }>>('/questions/stats');
  return res.data.data ?? { total: 0, by_type: {}, monthly_new: 0, ai_ratio: 0, total_papers: 0 };
}

export async function findSimilarQuestions(id: number, threshold: number = 0.92): Promise<Question[]> {
  const res = await client.get<UnifiedResponse<Question[]>>(`/questions/similar/${id}`, {
    params: { threshold },
  });
  return res.data.data ?? [];
}

export async function batchImport(questions: QuestionCreate[]): Promise<{ imported_count: number }> {
  const res = await client.post<UnifiedResponse<{ imported_count: number }>>('/questions/batch-import', { questions });
  return res.data.data ?? { imported_count: 0 };
}

export async function generateEmbedding(questionId: number): Promise<void> {
  await client.post(`/questions/${questionId}/embedding`);
}

export async function batchEmbedding(questionIds: number[]): Promise<void> {
  await client.post('/questions/batch-embedding', questionIds);
}
