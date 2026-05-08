/** 试卷生成页 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Form, InputNumber, Select, Slider, Space, Steps, Switch, message } from 'antd';
import { useGenerationStore } from '@/stores/generationStore';
import GenerationProgress from '@/components/GenerationProgress';
import * as templateApi from '@/api/templates';
import type { PaperTemplate } from '@/types/template';

const { Option } = Select;

const steps = [
  { title: '选择模板' },
  { title: '配置参数' },
  { title: '生成中' },
  { title: '完成' },
];

export default function PaperGenerator() {
  const navigate = useNavigate();
  const [current, setCurrent] = useState(0);
  const [selectedTemplate, setSelectedTemplate] = useState<number | null>(null);
  const [templates, setTemplates] = useState<PaperTemplate[]>([]);
  const [form] = Form.useForm();
  const { currentTask, startGeneration, loading } = useGenerationStore();
  const [taskId, setTaskId] = useState<string | null>(null);

  useEffect(() => {
    templateApi.listTemplates(1, 50)
      .then(({ data }) => setTemplates(data))
      .catch(() => message.error('加载模板列表失败'));
  }, []);

  const handleGenerate = async () => {
    if (!selectedTemplate) return;

    const values = form.getFieldsValue();
    try {
      const id = await startGeneration(selectedTemplate, {
        difficulty_target: values.difficulty,
        knowledge_focus: values.knowledgeFocus || [],
        count: values.count || 1,
        allow_ai_generation: values.allowAI ?? true,
      });
      setTaskId(id);
      setCurrent(2);
    } catch {
      message.error('生成失败');
    }
  };

  // 监听任务完成
  useEffect(() => {
    if (currentTask?.status === 'completed') {
      setCurrent(3);
    }
  }, [currentTask?.status]);

  return (
    <div>
      <Steps current={current} items={steps} style={{ marginBottom: 24 }} />

      {current === 0 && (
        <div>
          <h3>选择试卷模板</h3>
          <Space direction="vertical" style={{ width: '100%' }}>
            {templates.map((tpl) => (
              <Card
                key={tpl.id}
                hoverable
                style={{
                  border: selectedTemplate === tpl.id ? '2px solid #1890ff' : '1px solid #d9d9d9',
                }}
                onClick={() => setSelectedTemplate(tpl.id)}
              >
                <h4>{tpl.name}</h4>
                <p>{tpl.stage} · {tpl.grade} · 总分{tpl.total_score}分 · {tpl.duration_minutes}分钟</p>
                {tpl.description && <p style={{ color: '#999' }}>{tpl.description}</p>}
              </Card>
            ))}
          </Space>
          <Button
            type="primary"
            onClick={() => setCurrent(1)}
            disabled={!selectedTemplate}
            style={{ marginTop: 16 }}
          >
            下一步
          </Button>
        </div>
      )}

      {current === 1 && (
        <Form form={form} layout="vertical" initialValues={{ difficulty: 3.0, count: 1, allowAI: true }}>
          <Form.Item label="目标难度" name="difficulty">
            <Slider min={1} max={5} step={0.1} marks={{ 1: '简单', 3: '中等', 5: '困难' }} />
          </Form.Item>
          <Form.Item label="重点知识点" name="knowledgeFocus">
            <Select mode="multiple" placeholder="选择重点知识点" style={{ width: '100%' }}>
              <Option value="二次函数">二次函数</Option>
              <Option value="圆的性质">圆的性质</Option>
              <Option value="三角函数">三角函数</Option>
              <Option value="数列">数列</Option>
              <Option value="概率统计">概率统计</Option>
            </Select>
          </Form.Item>
          <Form.Item label="生成数量" name="count">
            <InputNumber min={1} max={10} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item label="允许AI生成新题" name="allowAI" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Space>
            <Button onClick={() => setCurrent(0)}>上一步</Button>
            <Button type="primary" onClick={handleGenerate} loading={loading}>
              开始生成
            </Button>
          </Space>
        </Form>
      )}

      {current === 2 && taskId && (
        <div>
          <GenerationProgress taskId={taskId} />
          <Button type="primary" onClick={() => setCurrent(3)} style={{ marginTop: 16 }}>
            查看结果
          </Button>
        </div>
      )}

      {current === 3 && (
        <Card>
          <h3>生成完成！</h3>
          <p>试卷已成功生成，点击查看。</p>
          <Space>
            <Button type="primary" onClick={() => navigate(`/papers/${currentTask?.paper_id}`)}>
              查看试卷
            </Button>
            <Button onClick={() => { setCurrent(0); setTaskId(null); }}>
              再次生成
            </Button>
          </Space>
        </Card>
      )}
    </div>
  );
}
