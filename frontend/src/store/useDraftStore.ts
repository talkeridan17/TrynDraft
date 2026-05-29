import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { championService } from '../utils/api';
import { getDraftSequence, type DraftMode } from '../utils/draftOrder';

export type GameModeType = DraftMode;
export type TeamSide = 'BLUE' | 'RED';
export type RoleType = 'TOP' | 'JUNGLE' | 'MID' | 'ADC' | 'SUPPORT' | 'FLEX';

interface DraftSettings {
  mode: GameModeType;
  side: TeamSide;
  role: RoleType;
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

  // Draft actions
  addBan: (champion: string, side: TeamSide, position?: number) => boolean;
  removeBan: (champion: string, side: TeamSide) => void;
  addPick: (champion: string, role: RoleType, side: TeamSide, position?: number) => boolean;
  removePick: (index: number, side: TeamSide) => void;
  movePick: (fromIndex: number, toIndex: number, side: TeamSide) => void;
  setRole: (index: number, side: TeamSide, role: RoleType) => void;
  
  resetDraft: () => void;
}

const defaultRoles: RoleType[] = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];

const defaultSettings: DraftSettings = {
  mode: 'SOLOQ',
  side: 'BLUE',
  role: 'TOP',
  patch: '16.2.1',
  phase: 'BAN',
};

const defaultPicks = defaultRoles.map(role => ({ champion: '', role }));

// Helper function to compute taken champions
// eslint-disable-next-line @typescript-eslint/no-explicit-any
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

      bans: { blue: ['', '', '', '', ''], red: ['', '', '', '', ''] },
      picks: { blue: [...defaultPicks], red: [...defaultPicks] },

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

        // If turn is -1, no cursor (all slots filled)
        if (turn === -1) return null;
        const sequence = getDraftSequence(state.settings.mode);
        const picker = sequence[turn];
        if (!picker) return null;
        return picker;
      },
      
      // Actions
      setSettings: (newSettings) => 
        set((state) => ({ 
          settings: { ...state.settings, ...newSettings }
        })),
      
      setCurrentTurn: (turn) =>
        set({ currentTurn: turn === -1 ? -1 : Math.max(0, Math.min(turn, 19)) }),
      
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
      
      // Draft actions with validation
      addBan: (champion, side, position = -1) => {
        const state = get();
        const sideKey = side.toLowerCase() as 'blue' | 'red';
        const currentBans = state.bans[sideKey];

        // Check if this champion is already banned (by either team) - unless clearing with ''
        // Allow if it's already in the SAME side's bans (swap operation)
        if (champion && champion !== '') {
          const otherSideKey = sideKey === 'blue' ? 'red' : 'blue';
          const otherSideBans = state.bans[otherSideKey];

          // If champion is in other side's bans, reject
          if (otherSideBans.includes(champion)) {
            console.error(`${champion} is already banned by the other team`);
            return false;
          }
          // If champion is in same side's bans, it's a swap - allow it (positions will be overwritten)

          // Check if already picked
          const allPicks = [...state.picks.blue, ...state.picks.red].map(p => p.champion).filter(Boolean);
          if (allPicks.includes(champion)) {
            console.error(`${champion} is already picked`);
            return false;
          }
        }

        // If position specified, place at that exact position
        if (position !== -1 && position < 5) {
          set((state) => {
            // Always ensure array has 5 slots
            const newBans = ['', '', '', '', ''];
            // Copy existing bans
            state.bans[sideKey].forEach((ban, i) => {
              if (i < 5) newBans[i] = ban;
            });
            // Set the new ban at position
            newBans[position] = champion;

            return {
              bans: {
                ...state.bans,
                [sideKey]: newBans
              }
            };
          });
          return true;
        }

        // Otherwise, find next empty slot
        const filledBans = currentBans.filter(b => b && b !== '').length;
        if (filledBans >= 5) {
          console.error(`${side} team already has 5 bans`);
          return false;
        }

        // Find first empty slot
        set((state) => {
          const newBans = ['', '', '', '', ''];
          state.bans[sideKey].forEach((ban, i) => {
            if (i < 5) newBans[i] = ban;
          });
          // Find first empty and place there
          for (let i = 0; i < 5; i++) {
            if (!newBans[i] || newBans[i] === '') {
              newBans[i] = champion;
              break;
            }
          }

          return {
            bans: {
              ...state.bans,
              [sideKey]: newBans
            }
          };
        });

        return true;
      },
      
      removeBan: (champion, side) => {
        set((state) => {
          const sideKey = side.toLowerCase() as 'blue' | 'red';
          const newBans = ['', '', '', '', ''];
          state.bans[sideKey].forEach((ban, i) => {
            if (i < 5) {
              newBans[i] = ban === champion ? '' : ban;
            }
          });
          return {
            bans: {
              ...state.bans,
              [sideKey]: newBans
            }
          };
        });
      },
      
      addPick: (champion, role, side, position = -1) => {
        const state = get();
        const sideKey = side.toLowerCase() as 'blue' | 'red';
        const picks = state.picks[sideKey];

        // Check if this champion is already picked or banned - unless clearing with ''
        // Allow if it's already in the SAME side's picks (swap operation)
        if (champion && champion !== '') {
          const otherSideKey = sideKey === 'blue' ? 'red' : 'blue';
          const otherSidePicks = state.picks[otherSideKey].map(p => p.champion).filter(Boolean);

          // If champion is in other side's picks, reject
          if (otherSidePicks.includes(champion)) {
            console.error(`${champion} is already picked by the other team`);
            return false;
          }
          // If champion is in same side's picks, it's a swap - allow it

          const allBans = [...state.bans.blue, ...state.bans.red].filter(Boolean);
          if (allBans.includes(champion)) {
            console.error(`${champion} is already banned`);
            return false;
          }
        }

        // Find position to place pick
        let targetPosition = position;

        if (targetPosition === -1) {
          // Find first empty slot
          targetPosition = picks.findIndex(p => !p.champion);
          if (targetPosition === -1) {
            console.error(`No empty slots on ${side} team`);
            return false;
          }
        }

        // Update state
        set((state) => {
          const newPicks = [...state.picks[sideKey]];
          newPicks[targetPosition] = { champion, role: role || defaultRoles[targetPosition] };

          const newPicksState = {
            ...state.picks,
            [sideKey]: newPicks
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
        set((state) => ({
          settings: {
            ...defaultSettings,
            // Preserve user's role and mode settings
            role: state.settings.role,
            mode: state.settings.mode,
            patch: state.settings.patch,
          },
          currentTurn: 0,
          bans: { blue: ['', '', '', '', ''], red: ['', '', '', '', ''] },
          picks: { blue: [...defaultPicks], red: [...defaultPicks] },
        }));
      }
    }),
    {
      name: 'tryndraft-draft-state',
      version: 3, // Increment to force migration and clear corrupted state
      partialize: (state) => ({
        settings: state.settings,
        currentTurn: state.currentTurn,
        bans: state.bans,
        picks: state.picks,
        // Don't persist allChampions - fetch fresh every time
      }),
      // Migrate old state format to new format
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      migrate: (persistedState: any, version: number) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const fixBansArray = (arr: any): string[] => {
          const result = ['', '', '', '', ''];
          if (Array.isArray(arr)) {
            arr.forEach((ban, i) => {
              if (i < 5 && typeof ban === 'string') {
                result[i] = ban;
              }
            });
          }
          return result;
        };

        // Helper to fix picks arrays
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const fixPicksArray = (arr: any): Array<{ champion: string; role: 'TOP' | 'JUNGLE' | 'MID' | 'ADC' | 'SUPPORT' | 'FLEX' }> => {
          const defaultRoles: Array<'TOP' | 'JUNGLE' | 'MID' | 'ADC' | 'SUPPORT'> = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];
          const result = defaultRoles.map(role => ({ champion: '', role }));
          if (Array.isArray(arr)) {
            arr.forEach((pick, i) => {
              if (i < 5 && pick && typeof pick === 'object') {
                result[i] = {
                  champion: typeof pick.champion === 'string' ? pick.champion : '',
                  role: [...defaultRoles, 'FLEX'].includes(pick.role) ? pick.role : defaultRoles[i]
                };
              }
            });
          }
          return result;
        };

        // Version 2 migration: fix bans arrays
        if (version < 2) {
          if (persistedState.bans) {
            persistedState.bans = {
              blue: fixBansArray(persistedState.bans.blue),
              red: fixBansArray(persistedState.bans.red)
            };
          }

          if (typeof persistedState.currentTurn !== 'number' || persistedState.currentTurn < 0) {
            persistedState.currentTurn = 0;
          }
        }

        // Version 3 migration: comprehensive state cleanup
        if (version < 3) {
          // Ensure bans are properly formatted
          persistedState.bans = {
            blue: fixBansArray(persistedState.bans?.blue),
            red: fixBansArray(persistedState.bans?.red)
          };

          // Ensure picks are properly formatted
          persistedState.picks = {
            blue: fixPicksArray(persistedState.picks?.blue),
            red: fixPicksArray(persistedState.picks?.red)
          };

          // Reset currentTurn to 0
          persistedState.currentTurn = 0;
        }

        // Normalize mode after older schemas
        if (!persistedState.settings) persistedState.settings = { ...defaultSettings };
        if (persistedState.settings.mode !== 'SOLOQ' && persistedState.settings.mode !== 'CLASH') {
          persistedState.settings.mode = 'SOLOQ';
        }

        return persistedState;
      },
    }
  )
);
