/** 统计卡片组件 */

import { Card, Statistic } from 'antd';
import type { ReactNode } from 'react';

interface StatsCardProps {
  title: string;
  value: number | string;
  prefix?: ReactNode;
  suffix?: string;
  precision?: number;
  valueStyle?: React.CSSProperties;
}

export default function StatsCard({ title, value, prefix, suffix, precision, valueStyle }: StatsCardProps) {
  return (
    <Card>
      <Statistic
        title={title}
        value={value}
        prefix={prefix}
        suffix={suffix}
        precision={precision}
        valueStyle={valueStyle}
      />
    </Card>
  );
}
