import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'sonner';
import { ExecutionProvider } from './context/ExecutionContext';
import { ThemeProvider } from './context/ThemeProvider';
import Landing from './pages/Landing';
import Dashboard from './pages/Dashboard';
import History from './pages/History';
import Templates from './pages/Templates';
import Settings from './pages/Settings';
import About from './pages/About';
import NotFound from './pages/NotFound';
import DeveloperOverlay from './components/DeveloperOverlay';

export default function App() {
  return (
    <ThemeProvider defaultTheme="light" storageKey="do-it-theme">
      <ExecutionProvider>
        <Router>
          <Routes>
            <Route path="/" element={<Landing />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/history" element={<History />} />
            <Route path="/templates" element={<Templates />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/about" element={<About />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Router>
        <DeveloperOverlay />
        <Toaster theme="dark" position="bottom-right" richColors />
      </ExecutionProvider>
    </ThemeProvider>
  );
}
