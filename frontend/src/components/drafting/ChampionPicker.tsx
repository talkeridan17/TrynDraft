import { useState, useEffect } from 'react';
import { Search, ChevronRight, ChevronLeft } from 'lucide-react';
import { MOCK_CHAMPIONS } from '../../utils/icons';

interface ChampionPickerProps {
  currentSide: 'BLUE' | 'RED';
  isBanPhase: boolean;
  pickIndex: number;
  onSelect: (champion: string) => void;
  onNext: () => void;
  onPrevious: () => void;
}

export const ChampionPicker: React.FC<ChampionPickerProps> = ({
  currentSide,
  isBanPhase,
  pickIndex,
  onSelect,
  onNext,
  onPrevious,
}) => {
  const [search, setSearch] = useState('');
  const [champions, setChampions] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadChampions();
  }, []);

  const loadChampions = async () => {
    setLoading(true);
    // Use mock champions for now
    setChampions(MOCK_CHAMPIONS);
    setLoading(false);
  };

  const getChampionImage = (championName: string) => {
    const normalizedName = championName.replace(/[^a-zA-Z]/g, '');
    return `https://ddragon.leagueoflegends.com/cdn/14.4.1/img/champion/${normalizedName}.png`;
  };

  const pickerText = isBanPhase 
    ? `Ban ${Math.min(pickIndex, 10)}/10 • ${currentSide}`
    : `Pick ${Math.min(pickIndex - 10, 10)}/10 • ${currentSide}`;

  const filteredChamps = champions
    .filter(champ => champ.toLowerCase().includes(search.toLowerCase()))
    .slice(0, 24);

  const handleImageError = (e: React.SyntheticEvent<HTMLImageElement>, champName: string) => {
    const target = e.target as HTMLImageElement;
    target.style.display = 'none';
    const fallback = document.createElement('div');
    fallback.className = 'w-full h-full flex items-center justify-center bg-gradient-to-br from-primary-600/30 to-secondary-600/30 rounded';
    fallback.textContent = champName.substring(0, 2);
    target.parentNode?.appendChild(fallback);
  };

  if (loading) {
    return (
      <div className="bg-white/5 rounded-xl p-4 flex items-center justify-center h-full">
        <div className="text-gray-400">Loading champions...</div>
      </div>
    );
  }

  return (
    <div className="bg-white/5 rounded-xl p-4 h-full flex flex-col">
      {/* Picker Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className={`w-3 h-3 rounded-full ${currentSide === 'BLUE' ? 'bg-blue-500' : 'bg-red-500'}`}></div>
          <div className="text-lg font-semibold text-white">{pickerText}</div>
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={onPrevious}
            className="p-2 bg-white/5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
            title="Previous picker"
          >
            <ChevronLeft size={20} />
          </button>
          <button
            onClick={onNext}
            className="p-2 bg-white/5 rounded-lg hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
            title="Next picker"
          >
            <ChevronRight size={20} />
          </button>
        </div>
      </div>

      {/* Search Bar */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-500" size={20} />
        <input
          type="text"
          placeholder="Search champion..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/10 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary-500 text-lg"
          autoFocus
        />
      </div>

      {/* Champion Grid */}
      <div className="grid grid-cols-6 gap-2 flex-1 overflow-y-auto">
        {filteredChamps.map((champ) => (
          <button
            key={champ}
            onClick={() => onSelect(champ)}
            className="p-2 bg-white/2 rounded-lg hover:bg-white/10 transition-colors text-center flex flex-col items-center justify-center"
          >
            <div className="w-12 h-12 mb-2 rounded-lg overflow-hidden">
              <img
                src={getChampionImage(champ)}
                alt={champ}
                className="w-full h-full object-cover"
                onError={(e) => handleImageError(e, champ)}
              />
            </div>
            <div className="text-sm text-gray-300 truncate w-full">{champ}</div>
          </button>
        ))}
      </div>

      {filteredChamps.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          No champions found
        </div>
      )}
    </div>
  );
};