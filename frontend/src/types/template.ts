/** 试卷模板类型定义 */

export interface TemplateSectionKnowledge {
  required_topics: string[];
  min_coverage: number;
}

export interface TemplateSectionConstraints {
  no_repeat_source: boolean;
  min_unique_knowledge_points: number;
  max_same_source_ratio: number;
}

export interface TemplateSection {
  name: string;
  type: string;
  score: number;
  count: number;
  per_question_score: number;
  difficulty_range: [number, number];
  knowledge_requirements?: TemplateSectionKnowledge;
  constraints?: TemplateSectionConstraints;
}

export interface TemplateStructure {
  sections: TemplateSection[];
  global_constraints?: {
    total_difficulty_target?: number;
    knowledge_coverage_min?: number;
    avoid_similar_questions?: boolean;
    similarity_threshold?: number;
  };
}

export interface PaperTemplate {
  id: number;
  name: string;
  stage: string;
  grade: string;
  subject: string;
  total_score: number;
  duration_minutes: number;
  structure: TemplateStructure;
  is_default: boolean;
  description: string | null;
}

export interface TemplateCreate {
  name: string;
  stage: string;
  grade: string;
  subject?: string;
  total_score: number;
  duration_minutes: number;
  structure: TemplateStructure;
  is_default?: boolean;
  description?: string;
}

export interface TemplateUpdate {
  name?: string;
  stage?: string;
  grade?: string;
  subject?: string;
  total_score?: number;
  duration_minutes?: number;
  structure?: TemplateStructure;
  is_default?: boolean;
  description?: string;
}
