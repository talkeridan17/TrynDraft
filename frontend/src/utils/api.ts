import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Champion service - UPDATED WITH REAL API CALLS
export const championService = {
  getAll: async (): Promise<string[]> => {
    try {
      const response = await api.get('/api/v1/champions');
      const champions = response.data;
      
      // Extract champion names
      if (Array.isArray(champions)) {
        return champions.map((champ: any) => champ.name || champ.id);
      }
      
      throw new Error('Invalid champion data format');
      
    } catch (error) {
      console.error('Failed to fetch champions from API, falling back...', error);
      
      // Fallback 1: Try direct Data Dragon API
      try {
        const ddResponse = await axios.get(
          'https://ddragon.leagueoflegends.com/cdn/14.5.1/data/en_US/champion.json',
          { timeout: 5000 }
        );
        
        const championsData = ddResponse.data.data;
        return Object.keys(championsData).map(id => championsData[id].name);
        
      } catch (ddError) {
        console.error('Failed to fetch from Data Dragon too:', ddError);
        
        // Fallback 2: Return mock data
        return [
          "Aatrox", "Ahri", "Akali", "Alistar", "Amumu", "Anivia", "Annie", "Aphelios",
          "Ashe", "Aurelion Sol", "Azir", "Bard", "Blitzcrank", "Brand", "Braum",
          "Caitlyn", "Camille", "Cassiopeia", "Cho'Gath", "Corki", "Darius", "Diana",
          "Draven", "Dr. Mundo", "Ekko", "Elise", "Evelynn", "Ezreal", "Fiddlesticks",
          "Fiora", "Fizz", "Galio", "Gangplank", "Garen", "Gnar", "Gragas", "Graves",
          "Hecarim", "Heimerdinger", "Illaoi", "Irelia", "Ivern", "Janna", "Jarvan IV",
          "Jax", "Jayce", "Jhin", "Jinx", "Kai'Sa", "Kalista", "Karma", "Karthus",
          "Kassadin", "Katarina", "Kayle", "Kayn", "Kennen", "Kha'Zix", "Kindred",
          "Kled", "Kog'Maw", "LeBlanc", "Lee Sin", "Leona", "Lillia", "Lissandra",
          "Lucian", "Lulu", "Lux", "Malphite", "Malzahar", "Maokai", "Master Yi",
          "Miss Fortune", "Mordekaiser", "Morgana", "Nami", "Nasus", "Nautilus",
          "Neeko", "Nidalee", "Nocturne", "Nunu & Willump", "Olaf", "Orianna",
          "Ornn", "Pantheon", "Poppy", "Pyke", "Qiyana", "Quinn", "Rakan", "Rammus",
          "Rek'Sai", "Rell", "Renekton", "Rengar", "Riven", "Rumble", "Ryze",
          "Samira", "Sejuani", "Senna", "Seraphine", "Sett", "Shaco", "Shen",
          "Shyvana", "Singed", "Sion", "Sivir", "Skarner", "Sona", "Soraka",
          "Swain", "Sylas", "Syndra", "Tahm Kench", "Taliyah", "Talon", "Taric",
          "Teemo", "Thresh", "Tristana", "Trundle", "Tryndamere", "Twisted Fate",
          "Twitch", "Udyr", "Urgot", "Varus", "Vayne", "Veigar", "Vel'Koz",
          "Vex", "Vi", "Viego", "Viktor", "Vladimir", "Volibear", "Warwick",
          "Wukong", "Xayah", "Xerath", "Xin Zhao", "Yasuo", "Yone", "Yorick",
          "Yuumi", "Zac", "Zed", "Zeri", "Ziggs", "Zilean", "Zoe", "Zyra"
        ];
      }
    }
  },

  getImageUrl: async (championName: string): Promise<string> => {
    try {
      const response = await api.get(`/api/v1/champions/${encodeURIComponent(championName)}/image`);
      return response.data.url;
    } catch (error) {
      // Fallback to Data Dragon
      const cleanName = championName.replace(/[^a-zA-Z]/g, '');
      return `https://ddragon.leagueoflegends.com/cdn/14.5.1/img/champion/${cleanName}.png`;
    }
  },

  getRoleIcon: async (role: string): Promise<string> => {
    try {
      const response = await api.get(`/api/v1/champions/roles/${role}`);
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
      const response = await api.get(`/api/v1/champions/ranks/${rank}`);
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
      const response = await api.get('/api/v1/champions/version/latest');
      return response.data.version;
    } catch (error) {
      return '14.5.1';
    }
  }
};

// Draft service - UPDATED WITH REAL ENDPOINTS
export const draftService = {
  create: async (draftData: any) => {
    const response = await api.post('/api/v1/drafts', draftData);
    return response.data;
  },

  get: async (draftId: string) => {
    const response = await api.get(`/api/v1/drafts/${draftId}`);
    return response.data;
  },

  update: async (draftId: string, draftData: any) => {
    const response = await api.put(`/api/v1/drafts/${draftId}`, draftData);
    return response.data;
  },

  addBan: async (draftId: string, champion: string, side: string) => {
    const response = await api.post(`/api/v1/drafts/${draftId}/ban`, {
      champion,
      side
    });
    return response.data;
  },

  addPick: async (draftId: string, champion: string, role: string, side: string) => {
    const response = await api.post(`/api/v1/drafts/${draftId}/pick`, {
      champion,
      role,
      side
    });
    return response.data;
  },

  getAvailableChampions: async (draftId: string) => {
    const response = await api.get(`/api/v1/drafts/${draftId}/available-champions`);
    return response.data;
  },

  delete: async (draftId: string) => {
    const response = await api.delete(`/api/v1/drafts/${draftId}`);
    return response.data;
  },

  getUserDrafts: async () => {
    const response = await api.get('/api/v1/drafts');
    return response.data;
  },

  getGameplan: async (draftState: any) => {
    try {
      const response = await api.post('/api/v1/llm/analyze', {
        draftState,
        availableChampions: draftState.availableChampions || [],
        topRecommendation: draftState.topRecommendation || ''
      });
      return response.data;
    } catch (error) {
      console.error('Failed to get gameplan:', error);
      return null;
    }
  }
};

// Auth service
export const authService = {
  login: async (username: string, password: string) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await api.post('/api/v1/users/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    
    if (response.data.access_token) {
      localStorage.setItem('access_token', response.data.access_token);
    }
    
    return response.data;
  },

  register: async (userData: any) => {
    const response = await api.post('/api/v1/users/register', userData);
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('access_token');
  },

  getCurrentUser: async () => {
    try {
      const response = await api.get('/api/v1/users/me');
      return response.data;
    } catch (error) {
      return null;
    }
  },

  updateUser: async (userData: any) => {
    const response = await api.put('/api/v1/users/me', userData);
    return response.data;
  }
};