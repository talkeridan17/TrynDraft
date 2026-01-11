import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { DraftPage } from './pages/DraftPage';
import { LoginPage } from './pages/LoginPage';
import { ProfilePage } from './pages/ProfilePage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Draft page - full screen, no layout wrapper */}
        <Route path="/" element={<DraftPage />} />
        <Route path="/draft" element={<DraftPage />} />

        {/* Other pages with layout */}
        <Route element={<Layout />}>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/profile" element={<ProfilePage />} />

          {/* 404 */}
          <Route path="*" element={
            <div className="p-6 text-center">
              <h1 className="text-4xl font-bold text-white mb-4">404 - Page Not Found</h1>
              <p className="text-gray-300">The page you're looking for doesn't exist.</p>
            </div>
          } />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;