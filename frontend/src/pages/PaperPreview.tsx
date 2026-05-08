/** 试卷预览页 */

import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Button,
  Card,
  Space,
  message,
  Spin,
  Typography,
  Statistic,
  Row,
  Col,
  Modal,
  Switch,
  Tooltip,
} from 'antd';
import {
  DownloadOutlined,
  CheckCircleOutlined,
  FileWordOutlined,
  CodeOutlined,
  CopyOutlined,
} from '@ant-design/icons';
import PaperSection from '@/components/PaperSection';
import { usePaperStore } from '@/stores/paperStore';
import { PAPER_STATUS_LABELS } from '@/types/paper';
import * as papersApi from '@/api/papers';

const { Title, Text } = Typography;

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function PaperPreview() {
  const { id } = useParams<{ id: string }>();
  const {
    currentPaper: paper,
    currentPaperDetail: detail,
    fetchPaper,
    fetchPaperDetail,
    exportLatex,
    exportPdf,
    exportDocx,
    loading,
  } = usePaperStore();

  const [exporting, setExporting] = useState<string | null>(null);
  const [includeAnswers, setIncludeAnswers] = useState(false);
  const [latexModalVisible, setLatexModalVisible] = useState(false);
  const [latexContent, setLatexContent] = useState('');

  useEffect(() => {
    if (id) {
      fetchPaper(Number(id));
      fetchPaperDetail(Number(id));
    }
  }, [id, fetchPaper, fetchPaperDetail]);

  const handleExportPdf = async () => {
    if (!id) return;
    setExporting('pdf');
    try {
      const blob = await exportPdf(Number(id), includeAnswers);
      downloadBlob(blob, `试卷_${paper?.title ?? id}.pdf`);
      message.success('PDF 导出成功');
    } catch {
      message.error('PDF 导出失败，请确认系统已安装 xelatex');
    } finally {
      setExporting(null);
    }
  };

  const handleExportDocx = async () => {
    if (!id) return;
    setExporting('docx');
    try {
      const blob = await exportDocx(Number(id), includeAnswers);
      downloadBlob(blob, `试卷_${paper?.title ?? id}.docx`);
      message.success('Word 导出成功');
    } catch {
      message.error('Word 导出失败');
    } finally {
      setExporting(null);
    }
  };

  const handleExportLatex = async () => {
    if (!id) return;
    setExporting('latex');
    try {
      const latex = await exportLatex(Number(id), includeAnswers);
      setLatexContent(latex);
      setLatexModalVisible(true);
    } catch {
      message.error('LaTeX 导出失败');
    } finally {
      setExporting(null);
    }
  };

  const handleCopyLatex = async () => {
    try {
      await navigator.clipboard.writeText(latexContent);
      message.success('LaTeX 源码已复制到剪贴板（可粘贴到 Overleaf 编译）');
    } catch {
      message.error('复制失败，请手动选择复制');
    }
  };

  const handleReview = async () => {
    if (!id) return;
    try {
      await papersApi.reviewPaper(Number(id), { status: 'approved' });
      message.success('审核通过');
      fetchPaper(Number(id));
    } catch {
      message.error('审核失败');
    }
  };

  if (loading || !paper) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  }

  return (
    <div style={{ display: 'flex', gap: 24 }}>
      {/* 左侧：试卷内容 */}
      <div style={{ flex: 1 }}>
        <Card>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <Title level={2}>{paper.title}</Title>
            <Space size="large">
              <Text type="secondary">总分：{paper.total_score}分</Text>
              <Text type="secondary">平均难度：{paper.difficulty_average?.toFixed(2)}</Text>
            </Space>
          </div>

          {detail && detail.sections.length > 0 ? (
            detail.sections.map((section, idx) => (
              <PaperSection
                key={section.name || idx}
                name={section.name}
                questions={section.questions}
                showAnswers={includeAnswers}
              />
            ))
          ) : (
            <Card size="small" style={{ background: '#fafafa' }}>
              <Text type="secondary">
                试卷包含 {paper.questions?.length ?? 0} 道题目（加载详细内容中...）
              </Text>
            </Card>
          )}
        </Card>
      </div>

      {/* 右侧：操作面板 */}
      <div style={{ width: 320 }}>
        <Card title="导出设置">
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Text>包含参考答案</Text>
              <Switch checked={includeAnswers} onChange={setIncludeAnswers} />
            </div>

            <Space direction="vertical" style={{ width: '100%' }}>
              <Tooltip title="通过 xelatex 编译生成 PDF（需系统安装 TeX Live）">
                <Button
                  type="primary"
                  icon={<DownloadOutlined />}
                  block
                  loading={exporting === 'pdf'}
                  onClick={handleExportPdf}
                >
                  导出 PDF
                </Button>
              </Tooltip>

              <Tooltip title="生成 Word 文档（公式以 LaTeX 源码显示）">
                <Button
                  icon={<FileWordOutlined />}
                  block
                  loading={exporting === 'docx'}
                  onClick={handleExportDocx}
                >
                  导出 Word
                </Button>
              </Tooltip>

              <Tooltip title="查看 LaTeX 源码（可复制到 Overleaf 编译）">
                <Button
                  icon={<CodeOutlined />}
                  block
                  loading={exporting === 'latex'}
                  onClick={handleExportLatex}
                >
                  查看 LaTeX 源码
                </Button>
              </Tooltip>
            </Space>
          </Space>
        </Card>

        <Card title="统计" style={{ marginTop: 16 }}>
          <Row gutter={[16, 16]}>
            <Col span={12}>
              <Statistic title="总题数" value={paper.questions?.length ?? 0} />
            </Col>
            <Col span={12}>
              <Statistic title="平均难度" value={paper.difficulty_average} precision={2} />
            </Col>
            <Col span={12}>
              <Statistic title="总分" value={paper.total_score} suffix="分" />
            </Col>
            <Col span={12}>
              <Statistic
                title="状态"
                valueRender={() => PAPER_STATUS_LABELS[paper.review_status] || paper.review_status}
              />
            </Col>
          </Row>
        </Card>

        <Card title="审核" style={{ marginTop: 16 }}>
          <Button icon={<CheckCircleOutlined />} block type="default" onClick={handleReview}>
            审核通过
          </Button>
        </Card>
      </div>

      {/* LaTeX 源码预览弹窗 */}
      <Modal
        title="LaTeX 源码"
        open={latexModalVisible}
        onCancel={() => setLatexModalVisible(false)}
        width={900}
        footer={[
          <Button key="copy" icon={<CopyOutlined />} type="primary" onClick={handleCopyLatex}>
            复制到剪贴板
          </Button>,
          <Button key="close" onClick={() => setLatexModalVisible(false)}>
            关闭
          </Button>,
        ]}
      >
        <pre
          style={{
            background: '#1e1e1e',
            color: '#d4d4d4',
            padding: 16,
            borderRadius: 8,
            maxHeight: '60vh',
            overflow: 'auto',
            fontSize: 13,
            lineHeight: 1.5,
            fontFamily: "'Cascadia Code', 'Fira Code', 'Consolas', monospace",
          }}
        >
          {latexContent}
        </pre>
      </Modal>
    </div>
  );
}
