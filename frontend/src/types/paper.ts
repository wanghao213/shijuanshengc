/** 试卷类型定义 */

export interface PaperQuestion {
  id: number;
  paper_id: number;
  question_id: number;
  section_index: number;
  position: number;
  assigned_score: number;
}

export interface PaperSectionQuestion {
  id: number;
  content_latex: string;
  question_type: string;
  difficulty: number;
  score: number;
  options?: { label: string; content_latex: string }[] | null;
  answer_latex?: string | null;
}

export interface PaperSectionData {
  name: string;
  questions: PaperSectionQuestion[];
}

export interface PaperDetail {
  id: number;
  title: string;
  total_score: number;
  sections: PaperSectionData[];
}

export interface Paper {
  id: number;
  title: string;
  template_id: number;
  generation_params: Record<string, unknown>;
  total_score: number;
  difficulty_average: number;
  knowledge_coverage: Record<string, unknown>;
  review_status: PaperReviewStatus;
  export_path: string | null;
  questions?: PaperQuestion[];
}

export type PaperReviewStatus = 'draft' | 'reviewed' | 'approved' | 'published';

export interface PaperReviewRequest {
  status: PaperReviewStatus;
}

export const PAPER_STATUS_LABELS: Record<PaperReviewStatus, string> = {
  draft: '草稿',
  reviewed: '已审核',
  approved: '已通过',
  published: '已发布',
};

export const PAPER_STATUS_COLORS: Record<PaperReviewStatus, string> = {
  draft: 'default',
  reviewed: 'processing',
  approved: 'success',
  published: 'success',
};
