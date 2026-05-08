/** 题目类型定义 */

export interface QuestionOption {
  label: string;
  content_latex: string;
}

export interface QuestionKnowledgePoint {
  id: number;
  name: string;
  level: string;
  stage: string | null;
  grade: string | null;
}

export interface QuestionVersion {
  version_number: number;
  change_reason: string | null;
  created_at: string;
}

export interface Question {
  id: number;
  content_latex: string;
  content_plain: string;
  question_type: QuestionType;
  difficulty: number;
  score: number | null;
  answer_latex: string | null;
  solution_steps: string[] | null;
  options: QuestionOption[] | null;
  source: string | null;
  source_year: number | null;
  region: string | null;
  exam_type: string | null;
  is_ai_generated: boolean;
  review_status: ReviewStatus;
  current_version: number;
  knowledge_points: QuestionKnowledgePoint[];
  versions?: QuestionVersion[];
}

export type QuestionType = 'choice' | 'fill_blank' | 'short_answer' | 'proof' | 'comprehensive';

export type ReviewStatus = 'pending' | 'approved' | 'rejected' | 'needs_revision';

export interface QuestionCreate {
  content_latex: string;
  content_plain: string;
  question_type: QuestionType;
  difficulty: number;
  score?: number;
  answer_latex?: string;
  solution_steps?: string[];
  options?: QuestionOption[];
  source?: string;
  source_year?: number;
  region?: string;
  exam_type?: string;
  is_ai_generated?: boolean;
  review_status?: ReviewStatus;
  knowledge_point_ids?: number[];
}

export interface QuestionUpdate {
  content_latex?: string;
  content_plain?: string;
  question_type?: QuestionType;
  difficulty?: number;
  score?: number;
  answer_latex?: string;
  solution_steps?: string[];
  options?: QuestionOption[];
  source?: string;
  source_year?: number;
  region?: string;
  exam_type?: string;
  review_status?: ReviewStatus;
  change_reason?: string;
}

export interface QuestionSearchParams {
  q?: string;
  mode?: 'keyword' | 'semantic' | 'hybrid';
  stage?: string;
  grade?: string;
  question_type?: QuestionType;
  difficulty_min?: number;
  difficulty_max?: number;
  knowledge_id?: number;
  source?: string;
  review_status?: ReviewStatus;
}

export const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  choice: '选择题',
  fill_blank: '填空题',
  short_answer: '解答题',
  proof: '证明题',
  comprehensive: '综合题',
};

export const QUESTION_TYPE_COLORS: Record<QuestionType, string> = {
  choice: 'blue',
  fill_blank: 'green',
  short_answer: 'orange',
  proof: 'purple',
  comprehensive: 'red',
};

export const REVIEW_STATUS_LABELS: Record<ReviewStatus, string> = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已拒绝',
  needs_revision: '需修改',
};
