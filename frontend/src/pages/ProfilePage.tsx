import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trash2, Plus, X, Search } from 'lucide-react';
import { authService } from '../utils/api';
import { getChampionImageUrl, getChampionSplashUrl } from '../utils/patch';
import { RoleIcon } from '../components/common/RoleIcon';
import { RankIcon } from '../components/common/RankIcon';
import { useDraftStore } from '../store/useDraftStore';

interface UserData {
  id: string;
  email: string;
  username: string;
  summoner_name?: string;
  region: string;
  created_at: string;
  preferences?: {
    preferred_roles?: string[];
    rank?: string;
    profile_picture?: string;
  };
}

interface ChampionPoolItem {
  id: string;
  champion_name: string;
  proficiency: number;
  created_at: string;
}

const ROLES = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];
const RANKS = ['IRON', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM', 'EMERALD', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER'];

export const ProfilePage: React.FC = () => {
  const [user, setUser] = useState<UserData | null>(null);
  const [championPool, setChampionPool] = useState<ChampionPoolItem[]>([]);
  const [loading, setLoading] = useState(true);
  const { allChampions, loadChampions: loadStoreChampions } = useDraftStore();
  const [showChampionPicker, setShowChampionPicker] = useState(false);
  const [championSearch, setChampionSearch] = useState('');
  const [preferredRoles, setPreferredRoles] = useState<string[]>([]);
  const [rank, setRank] = useState('PLATINUM');
  const [showProfilePicker, setShowProfilePicker] = useState(false);
  const [profilePicture, setProfilePicture] = useState<string>('Ahri');
  const [profileSearch, setProfileSearch] = useState('');
  const navigate = useNavigate();

  // Track saved state for visual feedback
  const [savedPreferredRoles, setSavedPreferredRoles] = useState<string[]>([]);
  const [savedRank, setSavedRank] = useState('PLATINUM');
  const [savedProfilePicture, setSavedProfilePicture] = useState<string>('Ahri');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    loadUserData();
    if (allChampions.length === 0) {
      loadStoreChampions();
    }
  }, []);

  // Check for unsaved changes
  useEffect(() => {
    const rolesChanged = JSON.stringify(preferredRoles.sort()) !== JSON.stringify(savedPreferredRoles.sort());
    const rankChanged = rank !== savedRank;
    const pictureChanged = profilePicture !== savedProfilePicture;
    setHasUnsavedChanges(rolesChanged || rankChanged || pictureChanged);
  }, [preferredRoles, rank, profilePicture, savedPreferredRoles, savedRank, savedProfilePicture]);

  const loadUserData = async () => {
    try {
      setLoading(true);
      const userData = await authService.getCurrentUser();
      if (userData) {
        setUser(userData);
        const roles = userData.preferences?.preferred_roles || [];
        const userRank = userData.preferences?.rank || 'PLATINUM';
        const picture = userData.preferences?.profile_picture || 'Ahri';

        setPreferredRoles(roles);
        setRank(userRank);
        setProfilePicture(picture);

        // Set saved state
        setSavedPreferredRoles(roles);
        setSavedRank(userRank);
        setSavedProfilePicture(picture);

        try {
          const pool = await authService.getChampionPool();
          setChampionPool(pool);
        } catch (error) {
          setChampionPool([]);
        }
      }
    } catch (error) {
      navigate('/login');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectPreferredRole = (role: string) => {
    // Single role selection - clicking same role deselects it, clicking different role switches to it
    if (preferredRoles.includes(role)) {
      setPreferredRoles([]);
    } else {
      setPreferredRoles([role]);
    }
  };

  const handleRankChange = (newRank: string) => {
    setRank(newRank);
  };

  const handleSelectProfilePicture = (champion: string) => {
    setProfilePicture(champion);
    setShowProfilePicker(false);
    setProfileSearch('');
  };

  const handleSavePreferences = async () => {
    try {
      setIsSaving(true);
      await authService.updatePreferences({
        preferred_roles: preferredRoles,
        rank: rank,
        profile_picture: profilePicture
      });

      // Update saved state after successful save
      setSavedPreferredRoles(preferredRoles);
      setSavedRank(rank);
      setSavedProfilePicture(profilePicture);
      setHasUnsavedChanges(false);

      // Dispatch event to notify Header to update profile picture
      window.dispatchEvent(new CustomEvent('profileUpdated', { detail: { profilePicture } }));
    } catch (error) {
      console.error('Failed to save preferences:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddChampion = async (champion: string) => {
    try {
      await authService.addToChampionPool({ champion_name: champion, playstyles: [] });
      await loadUserData();
      setShowChampionPicker(false);
      setChampionSearch('');
    } catch (error) {
      console.error('Failed to add champion:', error);
    }
  };

  const handleRemoveChampion = async (championId: string) => {
    try {
      await authService.removeFromChampionPool(championId);
      await loadUserData();
    } catch (error) {
      console.error('Failed to remove champion:', error);
    }
  };

  const handleUpdateProficiency = async (championId: string, proficiency: number) => {
    try {
      await authService.updateChampionPool(championId, { proficiency });
      await loadUserData();
    } catch (error) {
      console.error('Failed to update proficiency:', error);
    }
  };

  const filteredChampions = allChampions.filter(champ => champ.toLowerCase().includes(championSearch.toLowerCase()));
  const filteredProfileChampions = allChampions.filter(champ => champ.toLowerCase().includes(profileSearch.toLowerCase()));

  if (loading) {
    return <div className="h-screen w-screen bg-black flex items-center justify-center"><div className="text-white text-xl">Loading...</div></div>;
  }

  if (!user) return null;

  return (
    <div className="fixed inset-0 bg-gray-950 pt-24 pb-8 px-8">
      <div className="w-full h-full bg-black border border-gray-800 rounded-lg p-8 flex flex-col overflow-hidden">
        {/* Top Row: Profile, Roles, and Rank */}
        <div className="flex items-center justify-between gap-6 pb-6 border-b border-gray-800 mb-6">
          {/* Profile Picture and User Info */}
          <div className="flex items-center gap-4 flex-shrink-0 pr-6 border-r border-gray-800">
            <div className="relative flex-shrink-0">
              <div className="w-20 h-20 rounded-lg overflow-hidden border-2 border-gray-700">
                <img src={getChampionSplashUrl(profilePicture)} alt={profilePicture} className="w-full h-full object-cover" />
              </div>
              <button onClick={() => setShowProfilePicker(!showProfilePicker)} className="absolute -bottom-1 -right-1 p-1.5 bg-gray-900 hover:bg-gray-800 rounded border border-gray-700 transition-colors">
                <Search size={16} />
              </button>
            </div>
            <div className="min-w-0 max-w-[200px]">
              <h1 className="text-2xl font-bold text-white truncate" title={user.username}>{user.username}</h1>
              <p className="text-sm text-gray-400 truncate" title={user.email}>{user.email}</p>
            </div>
          </div>

          {/* Main Role (single selection) */}
          <div className="flex gap-3 px-6 border-r border-gray-800">
            {ROLES.map(role => {
              const isSelected = preferredRoles.includes(role);
              const isSaved = savedPreferredRoles.includes(role) === isSelected;
              return (
                <button
                  key={role}
                  onClick={() => handleSelectPreferredRole(role)}
                  title={role}
                  className={`w-14 h-14 rounded-lg border-2 transition-all overflow-hidden flex items-center justify-center ${
                    isSelected
                      ? isSaved
                        ? 'border-green-500 bg-green-500/20'
                        : 'border-amber-500 bg-amber-500/20'
                      : 'border-gray-800 hover:border-gray-700'
                  }`}
                >
                  <div className="flex items-center justify-center" style={{ transform: 'scale(1.5)' }}>
                    <RoleIcon role={role as any} size={36} />
                  </div>
                </button>
              );
            })}
          </div>

          {/* Current Rank */}
          <div className="flex gap-2 px-6 border-r border-gray-800">
            {RANKS.map(r => {
              const isSelected = rank === r;
              const isSaved = savedRank === r;
              return (
                <button
                  key={r}
                  onClick={() => handleRankChange(r)}
                  className={`w-14 h-14 rounded-lg border-2 transition-all flex items-center justify-center p-0 overflow-hidden ${
                    isSelected
                      ? isSaved
                        ? 'border-green-500 bg-green-500/20'
                        : 'border-amber-500 bg-amber-500/20'
                      : 'border-gray-800 hover:border-gray-700'
                  }`}
                  title={r}
                >
                  <div className="flex items-center justify-center" style={{ transform: 'scale(3, 1.4)' }}>
                    <RankIcon rank={r} size={70} />
                  </div>
                </button>
              );
            })}
          </div>

          {/* Save Button */}
          <div className="flex-shrink-0">
            <button
              onClick={handleSavePreferences}
              disabled={!hasUnsavedChanges || isSaving}
              className={`px-8 py-3 rounded-lg font-semibold transition-all whitespace-nowrap ${
                hasUnsavedChanges && !isSaving
                  ? 'bg-amber-500 hover:bg-amber-600 text-black'
                  : 'bg-gray-800 text-gray-600 cursor-not-allowed'
              }`}
            >
              {isSaving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>

        {/* Champion Pool Section */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-2xl font-bold text-white">Champion Pool</h2>
            <button
              onClick={() => setShowChampionPicker(true)}
              className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-black font-semibold rounded-lg transition-all flex items-center gap-2"
            >
              <Plus size={20} />
              Add Champion
            </button>
          </div>

          <div className="flex-1 overflow-y-auto overflow-x-hidden pr-2">
            {championPool.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <p className="text-gray-500 text-lg">No champions in your pool yet. Add some to get started!</p>
              </div>
            ) : (
              <div className="space-y-2">
                {championPool.map((champion) => (
                  <div
                    key={champion.id}
                    className="flex items-center gap-4 bg-gray-900 border border-gray-800 rounded-lg p-4 hover:border-gray-700 transition-all"
                  >
                    {/* Champion Image */}
                    <div className="w-16 h-16 rounded-lg overflow-hidden border-2 border-gray-700 flex-shrink-0">
                      <img
                        src={getChampionImageUrl(champion.champion_name)}
                        alt={champion.champion_name}
                        className="w-full h-full object-cover"
                      />
                    </div>

                    {/* Champion Name */}
                    <div className="flex-1">
                      <h3 className="text-white font-semibold text-lg">{champion.champion_name}</h3>
                    </div>

                    {/* Proficiency Stars */}
                    <div className="flex gap-1">
                      {[1, 2, 3, 4, 5].map((star) => (
                        <button
                          key={star}
                          onClick={() => handleUpdateProficiency(champion.id, star)}
                          className={`transition-colors ${
                            star <= (champion.proficiency || 0)
                              ? 'text-amber-500'
                              : 'text-gray-600 hover:text-amber-400'
                          }`}
                          title={`Rate ${star} stars`}
                        >
                          <span className="text-2xl">{star <= (champion.proficiency || 0) ? '★' : '☆'}</span>
                        </button>
                      ))}
                    </div>

                    {/* Remove Button */}
                    <button
                      onClick={() => handleRemoveChampion(champion.id)}
                      className="p-2 text-red-500 hover:text-red-400 transition-colors"
                      title="Remove champion"
                    >
                      <Trash2 size={20} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Champion Picker Modal */}
        {showChampionPicker && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
            <div className="bg-gray-900 p-6 rounded-lg border-2 border-gray-800 w-[90%] max-w-5xl h-[80vh] flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-2xl font-semibold text-white">Add Champion to Pool</h3>
                <button onClick={() => setShowChampionPicker(false)} className="text-gray-400 hover:text-white">
                  <X size={28} />
                </button>
              </div>

              <div className="relative mb-4 flex-shrink-0">
                <Search size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={championSearch}
                  onChange={(e) => setChampionSearch(e.target.value)}
                  placeholder="Search champions..."
                  className="w-full pl-12 pr-4 py-3 bg-black border-2 border-gray-800 rounded-lg text-white focus:outline-none focus:border-gray-700"
                />
              </div>
              <div className="flex-1 overflow-y-auto overflow-x-hidden pr-2">
                <div className="grid grid-cols-10 gap-2 auto-rows-max">
                  {filteredChampions.map(champ => (
                    <button
                      key={champ}
                      onClick={() => handleAddChampion(champ)}
                      className="aspect-square rounded-lg overflow-hidden border-2 border-gray-800 hover:border-amber-500 transition-all"
                    >
                      <img src={getChampionImageUrl(champ)} alt={champ} className="w-full h-full object-cover" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Profile Picture Picker Modal */}
        {showProfilePicker && (
          <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
            <div className="bg-gray-900 p-6 rounded-lg border-2 border-gray-800 w-[90%] max-w-5xl h-[80vh] flex flex-col">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-2xl font-semibold text-white">Select Profile Picture</h3>
                <button onClick={() => setShowProfilePicker(false)} className="text-gray-400 hover:text-white">
                  <X size={28} />
                </button>
              </div>
              <div className="relative mb-4 flex-shrink-0">
                <Search size={20} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={profileSearch}
                  onChange={(e) => setProfileSearch(e.target.value)}
                  placeholder="Search champions..."
                  className="w-full pl-12 pr-4 py-3 bg-black border-2 border-gray-800 rounded-lg text-white focus:outline-none focus:border-gray-700"
                />
              </div>
              <div className="flex-1 overflow-y-auto overflow-x-hidden pr-2">
                <div className="grid grid-cols-10 gap-2 auto-rows-max">
                  {filteredProfileChampions.map(champ => (
                    <button
                      key={champ}
                      onClick={() => handleSelectProfilePicture(champ)}
                      className={`aspect-square rounded-lg overflow-hidden border-2 transition-all hover:scale-105 ${profilePicture === champ ? 'border-amber-500 ring-2 ring-amber-500/50' : 'border-gray-800'}`}
                    >
                      <img src={getChampionImageUrl(champ)} alt={champ} className="w-full h-full object-cover" />
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
