import { useState, useEffect } from 'react';
import { X, Search, Users, Trophy, Crown } from 'lucide-react';
import { getChampionImageUrl } from '../utils/patch';
import { RoleIcon } from '../components/common/RoleIcon';
import { useDraftStore } from '../store/useDraftStore';

type GameMode = 'RANKED' | 'CLASH' | 'PRO';
type RoleType = 'TOP' | 'JUNGLE' | 'MID' | 'ADC' | 'SUPPORT';

interface OpponentData {
  role: RoleType;
  summonerName: string;
  championPool: string[];
}

const ROLES: RoleType[] = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];

const MODE_INFO = {
  RANKED: {
    icon: Trophy,
    title: 'Ranked Solo/Duo',
    description: 'Standard ranked mode with NN recommendations based on your elo',
    color: 'amber'
  },
  CLASH: {
    icon: Users,
    title: 'Clash',
    description: 'Set opponent champion pools for targeted ban recommendations',
    color: 'blue'
  },
  PRO: {
    icon: Crown,
    title: 'Pro Play',
    description: 'Professional data integration with team scouting reports',
    color: 'purple'
  }
};

export const SettingsPage: React.FC = () => {
  const { settings, setSettings, allChampions, loadChampions } = useDraftStore();
  const [gameMode, setGameMode] = useState<GameMode>((settings.mode as GameMode) || 'RANKED');
  const [opponents, setOpponents] = useState<OpponentData[]>(
    ROLES.map(role => ({ role, summonerName: '', championPool: [] }))
  );
  const [showChampionPicker, setShowChampionPicker] = useState<number | null>(null);
  const [championSearch, setChampionSearch] = useState('');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [savedMode, setSavedMode] = useState<GameMode>('RANKED');

  useEffect(() => {
    if (allChampions.length === 0) {
      loadChampions();
    }
    // Load saved mode from settings
    const mode = settings.mode as GameMode;
    if (mode && ['RANKED', 'CLASH', 'PRO'].includes(mode)) {
      setGameMode(mode);
      setSavedMode(mode);
    }
  }, []);

  useEffect(() => {
    setHasUnsavedChanges(gameMode !== savedMode);
  }, [gameMode, savedMode]);

  const handleModeChange = (mode: GameMode) => {
    setGameMode(mode);
  };

  const handleSave = () => {
    setSettings({ mode: gameMode });
    setSavedMode(gameMode);
    setHasUnsavedChanges(false);
    // Store opponents data in localStorage for now
    if (gameMode === 'CLASH' || gameMode === 'PRO') {
      localStorage.setItem('tryndraft_opponents', JSON.stringify(opponents));
    }
  };

  const handleOpponentNameChange = (index: number, name: string) => {
    const newOpponents = [...opponents];
    newOpponents[index].summonerName = name;
    setOpponents(newOpponents);
    setHasUnsavedChanges(true);
  };

  const handleAddChampionToPool = (opponentIndex: number, champion: string) => {
    const newOpponents = [...opponents];
    if (!newOpponents[opponentIndex].championPool.includes(champion)) {
      newOpponents[opponentIndex].championPool.push(champion);
      setOpponents(newOpponents);
      setHasUnsavedChanges(true);
    }
  };

  const handleRemoveChampionFromPool = (opponentIndex: number, champion: string) => {
    const newOpponents = [...opponents];
    newOpponents[opponentIndex].championPool = newOpponents[opponentIndex].championPool.filter(c => c !== champion);
    setOpponents(newOpponents);
    setHasUnsavedChanges(true);
  };

  const filteredChampions = allChampions.filter(
    champ => champ.toLowerCase().includes(championSearch.toLowerCase())
  );

  return (
    <div className="fixed inset-0 bg-gray-950 pt-24 pb-8 px-8">
      <div className="w-full h-full bg-black border border-gray-800 rounded-lg p-8 flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-6 border-b border-gray-800 mb-6">
          <div>
            <h1 className="text-3xl font-bold text-white">Game Settings</h1>
            <p className="text-gray-400 mt-1">Configure your draft mode and opponent data</p>
          </div>
          <button
            onClick={handleSave}
            disabled={!hasUnsavedChanges}
            className={`px-8 py-3 rounded-lg font-semibold transition-all ${
              hasUnsavedChanges
                ? 'bg-amber-500 hover:bg-amber-600 text-black'
                : 'bg-gray-800 text-gray-600 cursor-not-allowed'
            }`}
          >
            Save Changes
          </button>
        </div>

        {/* Game Mode Selection */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-white mb-4">Game Mode</h2>
          <div className="grid grid-cols-3 gap-4">
            {(Object.entries(MODE_INFO) as [GameMode, typeof MODE_INFO.RANKED][]).map(([mode, info]) => {
              const Icon = info.icon;
              const isSelected = gameMode === mode;
              const colorClasses = {
                amber: isSelected ? 'border-amber-500 bg-amber-500/10' : 'border-gray-800 hover:border-amber-500/50',
                blue: isSelected ? 'border-blue-500 bg-blue-500/10' : 'border-gray-800 hover:border-blue-500/50',
                purple: isSelected ? 'border-purple-500 bg-purple-500/10' : 'border-gray-800 hover:border-purple-500/50'
              };

              return (
                <button
                  key={mode}
                  onClick={() => handleModeChange(mode)}
                  className={`p-6 rounded-lg border-2 transition-all text-left ${colorClasses[info.color as keyof typeof colorClasses]}`}
                >
                  <div className="flex items-center gap-3 mb-3">
                    <Icon size={24} className={isSelected ? `text-${info.color}-500` : 'text-gray-400'} />
                    <h3 className={`text-lg font-semibold ${isSelected ? 'text-white' : 'text-gray-300'}`}>
                      {info.title}
                    </h3>
                  </div>
                  <p className="text-sm text-gray-400">{info.description}</p>
                </button>
              );
            })}
          </div>
        </div>

        {/* Opponent Settings - Only show for Clash and Pro */}
        {(gameMode === 'CLASH' || gameMode === 'PRO') && (
          <div className="flex-1 overflow-hidden flex flex-col">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-semibold text-white">
                {gameMode === 'PRO' ? 'Enemy Team Scouting' : 'Opponent Champion Pools'}
              </h2>
              {gameMode === 'PRO' && (
                <span className="text-sm text-purple-400 flex items-center gap-2">
                  <Crown size={16} />
                  Pro API Connected
                </span>
              )}
            </div>

            <div className="flex-1 overflow-y-auto pr-2">
              <div className="space-y-4">
                {opponents.map((opponent, index) => (
                  <div
                    key={opponent.role}
                    className="bg-gray-900 border border-gray-800 rounded-lg p-4"
                  >
                    <div className="flex items-center gap-4 mb-3">
                      {/* Role Icon */}
                      <div className="p-2 bg-gray-800 rounded-lg">
                        <RoleIcon role={opponent.role} size={24} />
                      </div>

                      {/* Role Name */}
                      <span className="text-white font-semibold w-24">{opponent.role}</span>

                      {/* Summoner Name Input */}
                      <input
                        type="text"
                        value={opponent.summonerName}
                        onChange={(e) => handleOpponentNameChange(index, e.target.value)}
                        placeholder={gameMode === 'PRO' ? 'Pro player name' : 'Summoner name (optional)'}
                        className="flex-1 px-4 py-2 bg-black border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-gray-600"
                      />

                      {/* Add Champion Button */}
                      <button
                        onClick={() => setShowChampionPicker(index)}
                        className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-all flex items-center gap-2"
                      >
                        <Search size={16} />
                        Add Champ
                      </button>
                    </div>

                    {/* Champion Pool */}
                    {opponent.championPool.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-3 pl-14">
                        {opponent.championPool.map(champ => (
                          <div
                            key={champ}
                            className="flex items-center gap-2 bg-gray-800 rounded-lg px-2 py-1 group"
                          >
                            <img
                              src={getChampionImageUrl(champ)}
                              alt={champ}
                              className="w-6 h-6 rounded"
                            />
                            <span className="text-sm text-white">{champ}</span>
                            <button
                              onClick={() => handleRemoveChampionFromPool(index, champ)}
                              className="text-gray-500 hover:text-red-500 transition-colors"
                            >
                              <X size={14} />
                            </button>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Ranked Mode Info */}
        {gameMode === 'RANKED' && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center max-w-md">
              <Trophy size={64} className="mx-auto text-amber-500 mb-4" />
              <h3 className="text-xl font-semibold text-white mb-2">Ranked Mode Active</h3>
              <p className="text-gray-400">
                Champion recommendations are based on your selected rank and role.
                The neural network analyzes high-elo games to suggest optimal picks and bans.
              </p>
            </div>
          </div>
        )}

        {/* Champion Picker Modal */}
        {showChampionPicker !== null && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
            <div className="bg-gray-900 p-6 rounded-lg border-2 border-gray-800 w-[80%] max-w-4xl h-[70vh] flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-semibold text-white">
                  Add Champion to {opponents[showChampionPicker].role} Pool
                </h3>
                <button
                  onClick={() => {
                    setShowChampionPicker(null);
                    setChampionSearch('');
                  }}
                  className="text-gray-400 hover:text-white"
                >
                  <X size={24} />
                </button>
              </div>

              <div className="relative mb-4">
                <Search size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={championSearch}
                  onChange={(e) => setChampionSearch(e.target.value)}
                  placeholder="Search champions..."
                  className="w-full pl-12 pr-4 py-3 bg-black border-2 border-gray-800 rounded-lg text-white focus:outline-none focus:border-gray-700"
                />
              </div>

              <div className="flex-1 overflow-y-auto pr-2">
                <div className="grid grid-cols-8 gap-2">
                  {filteredChampions.map(champ => {
                    const isInPool = opponents[showChampionPicker].championPool.includes(champ);
                    return (
                      <button
                        key={champ}
                        onClick={() => {
                          if (!isInPool) {
                            handleAddChampionToPool(showChampionPicker, champ);
                          }
                        }}
                        disabled={isInPool}
                        className={`aspect-square rounded-lg overflow-hidden border-2 transition-all ${
                          isInPool
                            ? 'border-green-500 opacity-50 cursor-not-allowed'
                            : 'border-gray-800 hover:border-amber-500'
                        }`}
                      >
                        <img src={getChampionImageUrl(champ)} alt={champ} className="w-full h-full object-cover" />
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
