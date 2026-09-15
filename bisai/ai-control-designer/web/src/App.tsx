import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import NewProject from './pages/NewProject';
import ProjectDetail from './pages/ProjectDetail';
import EvolutionView from './pages/EvolutionView';
import StrategyLibrary from './pages/StrategyLibrary';
import Settings from './pages/Settings';
import ClarifyPage from './pages/ClarifyPage';

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/projects/new" element={<NewProject />} />
          <Route path="/projects/clarify" element={<ClarifyPage />} />
          <Route path="/projects/:id" element={<ProjectDetail />} />
          <Route path="/evolution/:taskId" element={<EvolutionView />} />
          <Route path="/library" element={<StrategyLibrary />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;