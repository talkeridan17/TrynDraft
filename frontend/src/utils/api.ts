import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with auth handling
export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
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
  
  register: async (userData: {
    email: string;
    username: string;
    password: string;
    summoner_name?: string;
    region?: string;
  }) => {
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
  },
};

export const championService = {
  getAll: async () => {
    try {
      const response = await api.get('/api/v1/champions');
      return response.data;
    } catch (error) {
      console.error('Failed to fetch champions:', error);
      throw error;
    }
  },
  
  getRecommendations: async (draftState: any) => {
    try {
      const response = await api.post('/api/v1/recommendations', draftState);
      return response.data;
    } catch (error) {
      console.error('Failed to fetch recommendations:', error);
      return [];
    }
  },
};

export const draftService = {
  createDraft: async (draftData: any) => {
    const response = await api.post('/api/v1/drafts', draftData);
    return response.data;
  },
  
  saveDraft: async (draftId: string, draftData: any) => {
    const response = await api.put(`/api/v1/drafts/${draftId}`, draftData);
    return response.data;
  },
  
  getDraft: async (draftId: string) => {
    const response = await api.get(`/api/v1/drafts/${draftId}`);
    return response.data;
  },
  
  getUserDrafts: async () => {
    const response = await api.get('/api/v1/drafts');
    return response.data;
  },
};