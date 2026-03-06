import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ProjectProvider } from './store/projectStore';
import { AppLayout } from './components/layout/AppLayout';
import { Dashboard } from './pages/Dashboard';
import { Studio } from './pages/Studio';
import { PromptPage } from './pages/PromptPage';
import { PreviewPage } from './pages/PreviewPage';
import { ExportPage } from './pages/ExportPage';
import { NotFound } from './pages/NotFound';

export default function App() {
  return (
    <ProjectProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Dashboard />} />
            <Route path="/studio/:projectId" element={<Studio />} />
            <Route path="/studio/:projectId/prompt" element={<PromptPage />} />
            <Route path="/studio/:projectId/preview" element={<PreviewPage />} />
            <Route path="/studio/:projectId/export" element={<ExportPage />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ProjectProvider>
  );
}
