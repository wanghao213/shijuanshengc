/** 题目详情页 */

import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Card, Descriptions, Tag, Space, Button, Spin, Typography, message, Popconfirm, Timeline } from 'antd';
import { ArrowLeftOutlined, EditOutlined, DeleteOutlined, ExperimentOutlined } from '@ant-design/icons';
import MathRenderer from '@/components/MathRenderer';
import DifficultyBadge from '@/components/DifficultyBadge';
import KnowledgeTag from '@/components/KnowledgeTag';
import LaTeXEditor from '@/components/LaTeXEditor';
import { QUESTION_TYPE_LABELS, REVIEW_STATUS_LABELS } from '@/types/question';
import { formatDate } from '@/utils/helpers';
import { useQuestionStore } from '@/stores/questionStore';
import * as api from '@/api/questions';

const { Title, Text } = Typography;

export default function QuestionDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { currentQuestion: question, fetchQuestion, deleteQuestion, loading } = useQuestionStore();
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    if (id) fetchQuestion(Number(id));
  }, [id, fetchQuestion]);

  const handleDelete = async () => {
    if (!id) return;
    await deleteQuestion(Number(id));
    message.success('删除成功');
    navigate('/questions');
  };

  const handleGenerateEmbedding = async () => {
    if (!id) return;
    try {
      await api.generateEmbedding(Number(id));
      message.success('Embedding 生成成功');
    } catch {
      message.error('Embedding 生成失败');
    }
  };

  if (loading || !question) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/questions')}>
          返回题库
        </Button>
        <Button icon={<EditOutlined />} onClick={() => setEditing(!editing)}>
          {editing ? '取消编辑' : '编辑'}
        </Button>
        <Button icon={<ExperimentOutlined />} onClick={handleGenerateEmbedding}>
          生成 Embedding
        </Button>
        <Popconfirm title="确认删除此题目？" onConfirm={handleDelete}>
          <Button danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      </Space>

      <Card>
        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="题型">
            <Tag>{QUESTION_TYPE_LABELS[question.question_type] || question.question_type}</Tag>
          </Descriptions.Item>
          <Descriptions.Item label="难度">
            <DifficultyBadge value={question.difficulty} />
          </Descriptions.Item>
          <Descriptions.Item label="分值">{question.score ?? '-'}</Descriptions.Item>
          <Descriptions.Item label="审核状态">
            <Tag color={question.review_status === 'approved' ? 'success' : 'warning'}>
              {REVIEW_STATUS_LABELS[question.review_status] || question.review_status}
            </Tag>
          </Descriptions.Item>
          <Descriptions.Item label="来源">{question.source || '-'}</Descriptions.Item>
          <Descriptions.Item label="年份">{question.source_year || '-'}</Descriptions.Item>
          <Descriptions.Item label="AI生成">{question.is_ai_generated ? '是' : '否'}</Descriptions.Item>
          <Descriptions.Item label="版本">v{question.current_version}</Descriptions.Item>
          <Descriptions.Item label="知识点" span={2}>
            <Space size={[0, 4]} wrap>
              {question.knowledge_points.map((kp) => (
                <KnowledgeTag key={kp.id} name={kp.name} />
              ))}
            </Space>
          </Descriptions.Item>
        </Descriptions>
      </Card>

      <Card title="题目内容" style={{ marginTop: 16 }}>
        {editing ? (
          <LaTeXEditor value={question.content_latex} />
        ) : (
          <MathRenderer content={question.content_latex} />
        )}
      </Card>

      {question.options && question.options.length > 0 && (
        <Card title="选项" style={{ marginTop: 16 }}>
          <Space direction="vertical">
            {question.options.map((opt) => (
              <Space key={opt.label}>
                <Text strong>{opt.label}.</Text>
                <MathRenderer content={opt.content_latex} />
              </Space>
            ))}
          </Space>
        </Card>
      )}

      {question.answer_latex && (
        <Card title="答案" style={{ marginTop: 16 }}>
          <MathRenderer content={question.answer_latex} />
        </Card>
      )}

      {question.solution_steps && question.solution_steps.length > 0 && (
        <Card title="解题步骤" style={{ marginTop: 16 }}>
          <Timeline
            items={question.solution_steps.map((step, i) => ({
              children: <MathRenderer content={step} />,
              color: 'blue',
            }))}
          />
        </Card>
      )}

      {question.versions && question.versions.length > 0 && (
        <Card title="版本历史" style={{ marginTop: 16 }}>
          <Timeline
            items={question.versions.map((v) => ({
              children: (
                <Space direction="vertical" size={0}>
                  <Text strong>v{v.version_number}</Text>
                  <Text type="secondary">{v.change_reason || '无说明'}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>{formatDate(v.created_at)}</Text>
                </Space>
              ),
            }))}
          />
        </Card>
      )}
    </div>
  );
}
