/** 题目卡片组件 */

import { Card, Tag, Space, Button, Popconfirm } from 'antd';
import { EyeOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import MathRenderer from './MathRenderer';
import DifficultyBadge from './DifficultyBadge';
import KnowledgeTag from './KnowledgeTag';
import { QUESTION_TYPE_LABELS, QUESTION_TYPE_COLORS } from '@/types/question';
import type { Question, QuestionType } from '@/types/question';

interface QuestionCardProps {
  question: Question;
  onDelete?: (id: number) => void;
}

export default function QuestionCard({ question, onDelete }: QuestionCardProps) {
  const navigate = useNavigate();

  return (
    <Card
      size="small"
      hoverable
      actions={[
        <Button key="view" type="link" icon={<EyeOutlined />} onClick={() => navigate(`/questions/${question.id}`)}>
          查看
        </Button>,
        <Button key="edit" type="link" icon={<EditOutlined />} onClick={() => navigate(`/questions/${question.id}`)}>
          编辑
        </Button>,
        onDelete ? (
          <Popconfirm
            key="delete"
            title="确认删除此题目？"
            onConfirm={() => onDelete(question.id)}
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        ) : null,
      ].filter(Boolean)}
    >
      <Space direction="vertical" style={{ width: '100%' }}>
        <Space>
          <Tag color={QUESTION_TYPE_COLORS[question.question_type as QuestionType] || 'default'}>
            {QUESTION_TYPE_LABELS[question.question_type as QuestionType] || question.question_type}
          </Tag>
          <DifficultyBadge value={question.difficulty} />
          {question.source && <Tag>{question.source}</Tag>}
        </Space>

        <div style={{ maxHeight: 80, overflow: 'hidden' }}>
          <MathRenderer content={question.content_latex} maxLength={200} />
        </div>

        {question.knowledge_points.length > 0 && (
          <Space size={[0, 4]} wrap>
            {question.knowledge_points.map((kp) => (
              <KnowledgeTag key={kp.id} name={kp.name} />
            ))}
          </Space>
        )}
      </Space>
    </Card>
  );
}
