/** 试卷大题区块组件 - 支持虚拟滚动优化 */

import { Typography, Space, Tag } from 'antd';
import { FixedSizeList as List } from 'react-window';
import MathRenderer from './MathRenderer';
import type { PaperSectionQuestion } from '@/types/paper';
import { useCallback, useMemo, memo } from 'react';

const { Title, Text } = Typography;

interface PaperSectionProps {
  name: string;
  questions: PaperSectionQuestion[];
  showAnswers?: boolean;
  onReplaceQuestion?: (position: number) => void;
}

// 单个题目渲染组件 - 使用 React.memo 避免不必要的重渲染
const QuestionItem = memo(({ 
  index, 
  question, 
  showAnswers 
}: { 
  index: number; 
  question: PaperSectionQuestion; 
  showAnswers: boolean;
}) => {
  return (
    <div
      style={{ marginBottom: 16, padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}
    >
      <Space>
        <Text strong>{index + 1}.</Text>
        {question.score > 0 && <Tag color="blue">{question.score}分</Tag>}
      </Space>
      <div style={{ marginTop: 4 }}>
        <MathRenderer content={question.content_latex} />
      </div>

      {/* 选择题选项 */}
      {question.options && question.options.length > 0 && (
        <div style={{ marginLeft: 24, marginTop: 8 }}>
          <Space wrap>
            {question.options.map((opt) => (
              <span key={opt.label}>
                <Text strong>{opt.label}.</Text>{' '}
                <MathRenderer content={opt.content_latex} />
              </span>
            ))}
          </Space>
        </div>
      )}

      {/* 答案（可选显示） */}
      {showAnswers && question.answer_latex && (
        <div style={{ marginTop: 8, padding: '4px 8px', background: '#f6ffed', borderRadius: 4 }}>
          <Text type="secondary">答案：</Text>
          <MathRenderer content={question.answer_latex} />
        </div>
      )}
    </div>
  );
}, (prev, next) => {
  return prev.question === next.question && prev.showAnswers === next.showAnswers;
});

export default function PaperSection({ name, questions, showAnswers, onReplaceQuestion }: PaperSectionProps) {
  // 使用 useMemo 缓存题目列表
  const itemCount = useMemo(() => questions.length, [questions]);
  
  // 虚拟滚动行渲染器
  const Row = useCallback(({ index, style }: { index: number; style: React.CSSProperties }) => (
    <div style={style}>
      <QuestionItem
        index={index}
        question={questions[index]}
        showAnswers={!!showAnswers}
      />
    </div>
  ), [questions, showAnswers]);

  // 对于少量题目，直接渲染；大量题目使用虚拟滚动
  if (itemCount <= 10) {
    return (
      <div style={{ marginBottom: 32 }}>
        <Title level={4}>{name}</Title>
        {questions.map((q, idx) => (
          <QuestionItem
            key={q.id}
            index={idx}
            question={q}
            showAnswers={!!showAnswers}
          />
        ))}
      </div>
    );
  }

  return (
    <div style={{ marginBottom: 32 }}>
      <Title level={4}>{name}</Title>
      <div style={{ maxHeight: '70vh', overflow: 'auto' }}>
        <List
          height={Math.min(itemCount * 150, 800)}
          itemCount={itemCount}
          itemSize={150}
          width="100%"
        >
          {Row}
        </List>
      </div>
    </div>
  );
}
