/** 试卷生成类型定义 */

export interface GenerationCustomParams {
  difficulty_target?: number;
  knowledge_focus?: string[];
  avoid_question_ids?: number[];
  prefer_real_questions?: boolean;
  allow_ai_generation?: boolean;
  count?: number;
  title_override?: string;
}

export interface GenerationRequest {
  template_id: number;
  custom_params?: GenerationCustomParams;
}

export type GenerationStatus =
  | 'pending'
  | 'planning'
  | 'retrieving'
  | 'generating'
  | 'validating'
  | 'assembling'
  | 'completed'
  | 'failed';

export interface GenerationTaskStatus {
  task_id: string;
  status: GenerationStatus;
  current_step: string | null;
  progress_pct: number;
  paper_id: number | null;
  error_message: string | null;
  created_at: string | null;
}

export interface GenerationWsMessage {
  task_id: string;
  status: GenerationStatus;
  current_step: string | null;
  progress_pct: number;
  detail: Record<string, unknown> | null;
  timestamp: string;
}

export const GENERATION_STATUS_LABELS: Record<GenerationStatus, string> = {
  pending: '等待中',
  planning: '规划中',
  retrieving: '检索中',
  generating: '生成中',
  validating: '验证中',
  assembling: '组装中',
  completed: '已完成',
  failed: '失败',
};

export const AGENT_STEPS = [
  { key: 'planning', label: '规划', icon: '📋' },
  { key: 'retrieving', label: '检索', icon: '🔍' },
  { key: 'generating', label: '生成', icon: '✨' },
  { key: 'validating', label: '验证', icon: '✅' },
  { key: 'assembling', label: '组装', icon: '📦' },
] as const;
