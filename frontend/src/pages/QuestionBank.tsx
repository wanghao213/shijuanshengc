/** 题库管理页 */

import { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Col, Input, Row, Select, Slider, Radio, Button, Space, Pagination, message, Empty } from 'antd';
import { SearchOutlined, ImportOutlined, PlusOutlined } from '@ant-design/icons';
import QuestionCard from '@/components/QuestionCard';
import { useQuestionStore } from '@/stores/questionStore';
import { useDebounce } from '@/hooks/useDebounce';
import { QUESTION_TYPES, STAGES, GRADES } from '@/utils/constants';
import type { QuestionType } from '@/types/question';

const { Option } = Select;

export default function QuestionBank() {
  const navigate = useNavigate();
  const { questions, meta, loading, fetchQuestions, deleteQuestion } = useQuestionStore();

  const [stage, setStage] = useState<string | undefined>();
  const [grade, setGrade] = useState<string | undefined>();
  const [questionType, setQuestionType] = useState<string | undefined>();
  const [difficultyRange, setDifficultyRange] = useState<[number, number]>([1, 5]);
  const [searchText, setSearchText] = useState('');
  const [searchMode, setSearchMode] = useState('keyword');

  const debouncedSearch = useDebounce(searchText, 500);

  const loadQuestions = useCallback(() => {
    fetchQuestions({
      page: meta.page,
      page_size: meta.page_size,
      stage,
      grade,
      question_type: questionType,
      difficulty_min: difficultyRange[0],
      difficulty_max: difficultyRange[1],
      q: debouncedSearch || undefined,
      mode: searchMode,
    });
  }, [fetchQuestions, meta.page, meta.page_size, stage, grade, questionType, difficultyRange, debouncedSearch, searchMode]);

  useEffect(() => {
    loadQuestions();
  }, [loadQuestions]);

  const handleDelete = async (id: number) => {
    try {
      await deleteQuestion(id);
      message.success('删除成功');
      loadQuestions();
    } catch {
      message.error('删除失败');
    }
  };

  const grades = stage ? GRADES[stage] || [] : [];

  return (
    <div>
      <Card style={{ marginBottom: 16 }}>
        <Row gutter={16} align="middle">
          <Col span={3}>
            <Select placeholder="学段" style={{ width: '100%' }} allowClear value={stage} onChange={(v) => { setStage(v); setGrade(undefined); }}>
              {STAGES.map((s) => <Option key={s} value={s}>{s}</Option>)}
            </Select>
          </Col>
          <Col span={3}>
            <Select placeholder="年级" style={{ width: '100%' }} allowClear value={grade} onChange={setGrade} disabled={!stage}>
              {grades.map((g) => <Option key={g} value={g}>{g}</Option>)}
            </Select>
          </Col>
          <Col span={3}>
            <Select placeholder="题型" style={{ width: '100%' }} allowClear value={questionType} onChange={setQuestionType}>
              {QUESTION_TYPES.map((t) => <Option key={t.value} value={t.value}>{t.label}</Option>)}
            </Select>
          </Col>
          <Col span={4}>
            <Slider range min={1} max={5} step={0.5} value={difficultyRange} onChange={(v) => setDifficultyRange(v as [number, number])} />
          </Col>
          <Col span={5}>
            <Input placeholder="搜索题目..." prefix={<SearchOutlined />} value={searchText} onChange={(e) => setSearchText(e.target.value)} allowClear />
          </Col>
          <Col span={3}>
            <Radio.Group value={searchMode} onChange={(e) => setSearchMode(e.target.value)}>
              <Radio.Button value="keyword">关键词</Radio.Button>
              <Radio.Button value="semantic">语义</Radio.Button>
            </Radio.Group>
          </Col>
          <Col span={3}>
            <Space>
              <Button icon={<ImportOutlined />} onClick={() => navigate('/questions/import')}>导入</Button>
              <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/questions/new')}>新增</Button>
            </Space>
          </Col>
        </Row>
      </Card>

      {questions.length > 0 ? (
        <Row gutter={[16, 16]}>
          {questions.map((q) => (
            <Col span={8} key={q.id}>
              <QuestionCard question={q} onDelete={handleDelete} />
            </Col>
          ))}
        </Row>
      ) : (
        <Card>
          <Empty description={loading ? '加载中...' : '暂无题目'} />
        </Card>
      )}

      {meta.total > 0 && (
        <div style={{ marginTop: 16, textAlign: 'right' }}>
          <Pagination
            current={meta.page}
            pageSize={meta.page_size}
            total={meta.total}
            showSizeChanger
            showTotal={(total) => `共 ${total} 题`}
            onChange={(page, pageSize) => fetchQuestions({ page, page_size: pageSize, stage, grade, question_type: questionType, difficulty_min: difficultyRange[0], difficulty_max: difficultyRange[1], q: debouncedSearch || undefined, mode: searchMode })}
          />
        </div>
      )}
    </div>
  );
}
