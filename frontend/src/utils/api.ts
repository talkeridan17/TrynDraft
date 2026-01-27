import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Request interceptor for auth
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Only redirect on 401 for truly protected routes
    if (error.response?.status === 401) {
      const url = error.config?.url || '';
      // These requests are optional for guests - don't redirect on 401
      const isOptionalAuthRequest =
        url.includes('/champion-pool') ||
        url.includes('/users/me') ||
        url.includes('/preferences');

      // Don't redirect to login if:
      // 1. It's an optional auth request (guest users can view draft without these)
      // 2. We're already on the login page
      // 3. We're on the draft page (guests allowed)
      const isOnDraftPage = window.location.pathname === '/draft' || window.location.pathname === '/';
      if (!isOptionalAuthRequest && window.location.pathname !== '/login' && !isOnDraftPage) {
        localStorage.removeItem('access_token');
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Champion service - UPDATED WITH REAL API CALLS
export const championService = {
  getAll: async (): Promise<string[]> => {
    try {
      const response = await api.get('/champions/');
      const champions = response.data;
      
      // Extract champion names
      if (Array.isArray(champions)) {
        return champions.map((champ: any) => champ.name || champ.id);
      }
      
      throw new Error('Invalid champion data format');
      
    } catch (error) {
      console.error('Failed to fetch champions from API, trying Data Dragon directly...', error);

      // Fallback: Try direct Data Dragon API with latest patch
      try {
        // First get latest version
        const versionResponse = await axios.get(
          'https://ddragon.leagueoflegends.com/api/versions.json',
          { timeout: 10000 }
        );
        const latestVersion = versionResponse.data[0];

        // Then fetch champion data
        const ddResponse = await axios.get(
          `https://ddragon.leagueoflegends.com/cdn/${latestVersion}/data/en_US/champion.json`,
          { timeout: 10000 }
        );

        const championsData = ddResponse.data.data;
        const championNames = Object.keys(championsData).map(id => championsData[id].name);
        console.log(`Loaded ${championNames.length} champions from Data Dragon`);
        return championNames;

      } catch (ddError) {
        console.error('Failed to fetch from Data Dragon:', ddError);
        throw new Error('Failed to fetch champion data. Check network connection and try refreshing the page.');
      }
    }
  },

  getImageUrl: async (championName: string): Promise<string> => {
    try {
      const response = await api.get(`/champions/${encodeURIComponent(championName)}/image`);
      return response.data.url;
    } catch (error) {
      // Fallback to Data Dragon
      const cleanName = championName.replace(/[^a-zA-Z]/g, '');
      return `https://ddragon.leagueoflegends.com/cdn/14.5.1/img/champion/${cleanName}.png`;
    }
  },

  getRoleIcon: async (role: string): Promise<string> => {
    try {
      const response = await api.get(`/champions/roles/${role}`);
      return response.data.url;
    } catch (error) {
      console.error(`Failed to get role icon for ${role}:`, error);
      
      // Return proper fallback icons
      const fallbackIcons: Record<string, string> = {
        'TOP': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-top.png',
        'JUNGLE': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-jungle.png',
        'MID': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-middle.png',
        'ADC': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-bottom.png',
        'SUPPORT': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-utility.png',
        'FILL': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-fill.png'
      };
      
      return fallbackIcons[role] || fallbackIcons.FILL;
    }
  },

  getRankIcon: async (rank: string): Promise<string> => {
    try {
      const response = await api.get(`/champions/ranks/${rank}`);
      return response.data.url;
    } catch (error) {
      console.error(`Failed to get rank icon for ${rank}:`, error);
      
      // Return proper fallback icons
      const fallbackIcons: Record<string, string> = {
        'IRON': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/iron.png',
        'BRONZE': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/bronze.png',
        'SILVER': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/silver.png',
        'GOLD': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/gold.png',
        'PLATINUM': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/platinum.png',
        'EMERALD': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/emerald.png',
        'DIAMOND': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/diamond.png',
        'MASTER': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/master.png',
        'GRANDMASTER': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/grandmaster.png',
        'CHALLENGER': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/challenger.png'
      };
      
      return fallbackIcons[rank.toUpperCase()] || fallbackIcons.SILVER;
    }
  },

  getLatestVersion: async (): Promise<string> => {
    try {
      const response = await api.get('/champions/version/latest');
      return response.data.version;
    } catch (error) {
      return '14.5.1';
    }
  }
};

// Draft service - UPDATED WITH REAL ENDPOINTS
export const draftService = {
  create: async (draftData: any) => {
    const response = await api.post('/drafts', draftData);
    return response.data;
  },

  get: async (draftId: string) => {
    const response = await api.get(`/drafts/${draftId}`);
    return response.data;
  },

  update: async (draftId: string, draftData: any) => {
    const response = await api.put(`/drafts/${draftId}`, draftData);
    return response.data;
  },

  addBan: async (draftId: string, champion: string, side: string) => {
    const response = await api.post(`/drafts/${draftId}/ban`, {
      champion,
      side
    });
    return response.data;
  },

  addPick: async (draftId: string, champion: string, role: string, side: string) => {
    const response = await api.post(`/drafts/${draftId}/pick`, {
      champion,
      role,
      side
    });
    return response.data;
  },

  getAvailableChampions: async (draftId: string) => {
    const response = await api.get(`/drafts/${draftId}/available-champions`);
    return response.data;
  },

  delete: async (draftId: string) => {
    const response = await api.delete(`/drafts/${draftId}`);
    return response.data;
  },

  getUserDrafts: async () => {
    const response = await api.get('/drafts');
    return response.data;
  },

  getGameplan: async (draftState: any) => {
    try {
      const response = await api.post('/llm/analyze', {
        draftState,
        availableChampions: draftState.availableChampions || [],
        topRecommendation: draftState.topRecommendation || ''
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get gameplan:', error);
      return null;
    }
  },

  getStatistics: async (draftId: string) => {
    try {
      const response = await api.get(`/drafts/${draftId}/statistics`);
      return response.data;
    } catch (error) {
      console.error('Failed to get draft statistics:', error);
      return null;
    }
  }
};

// Recommendations service - NN + LLM powered suggestions
export interface DraftState {
  phase: 'BAN' | 'PICK' | 'COMPLETE';
  turn: number;
  side: 'BLUE' | 'RED';
  role: string;
  elo: string;
  patch: string;
  bans_blue: string[];
  bans_red: string[];
  picks_blue: Array<{ champion: string; role: string }>;
  picks_red: Array<{ champion: string; role: string }>;
  is_user_turn?: boolean; // Flag for detailed vs brief LLM response
}

export interface ScoredChampion {
  id: string;
  name: string;
  key: string;
  score: number;
  available: boolean;
  in_user_pool: boolean;
  user_proficiency: number | null;
  win_rate: number;
  pick_rate: number;
  roles: string[];
}

export interface AnalysisResult {
  analysis: string;
  stage: string;
  turn: number;
  phase: string;
  advantage: string;
  blue_power: number;
  red_power: number;
  source: string;
  model: string;
  recommendations?: string[];  // Champion suggestions
}

export const recommendationService = {
  // Get champions sorted by NN recommendation score
  getSortedChampions: async (draftState: DraftState): Promise<{ champions: ScoredChampion[]; model_type: string }> => {
    try {
      const response = await api.post('/recommendations/sorted-champions', draftState);
      return response.data;
    } catch (error) {
      console.error('Failed to get sorted champions:', error);
      return { champions: [], model_type: 'error' };
    }
  },

  // Get LLM analysis for current draft state
  getAnalysis: async (draftState: DraftState): Promise<AnalysisResult | null> => {
    try {
      const response = await api.post('/recommendations/analysis', draftState);
      return response.data;
    } catch (error) {
      console.error('Failed to get draft analysis:', error);
      return null;
    }
  },

  // Get full gameplan when draft is complete
  getGameplan: async (draftState: DraftState): Promise<any> => {
    try {
      const response = await api.post('/recommendations/gameplan', draftState);
      return response.data;
    } catch (error) {
      console.error('Failed to get gameplan:', error);
      return null;
    }
  },

  // Check which models are available
  getAvailableModels: async (): Promise<{ models: Record<string, boolean>; has_any_model: boolean; recommendation_mode: string }> => {
    try {
      const response = await api.get('/recommendations/models');
      return response.data;
    } catch (error) {
      console.error('Failed to get available models:', error);
      return { models: {}, has_any_model: false, recommendation_mode: 'error' };
    }
  }
};

// Auth service
export const authService = {
  login: async (username: string, password: string) => {
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await api.post('/users/login', formData, {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
    
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
    }
    
    return response.data;
  },

  register: async (userData: any) => {
    const response = await api.post('/users/register', userData);
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('access_token');
  },

  getCurrentUser: async () => {
    try {
      const response = await api.get('/users/me');
      return response.data;
    } catch (error) {
      return null;
    }
  },

  updateUser: async (userData: any) => {
    const response = await api.put('/users/me', userData);
    return response.data;
  },

  // Champion Pool Management
  getChampionPool: async () => {
    const response = await api.get('/users/me/champion-pool');
    return response.data;
  },

  addToChampionPool: async (championData: { champion_name: string; role?: string; playstyles?: string[] }) => {
    const response = await api.post('/users/me/champion-pool', championData);
    return response.data;
  },

  updateChampionPool: async (championId: string, updateData: { playstyles?: string[]; proficiency?: number }) => {
    const response = await api.put(`/users/me/champion-pool/${championId}`, updateData);
    return response.data;
  },

  removeFromChampionPool: async (championId: string) => {
    const response = await api.delete(`/users/me/champion-pool/${championId}`);
    return response.data;
  },

  // User Preferences
  getPreferences: async () => {
    const response = await api.get('/users/me/preferences');
    return response.data;
  },

  updatePreferences: async (preferences: { preferred_roles?: string[]; rank?: string; profile_picture?: string }) => {
    const response = await api.put('/users/me/preferences', preferences);
    return response.data;
  }
};