/** 试卷大题区块组件 */

import { Typography, Space, Tag } from 'antd';
import MathRenderer from './MathRenderer';
import type { PaperSectionQuestion } from '@/types/paper';

const { Title, Text } = Typography;

interface PaperSectionProps {
  name: string;
  questions: PaperSectionQuestion[];
  showAnswers?: boolean;
  onReplaceQuestion?: (position: number) => void;
}

export default function PaperSection({ name, questions, showAnswers, onReplaceQuestion }: PaperSectionProps) {
  return (
    <div style={{ marginBottom: 32 }}>
      <Title level={4}>{name}</Title>
      {questions.map((q, idx) => (
        <div
          key={q.id}
          style={{ marginBottom: 16, padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}
        >
          <Space>
            <Text strong>{idx + 1}.</Text>
            {q.score > 0 && <Tag color="blue">{q.score}分</Tag>}
          </Space>
          <div style={{ marginTop: 4 }}>
            <MathRenderer content={q.content_latex} />
          </div>

          {/* 选择题选项 */}
          {q.options && q.options.length > 0 && (
            <div style={{ marginLeft: 24, marginTop: 8 }}>
              <Space wrap>
                {q.options.map((opt) => (
                  <span key={opt.label}>
                    <Text strong>{opt.label}.</Text>{' '}
                    <MathRenderer content={opt.content_latex} />
                  </span>
                ))}
              </Space>
            </div>
          )}

          {/* 答案（可选显示） */}
          {showAnswers && q.answer_latex && (
            <div style={{ marginTop: 8, padding: '4px 8px', background: '#f6ffed', borderRadius: 4 }}>
              <Text type="secondary">答案：</Text>
              <MathRenderer content={q.answer_latex} />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
