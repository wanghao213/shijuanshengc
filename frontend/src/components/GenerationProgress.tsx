/** 生成进度组件 */

import { Progress, Steps, Typography, Card, Space, Tag } from 'antd';
import { useEffect } from 'react';
import { useGenerationStore } from '@/stores/generationStore';
import { GENERATION_STATUS_LABELS, AGENT_STEPS } from '@/types/generation';
import type { GenerationStatus } from '@/types/generation';

const { Text } = Typography;

interface GenerationProgressProps {
  taskId: string | number;
}

function getStepStatus(agentKey: string, currentStatus: GenerationStatus): 'wait' | 'process' | 'finish' | 'error' {
  const order = ['planning', 'retrieving', 'generating', 'validating', 'assembling'];
  const currentIdx = order.indexOf(currentStatus);
  const agentIdx = order.indexOf(agentKey);

  if (currentStatus === 'completed') return 'finish';
  if (currentStatus === 'failed') return 'error';
  if (agentIdx < currentIdx) return 'finish';
  if (agentIdx === currentIdx) return 'process';
  return 'wait';
}

export default function GenerationProgress({ taskId }: GenerationProgressProps) {
  const { currentTask, wsMessages, connectWs, disconnectWs } = useGenerationStore();

  useEffect(() => {
    connectWs(taskId);
    return () => disconnectWs();
  }, [taskId, connectWs, disconnectWs]);

  const status = currentTask?.status || 'pending';
  const pct = currentTask?.progress_pct || 0;
  const step = currentTask?.current_step || '';

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <Card>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text strong>整体进度</Text>
          <Progress percent={Math.round(pct)} status={status === 'failed' ? 'exception' : 'active'} />
          <Space>
            <Tag color={status === 'completed' ? 'success' : status === 'failed' ? 'error' : 'processing'}>
              {GENERATION_STATUS_LABELS[status] || status}
            </Tag>
            <Text type="secondary">{step}</Text>
          </Space>
        </Space>
      </Card>

      <Card title="Agent 执行状态">
        <Steps
          direction="vertical"
          size="small"
          items={AGENT_STEPS.map((agent) => ({
            title: agent.label,
            description: getStepStatus(agent.key, status) === 'process' ? '执行中...' : undefined,
            status: getStepStatus(agent.key, status),
          }))}
        />
      </Card>

      {wsMessages.length > 0 && (
        <Card title="实时日志" size="small">
          <div style={{ maxHeight: 200, overflow: 'auto' }}>
            {wsMessages.slice(-5).map((msg) => (
              <div key={msg.timestamp} style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
                <Text type="secondary" style={{ fontSize: 12 }}>
                  [{new Date(msg.timestamp).toLocaleTimeString()}]
                </Text>{' '}
                {msg.current_step}
              </div>
            ))}
          </div>
        </Card>
      )}
    </Space>
  );
}
