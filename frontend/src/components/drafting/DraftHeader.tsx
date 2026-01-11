import { Link } from 'react-router-dom';
import { Sword, Settings, User } from 'lucide-react';

export const DraftHeader: React.FC = () => {
  return (
    <header className="fixed top-0 left-0 right-0 h-12 bg-black/80 backdrop-blur-md border-b border-gray-800 z-50 flex items-center justify-between px-6">
      {/* Logo */}
      <Link to="/draft" className="flex items-center space-x-2 group">
        <Sword size={18} className="text-amber-500 group-hover:text-amber-400" />
        <span className="text-white font-bold text-sm">TrynDraft</span>
      </Link>

      {/* Right side - Settings & Profile */}
      <div className="flex items-center space-x-3">
        <Link
          to="/profile"
          className="p-2 hover:bg-gray-900 rounded-lg transition-colors text-gray-400 hover:text-white"
          title="Profile & Settings"
        >
          <Settings size={18} />
        </Link>

        <div className="w-8 h-8 bg-gray-900 rounded-full flex items-center justify-center border border-gray-800">
          <User size={14} className="text-gray-500" />
        </div>
      </div>
    </header>
  );
};
