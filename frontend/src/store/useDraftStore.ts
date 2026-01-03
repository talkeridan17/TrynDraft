import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { championService } from '../utils/api';

export type GameModeType = 'SWIFT' | 'DRAFT' | 'RANKED' | 'ARAM' | 'FLEX' | 'CLASH' | 'CUSTOM' | 'PRO';
export type TeamSide = 'BLUE' | 'RED';
export type RoleType = 'TOP' | 'JUNGLE' | 'MID' | 'ADC' | 'SUPPORT';

interface DraftSettings {
  mode: GameModeType;
  side: TeamSide;
  role: RoleType;
  elo: string;
  patch: string;
  phase: 'BAN' | 'PICK';
}

interface DraftState {
  // State
  settings: DraftSettings;
  currentTurn: number;
  
  // Champions data
  allChampions: string[];
  loadingChampions: boolean;
  
  // Draft selections
  bans: { blue: string[]; red: string[] };
  picks: { 
    blue: Array<{ champion: string; role: RoleType }>;
    red: Array<{ champion: string; role: RoleType }>;
  };
  
  // Backend draft ID
  draftId: string | null;
  
  // Computed getter functions
  getTakenChampions: () => Set<string>;
  getAvailableChampions: () => string[];
  isChampionAvailable: (champion: string) => boolean;
  getCurrentPicker: () => { side: TeamSide; position: number; isBan: boolean } | null;
  
  // Actions
  setSettings: (settings: Partial<DraftSettings>) => void;
  setCurrentTurn: (turn: number) => void;
  nextTurn: () => void;
  previousTurn: () => void;
  
  loadChampions: () => Promise<void>;
  createDraft: () => Promise<string | null>;
  syncWithBackend: () => Promise<void>;
  
  // Draft actions
  addBan: (champion: string, side: TeamSide) => boolean;
  removeBan: (champion: string, side: TeamSide) => void;
  addPick: (champion: string, role: RoleType, side: TeamSide, position?: number) => boolean;
  removePick: (index: number, side: TeamSide) => void;
  movePick: (fromIndex: number, toIndex: number, side: TeamSide) => void;
  setRole: (index: number, side: TeamSide, role: RoleType) => void;
  
  resetDraft: () => void;
}

const defaultRoles: RoleType[] = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];

const defaultSettings: DraftSettings = {
  mode: 'DRAFT',
  side: 'BLUE',
  role: 'TOP',
  elo: 'PLATINUM',
  patch: '14.5.1',
  phase: 'BAN',
};

const defaultPicks = defaultRoles.map(role => ({ champion: '', role }));

// Helper function to compute taken champions
const computeTakenChampions = (bans: { blue: string[]; red: string[] }, picks: { blue: any[]; red: any[] }) => {
  const taken = new Set<string>();
  
  // Add bans
  bans.blue.forEach(ban => taken.add(ban));
  bans.red.forEach(ban => taken.add(ban));
  
  // Add picks
  picks.blue.forEach(pick => {
    if (pick.champion) taken.add(pick.champion);
  });
  picks.red.forEach(pick => {
    if (pick.champion) taken.add(pick.champion);
  });
  
  return taken;
};

export const useDraftStore = create<DraftState>()(
  persist(
    (set, get) => ({
      settings: defaultSettings,
      currentTurn: 0,
      
      allChampions: [],
      loadingChampions: false,
      
      bans: { blue: [], red: [] },
      picks: { blue: [...defaultPicks], red: [...defaultPicks] },
      
      draftId: null,
      
      // Computed getters
      getTakenChampions: () => {
        const state = get();
        return computeTakenChampions(state.bans, state.picks);
      },
      
      getAvailableChampions: () => {
        const state = get();
        const taken = computeTakenChampions(state.bans, state.picks);
        return state.allChampions.filter(champ => !taken.has(champ));
      },
      
      isChampionAvailable: (champion: string) => {
        const taken = get().getTakenChampions();
        return !taken.has(champion);
      },
      
      getCurrentPicker: () => {
        const state = get();
        const turn = state.currentTurn;
        
        if (turn < 10) { // Ban phase
          const side: TeamSide = turn % 2 === 0 ? 'BLUE' : 'RED';
          const position = Math.floor(turn / 2);
          return { side, position, isBan: true };
        } else { // Pick phase
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
      
      // Actions
      setSettings: (newSettings) => 
        set((state) => ({ 
          settings: { ...state.settings, ...newSettings }
        })),
      
      setCurrentTurn: (turn) => 
        set({ currentTurn: Math.max(0, Math.min(turn, 19)) }),
      
      nextTurn: () => 
        set((state) => ({ currentTurn: Math.min(state.currentTurn + 1, 19) })),
      
      previousTurn: () => 
        set((state) => ({ currentTurn: Math.max(state.currentTurn - 1, 0) })),
      
      loadChampions: async () => {
        set({ loadingChampions: true });
        try {
          const champions = await championService.getAll();
          set({ 
            allChampions: champions,
            loadingChampions: false 
          });
        } catch (error) {
          console.error('Failed to load champions:', error);
          set({ loadingChampions: false });
        }
      },
      
      createDraft: async () => {
        const state = get();
        try {
          const draftData = {
            game_mode: state.settings.mode,
            side: state.settings.side,
            role: state.settings.role,
            elo: state.settings.elo,
            patch: state.settings.patch,
            phase: state.settings.phase,
            current_turn: state.currentTurn,
            bans_blue: state.bans.blue,
            bans_red: state.bans.red,
            picks_blue: state.picks.blue,
            picks_red: state.picks.red
          };
          
          // TODO: Implement actual API call
          // const draft = await draftService.create(draftData);
          // set({ draftId: draft.id });
          // return draft.id;
          
          console.log('Creating draft:', draftData);
          const mockId = `draft-${Date.now()}`;
          set({ draftId: mockId });
          return mockId;
          
        } catch (error) {
          console.error('Failed to create draft:', error);
          return null;
        }
      },
      
      syncWithBackend: async () => {
        const { draftId } = get();
        if (!draftId) return;
        
        try {
          // TODO: Implement actual API call
          // const draft = await draftService.get(draftId);
          // set({
          //   bans: { blue: draft.bans_blue || [], red: draft.bans_red || [] },
          //   picks: { blue: draft.picks_blue || defaultPicks, red: draft.picks_red || defaultPicks },
          //   currentTurn: draft.current_turn || 0,
          //   settings: {
          //     ...get().settings,
          //     phase: draft.phase || 'BAN',
          //     patch: draft.patch || '14.5.1'
          //   }
          // });
        } catch (error) {
          console.error('Failed to sync draft:', error);
        }
      },
      
      // Draft actions with validation
      addBan: (champion, side) => {
        const state = get();
        
        // Validation
        if (!state.isChampionAvailable(champion)) {
          console.error(`Champion ${champion} is already taken`);
          return false;
        }
        
        const bans = state.bans[side.toLowerCase() as 'blue' | 'red'];
        if (bans.length >= 5) {
          console.error(`${side} team already has 5 bans`);
          return false;
        }
        
        // Update state
        set((state) => {
          const newBans = {
            ...state.bans,
            [side.toLowerCase()]: [...state.bans[side.toLowerCase() as 'blue' | 'red'], champion]
          };
          
          return { bans: newBans };
        });
        
        return true;
      },
      
      removeBan: (champion, side) => {
        set((state) => ({
          bans: {
            ...state.bans,
            [side.toLowerCase()]: state.bans[side.toLowerCase() as 'blue' | 'red']
              .filter(b => b !== champion)
          }
        }));
      },
      
      addPick: (champion, role, side, position = -1) => {
        const state = get();
        
        // Validation
        if (!state.isChampionAvailable(champion)) {
          console.error(`Champion ${champion} is not available (banned or already picked)`);
          return false;
        }
        
        // Find position to place pick
        const picks = state.picks[side.toLowerCase() as 'blue' | 'red'];
        let targetPosition = position;
        
        if (targetPosition === -1) {
          // Find first empty slot
          targetPosition = picks.findIndex(p => !p.champion);
          if (targetPosition === -1) {
            console.error(`No empty slots on ${side} team`);
            return false;
          }
        } else if (picks[targetPosition]?.champion) {
          console.error(`Position ${targetPosition} on ${side} team is already filled`);
          return false;
        }
        
        // Update state
        set((state) => {
          const newPicks = [...state.picks[side.toLowerCase() as 'blue' | 'red']];
          newPicks[targetPosition] = { champion, role: role || defaultRoles[targetPosition] };
          
          const newPicksState = {
            ...state.picks,
            [side.toLowerCase()]: newPicks
          };
          
          return { picks: newPicksState };
        });
        
        return true;
      },
      
      removePick: (index, side) => {
        set((state) => {
          const newPicks = [...state.picks[side.toLowerCase() as 'blue' | 'red']];
          newPicks[index] = { champion: '', role: defaultRoles[index] };
          
          return {
            picks: {
              ...state.picks,
              [side.toLowerCase()]: newPicks
            }
          };
        });
      },
      
      movePick: (fromIndex, toIndex, side) => {
        set((state) => {
          const picks = [...state.picks[side.toLowerCase() as 'blue' | 'red']];
          
          // Swap positions
          const temp = picks[fromIndex];
          picks[fromIndex] = picks[toIndex];
          picks[toIndex] = temp;
          
          return {
            picks: {
              ...state.picks,
              [side.toLowerCase()]: picks
            }
          };
        });
      },
      
      setRole: (index, side, role) => {
        set((state) => {
          const newPicks = [...state.picks[side.toLowerCase() as 'blue' | 'red']];
          if (newPicks[index]) {
            newPicks[index].role = role;
          }
          
          return {
            picks: {
              ...state.picks,
              [side.toLowerCase()]: newPicks
            }
          };
        });
      },
      
      resetDraft: () => {
        set({
          settings: defaultSettings,
          currentTurn: 0,
          bans: { blue: [], red: [] },
          picks: { blue: [...defaultPicks], red: [...defaultPicks] },
          draftId: null
        });
      }
    }),
    {
      name: 'tryndraft-draft-state',
      partialize: (state) => ({
        settings: state.settings,
        currentTurn: state.currentTurn,
        bans: state.bans,
        picks: state.picks,
        draftId: state.draftId,
        allChampions: state.allChampions
      }),
    }
  )
);