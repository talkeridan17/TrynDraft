import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { DraftPage } from './pages/DraftPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<DraftPage />} />
        <Route path="/draft" element={<DraftPage />} />
        {/* Settings is handled inline on the draft page */}
        <Route path="/settings" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
