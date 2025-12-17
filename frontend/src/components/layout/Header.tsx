import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { Sword, Settings, User, LogIn } from 'lucide-react';

export const Header: React.FC = () => {
  const location = useLocation();
  
  // Highlight current page
  const isActive = (path: string) => location.pathname === path;

  return (
    <header className="bg-background-card/80 backdrop-blur-sm border-b border-white/10 sticky top-0 z-50">
      <div className="container mx-auto px-4 py-3">
        <div className="flex items-center justify-between">
          {/* Logo with Drafting focus */}
          <Link to="/draft" className="flex items-center space-x-3 group">
            <div className="p-2 bg-gradient-to-br from-primary-600 to-secondary-600 rounded-lg group-hover:from-primary-700 group-hover:to-secondary-700 transition-all">
              <Sword size={24} className="text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">TrynDraft</h1>
              <p className="text-xs text-gray-400">Drafting Assistant</p>
            </div>
          </Link>

          {/* Main Navigation - Only Draft + Settings */}
          <nav className="flex items-center space-x-1">
            <Link
              to="/draft"
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all ${
                isActive('/draft') 
                  ? 'bg-primary-900/40 text-primary-300' 
                  : 'text-gray-300 hover:bg-white/5 hover:text-white'
              }`}
            >
              <Sword size={20} />
              <span className="font-medium">Draft</span>
            </Link>
            
            <Link
              to="/profile"
              className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all ${
                isActive('/profile')
                  ? 'bg-primary-900/40 text-primary-300'
                  : 'text-gray-300 hover:bg-white/5 hover:text-white'
              }`}
            >
              <Settings size={20} />
              <span className="font-medium">Settings</span>
            </Link>
          </nav>

          {/* User/Login Section */}
          <div className="flex items-center space-x-3">
            <div className="hidden md:flex items-center space-x-3 px-4 py-2 bg-white/5 rounded-lg">
              <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-secondary-500 rounded-full flex items-center justify-center">
                <User size={16} className="text-white" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">Guest Mode</p>
                <p className="text-xs text-gray-400">Limited features</p>
              </div>
            </div>
            
            <Link
              to="/login"
              className="btn-primary flex items-center space-x-2 px-4 py-2"
            >
              <LogIn size={18} />
              <span>Login</span>
            </Link>
          </div>
        </div>
      </div>
    </header>
  );
};