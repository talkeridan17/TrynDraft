// frontend/src/utils/api.ts
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

// Champion service
export const championService = {
  getAll: async () => {
    try {
      const response = await api.get('/api/v1/champions');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch champions:', error);
      // Fallback to static list
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
  },

  getImageUrl: async (championName: string) => {
    try {
      const response = await api.get(`/api/v1/champions/${encodeURIComponent(championName)}/image`);
      return response.data.url;
    } catch (error) {
      // Fallback to Data Dragon
      const cleanName = championName.replace(/[^a-zA-Z]/g, '');
      return `https://ddragon.leagueoflegends.com/cdn/14.4.1/img/champion/${cleanName}.png`;
    }
  },

  getRoleIcon: async (role: string) => {
    try {
      const response = await api.get(`/api/v1/champions/roles/${role}`);
      return response.data.icon;
    } catch (error) {
      // Fallback emojis
      const emojis: Record<string, string> = {
        'TOP': '🥊',
        'JUNGLE': '🌿',
        'MID': '⚔️',
        'ADC': '🎯',
        'SUPPORT': '🛡️',
        'FILL': '🔄'
      };
      return emojis[role] || '❓';
    }
  },

  getRankIcon: async (rank: string) => {
    try {
      const response = await api.get(`/api/v1/champions/ranks/${rank}`);
      return response.data.url;
    } catch (error) {
      return '';
    }
  },

  getLatestVersion: async () => {
    try {
      const response = await api.get('/api/v1/champions/version/latest');
      return response.data.version;
    } catch (error) {
      return '14.4.1';
    }
  }
};

// Draft service
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

  getGameplan: async (draftState: any) => {
    try {
      const response = await api.post('/api/v1/llm/gameplan', draftState);
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
    
    const response = await api.post('/auth/login', formData, {
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
    const response = await api.post('/auth/register', userData);
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('access_token');
  },

  getCurrentUser: async () => {
    try {
      const response = await api.get('/auth/me');
      return response.data;
    } catch (error) {
      return null;
    }
  }
};