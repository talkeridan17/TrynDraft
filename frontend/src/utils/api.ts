/* eslint-disable @typescript-eslint/no-explicit-any */
import axios from 'axios';
import { fetchAndStoreDeeplolByRiotIds, getLLMModelOptions, importDeeplolJson, releaseOnnxSession, runFrontendExplainability, runFrontendRanking, setLLMModel, ALLY_PROF_KEY, ENEMY_PROF_KEY } from './frontendAi';

// Champion service — fetches from Riot Data Dragon CDN
export const championService = {
  getAll: async (): Promise<string[]> => {
    const versionResponse = await axios.get(
      'https://ddragon.leagueoflegends.com/api/versions.json',
      { timeout: 10000 }
    );
    const latestVersion = versionResponse.data[0];
    const ddResponse = await axios.get(
      `https://ddragon.leagueoflegends.com/cdn/${latestVersion}/data/en_US/champion.json`,
      { timeout: 10000 }
    );
    const championsData = ddResponse.data.data;
    return Object.keys(championsData).map((id: string) => championsData[id].name);
  },

  getImageUrl: (championName: string, patch: string = '16.2.1'): string => {
    const cleanName = championName.replace(/[^a-zA-Z]/g, '');
    return `https://ddragon.leagueoflegends.com/cdn/${patch}/img/champion/${cleanName}.png`;
  },

  getRoleIcon: (role: string): string => {
    const icons: Record<string, string> = {
      'TOP': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-top.png',
      'JUNGLE': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-jungle.png',
      'MID': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-middle.png',
      'ADC': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-bottom.png',
      'SUPPORT': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-utility.png',
      'FILL': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/position-selector/positions/icon-position-fill.png',
    };
    return icons[role] || icons.FILL;
  },

  getRankIcon: (rank: string): string => {
    const icons: Record<string, string> = {
      'IRON': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/iron.png',
      'BRONZE': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/bronze.png',
      'SILVER': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/silver.png',
      'GOLD': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/gold.png',
      'PLATINUM': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/platinum.png',
      'EMERALD': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/emerald.png',
      'DIAMOND': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/diamond.png',
      'MASTER': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/master.png',
      'GRANDMASTER': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/grandmaster.png',
      'CHALLENGER': 'https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-mini-crests/challenger.png',
    };
    return icons[rank.toUpperCase()] || icons.SILVER;
  },
};

// Recommendations service — ONNX + LLM powered, fully client-side
export interface DraftState {
  phase: 'BAN' | 'PICK' | 'COMPLETE';
  turn: number;
  side: 'BLUE' | 'RED';
  role: string;
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
  is_user_turn?: boolean;
  user_role?: string;
  is_user_slot?: boolean;
  current_slot_role?: string;
  current_slot_side?: string;
  current_slot_position?: number;
  matchup_override?: string;
}

export interface MatchupInfo {
  matchup_champion: string | null;
  matchup_type: 'counter' | 'blind' | 'unknown';
  confidence: number;
  reasoning: string;
  all_enemy_roles: Record<string, string>;
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
  recommendations?: string[];
  target_role?: string;
  user_role?: string;
  is_user_role?: boolean;
  matchup?: MatchupInfo;
}

export interface DraftStats {
  lane_matchup: {
    your_champion: string | null;
    enemy_champion: string | null;
    win_rate: number;
    games: number;
    confidence: 'high' | 'medium' | 'low';
  };
  comp_win: { your_team: number; enemy_team: number };
  synergy: {
    your_team: { score: number; max_score: number; details: Array<{ pair: string; win_rate: number; games: number; synergy: string }> };
    enemy_team: { score: number; max_score: number; details: Array<{ pair: string; win_rate: number; games: number; synergy: string }> };
  };
  damage_split: {
    your_team: { ad: number; ap: number };
    enemy_team: { ad: number; ap: number };
  };
  team_power: { your_team: number; enemy_team: number };
}

export const recommendationService = {
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
          reasoning: 'Frontend-only mode: matchup inference not yet implemented.',
          all_enemy_roles: {},
        },
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
          all_enemy_roles: {},
        },
      };
    }
  },

  getAnalysis: async (draftState: DraftState): Promise<AnalysisResult | null> => {
    try {
      const local = await runFrontendRanking(draftState);
      const topChampions = local.softmaxTop5.map((x: any) => ({
        name: x.champion,
        softmax: x.softmax,
        proficiency: x.proficiency,
      }));
      const llm = await runFrontendExplainability({ draftState, topChampions, isUserTurn: draftState.is_user_turn });
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

  getFrontendLLMOptions: () => getLLMModelOptions(),
  setFrontendLLMModel: (modelId: string) => setLLMModel(modelId),
  importDeeplolProficiencies: (rawJson: string) => importDeeplolJson(rawJson),
  fetchDeeplolProficienciesByRiotIds: async (riotIds: string[], region?: string, season?: number) =>
    fetchAndStoreDeeplolByRiotIds(riotIds, region, season, ALLY_PROF_KEY),
  fetchEnemyDeeplolProficienciesByRiotIds: async (riotIds: string[], region?: string, season?: number) =>
    fetchAndStoreDeeplolByRiotIds(riotIds, region, season, ENEMY_PROF_KEY),
  releaseOnnxSession: () => releaseOnnxSession(),
};
