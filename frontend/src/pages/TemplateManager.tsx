/** 试卷模板管理页 */

import { useEffect, useState, useCallback } from 'react';
import { Button, Card, Table, Tag, Space, Popconfirm, message, Modal, Form, Input, InputNumber, Select, Switch } from 'antd';
import { PlusOutlined, DeleteOutlined, CopyOutlined } from '@ant-design/icons';
import * as api from '@/api/templates';
import { STAGES, GRADES } from '@/utils/constants';
import type { PaperTemplate, TemplateCreate } from '@/types/template';
import type { ResponseMeta } from '@/types/common';

export default function TemplateManager() {
  const [templates, setTemplates] = useState<PaperTemplate[]>([]);
  const [meta, setMeta] = useState<ResponseMeta>({ page: 1, page_size: 20, total: 0 });
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();
  const [selectedStage, setSelectedStage] = useState<string | undefined>();

  const loadTemplates = useCallback(async (page = 1, pageSize = 20) => {
    setLoading(true);
    try {
      const { data, meta: m } = await api.listTemplates(page, pageSize);
      setTemplates(data);
      setMeta(m);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTemplates();
  }, [loadTemplates]);

  const handleDelete = async (id: number) => {
    try {
      await api.deleteTemplate(id);
      message.success('删除成功');
      loadTemplates(meta.page, meta.page_size);
    } catch {
      message.error('删除失败');
    }
  };

  const handleDuplicate = async (id: number) => {
    try {
      await api.duplicateTemplate(id);
      message.success('复制成功');
      loadTemplates(meta.page, meta.page_size);
    } catch {
      message.error('复制失败');
    }
  };

  const handleCreate = async () => {
    try {
      const values = await form.validateFields();
      const structure = {
        sections: [
          {
            name: '一、选择题',
            type: 'choice',
            score: values.choice_score || 30,
            count: values.choice_count || 10,
            per_question_score: Math.round((values.choice_score || 30) / (values.choice_count || 10)),
            difficulty_range: [1.0, 3.0],
          },
          {
            name: '二、填空题',
            type: 'fill_blank',
            score: values.fill_score || 24,
            count: values.fill_count || 6,
            per_question_score: Math.round((values.fill_score || 24) / (values.fill_count || 6)),
            difficulty_range: [2.0, 3.5],
          },
          {
            name: '三、解答题',
            type: 'short_answer',
            score: values.answer_score || 46,
            count: values.answer_count || 5,
            difficulty_range: [2.5, 5.0],
            progressive_difficulty: true,
          },
        ],
        global_constraints: {
          total_difficulty_target: 3.0,
          knowledge_coverage_min: 0.7,
          avoid_similar_questions: true,
          similarity_threshold: 0.85,
        },
      };

      const data: TemplateCreate = {
        name: values.name,
        stage: values.stage,
        grade: values.grade,
        subject: '数学',
        total_score: (values.choice_score || 30) + (values.fill_score || 24) + (values.answer_score || 46),
        duration_minutes: values.duration_minutes || 120,
        structure,
        is_default: values.is_default || false,
        description: values.description || undefined,
      };

      await api.createTemplate(data);
      message.success('创建成功');
      setModalOpen(false);
      form.resetFields();
      loadTemplates(meta.page, meta.page_size);
    } catch {
      // validation error
    }
  };

  const columns = [
    {
      title: '模板名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '学段',
      dataIndex: 'stage',
      key: 'stage',
      render: (stage: string) => <Tag>{stage}</Tag>,
    },
    {
      title: '年级',
      dataIndex: 'grade',
      key: 'grade',
    },
    {
      title: '总分',
      dataIndex: 'total_score',
      key: 'total_score',
      render: (v: number) => `${v}分`,
    },
    {
      title: '时长',
      dataIndex: 'duration_minutes',
      key: 'duration_minutes',
      render: (d: number) => `${d}分钟`,
    },
    {
      title: '默认',
      dataIndex: 'is_default',
      key: 'is_default',
      render: (v: boolean) => v ? <Tag color="green">是</Tag> : <Tag>否</Tag>,
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: PaperTemplate) => (
        <Space>
          <Button type="link" size="small" icon={<CopyOutlined />} onClick={() => handleDuplicate(record.id)}>
            复制
          </Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const grades = selectedStage ? GRADES[selectedStage] || [] : [];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>试卷模板管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          新建模板
        </Button>
      </div>
      <Card>
        <Table
          columns={columns}
          dataSource={templates}
          rowKey="id"
          loading={loading}
          pagination={{
            current: meta.page,
            pageSize: meta.page_size,
            total: meta.total,
            onChange: (page, pageSize) => loadTemplates(page, pageSize),
          }}
        />
      </Card>

      <Modal
        title="新建试卷模板"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => { setModalOpen(false); form.resetFields(); }}
        width={640}
        okText="创建"
      >
        <Form form={form} layout="vertical" initialValues={{ is_default: false, duration_minutes: 120, choice_count: 10, choice_score: 30, fill_count: 6, fill_score: 24, answer_count: 5, answer_score: 46 }}>
          <Form.Item name="name" label="模板名称" rules={[{ required: true, message: '请输入模板名称' }]}>
            <Input placeholder="如：初一上学期期末考试" />
          </Form.Item>
          <Space style={{ width: '100%' }}>
            <Form.Item name="stage" label="学段" rules={[{ required: true, message: '请选择学段' }]} style={{ width: 180 }}>
              <Select placeholder="选择学段" onChange={(v) => { setSelectedStage(v); form.setFieldValue('grade', undefined); }}>
                {STAGES.map((s) => <Select.Option key={s} value={s}>{s}</Select.Option>)}
              </Select>
            </Form.Item>
            <Form.Item name="grade" label="年级" rules={[{ required: true, message: '请选择年级' }]} style={{ width: 180 }}>
              <Select placeholder="选择年级" disabled={!selectedStage}>
                {grades.map((g) => <Select.Option key={g} value={g}>{g}</Select.Option>)}
              </Select>
            </Form.Item>
            <Form.Item name="duration_minutes" label="考试时长(分钟)" rules={[{ required: true }]} style={{ width: 180 }}>
              <InputNumber min={30} max={300} style={{ width: '100%' }} />
            </Form.Item>
          </Space>

          <Card size="small" title="选择题" style={{ marginBottom: 16 }}>
            <Space>
              <Form.Item name="choice_count" label="题数" style={{ width: 120 }}>
                <InputNumber min={1} max={50} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="choice_score" label="总分" style={{ width: 120 }}>
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Space>
          </Card>

          <Card size="small" title="填空题" style={{ marginBottom: 16 }}>
            <Space>
              <Form.Item name="fill_count" label="题数" style={{ width: 120 }}>
                <InputNumber min={1} max={50} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="fill_score" label="总分" style={{ width: 120 }}>
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Space>
          </Card>

          <Card size="small" title="解答题" style={{ marginBottom: 16 }}>
            <Space>
              <Form.Item name="answer_count" label="题数" style={{ width: 120 }}>
                <InputNumber min={1} max={50} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="answer_score" label="总分" style={{ width: 120 }}>
                <InputNumber min={1} max={100} style={{ width: '100%' }} />
              </Form.Item>
            </Space>
          </Card>

          <Form.Item name="description" label="描述">
            <Input.TextArea rows={2} placeholder="模板描述（可选）" />
          </Form.Item>
          <Form.Item name="is_default" label="设为默认" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
