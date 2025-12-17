import React from 'react';
import type { TeamSide, RoleType } from '../../store/useDraftStore';
import { Users, Shield, Sword, X } from 'lucide-react';

interface TeamDisplayProps {
  side: TeamSide;
  picks: Array<{ champion: string; role: RoleType }>;
  bans: string[];
  phase: 'BAN' | 'PICK';
  onSelectChampion: (position: number) => void;
  onRemovePick: (position: number) => void;
  onRemoveBan: (index: number) => void;
}

const ROLE_ICONS: Record<RoleType, string> = {
  TOP: 'TOP',
  JUNGLE: 'JG',
  MID: 'MID',
  ADC: 'ADC',
  SUPPORT: 'SUP',
  FILL: 'FILL',
};

const POSITION_NAMES = ['First Pick', 'Second Pick', 'Third Pick', 'Fourth Pick', 'Fifth Pick'];

export const TeamDisplay: React.FC<TeamDisplayProps> = ({
  side,
  picks,
  bans,
  phase,
  onSelectChampion,
  onRemovePick,
  onRemoveBan,
}) => {
  const isBlueSide = side === 'BLUE';
  const sideColor = isBlueSide 
    ? 'border-blue-500/30 bg-blue-500/5' 
    : 'border-red-500/30 bg-red-500/5';
  const textColor = isBlueSide ? 'text-blue-300' : 'text-red-300';

  return (
    <div className={`card border-2 ${sideColor}`}>
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className={`p-2 rounded-lg ${isBlueSide ? 'bg-blue-500/20' : 'bg-red-500/20'}`}>
            {isBlueSide ? (
              <Shield size={20} className="text-blue-400" />
            ) : (
              <Sword size={20} className="text-red-400" />
            )}
          </div>
          <div>
            <h3 className={`font-bold ${textColor}`}>
              {isBlueSide ? 'Blue Side' : 'Red Side'}
            </h3>
            <p className="text-sm text-gray-400">
              {isBlueSide ? 'First Pick' : 'Second Pick'}
            </p>
          </div>
        </div>
        <div className="text-sm text-gray-400">
          <Users size={16} className="inline mr-1" />
          {picks.filter(p => p.champion).length}/5 Picked
        </div>
      </div>

      {/* Bans Display */}
      {phase === 'PICK' && bans.length > 0 && (
        <div className="mb-6">
          <h4 className="text-sm font-medium text-gray-300 mb-2">Bans</h4>
          <div className="flex flex-wrap gap-2">
            {bans.map((ban, index) => (
              <div
                key={index}
                className="flex items-center space-x-2 px-3 py-1.5 bg-white/5 rounded-lg"
              >
                <div className="w-6 h-6 bg-gradient-to-br from-gray-700 to-gray-900 rounded flex items-center justify-center">
                  <X size={12} className="text-gray-400" />
                </div>
                <span className="text-gray-300">{ban || 'Empty Ban'}</span>
                <button
                  onClick={() => onRemoveBan(index)}
                  className="ml-2 text-gray-500 hover:text-red-400"
                >
                  <X size={14} />
                </button>
              </div>
            ))}
            {Array(5 - bans.length).fill(0).map((_, index) => (
              <div
                key={`empty-${index}`}
                className="px-3 py-1.5 bg-white/5 rounded-lg border border-dashed border-gray-700"
              >
                <span className="text-gray-500">Empty Ban</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Picks Display */}
      <div className="space-y-3">
        <h4 className="text-sm font-medium text-gray-300">Picks</h4>
        {picks.map((pick, index) => (
          <div
            key={index}
            className={`flex items-center justify-between p-3 rounded-lg transition-all ${
              pick.champion
                ? 'bg-white/5 hover:bg-white/10'
                : 'bg-white/2 hover:bg-white/5 border border-dashed border-gray-700'
            }`}
          >
            <div className="flex items-center space-x-3">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                pick.champion
                  ? 'bg-gradient-to-br from-primary-600/20 to-secondary-600/20'
                  : 'bg-white/5'
              }`}>
                {pick.champion ? (
                  <div className="text-center">
                    <div className="font-bold text-white">{pick.champion.substring(0, 3)}</div>
                    <div className="text-xs text-gray-400">Lv 1</div>
                  </div>
                ) : (
                  <div className="text-gray-500">?</div>
                )}
              </div>
              <div>
                <div className="font-medium text-white">
                  {pick.champion || 'Empty Slot'}
                </div>
                <div className="flex items-center space-x-2 text-sm">
                  <span className="text-gray-400">{POSITION_NAMES[index]}</span>
                  <span className="text-gray-500">•</span>
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    pick.role === 'FILL' 
                      ? 'bg-gray-700 text-gray-300'
                      : 'bg-primary-500/20 text-primary-300'
                  }`}>
                    {ROLE_ICONS[pick.role]}
                  </span>
                </div>
              </div>
            </div>
            
            <div className="flex items-center space-x-2">
              {pick.champion ? (
                <button
                  onClick={() => onRemovePick(index)}
                  className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded"
                >
                  <X size={16} />
                </button>
              ) : (
                <button
                  onClick={() => onSelectChampion(index)}
                  className="px-3 py-1.5 text-sm bg-gradient-to-r from-primary-600 to-primary-800 rounded-lg hover:from-primary-700 hover:to-primary-900 transition-all"
                >
                  Select Champ
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};