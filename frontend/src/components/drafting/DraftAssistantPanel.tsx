import { Sparkles } from 'lucide-react';

interface DraftAssistantPanelProps {
  phase: 'BAN' | 'PICK';
  currentTurn: number;
}

export const DraftAssistantPanel: React.FC<DraftAssistantPanelProps> = ({
  phase,
  currentTurn,
}) => {
  return (
    <div className="bg-gradient-to-br from-gray-900/50 to-background-card/50 rounded-xl p-4">
      <div className="flex items-center space-x-2 mb-3">
        <Sparkles size={18} className="text-primary-400" />
        <div className="text-sm text-gray-300">
          Turn {currentTurn} • {phase} Phase
        </div>
      </div>
      <p className="text-gray-200">
        {phase === 'BAN' 
          ? "Ban priority: Target meta champions that counter your intended composition."
          : "Analyzing current draft. Consider champions that complement your team composition."
        }
      </p>
      <div className="mt-3 text-xs text-gray-400">
        LLM analysis will appear here based on current draft state.
      </div>
    </div>
  );
};