import React from 'react';
import type { GameModeType } from '../../store/useDraftStore';
import { Brain, TrendingUp, Target, Zap, AlertCircle, Users, Sword, Shield } from 'lucide-react';

interface DraftAssistantPanelProps {
  gameMode: GameModeType;
  phase: 'BAN' | 'PICK';
  currentTurn: number;
  bluePicks: Array<{ champion: string; role: string }>;
  redPicks: Array<{ champion: string; role: string }>;
  blueBans: string[];
  redBans: string[];
}

export const DraftAssistantPanel: React.FC<DraftAssistantPanelProps> = ({
  gameMode,
  phase,
  currentTurn,
  bluePicks,
  redPicks,
  blueBans,
  redBans,
}) => {
  // Calculate statistics using the actual props
  const bluePickedCount = bluePicks.filter(p => p.champion).length;
  const redPickedCount = redPicks.filter(p => p.champion).length;
  const totalBans = blueBans.length + redBans.length;
  
  // Generate game plan based on actual draft state
  const generateGamePlan = () => {
    if (phase === 'BAN') {
      if (totalBans === 0) {
        return "Start by banning meta champions. Consider high-priority picks that dominate the current patch.";
      } else if (totalBans < 5) {
        return `Based on ${totalBans} bans so far, consider targeting champions that counter your team's preferred playstyle.`;
      } else {
        return "Good ban phase. Now analyze enemy bans to predict their strategy for the pick phase.";
      }
    } else {
      if (bluePickedCount + redPickedCount === 0) {
        return "First pick phase. Consider securing a flexible champion that doesn't reveal your strategy.";
      } else if (bluePickedCount + redPickedCount < 6) {
        return `Mid draft. Analyze team compositions forming. ${bluePickedCount} blue picks vs ${redPickedCount} red picks.`;
      } else {
        return "Late draft. Focus on rounding out your composition and countering enemy picks.";
      }
    }
  };

  // Mock recommendations - will be replaced with real data
  const recommendations = [
    { champion: 'Darius', winRate: '54.2%', reason: 'Strong lane bully vs current picks', confidence: 92 },
    { champion: 'Garen', winRate: '52.8%', reason: 'Easy to play, durable', confidence: 87 },
    { champion: 'Sett', winRate: '51.5%', reason: 'Good trades, strong all-in', confidence: 85 },
    { champion: 'Mordekaiser', winRate: '53.1%', reason: 'AP threat, good into tanks', confidence: 82 },
    { champion: 'Fiora', winRate: '50.9%', reason: 'Split push threat', confidence: 78 },
  ];

  // Get mode-specific color
  const getModeColor = () => {
    switch (gameMode) {
      case 'SWIFT': return 'from-green-500 to-green-600';
      case 'DRAFT': return 'from-blue-500 to-blue-600';
      case 'RANKED': return 'from-red-500 to-red-600';
      case 'ARAM': return 'from-yellow-500 to-yellow-600';
      case 'FLEX': return 'from-purple-500 to-purple-600';
      case 'CLASH': return 'from-orange-500 to-orange-600';
      case 'CUSTOM': return 'from-gray-500 to-gray-600';
      case 'PRO': return 'from-slate-700 to-gray-800';
      default: return 'from-primary-600 to-secondary-600';
    }
  };

  return (
    <div className="card h-full">
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <div className={`p-2 bg-gradient-to-br ${getModeColor()} rounded-lg`}>
            <Brain size={20} className="text-white" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">Draft Assistant</h3>
            <p className="text-sm text-gray-400">
              {gameMode} • {phase} Phase
            </p>
          </div>
        </div>
        <div className="flex items-center space-x-2">
          <div className="flex items-center text-xs text-blue-300">
            <Shield size={12} className="mr-1" />
            {bluePickedCount}
          </div>
          <div className="text-xs text-gray-400">vs</div>
          <div className="flex items-center text-xs text-red-300">
            <Sword size={12} className="mr-1" />
            {redPickedCount}
          </div>
        </div>
      </div>

      {/* LLM Game Plan */}
      <div className="mb-6">
        <div className="flex items-center space-x-2 mb-3">
          <Zap size={16} className="text-primary-400" />
          <h4 className="font-medium text-white">Game Plan Analysis</h4>
        </div>
        <div className="p-4 bg-gradient-to-br from-gray-900 to-background-card rounded-lg">
          <p className="text-gray-300 text-sm">
            {generateGamePlan()}
          </p>
          <div className="mt-3 flex items-center text-xs text-gray-400">
            <Users size={12} className="mr-1" />
            Turn {currentTurn} • {totalBans} bans placed
            <AlertCircle size={12} className="ml-2 mr-1" />
            Patch 14.1
          </div>
        </div>
      </div>

      {/* Top Recommendations */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center space-x-2">
            <Target size={16} className="text-secondary-400" />
            <h4 className="font-medium text-white">Top Picks</h4>
          </div>
          <div className="text-xs text-gray-400">
            For {phase === 'BAN' ? 'bans' : 'picks'}
          </div>
        </div>

        <div className="space-y-3">
          {recommendations.map((rec, index) => (
            <button
              key={index}
              onClick={() => console.log(`Selected ${rec.champion}`)}
              className="w-full p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-all text-left"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-3">
                  <div className="w-8 h-8 bg-gradient-to-br from-primary-600/30 to-secondary-600/30 rounded flex items-center justify-center">
                    <span className="font-bold text-white">{rec.champion.substring(0, 1)}</span>
                  </div>
                  <div>
                    <div className="font-semibold text-white">{rec.champion}</div>
                    <div className="flex items-center space-x-2 text-xs">
                      <div className="flex items-center text-green-400">
                        <TrendingUp size={10} className="mr-1" />
                        {rec.winRate}
                      </div>
                      <div className="text-gray-500">•</div>
                      <div className="text-primary-300">{rec.confidence}% conf</div>
                    </div>
                  </div>
                </div>
                <div className="text-xs px-2 py-1 rounded-full bg-gradient-to-r from-primary-500/20 to-secondary-500/20">
                  #{index + 1}
                </div>
              </div>
              <p className="text-sm text-gray-400">{rec.reason}</p>
            </button>
          ))}
        </div>

        {/* Action Buttons */}
        <div className="mt-6 grid grid-cols-2 gap-3">
          <button className="py-2.5 bg-gradient-to-r from-primary-600 to-primary-800 rounded-lg text-white font-medium hover:from-primary-700 hover:to-primary-900 transition-all">
            View Detailed Stats
          </button>
          <button className="py-2.5 bg-gradient-to-r from-secondary-600 to-secondary-800 rounded-lg text-white font-medium hover:from-secondary-700 hover:to-secondary-900 transition-all">
            Generate Full Plan
          </button>
        </div>
      </div>
    </div>
  );
};