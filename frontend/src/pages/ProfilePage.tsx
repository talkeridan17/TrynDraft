// frontend/src/pages/ProfilePage.tsx
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  User, Settings, Gamepad2, Globe, Star, Trophy, 
  Clock, Save, Trash2, Plus, LogOut
} from 'lucide-react';
import { authService } from '../utils/api'; // Removed championService

// ... rest of the code remains the same ...

interface UserData {
  id: string;
  email: string;
  username: string;
  summoner_name?: string;
  region: string;
  created_at: string;
  preferences?: any;
}

interface ChampionPoolItem {
  id: string;
  champion_name: string;
  role: string;
  proficiency: number;
  is_favorite: boolean;
  games_played: number;
  win_rate?: number;
}

export const ProfilePage: React.FC = () => {
  const [user, setUser] = useState<UserData | null>(null);
  const [championPool, setChampionPool] = useState<ChampionPoolItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [newChampion, setNewChampion] = useState('');
  const [newRole, setNewRole] = useState('FILL');
  const navigate = useNavigate();

  useEffect(() => {
    loadUserData();
  }, []);

  const loadUserData = async () => {
    try {
      setLoading(true);
      const userData = await authService.getCurrentUser();
      if (userData) {
        setUser(userData);
        // Load champion pool from API
        try {
          const pool = await authService.getChampionPool();
          setChampionPool(pool);
        } catch (error) {
          console.error('Failed to load champion pool:', error);
          setChampionPool([]);
        }
      } else {
        navigate('/login');
      }
    } catch (error) {
      console.error('Failed to load user data:', error);
      navigate('/login');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    authService.logout();
    navigate('/login');
  };

  const handleUpdateProfile = async () => {
    if (!user) return;

    try {
      await authService.updateUser({
        summoner_name: user.summoner_name,
        region: user.region
      });
      setEditing(false);
    } catch (error) {
      console.error('Failed to update profile:', error);
    }
  };

  const handleAddChampion = async () => {
    if (!newChampion.trim()) return;

    try {
      await authService.addToChampionPool({
        champion_name: newChampion,
        role: newRole,
        proficiency: 1
      });

      // Reload champion pool
      const pool = await authService.getChampionPool();
      setChampionPool(pool);
      setNewChampion('');
    } catch (error) {
      console.error('Failed to add champion:', error);
    }
  };

  const handleRemoveChampion = async (championName: string) => {
    try {
      await authService.removeFromChampionPool(championName);
      setChampionPool(championPool.filter(item => item.champion_name !== championName));
    } catch (error) {
      console.error('Failed to remove champion:', error);
    }
  };

  const handleToggleFavorite = (id: string) => {
    setChampionPool(championPool.map(item => 
      item.id === id ? { ...item, is_favorite: !item.is_favorite } : item
    ));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-gray-400">Loading profile...</div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <h1 className="text-3xl font-bold text-white">Profile & Settings</h1>
        <button
          onClick={handleLogout}
          className="flex items-center space-x-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition-colors"
        >
          <LogOut size={18} />
          <span>Logout</span>
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column - User Info */}
        <div className="lg:col-span-2 space-y-6">
          {/* Profile Card */}
          <div className="bg-white/5 rounded-xl p-6 border border-white/10">
            <div className="flex items-center justify-between mb-6">
              <div className="flex items-center space-x-4">
                <div className="w-16 h-16 bg-gradient-to-br from-primary-600 to-secondary-600 rounded-full flex items-center justify-center">
                  <User size={28} className="text-white" />
                </div>
                <div>
                  <h2 className="text-2xl font-bold text-white">{user.username}</h2>
                  <p className="text-gray-400">{user.email}</p>
                </div>
              </div>
              <button
                onClick={() => setEditing(!editing)}
                className="flex items-center space-x-2 px-4 py-2 bg-white/10 hover:bg-white/20 rounded-lg transition-colors"
              >
                <Settings size={18} />
                <span>{editing ? 'Cancel' : 'Edit'}</span>
              </button>
            </div>

            {editing ? (
              <div className="space-y-4">
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Summoner Name</label>
                  <input
                    type="text"
                    defaultValue={user.summoner_name || ''}
                    className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white"
                    placeholder="Your League name"
                  />
                </div>
                <div>
                  <label className="block text-sm text-gray-400 mb-2">Region</label>
                  <select
                    defaultValue={user.region}
                    className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white"
                  >
                    <option value="NA">NA</option>
                    <option value="EUW">EUW</option>
                    <option value="EUNE">EUNE</option>
                    <option value="KR">KR</option>
                    <option value="BR">BR</option>
                  </select>
                </div>
                <button
                  onClick={handleUpdateProfile}
                  className="w-full bg-gradient-to-r from-primary-600 to-secondary-600 text-white py-2 rounded-lg font-medium"
                >
                  Save Changes
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center space-x-3 p-3 bg-white/5 rounded-lg">
                  <Gamepad2 size={20} className="text-primary-400" />
                  <div>
                    <div className="text-sm text-gray-400">Summoner</div>
                    <div className="text-white font-medium">
                      {user.summoner_name || 'Not set'}
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-3 p-3 bg-white/5 rounded-lg">
                  <Globe size={20} className="text-primary-400" />
                  <div>
                    <div className="text-sm text-gray-400">Region</div>
                    <div className="text-white font-medium">{user.region}</div>
                  </div>
                </div>
                <div className="flex items-center space-x-3 p-3 bg-white/5 rounded-lg">
                  <Clock size={20} className="text-primary-400" />
                  <div>
                    <div className="text-sm text-gray-400">Member Since</div>
                    <div className="text-white font-medium">
                      {new Date(user.created_at).toLocaleDateString()}
                    </div>
                  </div>
                </div>
                <div className="flex items-center space-x-3 p-3 bg-white/5 rounded-lg">
                  <Trophy size={20} className="text-primary-400" />
                  <div>
                    <div className="text-sm text-gray-400">Drafts Created</div>
                    <div className="text-white font-medium">0</div>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Champion Pool */}
          <div className="bg-white/5 rounded-xl p-6 border border-white/10">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-white">Champion Pool</h3>
              <div className="flex items-center space-x-2">
                <input
                  type="text"
                  value={newChampion}
                  onChange={(e) => setNewChampion(e.target.value)}
                  placeholder="Champion name"
                  className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white"
                />
                <select
                  value={newRole}
                  onChange={(e) => setNewRole(e.target.value)}
                  className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-white"
                >
                  <option value="FILL">Fill</option>
                  <option value="TOP">Top</option>
                  <option value="JUNGLE">Jungle</option>
                  <option value="MID">Mid</option>
                  <option value="ADC">ADC</option>
                  <option value="SUPPORT">Support</option>
                </select>
                <button
                  onClick={handleAddChampion}
                  className="p-1.5 bg-primary-600 hover:bg-primary-700 rounded-lg"
                >
                  <Plus size={18} className="text-white" />
                </button>
              </div>
            </div>

            {championPool.length === 0 ? (
              <div className="text-center py-8 text-gray-500">
                <Star size={48} className="mx-auto mb-4 opacity-30" />
                <p>Your champion pool is empty</p>
                <p className="text-sm mt-2">Add champions you're comfortable playing</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {championPool.map((champ) => (
                  <div
                    key={champ.id}
                    className="flex items-center justify-between p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors"
                  >
                    <div className="flex items-center space-x-3">
                      <button
                        onClick={() => handleToggleFavorite(champ.id)}
                        className={`p-1 ${champ.is_favorite ? 'text-yellow-500' : 'text-gray-500'}`}
                      >
                        <Star size={16} fill={champ.is_favorite ? 'currentColor' : 'none'} />
                      </button>
                      <div>
                        <div className="font-medium text-white">{champ.champion_name}</div>
                        <div className="text-xs text-gray-400">{champ.role} • Proficiency: {champ.proficiency}/5</div>
                      </div>
                    </div>
                    <button
                      onClick={() => handleRemoveChampion(champ.champion_name)}
                      className="p-1 text-gray-500 hover:text-red-400"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column - Settings */}
        <div className="space-y-6">
          {/* Preferences */}
          <div className="bg-white/5 rounded-xl p-6 border border-white/10">
            <h3 className="text-xl font-bold text-white mb-4">Preferences</h3>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-white font-medium">Default Game Mode</div>
                  <div className="text-sm text-gray-400">Draft</div>
                </div>
                <button className="px-3 py-1 bg-white/10 rounded-lg text-sm">
                  Change
                </button>
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-white font-medium">Default Role</div>
                  <div className="text-sm text-gray-400">Fill</div>
                </div>
                <button className="px-3 py-1 bg-white/10 rounded-lg text-sm">
                  Change
                </button>
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-white font-medium">Default Elo</div>
                  <div className="text-sm text-gray-400">Platinum</div>
                </div>
                <button className="px-3 py-1 bg-white/10 rounded-lg text-sm">
                  Change
                </button>
              </div>
              
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-white font-medium">Notifications</div>
                  <div className="text-sm text-gray-400">Enabled</div>
                </div>
                <button className="px-3 py-1 bg-white/10 rounded-lg text-sm">
                  Toggle
                </button>
              </div>
            </div>
          </div>

          {/* Saved Drafts */}
          <div className="bg-white/5 rounded-xl p-6 border border-white/10">
            <h3 className="text-xl font-bold text-white mb-4">Recent Drafts</h3>
            <div className="text-center py-8 text-gray-500">
              <Save size={48} className="mx-auto mb-4 opacity-30" />
              <p>No saved drafts yet</p>
              <p className="text-sm mt-2">Your drafts will appear here</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};