import { useState, useEffect } from 'react';
import { Search } from 'lucide-react';
import { championService } from '../../utils/api';
import { getChampionImageUrl } from '../../utils/patch';

interface ChampionPickerProps {
  currentSide: 'BLUE' | 'RED';
  isBanPhase: boolean;
  pickIndex: number;
  bannedChampions?: string[];
  onSelect: (champion: string) => void;
  onNext: () => void;
  onPrevious: () => void;
}

export const ChampionPicker: React.FC<ChampionPickerProps> = ({
  currentSide,
  isBanPhase,
  pickIndex,
  bannedChampions = [],
  onSelect,
}) => {
  const [search, setSearch] = useState('');
  const [champions, setChampions] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [patch, setPatch] = useState('16.1.1');

  useEffect(() => {
    loadChampions();
    // Fetch latest patch
    fetch('https://ddragon.leagueoflegends.com/api/versions.json')
      .then(res => res.json())
      .then(versions => setPatch(versions[0]))
      .catch(() => setPatch('16.1.1'));
  }, []);

  const loadChampions = async () => {
    setLoading(true);
    try {
      const champData = await championService.getAll();
      setChampions(champData || []);
    } catch (error) {
      console.error('Failed to load champions:', error);
    }
    setLoading(false);
  };

  const filteredChamps = champions.filter(champ => {
    const champName = champ.name || '';
    const matchesSearch = champName.toLowerCase().includes(search.toLowerCase());
    const isNotBanned = isBanPhase || !bannedChampions.includes(champName);
    return matchesSearch && isNotBanned;
  }).slice(0, 70); // Limit to 70 champions visible at once

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-black/40 backdrop-blur-sm rounded-lg border border-gray-800">
        <div className="text-gray-400 text-lg">Loading champions...</div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-black/40 backdrop-blur-sm rounded-lg border border-gray-800">
      {/* Header */}
      <div className="p-4 border-b border-gray-800">
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="text-2xl font-bold text-white">
              {isBanPhase ? `BAN ${Math.min(pickIndex, 10)}/10` : `PICK ${Math.min(pickIndex - 10, 10)}/10`}
            </div>
            <div className={`text-sm font-medium uppercase tracking-wide ${currentSide === 'BLUE' ? 'text-slate-400' : 'text-red-400'}`}>
              {currentSide} TEAM
            </div>
          </div>
        </div>

        {/* Search Bar */}
        <div className="relative">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-500" size={20} />
          <input
            type="text"
            placeholder="Search champion..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full pl-12 pr-4 py-3 bg-gray-900/50 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/50 transition-colors"
            autoFocus
          />
        </div>
      </div>

      {/* Champion Grid - HUGE ICONS, NO SCROLL */}
      <div className="flex-1 p-4 overflow-hidden">
        <div className="grid grid-cols-10 gap-2 h-full content-start">
          {filteredChamps.map((champ) => {
            const champName = champ.name || '';
            const champId = champ.id || champName.replace(/[^a-zA-Z]/g, '');
            const isBanned = bannedChampions.includes(champName);

            return (
              <button
                key={champ.id || champName}
                onClick={() => !isBanned && onSelect(champName)}
                disabled={isBanned}
                className={`group relative aspect-square rounded overflow-hidden transition-all duration-150 ${
                  isBanned
                    ? 'opacity-30 cursor-not-allowed grayscale'
                    : 'hover:scale-110 hover:z-10 hover:shadow-2xl hover:shadow-amber-500/20'
                }`}
              >
                {/* Champion Image */}
                <img
                  src={getChampionImageUrl(champId, patch)}
                  alt={champName}
                  className="w-full h-full object-cover"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.opacity = '0.3';
                  }}
                />

                {/* Hover Overlay */}
                {!isBanned && (
                  <div className="absolute inset-0 bg-gradient-to-t from-amber-600/80 via-amber-600/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-center pb-1">
                    <span className="text-white font-bold text-[10px] uppercase tracking-wide drop-shadow-lg">
                      {champName}
                    </span>
                  </div>
                )}

                {/* Banned X Overlay */}
                {isBanned && (
                  <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                    <div className="text-red-500 font-bold text-2xl">✕</div>
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {filteredChamps.length === 0 && (
        <div className="flex-1 flex items-center justify-center text-gray-500">
          No champions found
        </div>
      )}
    </div>
  );
};
