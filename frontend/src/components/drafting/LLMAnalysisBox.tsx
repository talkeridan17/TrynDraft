import { useState, useEffect } from 'react';
import { Brain, Loader2 } from 'lucide-react';
import { draftService } from '../../utils/api';

interface LLMAnalysisBoxProps {
  draftState: any;
  availableChampions: string[];
  topRecommendation: string;
  isLoading?: boolean;
}

export const LLMAnalysisBox: React.FC<LLMAnalysisBoxProps> = ({
  draftState,
  availableChampions,
  topRecommendation,
  isLoading = false
}) => {
  const [analysis, setAnalysis] = useState<string>('');
  const [generating, setGenerating] = useState<boolean>(false);

  useEffect(() => {
    const generateAnalysis = async () => {
      if (!draftState || availableChampions.length === 0) return;
      
      setGenerating(true);
      try {
        // Call your backend LLM endpoint
        const response = await draftService.getGameplan({
          draftState,
          availableChampions,
          topRecommendation
        });
        
        if (response?.analysis) {
          setAnalysis(response.analysis);
        } else {
          setAnalysis(`Considering ${topRecommendation} - a strong pick in the current meta.`);
        }
      } catch (error) {
        console.error('Failed to generate analysis:', error);
        setAnalysis(`Recommended: ${topRecommendation}. This champion fits well with the current draft.`);
      } finally {
        setGenerating(false);
      }
    };

    // Debounce the analysis generation
    const timer = setTimeout(() => {
      generateAnalysis();
    }, 500);

    return () => clearTimeout(timer);
  }, [draftState, availableChampions, topRecommendation]);

  const phase = draftState?.phase || 'BAN';
  const turn = draftState?.turn || 0;
  const actionNumber = phase === 'BAN' ? Math.min(turn + 1, 10) : Math.min(turn - 9, 10);

  return (
    <div className="bg-gradient-to-br from-gray-900/50 to-background-card/50 rounded-xl p-4 h-full">
      <div className="flex items-center space-x-2 mb-3">
        <Brain size={18} className="text-primary-400" />
        <div className="text-sm text-gray-300">
          {phase} {actionNumber}/10 • AI Analysis
        </div>
        {generating && <Loader2 size={14} className="animate-spin text-primary-400" />}
      </div>
      
      <div className="space-y-3">
        <div className="p-3 bg-white/5 rounded-lg">
          <div className="text-xs text-gray-400 mb-1">Top Recommendation</div>
          <div className="font-semibold text-white">{topRecommendation || 'Analyzing...'}</div>
        </div>
        
        <div className="p-3 bg-white/5 rounded-lg">
          <div className="text-xs text-gray-400 mb-2">Strategic Analysis</div>
          {isLoading || generating ? (
            <div className="flex items-center space-x-2">
              <Loader2 size={16} className="animate-spin text-primary-400" />
              <div className="text-gray-400">Analyzing draft...</div>
            </div>
          ) : (
            <div className="text-sm text-gray-200">
              {analysis || 'Generating analysis based on current draft state...'}
            </div>
          )}
        </div>
        
        <div className="text-xs text-gray-500">
          Analysis updates automatically with each pick/ban
        </div>
      </div>
    </div>
  );
};