/** 知识点标签组件 */

import { Tag } from 'antd';

interface KnowledgeTagProps {
  name: string;
  color?: string;
  closable?: boolean;
  onClose?: () => void;
}

const COLORS = ['blue', 'green', 'orange', 'purple', 'cyan', 'magenta', 'gold', 'lime'];

function hashCode(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return Math.abs(hash);
}

export default function KnowledgeTag({ name, color, closable, onClose }: KnowledgeTagProps) {
  const tagColor = color || COLORS[hashCode(name) % COLORS.length];

  return (
    <Tag color={tagColor} closable={closable} onClose={onClose} style={{ marginRight: 4 }}>
      {name}
    </Tag>
  );
}
