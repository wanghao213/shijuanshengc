/** LaTeX 编辑器组件 */

import { Input, Tabs, Typography } from 'antd';
import { useState, useMemo } from 'react';
import MathRenderer from './MathRenderer';

const { TextArea } = Input;
const { Text } = Typography;

interface LaTeXEditorProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  rows?: number;
}

export default function LaTeXEditor({ value = '', onChange, placeholder, rows = 6 }: LaTeXEditorProps) {
  const [activeTab, setActiveTab] = useState<string>('edit');

  const previewContent = useMemo(() => {
    if (!value) return '（空）';
    return value;
  }, [value]);

  return (
    <div>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        size="small"
        items={[
          {
            key: 'edit',
            label: '编辑',
            children: (
              <TextArea
                value={value}
                onChange={(e) => onChange?.(e.target.value)}
                placeholder={placeholder || '输入 LaTeX 内容...'}
                rows={rows}
                style={{ fontFamily: 'monospace' }}
              />
            ),
          },
          {
            key: 'preview',
            label: '预览',
            children: (
              <div style={{ padding: 12, minHeight: 100, border: '1px solid #d9d9d9', borderRadius: 6 }}>
                <MathRenderer content={previewContent} />
              </div>
            ),
          },
          {
            key: 'split',
            label: '分屏',
            children: (
              <div style={{ display: 'flex', gap: 16 }}>
                <div style={{ flex: 1 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>编辑</Text>
                  <TextArea
                    value={value}
                    onChange={(e) => onChange?.(e.target.value)}
                    placeholder={placeholder || '输入 LaTeX 内容...'}
                    rows={rows}
                    style={{ fontFamily: 'monospace' }}
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <Text type="secondary" style={{ fontSize: 12 }}>预览</Text>
                  <div style={{ padding: 12, minHeight: 100, border: '1px solid #d9d9d9', borderRadius: 6 }}>
                    <MathRenderer content={previewContent} />
                  </div>
                </div>
              </div>
            ),
          },
        ]}
      />
    </div>
  );
}
