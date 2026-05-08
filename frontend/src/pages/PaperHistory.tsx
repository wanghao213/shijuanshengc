/** 历史试卷页 */

import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Table, Tag, Space, Button, Typography, Popconfirm, message, Empty } from 'antd';
import { EyeOutlined, DeleteOutlined, FilePdfOutlined, PlusOutlined } from '@ant-design/icons';
import { usePaperStore } from '@/stores/paperStore';
import { PAPER_STATUS_LABELS, PAPER_STATUS_COLORS } from '@/types/paper';
import type { Paper, PaperReviewStatus } from '@/types/paper';
import { formatDate } from '@/utils/helpers';

const { Title } = Typography;

export default function PaperHistory() {
  const navigate = useNavigate();
  const { papers, meta, loading, fetchPapers, deletePaper } = usePaperStore();

  useEffect(() => {
    fetchPapers();
  }, [fetchPapers]);

  const handleDelete = async (id: number) => {
    try {
      await deletePaper(id);
      message.success('删除成功');
      fetchPapers(meta.page, meta.page_size);
    } catch {
      message.error('删除失败');
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 60,
    },
    {
      title: '试卷标题',
      dataIndex: 'title',
      render: (title: string, record: Paper) => (
        <Button type="link" onClick={() => navigate(`/papers/${record.id}`)}>
          {title}
        </Button>
      ),
    },
    {
      title: '总分',
      dataIndex: 'total_score',
      width: 80,
    },
    {
      title: '平均难度',
      dataIndex: 'difficulty_average',
      width: 100,
      render: (v: number) => v?.toFixed(2) ?? '-',
    },
    {
      title: '状态',
      dataIndex: 'review_status',
      width: 100,
      render: (status: PaperReviewStatus) => (
        <Tag color={PAPER_STATUS_COLORS[status] || 'default'}>
          {PAPER_STATUS_LABELS[status] || status}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      width: 180,
      render: (v: string) => formatDate(v),
    },
    {
      title: '操作',
      width: 160,
      render: (_: unknown, record: Paper) => (
        <Space>
          <Button type="link" icon={<EyeOutlined />} onClick={() => navigate(`/papers/${record.id}`)}>
            查看
          </Button>
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: 'space-between', width: '100%' }}>
        <Title level={4} style={{ margin: 0 }}>历史试卷</Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/generator')}>
          生成试卷
        </Button>
      </Space>

      <Card>
        <Table
          dataSource={papers}
          columns={columns}
          rowKey="id"
          loading={loading}
          locale={{ emptyText: <Empty description="暂无试卷" /> }}
          pagination={{
            current: meta.page,
            pageSize: meta.page_size,
            total: meta.total,
            showSizeChanger: true,
            showTotal: (total) => `共 ${total} 份试卷`,
            onChange: (page, pageSize) => fetchPapers(page, pageSize),
          }}
        />
      </Card>
    </div>
  );
}
