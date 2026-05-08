/** 批量导入题目页 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Upload, Button, message, Typography, Space, Table, Alert } from 'antd';
import { UploadOutlined, ArrowLeftOutlined, ImportOutlined } from '@ant-design/icons';
import type { UploadFile } from 'antd';
import MathRenderer from '@/components/MathRenderer';
import { QUESTION_TYPE_LABELS } from '@/types/question';
import type { QuestionCreate, QuestionType } from '@/types/question';
import * as api from '@/api/questions';

const { Title, Text, Paragraph } = Typography;

export default function QuestionImport() {
  const navigate = useNavigate();
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [questions, setQuestions] = useState<QuestionCreate[]>([]);
  const [importing, setImporting] = useState(false);

  const handleFileRead = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        if (Array.isArray(data)) {
          setQuestions(data);
          message.success(`解析成功，共 ${data.length} 道题目`);
        } else {
          message.error('JSON 文件格式错误，需要是数组');
        }
      } catch {
        message.error('文件解析失败，请检查 JSON 格式');
      }
    };
    reader.readAsText(file);
    return false;
  };

  const handleImport = async () => {
    if (questions.length === 0) {
      message.warning('没有可导入的题目');
      return;
    }

    setImporting(true);
    try {
      const result = await api.batchImport(questions);
      message.success(`成功导入 ${result.imported_count} 道题目`);
      navigate('/questions');
    } catch {
      message.error('导入失败');
    } finally {
      setImporting(false);
    }
  };

  const columns = [
    {
      title: '题型',
      dataIndex: 'question_type',
      width: 100,
      render: (type: QuestionType) => QUESTION_TYPE_LABELS[type] || type,
    },
    {
      title: '难度',
      dataIndex: 'difficulty',
      width: 80,
    },
    {
      title: '题目内容（预览）',
      dataIndex: 'content_latex',
      render: (content: string) => (
        <div style={{ maxHeight: 60, overflow: 'hidden' }}>
          <MathRenderer content={content} maxLength={150} />
        </div>
      ),
    },
    {
      title: '来源',
      dataIndex: 'source',
      width: 150,
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/questions')}>
          返回题库
        </Button>
      </Space>

      <Card>
        <Title level={4}>批量导入题目</Title>
        <Paragraph type="secondary">
          支持 JSON 格式文件导入。每道题目需包含 content_latex、content_plain、question_type、difficulty 字段。
        </Paragraph>

        <Alert
          type="info"
          message="JSON 格式示例"
          description={`[
  {
    "content_latex": "已知 $x^2 + 2x - 3 = 0$，求 $x$ 的值。",
    "content_plain": "已知 x^2 + 2x - 3 = 0，求 x 的值。",
    "question_type": "short_answer",
    "difficulty": 2.5,
    "answer_latex": "$x = 1$ 或 $x = -3$",
    "knowledge_point_ids": [1, 2]
  }
]`}
          style={{ marginBottom: 16 }}
          showIcon
        />

        <Upload
          accept=".json"
          fileList={fileList}
          beforeUpload={(file) => {
            setFileList([file]);
            handleFileRead(file);
            return false;
          }}
          onRemove={() => {
            setFileList([]);
            setQuestions([]);
          }}
          maxCount={1}
        >
          <Button icon={<UploadOutlined />}>选择 JSON 文件</Button>
        </Upload>

        {questions.length > 0 && (
          <>
            <div style={{ margin: '16px 0' }}>
              <Text strong>预览：共 {questions.length} 道题目</Text>
            </div>
            <Table
              dataSource={questions.map((q, i) => ({ ...q, key: i }))}
              columns={columns}
              size="small"
              pagination={{ pageSize: 10 }}
            />
            <Button
              type="primary"
              icon={<ImportOutlined />}
              onClick={handleImport}
              loading={importing}
              style={{ marginTop: 16 }}
            >
              确认导入
            </Button>
          </>
        )}
      </Card>
    </div>
  );
}
