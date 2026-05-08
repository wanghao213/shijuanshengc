import { Routes, Route } from 'react-router-dom'
import AppLayout from './components/AppLayout'
import Dashboard from './pages/Dashboard'
import QuestionBank from './pages/QuestionBank'
import QuestionDetail from './pages/QuestionDetail'
import QuestionImport from './pages/QuestionImport'
import OCRImport from './pages/OCRImport'
import PaperGenerator from './pages/PaperGenerator'
import PaperPreview from './pages/PaperPreview'
import PaperHistory from './pages/PaperHistory'
import TemplateManager from './pages/TemplateManager'
import KnowledgeManager from './pages/KnowledgeManager'

function App() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="questions" element={<QuestionBank />} />
        <Route path="questions/:id" element={<QuestionDetail />} />
        <Route path="questions/import" element={<QuestionImport />} />
        <Route path="questions/ocr" element={<OCRImport />} />
        <Route path="generator" element={<PaperGenerator />} />
        <Route path="papers" element={<PaperHistory />} />
        <Route path="papers/:id" element={<PaperPreview />} />
        <Route path="templates" element={<TemplateManager />} />
        <Route path="knowledge" element={<KnowledgeManager />} />
      </Route>
    </Routes>
  )
}

export default App
