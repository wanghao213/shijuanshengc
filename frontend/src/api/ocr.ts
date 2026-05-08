/** OCR 识别 API */

import client from './client';
import type { UnifiedResponse } from '@/types/common';

export interface ExtractedQuestionData {
  number: string;
  content_latex: string;
  question_type: string;
  options: { label: string; content_latex: string }[] | null;
  answer_latex: string | null;
  knowledge_points: string[];
  estimated_difficulty: number;
}

export interface OCRResultData {
  status: string;
  raw_text: string;
  cleaned_text: string;
  questions: ExtractedQuestionData[];
  corrections: { original: string; corrected: string; reason: string }[];
  confidence: number;
  notes: string;
  error: string | null;
  saved_question_ids: number[];
}

export interface OCRProcessRequest {
  text: string;
  source?: string;
  source_year?: number;
  region?: string;
  exam_type?: string;
  auto_tag?: boolean;
}

/** 手动输入模式：文本提交 */
export async function processText(data: OCRProcessRequest): Promise<OCRResultData> {
  const res = await client.post<UnifiedResponse<OCRResultData>>('/ocr/process', data);
  if (!res.data.data) throw new Error('OCR 处理失败：服务器未返回数据');
  return res.data.data;
}

/** 文件上传模式 */
export async function uploadDocument(
  file: File,
  metadata?: {
    source?: string;
    source_year?: number;
    region?: string;
    exam_type?: string;
    auto_tag?: boolean;
  }
): Promise<OCRResultData> {
  const formData = new FormData();
  formData.append('file', file);
  if (metadata?.source) formData.append('source', metadata.source);
  if (metadata?.source_year) formData.append('source_year', String(metadata.source_year));
  if (metadata?.region) formData.append('region', metadata.region);
  if (metadata?.exam_type) formData.append('exam_type', metadata.exam_type);
  if (metadata?.auto_tag !== undefined) formData.append('auto_tag', String(metadata.auto_tag));

  const res = await client.post<UnifiedResponse<OCRResultData>>('/ocr/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000, // 5 分钟超时
  });
  if (!res.data.data) throw new Error('文件上传处理失败：服务器未返回数据');
  return res.data.data;
}
