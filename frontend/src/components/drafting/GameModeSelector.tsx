import React from 'react';
import type { GameModeType } from '../../store/useDraftStore';
import { Zap, Sword, Trophy, Users, Shield, Target, Settings, Crown } from 'lucide-react';

const GAME_MODES: Array<{
  id: GameModeType;
  name: string;
  color: string;
  icon: React.ReactNode;
  description: string;
}> = [
  { 
    id: 'SWIFT', 
    name: 'Swift Play', 
    color: 'from-green-500 to-green-700',
    icon: <Zap size={20} />,
    description: 'Quick matches'
  },
  { 
    id: 'DRAFT', 
    name: 'Normal Draft', 
    color: 'from-blue-500 to-blue-700',
    icon: <Sword size={20} />,
    description: 'Standard draft'
  },
  { 
    id: 'RANKED', 
    name: 'Ranked Solo', 
    color: 'from-red-500 to-red-700',
    icon: <Trophy size={20} />,
    description: 'Competitive solo'
  },
  { 
    id: 'ARAM', 
    name: 'ARAM', 
    color: 'from-yellow-500 to-yellow-700',
    icon: <Target size={20} />,
    description: 'All Random All Mid'
  },
  { 
    id: 'FLEX', 
    name: 'Flex Queue', 
    color: 'from-purple-500 to-purple-700',
    icon: <Users size={20} />,
    description: 'Team ranked'
  },
  { 
    id: 'CLASH', 
    name: 'Clash', 
    color: 'from-orange-500 to-orange-700',
    icon: <Shield size={20} />,
    description: 'Tournament mode'
  },
  { 
    id: 'CUSTOM', 
    name: 'Custom', 
    color: 'from-gray-500 to-gray-700',
    icon: <Settings size={20} />,
    description: 'Custom games'
  },
  { 
    id: 'PRO', 
    name: 'Pro View', 
    color: 'from-gray-800 to-slate-700',
    icon: <Crown size={20} />,
    description: 'Pro analysis'
  },
];

interface GameModeSelectorProps {
  currentMode: GameModeType;
  onModeChange: (mode: GameModeType) => void;
}

export const GameModeSelector: React.FC<GameModeSelectorProps> = ({
  currentMode,
  onModeChange,
}) => {
  return (
    <div className="mb-8">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-white">Game Mode</h2>
        <div className="text-sm text-gray-400">
          Select your game type for tailored recommendations
        </div>
      </div>
      
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-8 gap-2">
        {GAME_MODES.map((mode) => (
          <button
            key={mode.id}
            onClick={() => onModeChange(mode.id)}
            className={`relative p-4 rounded-xl transition-all duration-300 ${
              currentMode === mode.id
                ? `bg-gradient-to-br ${mode.color} ring-2 ring-white/20 scale-105`
                : 'bg-background-card hover:bg-white/5'
            }`}
          >
            <div className="flex flex-col items-center space-y-2">
              <div className={`p-2 rounded-lg ${
                currentMode === mode.id 
                  ? 'bg-white/20' 
                  : 'bg-white/5'
              }`}>
                {mode.icon}
              </div>
              <div className="text-center">
                <div className={`font-semibold ${
                  currentMode === mode.id ? 'text-white' : 'text-gray-300'
                }`}>
                  {mode.name}
                </div>
                <div className={`text-xs mt-1 ${
                  currentMode === mode.id ? 'text-white/80' : 'text-gray-500'
                }`}>
                  {mode.description}
                </div>
              </div>
            </div>
            
            {currentMode === mode.id && (
              <div className="absolute -top-1 -right-1 w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
            )}
          </button>
        ))}
      </div>
    </div>
  );
};