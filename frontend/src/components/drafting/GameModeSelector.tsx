import type { GameModeType } from '../../store/useDraftStore';
import { Zap, Sword, Trophy, Target, Users, Shield, Settings, Crown } from 'lucide-react';

const GAME_MODES = [
  { id: 'SWIFT' as GameModeType, name: 'Swift', icon: Zap, color: 'bg-green-500', gradient: 'from-green-500 to-emerald-600' },
  { id: 'DRAFT' as GameModeType, name: 'Draft', icon: Sword, color: 'bg-blue-500', gradient: 'from-blue-500 to-cyan-600' },
  { id: 'RANKED' as GameModeType, name: 'Ranked', icon: Trophy, color: 'bg-red-500', gradient: 'from-red-500 to-rose-600' },
  { id: 'ARAM' as GameModeType, name: 'ARAM', icon: Target, color: 'bg-yellow-500', gradient: 'from-yellow-500 to-amber-600' },
  { id: 'FLEX' as GameModeType, name: 'Flex', icon: Users, color: 'bg-purple-500', gradient: 'from-purple-500 to-violet-600' },
  { id: 'CLASH' as GameModeType, name: 'Clash', icon: Shield, color: 'bg-orange-500', gradient: 'from-orange-500 to-amber-600' },
  { id: 'CUSTOM' as GameModeType, name: 'Custom', icon: Settings, color: 'bg-gray-500', gradient: 'from-gray-500 to-slate-600' },
  { id: 'PRO' as GameModeType, name: 'Pro', icon: Crown, color: 'bg-slate-700', gradient: 'from-slate-700 to-gray-800' },
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
    <div className="flex justify-center mb-6">
      <div className="inline-flex items-center bg-white/5 rounded-xl p-1">
        {GAME_MODES.map((mode) => {
          const Icon = mode.icon;
          const isActive = currentMode === mode.id;
          
          return (
            <button
              key={mode.id}
              onClick={() => onModeChange(mode.id)}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-lg transition-all mx-1 ${
                isActive
                  ? `bg-gradient-to-r ${mode.gradient} text-white shadow-lg`
                  : 'text-gray-400 hover:text-white hover:bg-white/5'
              }`}
            >
              <Icon size={18} />
              <span className="font-medium">{mode.name}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};