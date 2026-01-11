import { RefreshCw } from 'lucide-react';
import type { RoleType } from '../../store/useDraftStore';
import { RoleIcon } from '../common/RoleIcon';
import { RankIcon } from '../common/RankIcon';

interface DraftControlsProps {
  side: 'BLUE' | 'RED';
  role: RoleType;
  elo: string;
  patch: string;
  phase: 'BAN' | 'PICK';
  onSideChange: (side: 'BLUE' | 'RED') => void;
  onRoleChange: (role: RoleType) => void;
  onEloChange: (elo: string) => void;
  onPatchChange: (patch: string) => void;
  onPhaseChange: (phase: 'BAN' | 'PICK') => void;
  onReset: () => void;
}

const ROLES: RoleType[] = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];

const ELO_RANKS = [
  'IRON', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM',
  'EMERALD', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER'
] as const;

export const DraftControls: React.FC<DraftControlsProps> = ({
  side,
  role,
  elo,
  patch,
  onSideChange,
  onRoleChange,
  onEloChange,
  onPatchChange,
  onReset,
}) => {
  return (
    <div className="flex justify-center items-center space-x-6 py-3 px-6 bg-black/40 backdrop-blur-md border-b border-white/10">
      {/* Team Side */}
      <div className="flex bg-black/30 rounded-lg p-1 border border-white/10">
        <button
          onClick={() => onSideChange('BLUE')}
          className={`px-4 py-2 rounded transition-all font-medium ${
            side === 'BLUE'
              ? 'bg-blue-600 text-white shadow-lg'
              : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          Blue Side
        </button>
        <button
          onClick={() => onSideChange('RED')}
          className={`px-4 py-2 rounded transition-all font-medium ${
            side === 'RED'
              ? 'bg-red-600 text-white shadow-lg'
              : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
        >
          Red Side
        </button>
      </div>

      {/* Role Selector */}
      <div className="flex items-center space-x-1 bg-black/30 rounded-lg p-1 border border-white/10">
        {ROLES.map((r) => (
          <button
            key={r}
            onClick={() => onRoleChange(r)}
            className={`p-2 rounded transition-all ${
              role === r
                ? 'bg-white/20 text-white shadow-lg'
                : 'text-gray-500 hover:text-white hover:bg-white/5'
            }`}
            title={r}
          >
            <RoleIcon role={r} size={20} />
          </button>
        ))}
      </div>

      {/* Rank Selector */}
      <div className="flex items-center space-x-2 bg-black/30 rounded-lg px-3 py-2 border border-white/10">
        <RankIcon rank={elo as any} size={18} />
        <select
          value={elo}
          onChange={(e) => onEloChange(e.target.value)}
          className="bg-transparent text-white focus:outline-none cursor-pointer text-sm font-medium"
        >
          {ELO_RANKS.map((rank) => (
            <option key={rank} value={rank} className="bg-gray-900">
              {rank}
            </option>
          ))}
        </select>
      </div>

      {/* Patch Selector */}
      <div className="flex items-center space-x-2 bg-black/30 rounded-lg px-3 py-2 border border-white/10">
        <span className="text-gray-400 text-sm">Patch</span>
        <span className="text-white font-mono font-medium">{patch}</span>
      </div>

      {/* Reset Button */}
      <button
        onClick={onReset}
        className="flex items-center space-x-2 px-4 py-2 bg-black/30 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white border border-white/10"
        title="Reset Draft"
      >
        <RefreshCw size={16} />
        <span className="text-sm font-medium">Reset</span>
      </button>
    </div>
  );
};
