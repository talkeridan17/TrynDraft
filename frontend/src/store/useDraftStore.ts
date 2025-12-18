import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type GameModeType = 'SWIFT' | 'DRAFT' | 'RANKED' | 'ARAM' | 'FLEX' | 'CLASH' | 'CUSTOM' | 'PRO';
export type TeamSide = 'BLUE' | 'RED';
export type RoleType = 'TOP' | 'JUNGLE' | 'MID' | 'ADC' | 'SUPPORT' | 'FILL';

interface DraftSettings {
  mode: GameModeType;
  side: TeamSide;
  role: RoleType;
  elo: string;
  region: string;
  patch: string;
  phase: 'BAN' | 'PICK';
}

interface DraftSelections {
  bans: {
    blue: string[];
    red: string[];
  };
  picks: {
    blue: Array<{ champion: string; role: RoleType }>;
    red: Array<{ champion: string; role: RoleType }>;
  };
}

interface DraftState {
  settings: DraftSettings;
  selections: DraftSelections;
  currentTurn: number; // Simple turn counter instead of complex draftOrder
  availablePatches: string[];
  champions: string[];
  isLoading: boolean;
  
  // Actions
  setGameMode: (mode: GameModeType) => void;
  setTeamSide: (side: TeamSide) => void;
  setRole: (role: RoleType) => void;
  setElo: (elo: string) => void;
  setRegion: (region: string) => void;
  setPatch: (patch: string) => void;
  setPhase: (phase: 'BAN' | 'PICK') => void;
  nextTurn: () => void;
  
  addBan: (champion: string, side: TeamSide) => void;
  addPick: (champion: string, role: RoleType, side: TeamSide) => void;
  removePick: (index: number, side: TeamSide) => void;
  movePick: (fromIndex: number, toIndex: number, side: TeamSide) => void;
  resetDraft: () => void;
  
  setChampions: (champions: string[]) => void;
  setLoading: (loading: boolean) => void;
}

const defaultSettings: DraftSettings = {
  mode: 'DRAFT',
  side: 'BLUE',
  role: 'TOP',
  elo: 'PLATINUM',
  region: 'NA',
  patch: '14.1',
  phase: 'BAN',
};

const defaultSelections: DraftSelections = {
  bans: {
    blue: [],
    red: [],
  },
  picks: {
    blue: Array(5).fill({ champion: '', role: 'FILL' }),
    red: Array(5).fill({ champion: '', role: 'FILL' }),
  },
};

const availablePatches = ['14.1', '13.24', '13.23'];

export const useDraftStore = create<DraftState>()(
  persist(
    (set) => ({
      settings: defaultSettings,
      selections: defaultSelections,
      currentTurn: 1,
      availablePatches,
      champions: [],
      isLoading: false,

      setGameMode: (mode) => set((state) => ({ 
        settings: { ...state.settings, mode } 
      })),

      setTeamSide: (side) => set((state) => ({ 
        settings: { ...state.settings, side } 
      })),

      setRole: (role) => set((state) => ({ 
        settings: { ...state.settings, role } 
      })),

      setElo: (elo) => set((state) => ({ 
        settings: { ...state.settings, elo } 
      })),

      setRegion: (region) => set((state) => ({ 
        settings: { ...state.settings, region } 
      })),

      setPatch: (patch) => set((state) => ({ 
        settings: { ...state.settings, patch } 
      })),

      setPhase: (phase) => set((state) => ({ 
        settings: { ...state.settings, phase } 
      })),

      nextTurn: () => set((state) => ({
        currentTurn: state.currentTurn + 1
      })),

      addBan: (champion, side) => set((state) => {
        const bans = [...state.selections.bans[side.toLowerCase() as keyof typeof state.selections.bans]];
        if (bans.length < 5) {
          bans.push(champion);
        }
        return {
          selections: {
            ...state.selections,
            bans: {
              ...state.selections.bans,
              [side.toLowerCase()]: bans,
            },
          },
        };
      }),

      addPick: (champion, role, side) => set((state) => {
        const picks = [...state.selections.picks[side.toLowerCase() as keyof typeof state.selections.picks]];
        const emptyIndex = picks.findIndex(p => p.champion === '');
        if (emptyIndex !== -1) {
          picks[emptyIndex] = { champion, role };
        }
        return {
          selections: {
            ...state.selections,
            picks: {
              ...state.selections.picks,
              [side.toLowerCase()]: picks,
            },
          },
        };
      }),

      removePick: (index, side) => set((state) => {
        const picks = [...state.selections.picks[side.toLowerCase() as keyof typeof state.selections.picks]];
        picks[index] = { champion: '', role: 'FILL' };
        return {
          selections: {
            ...state.selections,
            picks: {
              ...state.selections.picks,
              [side.toLowerCase()]: picks,
            },
          },
        };
      }),

      movePick: (fromIndex, toIndex, side) => set((state) => {
        const picks = [...state.selections.picks[side.toLowerCase() as keyof typeof state.selections.picks]];
        
        // Direct swap instead of insert
        if (fromIndex >= 0 && toIndex >= 0 && fromIndex < picks.length && toIndex < picks.length) {
          const temp = picks[fromIndex];
          picks[fromIndex] = picks[toIndex];
          picks[toIndex] = temp;
        }
        
        return {
          selections: {
            ...state.selections,
            picks: {
              ...state.selections.picks,
              [side.toLowerCase()]: picks,
            },
          },
        };
      }),

      resetDraft: () => set({
        settings: defaultSettings,
        selections: defaultSelections,
        currentTurn: 1,
      }),

      setChampions: (champions) => set({ champions }),
      
      setLoading: (loading) => set({ isLoading: loading }),
    }),
    {
      name: 'tryndraft-draft-state',
    }
  )
);