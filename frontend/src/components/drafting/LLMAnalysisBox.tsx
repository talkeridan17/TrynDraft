import { Brain } from 'lucide-react';

interface LLMAnalysisBoxProps {
  draftState: any;
  availableChampions: string[];
  topRecommendation: string;
  isLoading?: boolean;
}

export const LLMAnalysisBox: React.FC<LLMAnalysisBoxProps> = ({
  draftState,
  isLoading = false
}) => {
  const totalPicks = (draftState?.picks?.blue?.filter((p: any) => p.champion).length || 0) +
                     (draftState?.picks?.red?.filter((p: any) => p.champion).length || 0);

  const totalBans = (draftState?.bans?.blue?.length || 0) + (draftState?.bans?.red?.length || 0);

  return (
    <div className="h-full bg-black/40 backdrop-blur-sm rounded-lg border border-gray-800 p-4 flex items-center gap-4">
      <div className="flex-shrink-0">
        <Brain className="text-amber-500" size={32} />
      </div>

      <div className="flex-1">
        <div className="text-sm font-medium text-amber-500 uppercase tracking-wide mb-1">
          AI Analysis
        </div>
        {isLoading ? (
          <div className="text-gray-500 text-sm">Loading champions...</div>
        ) : (
          <div className="text-gray-300 text-sm">
            {draftState.phase === 'BAN'
              ? `${totalBans}/10 bans complete. Ban high-priority meta champions.`
              : `${totalPicks}/10 picks complete. Build a balanced team composition.`
            }
          </div>
        )}
      </div>

      <div className="flex gap-6 text-xs">
        <div className="text-center">
          <div className="text-slate-400 font-medium mb-1">BLUE</div>
          <div className="text-white font-bold text-lg">50%</div>
        </div>
        <div className="text-center">
          <div className="text-red-400 font-medium mb-1">RED</div>
          <div className="text-white font-bold text-lg">50%</div>
        </div>
      </div>
    </div>
  );
};
