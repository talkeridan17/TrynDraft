import { RefreshCw } from 'lucide-react';
import type { RoleType } from '../../store/useDraftStore';
import { useEffect, useState } from 'react';
import { championService } from '../../utils/api';

interface DraftControlsProps {
  side: 'BLUE' | 'RED';
  role: RoleType;
  elo: string;
  patch: string;
  availablePatches: string[];
  phase: 'BAN' | 'PICK';
  onSideChange: (side: 'BLUE' | 'RED') => void;
  onRoleChange: (role: RoleType) => void;
  onEloChange: (elo: string) => void;
  onPatchChange: (patch: string) => void;
  onPhaseChange: (phase: 'BAN' | 'PICK') => void;
  onReset: () => void;
}

const ROLES = [
  { id: 'TOP' as RoleType, name: 'Top' },
  { id: 'JUNGLE' as RoleType, name: 'Jungle' },
  { id: 'MID' as RoleType, name: 'Mid' },
  { id: 'ADC' as RoleType, name: 'ADC' },
  { id: 'SUPPORT' as RoleType, name: 'Support' }
];

const ELO_RANKS = [
  'IRON', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM', 
  'EMERALD', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER'
];

export const DraftControls: React.FC<DraftControlsProps> = ({
  side,
  role,
  elo,
  patch,
  availablePatches,
  phase,
  onSideChange,
  onRoleChange,
  onEloChange,
  onPatchChange,
  onPhaseChange,
  onReset,
}) => {
  const [rankIcons, setRankIcons] = useState<Record<string, string>>({});
  const [loadingIcons, setLoadingIcons] = useState(true);

  // Load rank icons
  useEffect(() => {
    const loadRankIcons = async () => {
      const icons: Record<string, string> = {};
      
      for (const rank of ELO_RANKS) {
        try {
          const iconUrl = await championService.getRankIcon(rank);
          icons[rank] = iconUrl;
        } catch (error) {
          console.warn(`Failed to load icon for rank ${rank}:`, error);
          // Use fallback emoji
          const fallbackEmojis: Record<string, string> = {
            'IRON': '🛡️',
            'BRONZE': '🥉',
            'SILVER': '🥈',
            'GOLD': '🥇',
            'PLATINUM': '💎',
            'EMERALD': '💚',
            'DIAMOND': '💎',
            'MASTER': '🌟',
            'GRANDMASTER': '🏆',
            'CHALLENGER': '👑'
          };
          icons[rank] = fallbackEmojis[rank] || '⭐';
        }
      }
      
      setRankIcons(icons);
      setLoadingIcons(false);
    };
    
    loadRankIcons();
  }, []);

  return (
    <div className="flex justify-center mb-6 w-full">
      <div className="inline-flex items-center bg-white/10 rounded-xl p-4 border border-white/20">
        <div className="flex items-center space-x-6">
          {/* Team Side */}
          <div className="flex bg-white/5 rounded-lg p-1">
            <button
              onClick={() => onSideChange('BLUE')}
              className={`px-6 py-3 rounded transition-all text-lg font-medium ${
                side === 'BLUE' 
                  ? 'bg-blue-600 text-white shadow-lg' 
                  : 'text-gray-300 hover:text-white hover:bg-white/10'
              }`}
            >
              Blue
            </button>
            <button
              onClick={() => onSideChange('RED')}
              className={`px-6 py-3 rounded transition-all text-lg font-medium ${
                side === 'RED' 
                  ? 'bg-red-600 text-white shadow-lg' 
                  : 'text-gray-300 hover:text-white hover:bg-white/10'
              }`}
            >
              Red
            </button>
          </div>

          {/* Your Role */}
          <div className="flex flex-col">
            <label className="text-sm text-gray-400 mb-1">Your Role</label>
            <select
              value={role}
              onChange={(e) => onRoleChange(e.target.value as RoleType)}
              className="bg-white/5 border border-white/20 rounded-lg px-4 py-3 text-white text-lg focus:outline-none focus:border-primary-500 min-w-[140px]"
            >
              {ROLES.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>

          {/* Elo */}
          <div className="flex flex-col">
            <label className="text-sm text-gray-400 mb-1">Rank</label>
            <select
              value={elo}
              onChange={(e) => onEloChange(e.target.value)}
              className="bg-white/5 border border-white/20 rounded-lg px-4 py-3 text-white text-lg focus:outline-none focus:border-primary-500 min-w-[160px]"
            >
              {ELO_RANKS.map((rank) => (
                <option key={rank} value={rank}>
                  {loadingIcons ? (
                    <span className="text-gray-400">Loading...</span>
                  ) : (
                    <span className="flex items-center">
                      {rankIcons[rank].startsWith('http') ? (
                        <img 
                          src={rankIcons[rank]}
                          alt={rank}
                          className="w-4 h-4 mr-2"
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            target.style.display = 'none';
                            const parent = target.parentElement;
                            if (parent) {
                              parent.textContent = rank.charAt(0);
                            }
                          }}
                        />
                      ) : (
                        <span className="mr-2">{rankIcons[rank]}</span>
                      )}
                      {rank}
                    </span>
                  )}
                </option>
              ))}
            </select>
          </div>

          {/* Patch */}
          <div className="flex flex-col">
            <label className="text-sm text-gray-400 mb-1">Patch</label>
            <select
              value={patch}
              onChange={(e) => onPatchChange(e.target.value)}
              className="bg-white/5 border border-white/20 rounded-lg px-4 py-3 text-white text-lg focus:outline-none focus:border-primary-500 min-w-[100px]"
            >
              {availablePatches.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>

          {/* Phase */}
          <div className="flex flex-col">
            <label className="text-sm text-gray-400 mb-1">Phase</label>
            <div className="flex bg-white/5 rounded-lg p-1">
              <button
                onClick={() => onPhaseChange('BAN')}
                className={`px-6 py-3 rounded transition-all text-lg font-medium ${
                  phase === 'BAN' 
                    ? 'bg-red-600 text-white shadow-lg' 
                    : 'text-gray-300 hover:text-white hover:bg-white/10'
                }`}
              >
                Ban
              </button>
              <button
                onClick={() => onPhaseChange('PICK')}
                className={`px-6 py-3 rounded transition-all text-lg font-medium ${
                  phase === 'PICK' 
                    ? 'bg-green-600 text-white shadow-lg' 
                    : 'text-gray-300 hover:text-white hover:bg-white/10'
                }`}
              >
                Pick
              </button>
            </div>
          </div>

          {/* Reset Button */}
          <div className="flex items-end h-full">
            <button
              onClick={onReset}
              className="flex items-center space-x-3 px-5 py-3 bg-white/10 hover:bg-white/20 rounded-lg transition-colors text-gray-300 hover:text-white text-lg font-medium border border-white/20"
            >
              <RefreshCw size={20} />
              <span>Reset Draft</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};