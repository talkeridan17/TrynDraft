import axios from 'axios';
import { fetchAndStoreDeeplolByRiotIds, getLLMModelOptions, importDeeplolJson, runFrontendExplainability, runFrontendRanking, setLLMModel } from './frontendAi';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000,
});

// No auth interceptors: frontend-only mode.

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
  role: string;  // User's selected role
  elo?: string;
  patch?: string;
  mode?: 'SOLOQ' | 'CLASH';
  solo_riot_id?: string;
  clash_blue_ids?: string[];
  clash_red_ids?: string[];
  clash_blue_by_role?: Array<{ role: string; riot_id: string }>;
  clash_red_by_role?: Array<{ role: string; riot_id: string }>;
  clash_enemy_unknown?: boolean;
  bans_blue: string[];
  bans_red: string[];
  picks_blue: Array<{ champion: string; role: string }>;
  picks_red: Array<{ champion: string; role: string }>;
  is_user_turn?: boolean; // Flag for detailed vs brief LLM response
  // Current slot info for proper recommendations
  current_slot_role?: string;    // Role of the slot being picked (e.g., TOP, JUNGLE)
  current_slot_side?: string;    // Side picking (BLUE or RED)
  current_slot_position?: number; // Position 0-4
  // User can override the assumed matchup
  matchup_override?: string;     // Champion name user selected as their matchup
}

export interface MatchupInfo {
  matchup_champion: string | null;  // The enemy champion assumed to be in target role
  matchup_type: 'counter' | 'blind' | 'unknown';
  confidence: number;  // 0-1, how confident we are in the matchup prediction
  reasoning: string;   // Human-readable explanation
  all_enemy_roles: Record<string, string>;  // champion -> predicted role
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
  // Role-specific stats for transparency
  role_win_rate?: number;
  role_games?: number;
  role_kda?: number | null;
  target_role?: string;
}

export interface SortedChampionsResponse {
  champions: ScoredChampion[];
  model_type: string;
  phase: string;
  target_role: string;
  user_role: string;
  turn: number;
  is_user_role: boolean;
  matchup: MatchupInfo;
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
  // Role and matchup context
  target_role?: string;
  user_role?: string;
  is_user_role?: boolean;
  matchup?: MatchupInfo;
}

export const recommendationService = {
  // Get champions sorted by NN recommendation score
  getSortedChampions: async (draftState: DraftState): Promise<SortedChampionsResponse> => {
    try {
      const local = await runFrontendRanking(draftState);
      return {
        champions: local.champions,
        model_type: local.model_type,
        phase: draftState.phase,
        target_role: draftState.current_slot_role || draftState.role,
        user_role: draftState.role,
        turn: draftState.turn,
        is_user_role: (draftState.current_slot_role || draftState.role) === draftState.role,
        matchup: {
          matchup_champion: null,
          matchup_type: 'unknown',
          confidence: 0.5,
          reasoning: 'Frontend-only mode does not infer lane matchup yet.',
          all_enemy_roles: {}
        }
      };
    } catch (error) {
      console.error('Failed to get sorted champions:', error);
      return {
        champions: [],
        model_type: 'onnx_unavailable',
        phase: draftState.phase,
        target_role: draftState.role,
        user_role: draftState.role,
        turn: draftState.turn,
        is_user_role: true,
        matchup: {
          matchup_champion: null,
          matchup_type: 'unknown',
          confidence: 0,
          reasoning: 'Required model unavailable. Ensure /models/model.onnx and /models/model.onnx.data are present.',
          all_enemy_roles: {}
        }
      };
    }
  },

  // Get LLM analysis for current draft state
  getAnalysis: async (draftState: DraftState): Promise<AnalysisResult | null> => {
    try {
      const local = await runFrontendRanking(draftState);
      const topChampions = local.softmaxTop5.map((x: any) => ({
        name: x.champion,
        softmax: x.softmax,
        proficiency: x.proficiency
      }));
      const llm = await runFrontendExplainability({
        draftState,
        topChampions,
        isUserTurn: draftState.is_user_turn
      });
      return {
        analysis: llm.analysis,
        stage: draftState.phase,
        turn: draftState.turn,
        phase: draftState.phase,
        advantage: 'N/A',
        blue_power: 0,
        red_power: 0,
        source: llm.source,
        model: llm.model,
        recommendations: topChampions.map((c: { name: string }) => c.name),
        target_role: draftState.current_slot_role || draftState.role,
        user_role: draftState.role,
        is_user_role: (draftState.current_slot_role || draftState.role) === draftState.role,
      };
    } catch (error) {
      console.error('Failed to get draft analysis:', error);
      return null;
    }
  },

  // Get full gameplan when draft is complete
  getGameplan: async (draftState: DraftState): Promise<any> => {
    const analysis = await recommendationService.getAnalysis(draftState);
    return analysis;
  },

  // Get draft statistics when draft is complete
  getDraftStats: async (draftState: DraftState): Promise<DraftStats | null> => {
    try {
      const local = await runFrontendRanking(draftState);
      const top = local.champions[0];
      return {
        lane_matchup: {
          your_champion: draftState.picks_blue[0]?.champion || null,
          enemy_champion: draftState.picks_red[0]?.champion || null,
          win_rate: top ? Number((top.win_rate * 100).toFixed(1)) : 50,
          games: top?.role_games || 0,
          confidence: top?.role_games && top.role_games > 25 ? 'high' : top?.role_games && top.role_games > 10 ? 'medium' : 'low',
        },
        comp_win: { your_team: 50, enemy_team: 50 },
        synergy: {
          your_team: { score: 5, max_score: 10, details: [] },
          enemy_team: { score: 5, max_score: 10, details: [] },
        },
        damage_split: {
          your_team: { ad: 50, ap: 50 },
          enemy_team: { ad: 50, ap: 50 },
        },
        team_power: { your_team: 50, enemy_team: 50 },
      };
    } catch (error) {
      console.error('Failed to get draft stats:', error);
      return null;
    }
  },

  // Check which models are available
  getAvailableModels: async (): Promise<{ models: Record<string, boolean>; has_any_model: boolean; recommendation_mode: string }> => {
    try {
      const llm = getLLMModelOptions();
      const models = llm.options.reduce((acc, model) => {
        acc[model.id] = true;
        return acc;
      }, {} as Record<string, boolean>);
      return { models, has_any_model: true, recommendation_mode: 'frontend_onnx_llm' };
    } catch (error) {
      console.error('Failed to get available models:', error);
      return { models: {}, has_any_model: false, recommendation_mode: 'error' };
    }
  },

  getFrontendLLMOptions: () => getLLMModelOptions(),
  setFrontendLLMModel: (modelId: string) => setLLMModel(modelId),
  importDeeplolProficiencies: (rawJson: string) => importDeeplolJson(rawJson),
  fetchDeeplolProficienciesByRiotIds: async (riotIds: string[], region?: string, season?: number) => fetchAndStoreDeeplolByRiotIds(riotIds, region, season),
};

// Draft Stats interface for completed draft
export interface DraftStats {
  lane_matchup: {
    your_champion: string | null;
    enemy_champion: string | null;
    win_rate: number;
    games: number;
    confidence: 'high' | 'medium' | 'low';
  };
  comp_win: {
    your_team: number;
    enemy_team: number;
  };
  synergy: {
    your_team: {
      score: number;
      max_score: number;
      details: Array<{ pair: string; win_rate: number; games: number; synergy: string }>;
    };
    enemy_team: {
      score: number;
      max_score: number;
      details: Array<{ pair: string; win_rate: number; games: number; synergy: string }>;
    };
  };
  damage_split: {
    your_team: { ad: number; ap: number };
    enemy_team: { ad: number; ap: number };
  };
  team_power: {
    your_team: number;
    enemy_team: number;
  };
}

// Login/profile APIs intentionally removed in frontend-only mode.
