/** 仪表盘 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Col, Row, Statistic, Table, Tag, Button, Space, Spin } from 'antd';
import {
  BookOutlined,
  FileTextOutlined,
  RobotOutlined,
  PlusOutlined,
  ImportOutlined,
  RiseOutlined,
} from '@ant-design/icons';
import { Pie, Column } from '@ant-design/charts';
import { useQuestionStore } from '@/stores/questionStore';
import { usePaperStore } from '@/stores/paperStore';
import { PAPER_STATUS_LABELS, PAPER_STATUS_COLORS } from '@/types/paper';
import { QUESTION_TYPE_LABELS } from '@/types/question';
import type { Paper, PaperReviewStatus } from '@/types/paper';
import { formatDate } from '@/utils/helpers';

export default function Dashboard() {
  const navigate = useNavigate();
  const { stats, statsLoading, fetchStats } = useQuestionStore();
  const { papers, loading: papersLoading, fetchPapers } = usePaperStore();

  useEffect(() => {
    fetchStats();
    fetchPapers(1, 5);
  }, [fetchStats, fetchPapers]);

  const typeData = Object.entries(stats.by_type).map(([type, count]) => ({
    type: QUESTION_TYPE_LABELS[type as keyof typeof QUESTION_TYPE_LABELS] || type,
    count,
  }));

  const columns = [
    {
      title: '试卷名称',
      dataIndex: 'title',
      key: 'title',
      render: (title: string, record: Paper) => (
        <Button type="link" onClick={() => navigate(`/papers/${record.id}`)}>
          {title}
        </Button>
      ),
    },
    {
      title: '状态',
      dataIndex: 'review_status',
      key: 'status',
      render: (status: PaperReviewStatus) => (
        <Tag color={PAPER_STATUS_COLORS[status] || 'default'}>
          {PAPER_STATUS_LABELS[status] || status}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (v: string) => formatDate(v),
    },
  ];

  return (
    <div>
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card>
            <Spin spinning={statsLoading}>
              <Statistic title="题库总量" value={stats.total} prefix={<BookOutlined />} />
            </Spin>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Spin spinning={statsLoading}>
              <Statistic
                title="本月新增"
                value={stats.monthly_new}
                prefix={<RiseOutlined />}
                valueStyle={{ color: '#3f8600' }}
              />
            </Spin>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Spin spinning={statsLoading}>
              <Statistic
                title="AI生成占比"
                value={stats.ai_ratio}
                prefix={<RobotOutlined />}
                suffix="%"
              />
            </Spin>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Spin spinning={statsLoading}>
              <Statistic title="已生成试卷" value={stats.total_papers} prefix={<FileTextOutlined />} />
            </Spin>
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={12}>
          <Card title="题型分布">
            {typeData.length > 0 ? (
              <Pie
                data={typeData}
                angleField="count"
                colorField="type"
                radius={0.8}
                innerRadius={0.5}
                label={{ text: 'type', position: 'outside' }}
                legend={{ position: 'bottom' }}
                height={260}
              />
            ) : (
              <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                暂无数据
              </div>
            )}
          </Card>
        </Col>
        <Col span={12}>
          <Card title="题型数量统计">
            {typeData.length > 0 ? (
              <Column
                data={typeData}
                xField="type"
                yField="count"
                colorField="type"
                label={{ position: 'top' }}
                height={260}
                legend={false}
              />
            ) : (
              <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
                暂无数据
              </div>
            )}
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={16}>
          <Card title="最近生成的试卷">
            <Table columns={columns} dataSource={papers} rowKey="id" pagination={false} size="small" loading={papersLoading} />
          </Card>
        </Col>
        <Col span={8}>
          <Card title="快捷操作">
            <Space direction="vertical" style={{ width: '100%' }}>
              <Button type="primary" block icon={<PlusOutlined />} onClick={() => navigate('/generator')}>
                生成新试卷
              </Button>
              <Button block icon={<ImportOutlined />} onClick={() => navigate('/questions/import')}>
                导入题目
              </Button>
              <Button block onClick={() => navigate('/templates')}>
                管理模板
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  );
}
