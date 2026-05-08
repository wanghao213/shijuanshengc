/** 难度标识组件 */

import { Tag } from 'antd';
import { getDifficultyLabel, getDifficultyColor } from '@/utils/constants';

interface DifficultyBadgeProps {
  value: number;
  showValue?: boolean;
}

export default function DifficultyBadge({ value, showValue = true }: DifficultyBadgeProps) {
  const label = getDifficultyLabel(value);
  const color = getDifficultyColor(value);

  return (
    <Tag color={color}>
      {showValue ? `${value.toFixed(1)} ${label}` : label}
    </Tag>
  );
}
