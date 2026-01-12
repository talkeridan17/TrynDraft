import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { Sword, Settings, User, LogIn, LogOut } from 'lucide-react';
import { authService } from '../../utils/api';

export const Header: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('');

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        setIsAuthenticated(true);
        try {
          const user = await authService.getCurrentUser();
          if (user) {
            setUsername(user.username || 'User');
          }
        } catch (error) {
          // Token might be invalid
          setIsAuthenticated(false);
          localStorage.removeItem('access_token');
        }
      }
    };
    checkAuth();
  }, [location]);

  const handleLogout = () => {
    authService.logout();
    setIsAuthenticated(false);
    setUsername('');
    navigate('/login');
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <header className="bg-black/60 backdrop-blur-md border-b border-gray-800 sticky top-0 z-50">
      <div className="container mx-auto px-6 py-3">
        <div className="flex items-center justify-between">
          {/* Logo */}
          <Link to="/draft" className="flex items-center space-x-3 group">
            <div className="p-2 bg-gray-900 border border-gray-800 rounded-lg group-hover:border-amber-500 transition-all">
              <Sword size={20} className="text-amber-500" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-white">TrynDraft</h1>
              <p className="text-[10px] text-gray-500 uppercase tracking-wider">Pro Draft Tool</p>
            </div>
          </Link>

          {/* Navigation */}
          <nav className="flex items-center space-x-1">
            <Link
              to="/draft"
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all ${
                isActive('/draft')
                  ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                  : 'text-gray-400 hover:bg-gray-900 hover:text-white border border-transparent'
              }`}
            >
              <Sword size={18} />
              <span className="font-medium">Draft</span>
            </Link>

            <Link
              to="/profile"
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all ${
                isActive('/profile')
                  ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                  : 'text-gray-400 hover:bg-gray-900 hover:text-white border border-transparent'
              }`}
            >
              <Settings size={18} />
              <span className="font-medium">Settings</span>
            </Link>
          </nav>

          {/* User Section */}
          <div className="flex items-center space-x-3">
            {isAuthenticated ? (
              <>
                <div className="hidden md:flex items-center space-x-3 px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg">
                  <div className="w-8 h-8 bg-amber-500/20 rounded-full flex items-center justify-center">
                    <User size={16} className="text-amber-500" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">{username}</p>
                    <p className="text-xs text-amber-500">Authenticated</p>
                  </div>
                </div>

                <button
                  onClick={handleLogout}
                  className="flex items-center space-x-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white font-medium rounded-lg transition-all border border-gray-700"
                >
                  <LogOut size={18} />
                  <span>Logout</span>
                </button>
              </>
            ) : (
              <>
                <div className="hidden md:flex items-center space-x-3 px-4 py-2 bg-gray-900 border border-gray-800 rounded-lg">
                  <div className="w-8 h-8 bg-gray-800 rounded-full flex items-center justify-center">
                    <User size={16} className="text-gray-500" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">Guest</p>
                    <p className="text-xs text-gray-500">Limited</p>
                  </div>
                </div>

                <Link
                  to="/login"
                  className="flex items-center space-x-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-black font-medium rounded-lg transition-all"
                >
                  <LogIn size={18} />
                  <span>Login</span>
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
