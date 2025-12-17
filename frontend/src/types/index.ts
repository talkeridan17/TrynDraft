// Core application types for TrynDraft

// User types
export interface User {
  id: string;
  email: string;
  username: string;
  summonerName?: string;
  region?: string;
  favoriteChampions: string[];
  createdAt: Date;
  updatedAt: Date;
}

// Champion types
export interface Champion {
  id: number;
  name: string;
  key: string;
  title: string;
  blurb: string;
  roles: string[];
  difficulty: number;
  image: {
    full: string;
    sprite: string;
  };
  stats: {
    attack: number;
    defense: number;
    magic: number;
    difficulty: number;
  };
}

// Game modes
export type GameMode = 'ARAM' | 'DRAFT' | 'RANKED' | 'PRO';

// Team sides
export type TeamSide = 'BLUE' | 'RED';

// Draft state
export interface DraftState {
  mode: GameMode;
  side: TeamSide;
  bans: string[];
  picks: {
    blue: string[];
    red: string[];
  };
  currentPhase: 'BAN' | 'PICK';
}

// Recommendation types
export interface ChampionRecommendation {
  champion: Champion;
  reason: string;
  winRate: number;
  confidence: number;
  synergyScore?: number;
  counterScore?: number;
}

// LLM Analysis
export interface GamePlan {
  summary: string;
  winConditions: string[];
  keyObjectives: string[];
  teamfightStrategy: string;
  laneAssignments: string[];
  draftGrade: number;
}

// API Response types
export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

// Error types
export interface ApiError {
  message: string;
  code: string;
  status: number;
}