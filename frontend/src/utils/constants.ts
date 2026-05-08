/** 常量定义 */

export const STAGES = ['小学', '初中', '高中'] as const;

export const GRADES: Record<string, string[]> = {
  小学: ['一年级', '二年级', '三年级', '四年级', '五年级', '六年级'],
  初中: ['初一', '初二', '初三'],
  高中: ['高一', '高二', '高三'],
};

export const QUESTION_TYPES = [
  { value: 'choice', label: '选择题' },
  { value: 'fill_blank', label: '填空题' },
  { value: 'short_answer', label: '解答题' },
  { value: 'proof', label: '证明题' },
  { value: 'comprehensive', label: '综合题' },
] as const;

export const DIFFICULTY_LEVELS = [
  { min: 1.0, max: 2.0, label: '简单', color: '#52c41a' },
  { min: 2.0, max: 3.0, label: '中等', color: '#1890ff' },
  { min: 3.0, max: 4.0, label: '偏难', color: '#faad14' },
  { min: 4.0, max: 5.0, label: '困难', color: '#f5222d' },
] as const;

export function getDifficultyLabel(value: number): string {
  for (const level of DIFFICULTY_LEVELS) {
    if (value >= level.min && value < level.max) return level.label;
  }
  return value >= 5.0 ? '困难' : '简单';
}

export function getDifficultyColor(value: number): string {
  for (const level of DIFFICULTY_LEVELS) {
    if (value >= level.min && value < level.max) return level.color;
  }
  return value >= 5.0 ? '#f5222d' : '#52c41a';
}
