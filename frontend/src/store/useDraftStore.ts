// frontend/src/store/useDraftStore.ts
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
  // State
  settings: DraftSettings;
  selections: DraftSelections;
  currentTurn: number;
  availablePatches: string[];
  champions: string[];
  isLoading: boolean;
  gameplan: any;
  
  // Draft ID for backend sync
  draftId: string | null;
  
  // Actions
  setGameMode: (mode: GameModeType) => void;
  setTeamSide: (side: TeamSide) => void;
  setRole: (role: RoleType) => void;
  setElo: (elo: string) => void;
  setRegion: (region: string) => void;
  setPatch: (patch: string) => void;
  setPhase: (phase: 'BAN' | 'PICK') => void;
  
  // Draft actions
  nextTurn: () => void;
  previousTurn: () => void;
  setTurn: (turn: number) => void;
  
  addBan: (champion: string, side: TeamSide) => void;
  removeBan: (champion: string, side: TeamSide) => void;
  addPick: (champion: string, role: RoleType, side: TeamSide) => void;
  removePick: (index: number, side: TeamSide) => void;
  movePick: (fromIndex: number, toIndex: number, side: TeamSide) => void;
  
  resetDraft: () => void;
  saveDraft: () => Promise<void>;
  loadDraft: (draftId: string) => Promise<void>;
  
  // Data loading
  setChampions: (champions: string[]) => void;
  setLoading: (loading: boolean) => void;
  setGameplan: (gameplan: any) => void;
  generateGameplan: () => Promise<void>;
  
  // Current picker info
  getCurrentPicker: () => { side: TeamSide; position: number; isBan: boolean } | null;
}

const defaultSettings: DraftSettings = {
  mode: 'DRAFT',
  side: 'BLUE',
  role: 'TOP',
  elo: 'PLATINUM',
  region: 'NA',
  patch: '14.4.1',
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

export const useDraftStore = create<DraftState>()(
  persist(
    (set, get) => ({
      settings: defaultSettings,
      selections: defaultSelections,
      currentTurn: 0,
      availablePatches: ['14.4.1', '14.3.1', '14.2.1', '14.1.1'],
      champions: [],
      isLoading: false,
      gameplan: null,
      draftId: null,

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
        currentTurn: Math.min(state.currentTurn + 1, 19)
      })),

      previousTurn: () => set((state) => ({
        currentTurn: Math.max(state.currentTurn - 1, 0)
      })),

      setTurn: (turn) => set({ currentTurn: Math.max(0, Math.min(turn, 19)) }),

      addBan: (champion, side) => set((state) => {
        const bans = [...state.selections.bans[side.toLowerCase() as keyof typeof state.selections.bans]];
        if (bans.length < 5 && !bans.includes(champion)) {
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

      removeBan: (champion, side) => set((state) => {
        const bans = [...state.selections.bans[side.toLowerCase() as keyof typeof state.selections.bans]];
        const index = bans.indexOf(champion);
        if (index !== -1) {
          bans.splice(index, 1);
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
        
        // Direct swap
        const temp = picks[fromIndex];
        picks[fromIndex] = picks[toIndex];
        picks[toIndex] = temp;
        
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
        currentTurn: 0,
        gameplan: null,
        draftId: null,
      }),

      saveDraft: async () => {
        const state = get();
        try {
          // This will be implemented when backend is ready
          console.log('Saving draft:', state);
        } catch (error) {
          console.error('Failed to save draft:', error);
        }
      },

      loadDraft: async (draftId: string) => {
        try {
          // This will be implemented when backend is ready
          console.log('Loading draft:', draftId);
        } catch (error) {
          console.error('Failed to load draft:', error);
        }
      },

      setChampions: (champions) => set({ champions }),
      
      setLoading: (loading) => set({ isLoading: loading }),
      
      setGameplan: (gameplan) => set({ gameplan }),
      
      generateGameplan: async () => {
        const state = get();
        try {
          // This will be implemented when LLM is ready
          console.log('Generating gameplan for:', state.selections);
          set({ gameplan: { summary: 'Gameplan will be generated by LLM' } });
        } catch (error) {
          console.error('Failed to generate gameplan:', error);
        }
      },

      getCurrentPicker: () => {
        const state = get();
        const turn = state.currentTurn;
        
        if (turn < 10) {
          // Ban phase
          const side: TeamSide = turn % 2 === 0 ? 'BLUE' : 'RED';
          const position = Math.floor(turn / 2);
          return { side, position, isBan: true };
        } else {
          // Pick phase
          const pickOrder = [
            { side: 'BLUE' as TeamSide, position: 0 },
            { side: 'RED' as TeamSide, position: 0 },
            { side: 'RED' as TeamSide, position: 1 },
            { side: 'BLUE' as TeamSide, position: 1 },
            { side: 'BLUE' as TeamSide, position: 2 },
            { side: 'RED' as TeamSide, position: 2 },
            { side: 'RED' as TeamSide, position: 3 },
            { side: 'BLUE' as TeamSide, position: 3 },
            { side: 'BLUE' as TeamSide, position: 4 },
            { side: 'RED' as TeamSide, position: 4 },
          ];
          const picker = pickOrder[turn - 10];
          return { ...picker, isBan: false };
        }
      },
    }),
    {
      name: 'tryndraft-draft-state',
    }
  )
);