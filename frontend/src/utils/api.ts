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
    // Only redirect on 401 if it's NOT from champion-pool or if we're already on a protected page
    if (error.response?.status === 401) {
      const url = error.config?.url || '';
      const isChampionPoolRequest = url.includes('/champion-pool');

      // Don't redirect to login if:
      // 1. It's a champion pool request (guest users can view draft without pool)
      // 2. We're already on the login page
      if (!isChampionPoolRequest && window.location.pathname !== '/login') {
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
      console.error('Failed to fetch champions from API, falling back...', error);
      
      // Fallback 1: Try direct Data Dragon API with latest patch
      try {
        // First get latest version
        const versionResponse = await axios.get(
          'https://ddragon.leagueoflegends.com/api/versions.json',
          { timeout: 5000 }
        );
        const latestVersion = versionResponse.data[0];

        // Then fetch champion data
        const ddResponse = await axios.get(
          `https://ddragon.leagueoflegends.com/cdn/${latestVersion}/data/en_US/champion.json`,
          { timeout: 5000 }
        );

        const championsData = ddResponse.data.data;
        return Object.keys(championsData).map(id => championsData[id].name);
        
      } catch (ddError) {
        console.error('Failed to fetch from Data Dragon too:', ddError);
        
        // Fallback 2: Return mock data (updated for patch 16.1.1)
        return [
          "Aatrox", "Ahri", "Akali", "Akshan", "Alistar", "Ambessa", "Amumu", "Anivia", "Annie", "Aphelios",
          "Ashe", "Aurelion Sol", "Aurora", "Azir", "Bard", "Bel'Veth", "Blitzcrank", "Brand", "Braum", "Briar",
          "Caitlyn", "Camille", "Cassiopeia", "Cho'Gath", "Corki", "Darius", "Diana", "Dr. Mundo", "Draven",
          "Ekko", "Elise", "Evelynn", "Ezreal", "Fiddlesticks", "Fiora", "Fizz", "Galio", "Gangplank", "Garen",
          "Gnar", "Gragas", "Graves", "Gwen", "Hecarim", "Heimerdinger", "Hwei", "Illaoi", "Irelia", "Ivern",
          "Janna", "Jarvan IV", "Jax", "Jayce", "Jhin", "Jinx", "K'Sante", "Kai'Sa", "Kalista", "Karma",
          "Karthus", "Kassadin", "Katarina", "Kayle", "Kayn", "Kennen", "Kha'Zix", "Kindred", "Kled",
          "Kog'Maw", "LeBlanc", "Lee Sin", "Leona", "Lillia", "Lissandra", "Lucian", "Lulu", "Lux",
          "Malphite", "Malzahar", "Maokai", "Master Yi", "Mel", "Milio", "Miss Fortune", "Mordekaiser",
          "Morgana", "Naafiri", "Nami", "Nasus", "Nautilus", "Neeko", "Nidalee", "Nilah", "Nocturne",
          "Nunu & Willump", "Olaf", "Orianna", "Ornn", "Pantheon", "Poppy", "Pyke", "Qiyana", "Quinn",
          "Rakan", "Rammus", "Rek'Sai", "Rell", "Renata Glasc", "Renekton", "Rengar", "Riven", "Rumble",
          "Ryze", "Samira", "Sejuani", "Senna", "Seraphine", "Sett", "Shaco", "Shen", "Shyvana", "Singed",
          "Sion", "Sivir", "Skarner", "Smolder", "Sona", "Soraka", "Swain", "Sylas", "Syndra", "Tahm Kench",
          "Taliyah", "Talon", "Taric", "Teemo", "Thresh", "Tristana", "Trundle", "Tryndamere", "Twisted Fate",
          "Twitch", "Udyr", "Urgot", "Varus", "Vayne", "Veigar", "Vel'Koz", "Vex", "Vi", "Viego", "Viktor",
          "Vladimir", "Volibear", "Warwick", "Wukong", "Xayah", "Xerath", "Xin Zhao", "Yasuo", "Yone",
          "Yorick", "Yunara", "Yuumi", "Zaahen", "Zac", "Zed", "Zeri", "Ziggs", "Zilean", "Zoe", "Zyra"
        ];
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