/** 知识点管理页 */

import { useEffect, useState, useMemo } from 'react';
import { Card, Tree, Button, Space, Modal, Form, Input, InputNumber, Select, message, Spin, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons';
import type { DataNode } from 'antd/es/tree';
import { useKnowledgeStore } from '@/stores/knowledgeStore';
import { STAGES } from '@/utils/constants';
import type { KnowledgeNode } from '@/types/knowledge';
import * as api from '@/api/knowledge';

function toTreeData(nodes: KnowledgeNode[]): DataNode[] {
  return nodes.map((node) => ({
    title: node.name,
    key: node.id,
    children: node.children ? toTreeData(node.children) : [],
  }));
}

export default function KnowledgeManager() {
  const { tree, loading, fetchTree, deleteNode } = useKnowledgeStore();
  const [stage, setStage] = useState<string | undefined>();
  const [modalOpen, setModalOpen] = useState(false);
  const [form] = Form.useForm();

  useEffect(() => {
    fetchTree(stage);
  }, [fetchTree, stage]);

  const treeData = useMemo(() => toTreeData(tree), [tree]);

  const handleAdd = async () => {
    try {
      const values = await form.validateFields();
      await api.createKnowledgeNode(values);
      message.success('创建成功');
      setModalOpen(false);
      form.resetFields();
      fetchTree(stage);
    } catch {
      // validation error
    }
  };

  const handleDelete = async (id: number) => {
    try {
      await deleteNode(id);
      message.success('删除成功');
    } catch {
      message.error('删除失败');
    }
  };

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>知识点管理</h2>
        <Space>
          <Select placeholder="筛选学段" allowClear style={{ width: 120 }} value={stage} onChange={setStage}>
            {STAGES.map((s) => <Select.Option key={s} value={s}>{s}</Select.Option>)}
          </Select>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
            添加节点
          </Button>
        </Space>
      </div>

      <Card>
        {loading ? (
          <Spin style={{ display: 'block', margin: '40px auto' }} />
        ) : (
          <Tree
            treeData={treeData}
            defaultExpandAll
            showLine
            titleRender={(node) => (
              <Space>
                <span>{node.title as string}</span>
                <Popconfirm title="确认删除？" onConfirm={() => handleDelete(node.key as number)}>
                  <Button type="link" size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </Space>
            )}
          />
        )}
      </Card>

      <Modal
        title="添加知识点节点"
        open={modalOpen}
        onOk={handleAdd}
        onCancel={() => { setModalOpen(false); form.resetFields(); }}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="知识点名称" />
          </Form.Item>
          <Form.Item name="level" label="层级" rules={[{ required: true, message: '请选择层级' }]}>
            <Select placeholder="选择层级">
              <Select.Option value="stage">学段</Select.Option>
              <Select.Option value="grade">年级</Select.Option>
              <Select.Option value="chapter">章节</Select.Option>
              <Select.Option value="section">小节</Select.Option>
              <Select.Option value="knowledge_point">知识点</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="parent_id" label="父节点ID">
            <InputNumber placeholder="留空为顶级节点" style={{ width: '100%' }} min={1} />
          </Form.Item>
          <Form.Item name="stage" label="学段">
            <Select allowClear placeholder="选择学段">
              {STAGES.map((s) => <Select.Option key={s} value={s}>{s}</Select.Option>)}
            </Select>
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
