import React from 'react';
import type { TeamSide, RoleType } from '../../store/useDraftStore';
import { Shield, Target, Globe, Filter, RefreshCw } from 'lucide-react';

const ELO_RANKS = [
  'IRON', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM', 
  'EMERALD', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER'
];

const REGIONS = [
  'NA', 'EUW', 'EUNE', 'KR', 'BR', 'LAN', 'LAS', 
  'OCE', 'RU', 'TR', 'JP', 'VN', 'SG', 'PH', 'TW', 'TH'
];

const ROLES: Array<{ id: RoleType; name: string; short: string }> = [
  { id: 'TOP', name: 'Top Lane', short: 'TOP' },
  { id: 'JUNGLE', name: 'Jungle', short: 'JG' },
  { id: 'MID', name: 'Mid Lane', short: 'MID' },
  { id: 'ADC', name: 'Bot Carry', short: 'ADC' },
  { id: 'SUPPORT', name: 'Support', short: 'SUP' },
  { id: 'FILL', name: 'Fill', short: 'FILL' },
];

interface DraftControlsProps {
  side: TeamSide;
  role: RoleType;
  elo: string;
  region: string;
  patch: string;
  availablePatches: string[];
  phase: 'BAN' | 'PICK';
  currentTurn: number;
  onSideChange: (side: TeamSide) => void;
  onRoleChange: (role: RoleType) => void;
  onEloChange: (elo: string) => void;
  onRegionChange: (region: string) => void;
  onPatchChange: (patch: string) => void;
  onPhaseChange: (phase: 'BAN' | 'PICK') => void;
  onNextTurn: () => void;
  onReset: () => void;
}

export const DraftControls: React.FC<DraftControlsProps> = ({
  side,
  role,
  elo,
  region,
  patch,
  availablePatches,
  phase,
  currentTurn,
  onSideChange,
  onRoleChange,
  onEloChange,
  onRegionChange,
  onPatchChange,
  onPhaseChange,
  onNextTurn,
  onReset,
}) => {
  return (
    <div className="card mb-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-white">Draft Settings</h3>
        <button
          onClick={onReset}
          className="flex items-center space-x-2 px-3 py-1.5 text-sm bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
        >
          <RefreshCw size={14} />
          <span>Reset Draft</span>
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Team Side */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            <Shield size={16} className="inline mr-1" />
            Team Side
          </label>
          <div className="flex space-x-2">
            <button
              onClick={() => onSideChange('BLUE')}
              className={`flex-1 py-2 rounded-lg transition-all ${
                side === 'BLUE'
                  ? 'bg-blue-600 text-white'
                  : 'bg-white/5 text-gray-300 hover:bg-white/10'
              }`}
            >
              Blue Side
            </button>
            <button
              onClick={() => onSideChange('RED')}
              className={`flex-1 py-2 rounded-lg transition-all ${
                side === 'RED'
                  ? 'bg-red-600 text-white'
                  : 'bg-white/5 text-gray-300 hover:bg-white/10'
              }`}
            >
              Red Side
            </button>
          </div>
        </div>

        {/* Your Role */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            <Target size={16} className="inline mr-1" />
            Your Role
          </label>
          <select
            value={role}
            onChange={(e) => onRoleChange(e.target.value as RoleType)}
            className="w-full input-field py-2"
          >
            {ROLES.map((r) => (
              <option key={r.id} value={r.id}>
                {r.name}
              </option>
            ))}
          </select>
        </div>

        {/* Elo/Rank */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            <Filter size={16} className="inline mr-1" />
            Rank Tier
          </label>
          <select
            value={elo}
            onChange={(e) => onEloChange(e.target.value)}
            className="w-full input-field py-2"
          >
            {ELO_RANKS.map((rank) => (
              <option key={rank} value={rank}>
                {rank}
              </option>
            ))}
          </select>
        </div>

        {/* Region */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            <Globe size={16} className="inline mr-1" />
            Region
          </label>
          <select
            value={region}
            onChange={(e) => onRegionChange(e.target.value)}
            className="w-full input-field py-2"
          >
            {REGIONS.map((reg) => (
              <option key={reg} value={reg}>
                {reg}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Phase & Patch Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-4">
        {/* Draft Phase */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Draft Phase
          </label>
          <div className="flex items-center space-x-4">
            <div className="flex space-x-2">
              <button
                onClick={() => onPhaseChange('BAN')}
                className={`px-4 py-2 rounded-lg transition-all ${
                  phase === 'BAN'
                    ? 'bg-red-600 text-white'
                    : 'bg-white/5 text-gray-300 hover:bg-white/10'
                }`}
              >
                Ban Phase
              </button>
              <button
                onClick={() => onPhaseChange('PICK')}
                className={`px-4 py-2 rounded-lg transition-all ${
                  phase === 'PICK'
                    ? 'bg-green-600 text-white'
                    : 'bg-white/5 text-gray-300 hover:bg-white/10'
                }`}
              >
                Pick Phase
              </button>
            </div>
            <div className="text-sm">
              <span className="text-gray-400">Turn:</span>
              <span className="ml-2 font-semibold text-white">{currentTurn}</span>
            </div>
          </div>
        </div>

        {/* Game Patch */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Game Patch
          </label>
          <div className="flex items-center space-x-2">
            <select
              value={patch}
              onChange={(e) => onPatchChange(e.target.value)}
              className="flex-1 input-field py-2"
            >
              {availablePatches.map((p) => (
                <option key={p} value={p}>
                  Patch {p}
                </option>
              ))}
            </select>
            <button
              onClick={onNextTurn}
              className="px-4 py-2 bg-gradient-to-r from-primary-600 to-primary-800 text-white rounded-lg hover:from-primary-700 hover:to-primary-900 transition-all"
            >
              Next Turn
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};