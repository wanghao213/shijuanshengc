/** 知识点类型定义 */

export interface KnowledgeNode {
  id: number;
  name: string;
  level: 'stage' | 'grade' | 'chapter' | 'section' | 'knowledge_point';
  stage: string | null;
  grade: string | null;
  description: string | null;
  parent_id: number | null;
  materialized_path: string;
  sort_order: number;
  children: KnowledgeNode[];
}

export interface KnowledgeNodeCreate {
  name: string;
  level: string;
  stage?: string;
  grade?: string;
  description?: string;
  parent_id?: number;
  sort_order?: number;
}

export interface KnowledgeNodeUpdate {
  name?: string;
  description?: string;
  sort_order?: number;
}
