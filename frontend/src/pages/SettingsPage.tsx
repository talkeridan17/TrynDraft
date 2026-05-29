import { Settings } from 'lucide-react';

export const SettingsPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="text-center space-y-4">
        <Settings className="w-12 h-12 text-gray-600 mx-auto" />
        <h1 className="text-2xl font-bold text-white">Settings</h1>
        <p className="text-gray-400 text-lg">Coming soon</p>
        <p className="text-gray-600 text-sm max-w-xs mx-auto">
          SoloQ and Clash settings are under construction.
          Use the Draft page to get started.
        </p>
      </div>
    </div>
  );
};

export default SettingsPage;
