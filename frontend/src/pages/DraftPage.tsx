import { useEffect, useState, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import { useDraftStore } from '../store/useDraftStore';
import { getLatestPatch, getChampionImageUrl, getChampionSplashUrl } from '../utils/patch';
import { Search, X, Settings, Loader2 } from 'lucide-react';
import { RoleIcon } from '../components/common/RoleIcon';
import { authService, recommendationService, type ScoredChampion, type AnalysisResult, type DraftState } from '../utils/api';
import type { RoleType } from '../store/useDraftStore';

const ROLES: RoleType[] = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];
const RANKS = ['IRON', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM', 'EMERALD', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER'];

interface ChampionPoolItem {
  id: string;
  champion_name: string;
  role: string;
  playstyles?: string[];
}

export const DraftPage: React.FC = () => {
  const {
    settings,
    currentTurn,
    bans,
    picks,
    setSettings,
    setCurrentTurn,
    addBan,
    addPick,
    resetDraft,
    getCurrentPicker,
    allChampions,
    loadChampions,
  } = useDraftStore();

  const [latestPatch, setLatestPatch] = useState('16.1.1');
  const [search, setSearch] = useState('');
  const [draftPhase, setDraftPhase] = useState<'BAN' | 'PICK' | 'COMPLETE'>('BAN');
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [draggedSide, setDraggedSide] = useState<'BLUE' | 'RED' | null>(null);
  const [draggedIsBan, setDraggedIsBan] = useState(false);
  const [hoveredSlot, setHoveredSlot] = useState<{side: 'BLUE' | 'RED', index: number, isBan: boolean} | null>(null);
  const [draggedChampion, setDraggedChampion] = useState<string | null>(null);

  // Champion pool state
  const [championPoolNames, setChampionPoolNames] = useState<Set<string>>(new Set());

  // NN-sorted champions and LLM analysis
  const [sortedChampions, setSortedChampions] = useState<ScoredChampion[]>([]);
  const [llmAnalysis, setLlmAnalysis] = useState<AnalysisResult | null>(null);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false);
  const [modelType, setModelType] = useState<string>('loading');

  // Track if phase change was manual (to prevent auto-switch interference)
  const manualPhaseChangeRef = useRef(false);

  const currentPicker = getCurrentPicker();

  // Define loadUserPreferences first so it can be used in useEffect and reset button
  const loadUserPreferences = useCallback(async () => {
    try {
      const user = await authService.getCurrentUser();
      if (user?.preferences) {
        // Auto-populate rank from user preferences
        if (user.preferences.rank) {
          setSettings({ elo: user.preferences.rank });
        }
        // Auto-populate role from first preferred role
        if (user.preferences.preferred_roles && user.preferences.preferred_roles.length > 0) {
          setSettings({ role: user.preferences.preferred_roles[0] as RoleType });
        }
      }
    } catch (error) {
      // User might not be logged in, that's okay
      console.log('Could not load user preferences');
    }
  }, [setSettings]);

  const loadChampionPool = useCallback(async () => {
    try {
      const pool = await authService.getChampionPool();
      // Create a Set of champion names for quick lookup
      setChampionPoolNames(new Set(pool.map((c: ChampionPoolItem) => c.champion_name)));
    } catch (error) {
      console.error('Failed to load champion pool:', error);
      // User might not be logged in, that's okay
    }
  }, []);

  // Build draft state object for API calls
  const buildDraftState = useCallback((): DraftState => {
    return {
      phase: draftPhase,
      turn: currentTurn,
      side: settings.side,
      role: settings.role,
      elo: settings.elo,
      patch: settings.patch,
      bans_blue: bans.blue.filter(b => b),
      bans_red: bans.red.filter(b => b),
      picks_blue: picks.blue.filter(p => p.champion).map(p => ({ champion: p.champion, role: p.role })),
      picks_red: picks.red.filter(p => p.champion).map(p => ({ champion: p.champion, role: p.role })),
    };
  }, [draftPhase, currentTurn, settings, bans, picks]);

  // Fetch NN-sorted champions when draft state changes
  const fetchSortedChampions = useCallback(async () => {
    if (draftPhase === 'COMPLETE') return;

    try {
      const draftState = buildDraftState();
      const result = await recommendationService.getSortedChampions(draftState);
      if (result.champions.length > 0) {
        setSortedChampions(result.champions);
        setModelType(result.model_type);
      }
    } catch (error) {
      console.error('Failed to fetch sorted champions:', error);
    }
  }, [buildDraftState, draftPhase]);

  // Determine user's pick position based on role (0-4)
  const getUserPickPosition = useCallback((): number => {
    const roleOrder: RoleType[] = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];
    return roleOrder.indexOf(settings.role);
  }, [settings.role]);

  // Check if current turn is user's specific turn (not just team's turn)
  const isUsersTurn = useCallback((): boolean => {
    if (!currentPicker) return false;
    if (currentPicker.side !== settings.side) return false;

    const userPosition = getUserPickPosition();

    if (currentPicker.isBan) {
      // User's ban is at their pick position (e.g., jungle = 2nd ban = position 1)
      return currentPicker.position === userPosition;
    } else {
      // User's pick is at their role position
      return currentPicker.position === userPosition;
    }
  }, [currentPicker, settings.side, getUserPickPosition]);

  // Check if it's user's team's turn (for brief teammate pick updates)
  const isUserTeamsTurn = useCallback((): boolean => {
    if (!currentPicker) return false;
    return currentPicker.side === settings.side && !currentPicker.isBan;
  }, [currentPicker, settings.side]);

  // Fetch LLM analysis
  const fetchLLMAnalysis = useCallback(async () => {
    // Trigger conditions:
    // 1. Throughout entire ban phase - suggest bans to user
    // 2. Any of user's team's pick turns (brief for teammates, detailed for user)
    // 3. Draft complete
    const userTurn = isUsersTurn();
    const teamPickTurn = isUserTeamsTurn();

    // During ban phase, always provide suggestions (user wants help with their bans)
    // During pick phase, only on user's team's turns
    if (draftPhase === 'PICK' && !teamPickTurn) return;

    setIsLoadingAnalysis(true);
    try {
      const draftState = buildDraftState();
      // Add flag for whether this is user's specific turn (for detailed vs brief response)
      const result = await recommendationService.getAnalysis({
        ...draftState,
        is_user_turn: userTurn || draftPhase === 'BAN' // Always detailed during ban phase
      });
      if (result) {
        setLlmAnalysis(result);
      }
    } catch (error) {
      console.error('Failed to fetch LLM analysis:', error);
    } finally {
      setIsLoadingAnalysis(false);
    }
  }, [buildDraftState, isUsersTurn, isUserTeamsTurn, draftPhase]);

  useEffect(() => {
    // Load champions if not already loaded
    if (allChampions.length === 0) {
      loadChampions();
    }

    // Get latest patch version
    getLatestPatch().then(version => {
      setLatestPatch(version);
      setSettings({ patch: version });
    });

    // Load user's champion pool and preferences
    loadChampionPool();
    loadUserPreferences();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch sorted champions when draft state changes (debounced)
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchSortedChampions();
    }, 500); // Debounce to avoid rapid API calls
    return () => clearTimeout(timer);
  }, [bans, picks, settings.role, settings.elo, draftPhase]);

  // Fetch LLM analysis when turn changes (heavily debounced since it's slow)
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchLLMAnalysis();
    }, 800); // Longer debounce for LLM calls
    return () => clearTimeout(timer);
  }, [currentTurn, draftPhase]);

  // Auto-switch phases based on draft state
  useEffect(() => {
    // Skip auto-switching if the user just manually changed the phase
    if (manualPhaseChangeRef.current) {
      manualPhaseChangeRef.current = false;
      return;
    }

    const totalBans = bans.blue.filter(b => b).length + bans.red.filter(b => b).length;
    const totalPicks = picks.blue.filter(p => p.champion).length + picks.red.filter(p => p.champion).length;

    // Only auto-switch to COMPLETE if we're not already in COMPLETE
    if (totalBans === 10 && totalPicks === 10 && draftPhase !== 'COMPLETE') {
      setDraftPhase('COMPLETE');
    }
    // Check if we've moved to pick phase (all bans done, but picks not complete)
    else if (totalBans === 10 && totalPicks < 10 && draftPhase !== 'PICK') {
      setDraftPhase('PICK');
    }
    // If we're in pick phase but have unfilled bans, stay in ban phase
    else if (totalBans < 10 && draftPhase === 'PICK') {
      setDraftPhase('BAN');
    }
  }, [bans, picks, draftPhase]);

  const findNextUnfilledSlot = useCallback(() => {
    const userSide = settings.side;
    const enemySide = userSide === 'BLUE' ? 'RED' : 'BLUE';

    // Define the full draft sequence
    // Turns 0-4: User's bans
    // Turns 5-9: Enemy's bans
    // Turns 10-19: Picks in snake order

    // Get ban lists based on user's side
    const userBanList = userSide === 'BLUE' ? bans.blue : bans.red;
    const enemyBanList = enemySide === 'BLUE' ? bans.blue : bans.red;

    // Check user's bans (turns 0-4)
    for (let i = 0; i < 5; i++) {
      const banValue = userBanList[i];
      if (!banValue || banValue === '') {
        setCurrentTurn(i);
        return;
      }
    }

    // Check enemy's bans (turns 5-9)
    for (let i = 0; i < 5; i++) {
      const banValue = enemyBanList[i];
      if (!banValue || banValue === '') {
        setCurrentTurn(5 + i);
        return;
      }
    }

    // Pick phase sequence (turns 10-19) - snake draft order
    const pickSequence = [
      { side: 'BLUE', pos: 0 }, { side: 'RED', pos: 0 }, { side: 'RED', pos: 1 }, { side: 'BLUE', pos: 1 },
      { side: 'BLUE', pos: 2 }, { side: 'RED', pos: 2 }, { side: 'RED', pos: 3 }, { side: 'BLUE', pos: 3 },
      { side: 'BLUE', pos: 4 }, { side: 'RED', pos: 4 },
    ];

    // Check picks (turns 10-19)
    for (let i = 0; i < pickSequence.length; i++) {
      const slot = pickSequence[i];
      const pickList = slot.side === 'BLUE' ? picks.blue : picks.red;
      const champValue = pickList[slot.pos]?.champion;
      if (!champValue || champValue === '') {
        setCurrentTurn(10 + i);
        return;
      }
    }

    // All slots filled
    setCurrentTurn(-1);
  }, [bans, picks, settings.side, setCurrentTurn]);


  // Helper to check if draft is complete
  const isDraftComplete = useCallback(() => {
    const totalBans = bans.blue.filter(b => b).length + bans.red.filter(b => b).length;
    const totalPicks = picks.blue.filter(p => p.champion).length + picks.red.filter(p => p.champion).length;
    return totalBans === 10 && totalPicks === 10;
  }, [bans, picks]);

  // Keyboard handler for clearing slots and advancing cursor
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Enter key advances cursor or completes draft
      if (e.key === 'Enter') {
        e.preventDefault();
        // If draft is complete, switch to COMPLETE phase
        if (isDraftComplete()) {
          manualPhaseChangeRef.current = true;
          setDraftPhase('COMPLETE');
          setCurrentTurn(-1);
        } else {
          findNextUnfilledSlot();
        }
        return;
      }

      // Backspace/Delete clears hovered slot - but only if not in COMPLETE phase
      if ((e.key === 'Backspace' || e.key === 'Delete') && hoveredSlot && draftPhase !== 'COMPLETE') {
        e.preventDefault();
        if (hoveredSlot.isBan) {
          // Clear ban
          const banList = hoveredSlot.side === 'BLUE' ? bans.blue : bans.red;
          if (banList[hoveredSlot.index]) {
            addBan('', hoveredSlot.side, hoveredSlot.index);
            // Update phase to BAN since we're removing a ban
            manualPhaseChangeRef.current = true;
            setDraftPhase('BAN');
          }
        } else {
          // Clear pick
          const pickList = hoveredSlot.side === 'BLUE' ? picks.blue : picks.red;
          if (pickList[hoveredSlot.index]?.champion) {
            addPick('', pickList[hoveredSlot.index].role, hoveredSlot.side, hoveredSlot.index);
            // Update phase to PICK since we're removing a pick
            manualPhaseChangeRef.current = true;
            setDraftPhase('PICK');
          }
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [hoveredSlot, picks, bans, findNextUnfilledSlot, addBan, addPick, draftPhase, isDraftComplete, setCurrentTurn]);

  // Remove banned and picked champions from available list
  const allBannedPicked = new Set([
    ...bans.blue.filter(Boolean),
    ...bans.red.filter(Boolean),
    ...picks.blue.map(p => p.champion).filter(Boolean),
    ...picks.red.map(p => p.champion).filter(Boolean)
  ]);

  // Filter champions - use NN-sorted if available, otherwise alphabetical
  // ALWAYS check against local allBannedPicked since API data may be stale
  const filteredChamps = (() => {
    const searchLower = search.toLowerCase().trim();

    if (sortedChampions.length > 0) {
      // Use NN-sorted champions but ALSO check local banned/picked state
      return sortedChampions
        .filter(champ => {
          // Check BOTH API availability AND local state
          if (!champ.available) return false;
          if (allBannedPicked.has(champ.name)) return false; // Local state check
          if (!searchLower) return true;
          return champ.name.toLowerCase().includes(searchLower);
        })
        .map(champ => champ.name);
    } else {
      // Fallback to allChampions from store
      return allChampions
        .filter(champ => {
          if (allBannedPicked.has(champ)) return false;
          if (!searchLower) return true;
          return champ.toLowerCase().includes(searchLower);
        })
        .sort((a, b) => a.localeCompare(b));
    }
  })();

  const handleChampionSelect = (champion: string) => {
    // Get fresh picker state directly from store
    const picker = getCurrentPicker();
    if (!picker) return;

    // Check if champion is already banned or picked
    const currentBannedPicked = new Set([
      ...bans.blue.filter(Boolean),
      ...bans.red.filter(Boolean),
      ...picks.blue.map(p => p.champion).filter(Boolean),
      ...picks.red.map(p => p.champion).filter(Boolean)
    ]);

    if (currentBannedPicked.has(champion)) {
      console.log(`${champion} already banned/picked, ignoring`);
      return;
    }

    let success = false;
    if (picker.isBan) {
      success = addBan(champion, picker.side, picker.position);
    } else {
      const currentPicks = picker.side === 'BLUE' ? picks.blue : picks.red;
      const currentRole = currentPicks[picker.position]?.role || 'TOP';
      success = addPick(champion, currentRole, picker.side, picker.position);
    }

    if (success) {
      // IMMEDIATELY advance to next slot (don't wait for useEffect)
      advanceToNextSlot(champion, picker);
    }
    setSearch('');
  };

  // Immediately compute and set next turn after a selection
  const advanceToNextSlot = (justSelectedChampion: string, justUsedPicker: { side: 'BLUE' | 'RED'; position: number; isBan: boolean }) => {
    const userSide = settings.side;
    const enemySide = userSide === 'BLUE' ? 'RED' : 'BLUE';

    // Get current bans/picks but account for the one we just added
    const userBanList = [...(userSide === 'BLUE' ? bans.blue : bans.red)];
    const enemyBanList = [...(enemySide === 'BLUE' ? bans.blue : bans.red)];
    const bluePickList = [...picks.blue];
    const redPickList = [...picks.red];

    // Mark the slot we just filled
    if (justUsedPicker.isBan) {
      if (justUsedPicker.side === userSide) {
        userBanList[justUsedPicker.position] = justSelectedChampion;
      } else {
        enemyBanList[justUsedPicker.position] = justSelectedChampion;
      }
    } else {
      if (justUsedPicker.side === 'BLUE') {
        bluePickList[justUsedPicker.position] = { ...bluePickList[justUsedPicker.position], champion: justSelectedChampion };
      } else {
        redPickList[justUsedPicker.position] = { ...redPickList[justUsedPicker.position], champion: justSelectedChampion };
      }
    }

    // Find next empty slot
    for (let i = 0; i < 5; i++) {
      if (!userBanList[i] || userBanList[i] === '') {
        setCurrentTurn(i);
        return;
      }
    }
    for (let i = 0; i < 5; i++) {
      if (!enemyBanList[i] || enemyBanList[i] === '') {
        setCurrentTurn(5 + i);
        return;
      }
    }

    const pickSequence = [
      { side: 'BLUE' as const, pos: 0 }, { side: 'RED' as const, pos: 0 },
      { side: 'RED' as const, pos: 1 }, { side: 'BLUE' as const, pos: 1 },
      { side: 'BLUE' as const, pos: 2 }, { side: 'RED' as const, pos: 2 },
      { side: 'RED' as const, pos: 3 }, { side: 'BLUE' as const, pos: 3 },
      { side: 'BLUE' as const, pos: 4 }, { side: 'RED' as const, pos: 4 },
    ];

    for (let i = 0; i < pickSequence.length; i++) {
      const slot = pickSequence[i];
      const pickList = slot.side === 'BLUE' ? bluePickList : redPickList;
      if (!pickList[slot.pos]?.champion || pickList[slot.pos]?.champion === '') {
        setCurrentTurn(10 + i);
        return;
      }
    }

    setCurrentTurn(-1);
  };

  const handleSlotClick = (side: 'BLUE' | 'RED', position: number, isBan: boolean) => {
    // If draft is complete (all slots filled), always update phase based on slot type clicked
    if (isDraftComplete()) {
      manualPhaseChangeRef.current = true;
      setDraftPhase(isBan ? 'BAN' : 'PICK');
    }

    if (isBan) {
      // Calculate turn based on new ban order (user's 5 bans first, then enemy's 5)
      const userSide = settings.side;
      if (side === userSide) {
        setCurrentTurn(position); // User's bans are turns 0-4
      } else {
        setCurrentTurn(5 + position); // Enemy's bans are turns 5-9
      }
    } else {
      const pickOrder = [
        { side: 'BLUE', pos: 0 }, { side: 'RED', pos: 0 }, { side: 'RED', pos: 1 }, { side: 'BLUE', pos: 1 },
        { side: 'BLUE', pos: 2 }, { side: 'RED', pos: 2 }, { side: 'RED', pos: 3 }, { side: 'BLUE', pos: 3 },
        { side: 'BLUE', pos: 4 }, { side: 'RED', pos: 4 },
      ];
      const turnIndex = pickOrder.findIndex(p => p.side === side && p.pos === position);
      if (turnIndex !== -1) setCurrentTurn(10 + turnIndex);
    }
  };

  const handleDragStart = (side: 'BLUE' | 'RED', index: number, isBan: boolean = false) => {
    setDraggedIndex(index);
    setDraggedSide(side);
    setDraggedIsBan(isBan);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  // Handler for ban slot drops
  const handleBanDrop = (side: 'BLUE' | 'RED', targetIndex: number) => {
    // If dragging a champion from selector
    if (draggedChampion) {
      const success = addBan(draggedChampion, side, targetIndex);
      if (success) {
        advanceToNextSlot(draggedChampion, { side, position: targetIndex, isBan: true });
      }
      setDraggedChampion(null);
      return;
    }

    // If dragging from a ban slot
    if (draggedIndex === null || draggedSide === null || !draggedIsBan) return;
    if (draggedSide !== side) return;
    if (draggedIndex === targetIndex) return;

    const banList = side === 'BLUE' ? bans.blue : bans.red;
    const sourceBan = banList[draggedIndex] || '';
    const targetBan = banList[targetIndex] || '';

    // Swap bans - don't change cursor position, just swap the champions
    addBan(sourceBan, side, targetIndex);
    addBan(targetBan, side, draggedIndex);

    // Clear drag state immediately
    setDraggedIndex(null);
    setDraggedSide(null);
    setDraggedIsBan(false);
    setDraggedChampion(null);
    // Clear hovered slot to prevent stale state issues
    setHoveredSlot(null);
  };

  // Handler for pick slot drops
  const handlePickDrop = (side: 'BLUE' | 'RED', targetIndex: number) => {
    // If dragging a champion from selector
    if (draggedChampion) {
      const pickList = side === 'BLUE' ? picks.blue : picks.red;
      const success = addPick(draggedChampion, pickList[targetIndex].role, side, targetIndex);
      if (success) {
        advanceToNextSlot(draggedChampion, { side, position: targetIndex, isBan: false });
      }
      setDraggedChampion(null);
      return;
    }

    // If dragging from a slot
    if (draggedIndex === null || draggedSide === null || draggedIsBan) return;
    if (draggedSide !== side) return;
    if (draggedIndex === targetIndex) return;

    const pickList = side === 'BLUE' ? picks.blue : picks.red;
    const sourceChampion = pickList[draggedIndex].champion;
    const targetChampion = pickList[targetIndex].champion;
    const sourceRole = pickList[draggedIndex].role;
    const targetRole = pickList[targetIndex].role;

    // If both slots are empty, swap the role slots themselves
    if (!sourceChampion && !targetChampion) {
      addPick('', targetRole, side, draggedIndex);
      addPick('', sourceRole, side, targetIndex);
    }
    // If dragging empty slot to filled slot, swap slots (move champion with its role)
    else if (!sourceChampion && targetChampion) {
      addPick('', sourceRole, side, targetIndex);
      addPick(targetChampion, targetRole, side, draggedIndex);
    }
    // If dragging filled slot to empty slot, move champion to target role
    else if (sourceChampion && !targetChampion) {
      addPick(sourceChampion, targetRole, side, targetIndex);
      addPick('', sourceRole, side, draggedIndex);
    }
    // If both have champions, swap only the champions
    else {
      addPick(sourceChampion, targetRole, side, targetIndex);
      addPick(targetChampion, sourceRole, side, draggedIndex);
    }

    // Clear drag state immediately
    setDraggedIndex(null);
    setDraggedSide(null);
    setDraggedIsBan(false);
    setDraggedChampion(null);
    // Clear hovered slot to prevent stale state issues
    setHoveredSlot(null);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
    setDraggedSide(null);
    setDraggedIsBan(false);
    setDraggedChampion(null);
    // Clear hovered slot to prevent issues with stale state
    setHoveredSlot(null);
  };

  // Handle dragging back to center (picker or LLM box) to clear slot
  const handleDropOnCenter = (e: React.DragEvent) => {
    e.preventDefault();
    if (draggedIndex !== null && draggedSide !== null) {
      if (draggedIsBan) {
        // Clear ban
        const banList = draggedSide === 'BLUE' ? bans.blue : bans.red;
        if (banList[draggedIndex]) {
          addBan('', draggedSide, draggedIndex);
          // Move cursor to the cleared ban slot
          const userSide = settings.side;
          if (draggedSide === userSide) {
            setCurrentTurn(draggedIndex); // User's bans are turns 0-4
          } else {
            setCurrentTurn(5 + draggedIndex); // Enemy's bans are turns 5-9
          }
          // Update phase to BAN since we're now missing a ban
          manualPhaseChangeRef.current = true;
          setDraftPhase('BAN');
        }
      } else {
        // Clear pick
        const pickList = draggedSide === 'BLUE' ? picks.blue : picks.red;
        if (pickList[draggedIndex]?.champion) {
          addPick('', pickList[draggedIndex].role, draggedSide, draggedIndex);
          // Move cursor to the now-empty slot
          const pickOrder = [
            { side: 'BLUE', pos: 0 }, { side: 'RED', pos: 0 }, { side: 'RED', pos: 1 }, { side: 'BLUE', pos: 1 },
            { side: 'BLUE', pos: 2 }, { side: 'RED', pos: 2 }, { side: 'RED', pos: 3 }, { side: 'BLUE', pos: 3 },
            { side: 'BLUE', pos: 4 }, { side: 'RED', pos: 4 },
          ];
          const turnIndex = pickOrder.findIndex(p => p.side === draggedSide && p.pos === draggedIndex);
          if (turnIndex !== -1) setCurrentTurn(10 + turnIndex);
          // Update phase to PICK since we're now missing a pick
          manualPhaseChangeRef.current = true;
          setDraftPhase('PICK');
        }
      }
    }
    setDraggedIndex(null);
    setDraggedSide(null);
    setDraggedIsBan(false);
    setDraggedChampion(null);
  };

  const phaseColorClass = draftPhase === 'BAN' ? 'border-red-500/30' : draftPhase === 'PICK' ? 'border-blue-500/30' : 'border-green-500/30';

  return (
    <div className="h-screen w-screen bg-black flex flex-col overflow-hidden select-none">
      {/* Top Header */}
      <header className="h-20 bg-black/90 backdrop-blur border-b border-gray-900 flex items-center justify-between px-8">
        <Link to="/draft" className="flex items-center gap-2">
          <img src="/logo.svg" alt="TrynDraft" className="w-8 h-8" />
          <span className="text-white font-bold text-base">TrynDraft</span>
        </Link>

        <div className="flex items-center gap-6">
          {/* Side */}
          <div className="flex gap-2 bg-gray-900 rounded p-1">
            <button onClick={() => setSettings({ side: 'BLUE' })} className={`px-5 py-2 rounded text-sm font-medium ${settings.side === 'BLUE' ? 'bg-gray-700 text-white' : 'text-gray-500'}`}>Blue</button>
            <button onClick={() => setSettings({ side: 'RED' })} className={`px-5 py-2 rounded text-sm font-medium ${settings.side === 'RED' ? 'bg-gray-700 text-white' : 'text-gray-500'}`}>Red</button>
          </div>

          {/* Roles */}
          <div className="flex gap-2">
            {ROLES.map(role => (
              <button key={role} onClick={() => setSettings({ role })} className={`p-2 rounded bg-gray-900 ${settings.role === role ? 'ring-2 ring-gray-400' : ''}`} title={role}>
                <RoleIcon role={role} size={18} className={settings.role === role ? 'opacity-100' : 'opacity-40'} />
              </button>
            ))}
          </div>

          {/* Rank - Icon Selector */}
          <div className="flex gap-1.5 bg-gray-900 rounded p-1">
            {RANKS.map(rank => {
              const rankLower = rank.toLowerCase();
              const rankIconUrl = `https://raw.communitydragon.org/pbe/plugins/rcp-fe-lol-shared-components/global/default/${rankLower}.png`;
              return (
                <button
                  key={rank}
                  onClick={() => setSettings({ elo: rank })}
                  className={`p-1.5 rounded ${settings.elo === rank ? 'ring-2 ring-gray-400' : ''}`}
                  title={rank}
                >
                  <img src={rankIconUrl} alt={rank} className={`w-6 h-6 ${settings.elo === rank ? 'opacity-100' : 'opacity-40'}`} />
                </button>
              );
            })}
          </div>

          {/* Patch */}
          <div className="text-sm text-gray-500 font-mono">{latestPatch}</div>

          {/* Phase Toggle */}
          <div className="flex gap-2 bg-gray-900 rounded p-1">
            <button onClick={() => { manualPhaseChangeRef.current = true; setDraftPhase('BAN'); setCurrentTurn(0); }} className={`px-4 py-2 rounded text-sm font-bold ${draftPhase === 'BAN' ? 'bg-red-500 text-white' : 'text-gray-600'}`}>BAN</button>
            <button onClick={() => { manualPhaseChangeRef.current = true; setDraftPhase('PICK'); setCurrentTurn(10); }} className={`px-4 py-2 rounded text-sm font-bold ${draftPhase === 'PICK' ? 'bg-blue-500 text-white' : 'text-gray-600'}`}>PICK</button>
            <button
              onClick={() => { manualPhaseChangeRef.current = true; setDraftPhase('COMPLETE'); }}
              disabled={bans.blue.filter(b => b).length + bans.red.filter(b => b).length < 10 || picks.blue.filter(p => p.champion).length + picks.red.filter(p => p.champion).length < 10}
              className={`px-4 py-2 rounded text-sm font-bold ${draftPhase === 'COMPLETE' ? 'bg-green-500 text-white' : 'text-gray-600'} disabled:opacity-30 disabled:cursor-not-allowed`}
            >
              DONE
            </button>
          </div>

          <button onClick={() => { resetDraft(); manualPhaseChangeRef.current = true; setDraftPhase('BAN'); }} className="px-3 py-2 text-sm text-gray-500 hover:text-white">Reset</button>
        </div>

        <Link to="/profile" className="p-2 hover:bg-gray-900 rounded text-gray-500 hover:text-white">
          <Settings size={20} />
        </Link>
      </header>

      {/* Main Content */}
      <div className="flex-1 flex gap-2 p-2 overflow-hidden">
        {/* LEFT - Blue Team */}
        <div className="w-80 flex flex-col gap-3">
          <div className="text-[10px] uppercase tracking-widest text-gray-700 font-bold">Blue Team</div>

          {/* Bans - BIGGER */}
          <div className="flex gap-2 mb-2">
            {[0, 1, 2, 3, 4].map(i => {
              const ban = bans.blue[i];
              const isActive = draftPhase !== 'COMPLETE' && currentPicker?.side === 'BLUE' && currentPicker?.isBan && currentPicker?.position === i;
              return (
                <button
                  key={i}
                  onClick={() => handleSlotClick('BLUE', i, true)}
                  draggable={true}
                  onDragStart={() => handleDragStart('BLUE', i, true)}
                  onDragOver={handleDragOver}
                  onDrop={() => handleBanDrop('BLUE', i)}
                  onDragEnd={handleDragEnd}
                  onMouseEnter={() => setHoveredSlot({side: 'BLUE', index: i, isBan: true})}
                  onMouseLeave={() => setHoveredSlot(null)}
                  className={`w-12 h-12 rounded border ${isActive ? `ring-2 ${phaseColorClass}` : 'border-gray-900'} ${ban ? 'bg-gray-900 cursor-move' : 'bg-black cursor-pointer'}`}>
                  {ban && (
                    <div className="relative w-full h-full">
                      <img src={getChampionImageUrl(ban, latestPatch)} alt={ban} className="w-full h-full object-cover rounded" />
                      <X className="absolute inset-0 m-auto text-gray-500/60" size={16} strokeWidth={2} />
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          {/* Picks - HORIZONTAL RECTANGLES with splash art */}
          <div className="flex-1 flex flex-col gap-2">
            {picks.blue.map((pick, i) => {
              const isActive = draftPhase !== 'COMPLETE' && currentPicker?.side === 'BLUE' && !currentPicker?.isBan && currentPicker?.position === i;
              const isDragging = draggedIndex === i && draggedSide === 'BLUE' && !draggedIsBan;
              const hasChampion = !!pick.champion;
              return (
                <button
                  key={i}
                  onClick={() => handleSlotClick('BLUE', i, false)}
                  draggable={true}
                  onDragStart={() => handleDragStart('BLUE', i, false)}
                  onDragOver={handleDragOver}
                  onDrop={() => handlePickDrop('BLUE', i)}
                  onDragEnd={handleDragEnd}
                  onMouseEnter={() => setHoveredSlot({side: 'BLUE', index: i, isBan: false})}
                  onMouseLeave={() => setHoveredSlot(null)}
                  className={`h-[calc((100vh-16rem)/5)] rounded overflow-hidden relative border ${isActive ? `ring-2 ${phaseColorClass}` : 'border-gray-900'} flex items-center ${isDragging ? 'opacity-50' : ''} ${hasChampion ? 'cursor-move' : 'cursor-pointer'}`}>
                  {pick.champion ? (
                    <>
                      <img src={getChampionSplashUrl(pick.champion)} alt={pick.champion} className="w-full h-full object-cover object-center pointer-events-none" />
                      {/* Role icon overlay - only show for user's team */}
                      {settings.side === 'BLUE' && (
                        <div className="absolute right-2 top-1/2 -translate-y-1/2 bg-black/70 rounded-md p-1.5 backdrop-blur-sm">
                          <RoleIcon role={pick.role} size={20} />
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="w-full h-full bg-gray-950 flex items-center justify-center border border-gray-900">
                      {settings.side === 'BLUE' && <RoleIcon role={pick.role} size={24} className="text-gray-800" />}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* CENTER - Statistics Bar, Champion Picker and LLM Box */}
        <div className={`flex-1 flex flex-col border-l border-r ${phaseColorClass} min-w-0`}>
          {/* Statistics Bar - Only visible when draft is complete */}
          {/* TODO: These statistics are placeholders. Will be calculated from scraped data:
              - Lane matchup win rates from opponent.gg/op.gg
              - Team synergy scores from high-elo game analysis
              - Composition win rates and counter-matchups
              - Damage type analysis for itemization strategy
              - Backend endpoint: /api/v1/drafts/{draft_id}/statistics */}
          {draftPhase === 'COMPLETE' && (
            <div className="h-20 bg-gradient-to-r from-black/90 via-gray-900/80 to-black/90 border-b-2 border-amber-500/30 px-6 flex items-center justify-between">
              <div className="flex items-center gap-8">
                {/* Lane Matchup */}
                <div className="text-xs">
                  <div className="text-gray-500 uppercase tracking-wider font-bold mb-1">Lane Matchup</div>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400">{settings.role}:</span>
                    <div className="text-green-400 font-bold text-lg">54%</div>
                    <span className="text-xs text-gray-600">WR</span>
                  </div>
                </div>

                <div className="w-px h-12 bg-gray-800"></div>

                {/* Overall Team Win % */}
                <div className="text-xs">
                  <div className="text-gray-500 uppercase tracking-wider font-bold mb-1">Comp Win %</div>
                  <div className="flex items-center gap-2">
                    <div className="text-blue-400 font-bold text-lg">52.3%</div>
                    <span className="text-gray-600">vs</span>
                    <div className="text-red-400 font-bold text-lg">47.7%</div>
                  </div>
                </div>

                <div className="w-px h-12 bg-gray-800"></div>

                {/* Synergy Score */}
                <div className="text-xs">
                  <div className="text-gray-500 uppercase tracking-wider font-bold mb-1">Synergy Score</div>
                  <div className="flex items-center gap-1">
                    <div className="w-20 h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-green-500 to-emerald-400" style={{width: '78%'}}></div>
                    </div>
                    <span className="text-green-400 font-mono text-sm ml-1">7.8/10</span>
                  </div>
                </div>

                <div className="w-px h-12 bg-gray-800"></div>

                {/* Damage Split */}
                <div className="text-xs">
                  <div className="text-gray-500 uppercase tracking-wider font-bold mb-1">Damage Split</div>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 bg-orange-500 rounded"></div>
                      <span className="text-gray-400 text-xs">AD</span>
                      <span className="text-white font-mono text-sm">58%</span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 bg-blue-500 rounded"></div>
                      <span className="text-gray-400 text-xs">AP</span>
                      <span className="text-white font-mono text-sm">42%</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <div className="text-xs text-gray-500 uppercase tracking-wider">Draft Complete</div>
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              </div>
            </div>
          )}

          {/* Champion Picker - Only show when draft is not complete */}
          {draftPhase !== 'COMPLETE' && (
            <div className="flex-1 flex flex-col min-h-0">
              {/* Search */}
              <div className="relative m-3 mb-2">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-600" size={16} />
                <input type="text" placeholder="Search champion..." value={search} onChange={e => setSearch(e.target.value)}
                  className={`w-full pl-10 pr-4 py-2 bg-gray-950 border ${phaseColorClass} rounded text-white text-sm focus:outline-none`} />
              </div>

              {/* Champion Grid - SCROLLABLE & DROP ZONE */}
              <div
                className="flex-1 overflow-y-scroll custom-scrollbar px-3 pb-3 min-h-0"
                onDragOver={handleDragOver}
                onDrop={handleDropOnCenter}>
                <div className="grid grid-cols-8 gap-2 pr-1">
                  {filteredChamps.map(champ => {
                    const isInPool = championPoolNames.has(champ);
                    return (
                      <button
                        key={champ}
                        onClick={() => handleChampionSelect(champ)}
                        draggable={true}
                        onDragStart={() => setDraggedChampion(champ)}
                        onDragEnd={handleDragEnd}
                        className={`aspect-square rounded overflow-hidden relative group hover:scale-105 hover:z-10 transition-transform cursor-grab active:cursor-grabbing ${
                          isInPool
                            ? 'border-2 border-cyan-400 shadow-lg shadow-cyan-400/50 ring-1 ring-cyan-400/30'
                            : 'border border-gray-900 hover:border-amber-500'
                        }`}>
                        <img src={getChampionImageUrl(champ, latestPatch)} alt={champ} className="w-full h-full object-cover pointer-events-none" />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/90 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-center pb-1 pointer-events-none">
                          <span className="text-white font-bold text-[10px] uppercase tracking-wide">{champ}</span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {/* LLM Box - Expands to fill space when draft is complete */}
          <div
            className={`${draftPhase === 'COMPLETE' ? 'flex-1' : 'h-1/2'} bg-black/90 border-t-2 ${phaseColorClass} p-4 flex flex-col`}
            onDragOver={handleDragOver}
            onDrop={handleDropOnCenter}>
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-gray-600 uppercase tracking-wider font-bold">AI Analysis</div>
              <div className="flex items-center gap-2">
                {isLoadingAnalysis && <Loader2 className="w-3 h-3 animate-spin text-gray-500" />}
                <span className="text-[10px] text-gray-700 font-mono">
                  {modelType === 'neural_network' ? 'NN' : modelType === 'rule_based' ? 'Rules' : ''}
                </span>
              </div>
            </div>
            <div className="flex-1 text-sm text-gray-400 overflow-y-auto">
              {isLoadingAnalysis && !llmAnalysis ? (
                <div className="flex items-center justify-center h-full">
                  <Loader2 className="w-6 h-6 animate-spin text-gray-600" />
                </div>
              ) : llmAnalysis ? (
                <div className="space-y-2">
                  {/* Analysis text */}
                  <p className="text-gray-300 leading-relaxed">{llmAnalysis.analysis}</p>

                  {/* Source indicator */}
                  <div className="text-[10px] text-gray-700 pt-2 border-t border-gray-800">
                    {llmAnalysis.source === 'huggingface' ? `${llmAnalysis.model}` : 'Rule-based'}
                  </div>
                </div>
              ) : (
                <div className="text-gray-600">
                  {draftPhase === 'COMPLETE' ? (
                    <div className="text-center mt-8">
                      <p className="text-lg font-bold mb-2 text-gray-500">Draft Complete!</p>
                      <p className="text-sm">Generating analysis...</p>
                    </div>
                  ) : (
                    <div>
                      {draftPhase === 'BAN'
                        ? `${bans.blue.filter(b => b).length + bans.red.filter(b => b).length}/10 bans`
                        : `${picks.blue.filter(p => p.champion).length + picks.red.filter(p => p.champion).length}/10 picks`}
                      <p className="text-xs text-gray-700 mt-2">Suggestions will appear when it's your turn...</p>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT - Red Team */}
        <div className="w-80 flex flex-col gap-3">
          <div className="text-[10px] uppercase tracking-widest text-gray-700 font-bold">Red Team</div>

          {/* Bans */}
          <div className="flex gap-2 mb-2">
            {[0, 1, 2, 3, 4].map(i => {
              const ban = bans.red[i];
              const isActive = draftPhase !== 'COMPLETE' && currentPicker?.side === 'RED' && currentPicker?.isBan && currentPicker?.position === i;
              return (
                <button
                  key={i}
                  onClick={() => handleSlotClick('RED', i, true)}
                  draggable={true}
                  onDragStart={() => handleDragStart('RED', i, true)}
                  onDragOver={handleDragOver}
                  onDrop={() => handleBanDrop('RED', i)}
                  onDragEnd={handleDragEnd}
                  onMouseEnter={() => setHoveredSlot({side: 'RED', index: i, isBan: true})}
                  onMouseLeave={() => setHoveredSlot(null)}
                  className={`w-12 h-12 rounded border ${isActive ? `ring-2 ${phaseColorClass}` : 'border-gray-900'} ${ban ? 'bg-gray-900 cursor-move' : 'bg-black cursor-pointer'}`}>
                  {ban && (
                    <div className="relative w-full h-full">
                      <img src={getChampionImageUrl(ban, latestPatch)} alt={ban} className="w-full h-full object-cover rounded" />
                      <X className="absolute inset-0 m-auto text-gray-500/60" size={16} strokeWidth={2} />
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          {/* Picks */}
          <div className="flex-1 flex flex-col gap-2">
            {picks.red.map((pick, i) => {
              const isActive = draftPhase !== 'COMPLETE' && currentPicker?.side === 'RED' && !currentPicker?.isBan && currentPicker?.position === i;
              const isDragging = draggedIndex === i && draggedSide === 'RED' && !draggedIsBan;
              const hasChampion = !!pick.champion;
              return (
                <button
                  key={i}
                  onClick={() => handleSlotClick('RED', i, false)}
                  draggable={true}
                  onDragStart={() => handleDragStart('RED', i, false)}
                  onDragOver={handleDragOver}
                  onDrop={() => handlePickDrop('RED', i)}
                  onDragEnd={handleDragEnd}
                  onMouseEnter={() => setHoveredSlot({side: 'RED', index: i, isBan: false})}
                  onMouseLeave={() => setHoveredSlot(null)}
                  className={`h-[calc((100vh-16rem)/5)] rounded overflow-hidden relative border ${isActive ? `ring-2 ${phaseColorClass}` : 'border-gray-900'} flex items-center ${isDragging ? 'opacity-50' : ''} ${hasChampion ? 'cursor-move' : 'cursor-pointer'}`}>
                  {pick.champion ? (
                    <>
                      <img src={getChampionSplashUrl(pick.champion)} alt={pick.champion} className="w-full h-full object-cover object-center pointer-events-none" />
                      {/* Role icon overlay - only show for user's team */}
                      {settings.side === 'RED' && (
                        <div className="absolute right-2 top-1/2 -translate-y-1/2 bg-black/70 rounded-md p-1.5 backdrop-blur-sm">
                          <RoleIcon role={pick.role} size={20} />
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="w-full h-full bg-gray-950 flex items-center justify-center border border-gray-900">
                      {settings.side === 'RED' && <RoleIcon role={pick.role} size={24} className="text-gray-800" />}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
