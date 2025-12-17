import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import { DraftPage } from './pages/DraftPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          {/* Redirect root to /draft */}
          <Route index element={<Navigate to="/draft" replace />} />
          
          {/* Main drafting interface */}
          <Route path="/draft" element={<DraftPage />} />
          
          {/* Profile page */}
          <Route path="/profile" element={
            <div className="p-6">
              <h1 className="text-3xl font-bold text-white mb-4">Profile & Settings</h1>
              <p className="text-gray-300">Manage your champion pool and preferences.</p>
            </div>
          } />
          
          {/* Login page (to be built) */}
          <Route path="/login" element={
            <div className="p-6">
              <h1 className="text-3xl font-bold text-white mb-4">Login / Sign Up</h1>
              <p className="text-gray-300">Authentication will go here.</p>
            </div>
          } />
          
          {/* Catch-all route for 404 */}
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