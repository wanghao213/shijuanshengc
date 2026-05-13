/** OCR 试卷识别导入页 */

import { useState, useMemo } from 'react';
import {
  Card,
  Tabs,
  Input,
  Button,
  Upload,
  Form,
  Select,
  Switch,
  Space,
  message,
  Table,
  Tag,
  Progress,
  Alert,
  Typography,
  Collapse,
} from 'antd';
import {
  UploadOutlined,
  FileTextOutlined,
  ScanOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useOcrStore } from '@/stores/ocrStore';
import type { UploadFile } from 'antd/es/upload/interface';

const { TextArea } = Input;
const { Title, Text, Paragraph } = Typography;

const QUESTION_TYPE_MAP: Record<string, string> = {
  choice: '选择题',
  fill_blank: '填空题',
  short_answer: '解答题',
  proof: '证明题',
  comprehensive: '综合题',
};

export default function OCRImport() {
  const navigate = useNavigate();
  const { result, loading, processText, uploadDocument, clearResult } = useOcrStore();

  const [textValue, setTextValue] = useState('');
  const [source, setSource] = useState('');
  const [autoTag, setAutoTag] = useState(true);
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  const handleTextSubmit = async () => {
    if (textValue.trim().length < 10) {
      message.warning('请输入至少 10 个字符的文本');
      return;
    }

    try {
      const res = await processText({
        text: textValue,
        source: source || undefined,
        auto_tag: autoTag,
      });

      if (res.status === 'success') {
        message.success(`成功提取 ${res.questions.length} 道题目，已保存到题库`);
      } else if (res.status === 'partial') {
        message.warning('部分提取成功，请检查结果');
      } else {
        message.error(res.error || '提取失败');
      }
    } catch {
      message.error('处理失败，请稍后重试');
    }
  };

  const handleFileUpload = async () => {
    if (fileList.length === 0) {
      message.warning('请先选择文件');
      return;
    }

    const file = fileList[0].originFileObj;
    if (!file) return;

    try {
      const res = await uploadDocument(file, {
        source: source || undefined,
        auto_tag: autoTag,
      });

      if (res.status === 'success') {
        message.success(`成功提取 ${res.questions.length} 道题目`);
      } else {
        message.error(res.error || '提取失败');
      }
    } catch {
      message.error('处理失败，请确认 MinerU 已安装或使用手动输入模式');
    }
  };

  const questionColumns = useMemo(() => [
    {
      title: '题号',
      dataIndex: 'number',
      key: 'number',
      width: 60,
    },
    {
      title: '题型',
      dataIndex: 'question_type',
      key: 'question_type',
      width: 80,
      render: (t: string) => <Tag>{QUESTION_TYPE_MAP[t] || t}</Tag>,
    },
    {
      title: '题目内容',
      dataIndex: 'content_latex',
      key: 'content_latex',
      ellipsis: true,
      render: (text: string) => (
        <Text style={{ fontFamily: 'monospace', fontSize: 12 }} ellipsis={{ tooltip: text }}>
          {text.substring(0, 100)}{text.length > 100 ? '...' : ''}
        </Text>
      ),
    },
    {
      title: '答案',
      dataIndex: 'answer_latex',
      key: 'answer_latex',
      width: 120,
      render: (t: string | null) => t ? <Text type="success">{t.substring(0, 30)}</Text> : '-',
    },
    {
      title: '难度',
      dataIndex: 'estimated_difficulty',
      key: 'difficulty',
      width: 80,
      render: (d: number) => <Tag color={d >= 4 ? 'red' : d >= 3 ? 'orange' : 'green'}>{d.toFixed(1)}</Tag>,
    },
    {
      title: '知识点',
      dataIndex: 'knowledge_points',
      key: 'knowledge_points',
      render: (kps: string[]) => kps?.map((kp: string, i: number) => <Tag key={i} color="blue">{kp}</Tag>) || '-',
    },
  ], []);

  const correctionColumns = useMemo(() => [
    { title: '原文', dataIndex: 'original', key: 'original', ellipsis: true },
    { title: '修正', dataIndex: 'corrected', key: 'corrected', ellipsis: true },
    { title: '原因', dataIndex: 'reason', key: 'reason', ellipsis: true },
  ], []);

  return (
    <div>
      <Title level={3}>OCR 试卷识别导入</Title>
      <Paragraph type="secondary">
        通过 OCR 识别试卷文档，自动提取题目并导入题库。支持 PDF/图片上传或手动粘贴文本。
      </Paragraph>

      <Tabs
        defaultActiveKey="text"
        onChange={(key) => {
          clearResult();
          if (key === 'text' || key === 'file') {
            useOcrStore.getState().setMode(key as 'text' | 'file');
          }
        }}
        items={[
          {
            key: 'text',
            label: (
              <span>
                <FileTextOutlined /> 手动输入
              </span>
            ),
            children: (
              <Card>
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  <Alert
                    type="info"
                    message="粘贴试卷文本，AI 将自动识别题目结构、修复 OCR 错误并提取题目"
                    showIcon
                  />

                  <Form layout="vertical">
                    <Form.Item label="试卷来源（可选）">
                      <Input
                        placeholder="如：2024年北京市中考数学真题"
                        value={source}
                        onChange={(e) => setSource(e.target.value)}
                      />
                    </Form.Item>

                    <Form.Item label="试卷文本">
                      <TextArea
                        rows={12}
                        placeholder="请粘贴试卷文本内容..."
                        value={textValue}
                        onChange={(e) => setTextValue(e.target.value)}
                        style={{ fontFamily: 'monospace' }}
                      />
                    </Form.Item>

                    <Form.Item label="自动标注知识点和难度">
                      <Switch checked={autoTag} onChange={setAutoTag} />
                    </Form.Item>
                  </Form>

                  <Button
                    type="primary"
                    icon={<ScanOutlined />}
                    size="large"
                    loading={loading}
                    onClick={handleTextSubmit}
                    block
                  >
                    开始识别提取
                  </Button>
                </Space>
              </Card>
            ),
          },
          {
            key: 'file',
            label: (
              <span>
                <UploadOutlined /> 文件上传
              </span>
            ),
            children: (
              <Card>
                <Space direction="vertical" style={{ width: '100%' }} size="middle">
                  <Alert
                    type="warning"
                    message="文件上传模式需要系统安装 MinerU OCR 引擎。如不可用，请使用手动输入模式。"
                    showIcon
                  />

                  <Form layout="vertical">
                    <Form.Item label="试卷来源（可选）">
                      <Input
                        placeholder="如：2024年高考数学全国卷I"
                        value={source}
                        onChange={(e) => setSource(e.target.value)}
                      />
                    </Form.Item>

                    <Form.Item label="上传文件（PDF/图片）">
                      <Upload
                        accept=".pdf,.png,.jpg,.jpeg,.bmp,.tiff"
                        maxCount={1}
                        fileList={fileList}
                        beforeUpload={() => false}
                        onChange={({ fileList: newList }) => setFileList(newList)}
                      >
                        <Button icon={<UploadOutlined />}>选择文件</Button>
                      </Upload>
                    </Form.Item>

                    <Form.Item label="自动标注知识点和难度">
                      <Switch checked={autoTag} onChange={setAutoTag} />
                    </Form.Item>
                  </Form>

                  <Button
                    type="primary"
                    icon={<ScanOutlined />}
                    size="large"
                    loading={loading}
                    onClick={handleFileUpload}
                    block
                  >
                    上传并识别
                  </Button>
                </Space>
              </Card>
            ),
          },
        ]}
      />

      {/* 识别结果 */}
      {result && (
        <Card style={{ marginTop: 24 }}>
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {/* 状态概览 */}
            <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
              {result.status === 'success' ? (
                <CheckCircleOutlined style={{ fontSize: 24, color: '#52c41a' }} />
              ) : (
                <ExclamationCircleOutlined style={{ fontSize: 24, color: '#faad14' }} />
              )}
              <div>
                <Text strong>
                  {result.status === 'success' ? '识别成功' : '部分成功'}
                </Text>
                <Text type="secondary" style={{ marginLeft: 16 }}>
                  提取 {result.questions.length} 道题目
                  {result.saved_question_ids.length > 0 &&
                    `，已保存 ${result.saved_question_ids.length} 道到题库`}
                </Text>
              </div>
              <div style={{ marginLeft: 'auto' }}>
                <Text type="secondary">置信度：</Text>
                <Progress
                  percent={Math.round(result.confidence * 100)}
                  size="small"
                  style={{ width: 120, display: 'inline-block', marginLeft: 8 }}
                  status={result.confidence >= 0.7 ? 'success' : 'normal'}
                />
              </div>
            </div>

            {/* 错误信息 */}
            {result.error && <Alert type="error" message={result.error} showIcon />}

            {/* AI 修正记录 */}
            {result.corrections.length > 0 && (
              <Collapse
                items={[
                  {
                    key: 'corrections',
                    label: `AI 修正记录（${result.corrections.length} 项）`,
                    children: (
                      <Table
                        dataSource={result.corrections}
                        columns={correctionColumns}
                        size="small"
                        pagination={false}
                        rowKey={(_, i) => String(i)}
                      />
                    ),
                  },
                ]}
              />
            )}

            {/* 提取的题目列表 */}
            <Table
              dataSource={result.questions}
              columns={questionColumns}
              size="small"
              rowKey={(_, i) => String(i)}
              pagination={{ pageSize: 20 }}
              title={() => (
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Text strong>提取的题目</Text>
                  {result.saved_question_ids.length > 0 && (
                    <Button
                      type="link"
                      onClick={() => navigate('/questions?review_status=pending')}
                    >
                      查看已保存的题目 →
                    </Button>
                  )}
                </div>
              )}
            />

            {/* 处理备注 */}
            {result.notes && (
              <Alert type="info" message="处理备注" description={result.notes} showIcon />
            )}
          </Space>
        </Card>
      )}
    </div>
  );
}
