import React, { useState } from 'react';
import { X, Search, Filter, Star } from 'lucide-react';

interface ChampionSearchProps {
  onSelect: (champion: string) => void;
  onClose: () => void;
}

// Mock champion data - will be replaced with real data from API
const MOCK_CHAMPIONS = [
  'Aatrox', 'Ahri', 'Akali', 'Alistar', 'Amumu', 'Anivia', 'Annie', 'Aphelios',
  'Ashe', 'Aurelion Sol', 'Azir', 'Bard', 'Blitzcrank', 'Brand', 'Braum',
  'Caitlyn', 'Camille', 'Cassiopeia', 'ChoGath', 'Corki', 'Darius', 'Diana',
  'Draven', 'Dr. Mundo', 'Ekko', 'Elise', 'Evelynn', 'Ezreal', 'Fiddlesticks',
  'Fiora', 'Fizz', 'Galio', 'Gangplank', 'Garen', 'Gnar', 'Gragas', 'Graves',
  'Hecarim', 'Heimerdinger', 'Illaoi', 'Irelia', 'Ivern', 'Janna', 'Jarvan IV',
  'Jax', 'Jayce', 'Jhin', 'Jinx', 'KaiSa', 'Kalista', 'Karma', 'Karthus',
  'Kassadin', 'Katarina', 'Kayle', 'Kayn', 'Kennen', 'KhaZix', 'Kindred',
  'Kled', 'KogMaw', 'LeBlanc', 'Lee Sin', 'Leona', 'Lillia', 'Lissandra',
  'Lucian', 'Lulu', 'Lux', 'Malphite', 'Malzahar', 'Maokai', 'Master Yi',
  'Miss Fortune', 'Mordekaiser', 'Morgana', 'Nami', 'Nasus', 'Nautilus',
  'Neeko', 'Nidalee', 'Nocturne', 'Nunu & Willump', 'Olaf', 'Orianna',
  'Ornn', 'Pantheon', 'Poppy', 'Pyke', 'Qiyana', 'Quinn', 'Rakan', 'Rammus',
  'RekSai', 'Rell', 'Renekton', 'Rengar', 'Riven', 'Rumble', 'Ryze',
  'Samira', 'Sejuani', 'Senna', 'Seraphine', 'Sett', 'Shaco', 'Shen',
  'Shyvana', 'Singed', 'Sion', 'Sivir', 'Skarner', 'Sona', 'Soraka',
  'Swain', 'Sylas', 'Syndra', 'Tahm Kench', 'Taliyah', 'Talon', 'Taric',
  'Teemo', 'Thresh', 'Tristana', 'Trundle', 'Tryndamere', 'Twisted Fate',
  'Twitch', 'Udyr', 'Urgot', 'Varus', 'Vayne', 'Veigar', 'VelKoz',
  'Vex', 'Vi', 'Viego', 'Viktor', 'Vladimir', 'Volibear', 'Warwick',
  'Wukong', 'Xayah', 'Xerath', 'Xin Zhao', 'Yasuo', 'Yone', 'Yorick',
  'Yuumi', 'Zac', 'Zed', 'Zeri', 'Ziggs', 'Zilean', 'Zoe', 'Zyra'
];

const ROLES = ['All', 'Top', 'Jungle', 'Mid', 'ADC', 'Support'];

export const ChampionSearch: React.FC<ChampionSearchProps> = ({
  onSelect,
  onClose,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedRole, setSelectedRole] = useState('All');
  const [favorites, setFavorites] = useState<string[]>(['Darius', 'Garen', 'Sett', 'Ahri', 'Jinx']);

  const toggleFavorite = (champion: string) => {
    if (favorites.includes(champion)) {
      setFavorites(favorites.filter(f => f !== champion));
    } else {
      setFavorites([...favorites, champion]);
    }
  };

  const filteredChampions = MOCK_CHAMPIONS.filter(champion => {
    const matchesSearch = champion.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = selectedRole === 'All' || true; // Role filtering will be implemented later
    return matchesSearch && matchesRole;
  });

  const handleChampionSelect = (champion: string) => {
    onSelect(champion);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
      <div className="relative w-full max-w-4xl max-h-[80vh] bg-background-darker rounded-2xl border border-white/10 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-6 border-b border-white/10">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-2xl font-bold text-white">Select Champion</h2>
              <p className="text-gray-400">Choose a champion for your selection</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
            >
              <X size={24} />
            </button>
          </div>

          {/* Search Bar */}
          <div className="relative mb-4">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-500" size={20} />
            <input
              type="text"
              placeholder="Search champions..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-12 pr-4 py-3 bg-background-card border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-primary-500"
              autoFocus
            />
          </div>

          {/* Role Filters */}
          <div className="flex flex-wrap gap-2">
            {ROLES.map((role) => (
              <button
                key={role}
                onClick={() => setSelectedRole(role)}
                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                  selectedRole === role
                    ? 'bg-primary-600 text-white'
                    : 'bg-white/5 text-gray-300 hover:bg-white/10'
                }`}
              >
                {role}
              </button>
            ))}
          </div>
        </div>

        {/* Favorites Section */}
        {favorites.length > 0 && (
          <div className="p-4 border-b border-white/10">
            <h3 className="text-sm font-semibold text-gray-400 mb-2">FAVORITES</h3>
            <div className="flex flex-wrap gap-2">
              {favorites.map((champion) => (
                <button
                  key={champion}
                  onClick={() => handleChampionSelect(champion)}
                  className="group relative px-4 py-2 bg-gradient-to-r from-primary-600/20 to-secondary-600/20 rounded-lg hover:from-primary-600/30 hover:to-secondary-600/30 transition-all"
                >
                  <span className="text-white font-medium">{champion}</span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleFavorite(champion);
                    }}
                    className="absolute -top-1 -right-1 p-1 bg-background-darker rounded-full opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Star size={12} className="text-yellow-500 fill-yellow-500" />
                  </button>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Champion Grid */}
        <div className="p-4 overflow-y-auto max-h-[50vh]">
          {filteredChampions.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-400">No champions found matching "{searchTerm}"</p>
            </div>
          ) : (
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-2">
              {filteredChampions.map((champion) => (
                <button
                  key={champion}
                  onClick={() => handleChampionSelect(champion)}
                  className="group relative p-3 bg-white/2 rounded-lg hover:bg-white/10 transition-all"
                >
                  <div className="flex flex-col items-center space-y-2">
                    <div className="w-12 h-12 bg-gradient-to-br from-primary-600/20 to-secondary-600/20 rounded-lg flex items-center justify-center">
                      <span className="text-lg font-bold text-white">{champion.substring(0, 2)}</span>
                    </div>
                    <span className="text-sm text-gray-300 group-hover:text-white">{champion}</span>
                  </div>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleFavorite(champion);
                    }}
                    className="absolute top-2 right-2 p-1 bg-black/50 rounded opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <Star
                      size={14}
                      className={favorites.includes(champion) ? 'text-yellow-500 fill-yellow-500' : 'text-gray-500'}
                    />
                  </button>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-white/10 bg-background-card">
          <div className="flex items-center justify-between text-sm text-gray-400">
            <div className="flex items-center space-x-4">
              <div className="flex items-center">
                <Filter size={14} className="mr-1" />
                <span>{filteredChampions.length} champions</span>
              </div>
              <div className="flex items-center">
                <Star size={14} className="mr-1 text-yellow-500" />
                <span>{favorites.length} favorites</span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="px-4 py-2 bg-white/5 hover:bg-white/10 rounded-lg transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};