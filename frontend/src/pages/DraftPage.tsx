import { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useDraftStore } from '../store/useDraftStore';
import { getLatestPatch, getChampionImageUrl, getChampionSplashUrl } from '../utils/patch';
import { Search, X, Loader2, CheckCircle, AlertCircle, ExternalLink } from 'lucide-react';
import { RoleIcon } from '../components/common/RoleIcon';
import { recommendationService, type ScoredChampion, type AnalysisResult, type DraftState, type MatchupInfo, type DraftStats } from '../utils/api';
import type { RoleType } from '../store/useDraftStore';
import { getDraftSequence, getTurnFromSlot, type DraftMode } from '../utils/draftOrder';

const ROLES: RoleType[] = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];

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

  const [latestPatch, setLatestPatch] = useState('16.2.1');
  const [search, setSearch] = useState('');
  const [draftPhase, setDraftPhase] = useState<'BAN' | 'PICK' | 'COMPLETE'>('BAN');
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [draggedSide, setDraggedSide] = useState<'BLUE' | 'RED' | null>(null);
  const [draggedIsBan, setDraggedIsBan] = useState(false);
  const [hoveredSlot, setHoveredSlot] = useState<{side: 'BLUE' | 'RED', index: number, isBan: boolean} | null>(null);
  const [draggedChampion, setDraggedChampion] = useState<string | null>(null);

  // Champion pool state

  // NN-sorted champions and LLM analysis
  const [sortedChampions, setSortedChampions] = useState<ScoredChampion[]>([]);
  const [llmAnalysis, setLlmAnalysis] = useState<AnalysisResult | null>(null);
  const [isLoadingAnalysis, setIsLoadingAnalysis] = useState(false);
  const [modelType, setModelType] = useState<string>('loading');
  const [profileSettings, setProfileSettings] = useState({
    soloRiotIds: [] as string[],
    clashBlueByRole: [] as Array<{ role: string; riot_id: string }>,
    clashRedByRole: [] as Array<{ role: string; riot_id: string }>,
    clashEnemyUnknown: false,
  });
  const [hoveredChampion, setHoveredChampion] = useState<string | null>(null);
  // Last champion the user explicitly picked or clicked — stays shown when mouse is idle
  const [pinnedChampion, setPinnedChampion] = useState<string | null>(null);
  // Cache ranked champion data so hovering a placed pick still shows stats
  const champInfoCache = useRef<Record<string, ScoredChampion>>({});

  // Clash mode: per-slot IGN inputs
  const [clashBlueIgns, setClashBlueIgns] = useState<string[]>(['', '', '', '', '']);
  const [clashRedIgns, setClashRedIgns] = useState<string[]>(['', '', '', '', '']);
  const [clashIgnStatus, setClashIgnStatus] = useState<Record<string, 'idle' | 'loading' | 'loaded' | 'error'>>({});
  const [clashIgnNames, setClashIgnNames] = useState<Record<string, string>>({});
  // Incremented after IGN load to force ONNX re-run with fresh proficiency data
  const [profVersion, setProfVersion] = useState(0);

  // SID (Summoner ID / Riot ID) quick-entry
  const [sidInput, setSidInput] = useState('');
  const [sidStatus, setSidStatus] = useState<'idle' | 'loading' | 'loaded' | 'error'>('idle');
  const [profCount, setProfCount] = useState(0);
  const [summonerInfo, setSummonerInfo] = useState<{ gameName: string; tagLine: string; tier?: string; division?: string } | null>(null);

  // Matchup info from NN predictions
  const [matchupInfo, setMatchupInfo] = useState<MatchupInfo | null>(null);
  const [matchupOverride, setMatchupOverride] = useState<string | null>(null);  // User can override assumed matchup

  // Draft stats for completed draft
  const [draftStats, setDraftStats] = useState<DraftStats | null>(null);

  // Track if phase change was manual (to prevent auto-switch interference)
  const manualPhaseChangeRef = useRef(false);

  // AbortController for cancelling pending LLM requests
  const llmAbortRef = useRef<AbortController | null>(null);
  // Tracks last ONNX input so we never run inference twice for the same draft state
  const lastOnnxKeyRef = useRef<string>('');
  // Track the turn we last requested analysis for
  const lastAnalysisTurnRef = useRef<number>(-1);

  const currentPicker = getCurrentPicker();
  const ROLE_ORDER: RoleType[] = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];
  const currentSlotRole = (() => {
    if (!currentPicker || currentPicker.isBan) return settings.role;
    if (currentPicker.side === settings.side) {
      const picksForSide = currentPicker.side === 'BLUE' ? picks.blue : picks.red;
      return picksForSide[currentPicker.position]?.role || settings.role;
    }
    // Enemy pick — assume standard role order by pick position
    return ROLE_ORDER[currentPicker.position] || settings.role;
  })();

  // Restore state from localStorage on mount
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('deeplol_proficiencies') || '{}');
      const count = Object.keys(saved).length;
      if (count > 0) setProfCount(count);
      // Restore SoloQ summoner info so the loaded state shows without re-entering IGN
      const info = JSON.parse(localStorage.getItem('tryndraft_summoner_info') || 'null');
      if (info) { setSummonerInfo(info); setSidStatus('loaded'); }
      // Restore clash IGN loaded state so user doesn't have to re-enter after page reload
      const savedClashNames = JSON.parse(localStorage.getItem('tryndraft_clash_names') || '{}');
      const savedClashStatus = JSON.parse(localStorage.getItem('tryndraft_clash_status') || '{}');
      if (Object.keys(savedClashNames).length > 0) setClashIgnNames(savedClashNames);
      if (Object.keys(savedClashStatus).length > 0) setClashIgnStatus(savedClashStatus);
    } catch { /* ignore */ }
  }, []);

  const loadLocalProfileSettings = useCallback(() => {
    try {
      const raw = localStorage.getItem('tryndraft_player_settings');
      if (!raw) return;
      const parsed = JSON.parse(raw);
      // Do NOT override mode/role here — Zustand persist already restores those correctly.
      // Overriding here caused clash mode to reset to soloq on every page reload.
      setProfileSettings({
        soloRiotIds: Array.isArray(parsed.soloRiotIds) ? parsed.soloRiotIds : [],
        clashBlueByRole: Array.isArray(parsed.clashBlueByRole) ? parsed.clashBlueByRole : [],
        clashRedByRole: Array.isArray(parsed.clashRedByRole) ? parsed.clashRedByRole : [],
        clashEnemyUnknown: !!parsed.clashEnemyUnknown,
      });
    } catch (error) {
      console.error('Failed to load local profile settings', error);
    }
  }, []);

  // Build draft state object for API calls
  const buildDraftState = useCallback((): DraftState => {
    // Read picker fresh from store — not in deps so it doesn't recreate this callback on every render
    const picker = useDraftStore.getState().getCurrentPicker();
    const roleOrder: RoleType[] = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];
    let currentSlotRole = settings.role;

    if (picker && !picker.isBan) {
      if (picker.side === settings.side) {
        const picksForSide = picker.side === 'BLUE' ? picks.blue : picks.red;
        currentSlotRole = picksForSide[picker.position]?.role || settings.role;
      } else {
        // Enemy pick — assume standard role order
        currentSlotRole = roleOrder[picker.position] || settings.role;
      }
    }

    // Proficiency boost only when cursor is on the user's own pick slot
    const isUserPickSlot = !picker
      ? true
      : !picker.isBan && picker.side === settings.side && currentSlotRole === settings.role;

    const mode = (settings.mode || 'SOLOQ') as DraftMode;
    const draftState = {
      phase: draftPhase,
      turn: currentTurn,
      side: settings.side,
      role: currentSlotRole || settings.role,
      user_role: settings.role,
      is_user_slot: isUserPickSlot,
      patch: settings.patch,
      mode,
      solo_riot_id: mode === 'SOLOQ' ? (profileSettings.soloRiotIds[0] || '') : undefined,
      clash_blue_ids: mode === 'CLASH' ? profileSettings.clashBlueByRole.map(x => x.riot_id).filter(Boolean) : undefined,
      clash_red_ids: mode === 'CLASH' ? profileSettings.clashRedByRole.map(x => x.riot_id).filter(Boolean) : undefined,
      clash_blue_by_role: mode === 'CLASH' ? profileSettings.clashBlueByRole.filter(x => x.riot_id) : undefined,
      clash_red_by_role: mode === 'CLASH' ? profileSettings.clashRedByRole.filter(x => x.riot_id) : undefined,
      clash_enemy_unknown: mode === 'CLASH' ? profileSettings.clashEnemyUnknown : undefined,
      bans_blue: bans.blue.filter(b => b),
      bans_red: bans.red.filter(b => b),
      picks_blue: picks.blue.filter(p => p.champion).map(p => ({ champion: p.champion, role: p.role })),
      picks_red: picks.red.filter(p => p.champion).map(p => ({ champion: p.champion, role: p.role })),
      // CRITICAL: Include the current slot's role for proper recommendations
      current_slot_role: currentSlotRole,
      current_slot_side: picker?.side || settings.side,
      current_slot_position: picker?.position ?? -1,
      // User can override the assumed matchup
      matchup_override: matchupOverride || undefined,
    };
    return draftState;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftPhase, currentTurn, settings, bans, picks, matchupOverride, profileSettings]);

  // Fetch NN-sorted champions when draft state changes
  const fetchSortedChampions = useCallback(async () => {
    if (draftPhase === 'COMPLETE') return;

    const draftState = buildDraftState();
    // Skip ONNX if draft state hasn't actually changed (prevents CPU thrash from unstable deps)
    const onnxKey = JSON.stringify({
      b: draftState.bans_blue, br: draftState.bans_red,
      p: draftState.picks_blue, pr: draftState.picks_red,
      r: draftState.role, ur: draftState.user_role, t: draftState.turn, ph: draftState.phase,
      mo: draftState.matchup_override,
    });
    if (onnxKey === lastOnnxKeyRef.current) return;
    lastOnnxKeyRef.current = onnxKey;

    try {
      const result = await recommendationService.getSortedChampions(draftState);
      if (result.champions.length > 0) {
        setSortedChampions(result.champions);
        result.champions.forEach((c: ScoredChampion) => { champInfoCache.current[c.name] = c; });
        setModelType(result.model_type);
        if (result.matchup) {
          setMatchupInfo(result.matchup);
        }
      }
    } catch (error) {
      console.error('Failed to fetch sorted champions:', error);
    }
  }, [buildDraftState, draftPhase]);

  const handleSidLoad = useCallback(async () => {
    const trimmed = sidInput.trim();
    if (!trimmed) return;
    setSidStatus('loading');
    try {
      const playerSettings = JSON.parse(localStorage.getItem('tryndraft_player_settings') || '{}');
      const region = playerSettings.deeplolRegion || 'NA1';
      const season = playerSettings.deeplolSeason || 27;

      const result = await recommendationService.fetchDeeplolProficienciesByRiotIds([trimmed], region, season);

      const updated = { ...playerSettings, soloRiotIds: [trimmed] };
      localStorage.setItem('tryndraft_player_settings', JSON.stringify(updated));
      setProfileSettings(prev => ({ ...prev, soloRiotIds: [trimmed] }));

      setProfCount(result.imported);
      setSidStatus(result.found ? 'loaded' : 'error');

      if (result.found) {
        setSidInput(''); // clear on success
        lastOnnxKeyRef.current = ''; // invalidate so ONNX re-runs with fresh proficiency
        setProfVersion(v => v + 1);
        try {
          const info = JSON.parse(localStorage.getItem('tryndraft_summoner_info') || 'null');
          if (info) setSummonerInfo(info);
        } catch { /* ignore */ }

        // In Clash mode, auto-mark the user's role slot as loaded
        const freshSettings = useDraftStore.getState().settings;
        if (freshSettings.mode === 'CLASH') {
          const roleOrder: RoleType[] = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];
          const userPos = roleOrder.indexOf(freshSettings.role as RoleType);
          if (userPos !== -1) {
            const key = `${freshSettings.side}-${userPos}`;
            const gameName = trimmed.split('#')[0];
            setClashIgnNames(prev => ({ ...prev, [key]: gameName }));
            setClashIgnStatus(prev => ({ ...prev, [key]: 'loaded' }));
          }
        }
      }
    } catch {
      setSidStatus('error');
    }
  }, [sidInput]);

  const handleReset = useCallback(() => {
    resetDraft();
    manualPhaseChangeRef.current = true;
    setDraftPhase('BAN');
    localStorage.removeItem('deeplol_proficiencies');
    localStorage.removeItem('tryndraft_summoner_info');
    setSidStatus('idle');
    setSummonerInfo(null);
    setProfCount(0);
    setPinnedChampion(null);
    setSortedChampions([]);
    lastOnnxKeyRef.current = ''; // force fresh ONNX run after reset
    setClashBlueIgns(['', '', '', '', '']);
    setClashRedIgns(['', '', '', '', '']);
    setClashIgnStatus({});
    setClashIgnNames({});
    localStorage.removeItem('tryndraft_clash_names');
    localStorage.removeItem('tryndraft_clash_status');
  }, [resetDraft]);

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

  // Fetch LLM analysis — only called when user explicitly clicks "Explain"
  const fetchLLMAnalysis = useCallback(async () => {
    const freshState = useDraftStore.getState();
    const hasActivity =
      freshState.bans.blue.some(b => b) || freshState.bans.red.some(b => b) ||
      freshState.picks.blue.some(p => p.champion) || freshState.picks.red.some(p => p.champion);
    if (!hasActivity) return;

    if (llmAbortRef.current) {
      llmAbortRef.current.abort();
    }

    const abortController = new AbortController();
    llmAbortRef.current = abortController;
    lastAnalysisTurnRef.current = currentTurn;

    setIsLoadingAnalysis(true);
    try {
      const draftState = buildDraftState();
      const result = await recommendationService.getAnalysis({
        ...draftState,
        is_user_turn: isUsersTurn() || draftPhase === 'BAN',
      });

      if (!abortController.signal.aborted && lastAnalysisTurnRef.current === currentTurn) {
        if (result) setLlmAnalysis(result);
      }
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError') {
        console.error('Failed to fetch LLM analysis:', error);
      }
    } finally {
      if (!abortController.signal.aborted) {
        setIsLoadingAnalysis(false);
      }
    }
  }, [buildDraftState, isUsersTurn, draftPhase, currentTurn]);

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

    // Local profile settings
    loadLocalProfileSettings();

    // If draft is empty, reset to turn 0 (prevents persisted turn jumping straight to PICK)
    const freshState = useDraftStore.getState();
    const hasAnyActivity =
      freshState.bans.blue.some(b => b) || freshState.bans.red.some(b => b) ||
      freshState.picks.blue.some(p => p.champion) || freshState.picks.red.some(p => p.champion);
    if (!hasAnyActivity) setCurrentTurn(0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fetch sorted champions when draft state changes (debounced)
  // Refetch on turn change because each slot may have a different role!
  // Also refetch when matchup override changes
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchSortedChampions();
    }, 300);
    return () => clearTimeout(timer);
  }, [settings.role, draftPhase, currentTurn, matchupOverride, fetchSortedChampions, profVersion]);

  // Persist clash IGN loaded state so it survives page reloads
  useEffect(() => {
    localStorage.setItem('tryndraft_clash_names', JSON.stringify(clashIgnNames));
  }, [clashIgnNames]);
  useEffect(() => {
    localStorage.setItem('tryndraft_clash_status', JSON.stringify(clashIgnStatus));
  }, [clashIgnStatus]);

  // Clear stale LLM analysis when the turn changes
  useEffect(() => {
    setLlmAnalysis(null);
  }, [currentTurn]);

  // Auto-pin the user's champion in their role when draft becomes complete
  useEffect(() => {
    if (draftPhase !== 'COMPLETE') return;
    const roleOrder: RoleType[] = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];
    const userPosition = roleOrder.indexOf(settings.role);
    const userSidePicks = settings.side === 'BLUE' ? picks.blue : picks.red;
    const userChamp = userSidePicks[userPosition]?.champion;
    if (userChamp) setPinnedChampion(userChamp);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftPhase]);

  // Fetch draft stats once when draft becomes complete, then free ONNX from memory
  useEffect(() => {
    if (draftPhase !== 'COMPLETE') { setDraftStats(null); return; }
    const fetchStats = async () => {
      const draftState = buildDraftState();
      const stats = await recommendationService.getDraftStats(draftState);
      if (stats) setDraftStats(stats);
      // Free the ONNX model from WASM memory — won't be needed again until reset
      recommendationService.releaseOnnxSession();
    };
    fetchStats();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [draftPhase]);

  // Auto-switch phases based on draft state
  useEffect(() => {
    if (manualPhaseChangeRef.current) {
      manualPhaseChangeRef.current = false;
      return;
    }

    const totalBans = bans.blue.filter(b => b).length + bans.red.filter(b => b).length;
    const totalPicks = picks.blue.filter(p => p.champion).length + picks.red.filter(p => p.champion).length;
    if (totalBans === 10 && totalPicks === 10) {
      if (draftPhase !== 'COMPLETE') setDraftPhase('COMPLETE');
      return;
    }

    if (currentPicker?.isBan && draftPhase !== 'BAN') setDraftPhase('BAN');
    if (!currentPicker?.isBan && draftPhase !== 'PICK') setDraftPhase('PICK');
  }, [bans, picks, draftPhase, currentPicker]);

  const findNextUnfilledSlot = useCallback(() => {
    const mode = (settings.mode || 'SOLOQ') as DraftMode;
    const sequence = getDraftSequence(mode);
    for (let i = 0; i < sequence.length; i++) {
      const slot = sequence[i];
      if (slot.isBan) {
        const banList = slot.side === 'BLUE' ? bans.blue : bans.red;
        if (!banList[slot.position]) {
          setCurrentTurn(i);
          return;
        }
      } else {
        const pickList = slot.side === 'BLUE' ? picks.blue : picks.red;
        if (!pickList[slot.position]?.champion) {
          setCurrentTurn(i);
          return;
        }
      }
    }
    setCurrentTurn(-1);
  }, [bans, picks, settings.mode, setCurrentTurn]);


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
  const allBannedPicked = useMemo(() => new Set([
    ...bans.blue.filter(Boolean),
    ...bans.red.filter(Boolean),
    ...picks.blue.map(p => p.champion).filter(Boolean),
    ...picks.red.map(p => p.champion).filter(Boolean)
  ]), [bans.blue, bans.red, picks.blue, picks.red]);

  // Filter champions - use NN-sorted if available, otherwise alphabetical
  // ALWAYS check against local allBannedPicked since API data may be stale
  // Also de-duplicate by normalized name to prevent display bugs
  const filteredChamps = useMemo(() => {
    const searchLower = search.toLowerCase().trim();
    const seenNames = new Set<string>();

    const dedup = (names: string[]) => {
      return names.filter(name => {
        const normalized = name.toLowerCase();
        if (seenNames.has(normalized)) return false;
        seenNames.add(normalized);
        return true;
      });
    };

    if (sortedChampions.length > 0) {
      const filtered = sortedChampions
        .filter(champ => {
          if (!champ.available) return false;
          if (allBannedPicked.has(champ.name)) return false;
          if (!searchLower) return true;
          return champ.name.toLowerCase().includes(searchLower);
        })
        .map(champ => champ.name);
      return dedup(filtered);
    } else {
      const filtered = allChampions
        .filter(champ => {
          if (allBannedPicked.has(champ)) return false;
          if (!searchLower) return true;
          return champ.toLowerCase().includes(searchLower);
        })
        .sort((a, b) => a.localeCompare(b));
      return dedup(filtered);
    }
  }, [sortedChampions, allBannedPicked, allChampions, search]);

  // Immediately compute and set next turn after a selection
  const advanceToNextSlot = useCallback((justSelectedChampion: string, justUsedPicker: { side: 'BLUE' | 'RED'; position: number; isBan: boolean }) => {
    const freshState = useDraftStore.getState();
    const freshBans = freshState.bans;
    const freshPicks = freshState.picks;

    const mode = (freshState.settings.mode || 'SOLOQ') as DraftMode;
    const sequence = getDraftSequence(mode);
    const blueBans = [...freshBans.blue];
    const redBans = [...freshBans.red];
    const bluePicks = [...freshPicks.blue];
    const redPicks = [...freshPicks.red];

    if (justUsedPicker.isBan) {
      if (justUsedPicker.side === 'BLUE') blueBans[justUsedPicker.position] = justSelectedChampion;
      else redBans[justUsedPicker.position] = justSelectedChampion;
    } else {
      if (justUsedPicker.side === 'BLUE') bluePicks[justUsedPicker.position] = { ...bluePicks[justUsedPicker.position], champion: justSelectedChampion };
      else redPicks[justUsedPicker.position] = { ...redPicks[justUsedPicker.position], champion: justSelectedChampion };
    }

    for (let i = 0; i < sequence.length; i++) {
      const slot = sequence[i];
      if (slot.isBan) {
        const banList = slot.side === 'BLUE' ? blueBans : redBans;
        if (!banList[slot.position]) {
          setCurrentTurn(i);
          return;
        }
      } else {
        const pickList = slot.side === 'BLUE' ? bluePicks : redPicks;
        if (!pickList[slot.position]?.champion) {
          setCurrentTurn(i);
          return;
        }
      }
    }
    setCurrentTurn(-1);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setCurrentTurn]);

  const handleChampionSelect = useCallback((champion: string) => {
    const freshState = useDraftStore.getState();
    const picker = freshState.getCurrentPicker();
    if (!picker) return;

    const { bans: freshBans, picks: freshPicks, addBan, addPick } = freshState;
    const currentBannedPicked = new Set([
      ...freshBans.blue.filter(Boolean),
      ...freshBans.red.filter(Boolean),
      ...freshPicks.blue.map(p => p.champion).filter(Boolean),
      ...freshPicks.red.map(p => p.champion).filter(Boolean)
    ]);

    if (currentBannedPicked.has(champion)) return;

    let success = false;
    if (picker.isBan) {
      success = addBan(champion, picker.side, picker.position);
    } else {
      const currentPicks = picker.side === 'BLUE' ? freshPicks.blue : freshPicks.red;
      const currentRole = currentPicks[picker.position]?.role || 'TOP';
      success = addPick(champion, currentRole, picker.side, picker.position);
    }

    if (success) {
      if (!picker.isBan) setPinnedChampion(champion);
      advanceToNextSlot(champion, picker);
    }
    setSearch('');
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [advanceToNextSlot, setPinnedChampion]);

  const handleSlotClick = (side: 'BLUE' | 'RED', position: number, isBan: boolean) => {
    // If draft is complete (all slots filled), always update phase based on slot type clicked
    if (isDraftComplete()) {
      manualPhaseChangeRef.current = true;
      setDraftPhase(isBan ? 'BAN' : 'PICK');
    }

    if (isBan) {
      const turn = getTurnFromSlot((settings.mode || 'SOLOQ') as DraftMode, side, position, true);
      if (turn !== -1) setCurrentTurn(turn);
    } else {
      const turn = getTurnFromSlot((settings.mode || 'SOLOQ') as DraftMode, side, position, false);
      if (turn !== -1) setCurrentTurn(turn);
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
        setPinnedChampion(draggedChampion);
        advanceToNextSlot(draggedChampion, { side, position: targetIndex, isBan: false });
      }
      setDraggedChampion(null);
      return;
    }

    // Slot drag
    if (draggedIndex === null || draggedSide === null || draggedIsBan) return;
    if (draggedSide !== side) return;
    if (draggedIndex === targetIndex) return;

    const pickList = side === 'BLUE' ? picks.blue : picks.red;
    // On enemy side, only allow moving a champion — not reordering empty boxes
    if (side !== settings.side && !pickList[draggedIndex].champion) return;
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

  const handleDragEnd = useCallback(() => {
    setDraggedIndex(null);
    setDraggedSide(null);
    setDraggedIsBan(false);
    setDraggedChampion(null);
    setHoveredSlot(null);
  }, []);

  // Only rebuilds when champion list or patch changes — NOT on every hover event
  const championGrid = useMemo(() => (
    <div className="grid grid-cols-8 gap-2 pr-1">
      {filteredChamps.map((champ, idx) => (
        <button
          key={`${champ}-${idx}`}
          onClick={() => handleChampionSelect(champ)}
          draggable={true}
          onDragStart={() => setDraggedChampion(champ)}
          onDragEnd={handleDragEnd}
          onMouseEnter={() => setHoveredChampion(champ)}
          className="aspect-square rounded overflow-hidden relative group hover:scale-105 hover:z-10 transition-transform cursor-grab active:cursor-grabbing border border-gray-900 hover:border-amber-500">
          <img src={getChampionImageUrl(champ, latestPatch)} alt={champ} className="w-full h-full object-cover pointer-events-none" />
          <div className="absolute inset-0 bg-gradient-to-t from-black/90 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-center pb-1 pointer-events-none">
            <span className="text-white font-bold text-[10px] uppercase tracking-wide">{champ}</span>
          </div>
        </button>
      ))}
    </div>
  // eslint-disable-next-line react-hooks/exhaustive-deps
  ), [filteredChamps, latestPatch, handleChampionSelect, handleDragEnd]);

  // Handle dragging back to center (picker or LLM box) to clear slot
  const handleDropOnCenter = (e: React.DragEvent) => {
    e.preventDefault();
    if (draggedIndex !== null && draggedSide !== null) {
      if (draggedIsBan) {
        // Clear ban
        const banList = draggedSide === 'BLUE' ? bans.blue : bans.red;
        if (banList[draggedIndex]) {
          addBan('', draggedSide, draggedIndex);
          const turn = getTurnFromSlot((settings.mode || 'SOLOQ') as DraftMode, draggedSide, draggedIndex, true);
          if (turn !== -1) setCurrentTurn(turn);
          // Update phase to BAN since we're now missing a ban
          manualPhaseChangeRef.current = true;
          setDraftPhase('BAN');
        }
      } else {
        // Clear pick
        const pickList = draggedSide === 'BLUE' ? picks.blue : picks.red;
        if (pickList[draggedIndex]?.champion) {
          addPick('', pickList[draggedIndex].role, draggedSide, draggedIndex);
          const turn = getTurnFromSlot((settings.mode || 'SOLOQ') as DraftMode, draggedSide, draggedIndex, false);
          if (turn !== -1) setCurrentTurn(turn);
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

  const handleClashIgnLoad = async (side: 'BLUE' | 'RED', position: number) => {
    const ign = side === 'BLUE' ? clashBlueIgns[position] : clashRedIgns[position];
    if (!ign.trim()) return;
    const key = `${side}-${position}`;
    setClashIgnStatus(prev => ({ ...prev, [key]: 'loading' }));
    // Enemy team IGNs go into a separate pool used only for ban suggestions
    const isEnemy = side !== settings.side;
    try {
      const fetchFn = isEnemy
        ? recommendationService.fetchEnemyDeeplolProficienciesByRiotIds
        : recommendationService.fetchDeeplolProficienciesByRiotIds;
      const result = await fetchFn([ign], 'NA1');
      if (result.found) {
        const gameName = ign.split('#')[0] || ign;
        setClashIgnNames(prev => ({ ...prev, [key]: gameName }));
        if (side === 'BLUE') {
          setClashBlueIgns(prev => { const n = [...prev]; n[position] = ''; return n; });
        } else {
          setClashRedIgns(prev => { const n = [...prev]; n[position] = ''; return n; });
        }
      }
      setClashIgnStatus(prev => ({ ...prev, [key]: result.found ? 'loaded' : 'error' }));
    } catch {
      setClashIgnStatus(prev => ({ ...prev, [key]: 'error' }));
    }
  };

  const handleLoadAll = async () => {
    const { side } = useDraftStore.getState().settings;
    const igns = side === 'BLUE' ? clashBlueIgns : clashRedIgns;
    for (let i = 0; i < igns.length; i++) {
      if (igns[i].trim() && clashIgnStatus[`${side}-${i}`] !== 'loaded') {
        await handleClashIgnLoad(side, i);
      }
    }
    // Refresh ONNX recommendations and transparency with newly loaded proficiency data
    lastOnnxKeyRef.current = '';
    setProfVersion(v => v + 1);
  };

  const resetClashSlot = (side: 'BLUE' | 'RED', position: number) => {
    const key = `${side}-${position}`;
    setClashIgnStatus(prev => { const n = { ...prev }; delete n[key]; return n; });
    setClashIgnNames(prev => { const n = { ...prev }; delete n[key]; return n; });
    // Clear the appropriate pool — ally slots use main proficiency pool, enemy slots use enemy pool
    const isEnemy = side !== settings.side;
    localStorage.removeItem(isEnemy ? 'tryndraft_enemy_proficiencies' : 'deeplol_proficiencies');
    if (!isEnemy) setProfCount(0);
    lastOnnxKeyRef.current = '';
    setProfVersion(v => v + 1);
  };

  // Build op.gg URL — uses display name (e.g. "Wukong" not "MonkeyKing")
  const getOpGGUrl = (champName: string, role?: string) => {
    const slug = champName.toLowerCase().replace(/[^a-z0-9]/g, '');
    const roleMap: Record<string, string> = { TOP: 'top', JUNGLE: 'jungle', MID: 'mid', ADC: 'adc', SUPPORT: 'support' };
    const pos = roleMap[(role || '').toUpperCase()];
    return `https://www.op.gg/champions/${slug}/build${pos ? `?position=${pos}` : ''}`;
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

          {/* My Role */}
          <div className="flex items-center gap-1 bg-gray-900 rounded p-1" title="Your role">
            {ROLES.map(r => (
              <button
                key={r}
                onClick={() => setSettings({ role: r })}
                className={`p-1.5 rounded transition-colors ${settings.role === r ? 'bg-amber-600' : 'opacity-30 hover:opacity-70'}`}
                title={r}
              >
                <RoleIcon role={r} size={18} />
              </button>
            ))}
          </div>

          {/* Patch */}
          <div className="text-sm text-gray-500 font-mono">{latestPatch}</div>

          {/* Phase Toggle */}
          <div className="flex gap-2 bg-gray-900 rounded p-1">
            <button onClick={() => { manualPhaseChangeRef.current = true; setDraftPhase('BAN'); setCurrentTurn(0); }} className={`px-4 py-2 rounded text-sm font-bold ${draftPhase === 'BAN' ? 'bg-red-500 text-white' : 'text-gray-600'}`}>BAN</button>
            <button onClick={() => {
              manualPhaseChangeRef.current = true;
              setDraftPhase('PICK');
              const sequence = getDraftSequence((settings.mode || 'SOLOQ') as DraftMode);
              const firstPickTurn = sequence.findIndex(s => !s.isBan);
              setCurrentTurn(firstPickTurn === -1 ? 10 : firstPickTurn);
            }} className={`px-4 py-2 rounded text-sm font-bold ${draftPhase === 'PICK' ? 'bg-blue-500 text-white' : 'text-gray-600'}`}>PICK</button>
            <button
              onClick={() => { manualPhaseChangeRef.current = true; setDraftPhase('COMPLETE'); }}
              disabled={bans.blue.filter(b => b).length + bans.red.filter(b => b).length < 10 || picks.blue.filter(p => p.champion).length + picks.red.filter(p => p.champion).length < 10}
              className={`px-4 py-2 rounded text-sm font-bold ${draftPhase === 'COMPLETE' ? 'bg-green-500 text-white' : 'text-gray-600'} disabled:opacity-30 disabled:cursor-not-allowed`}
            >
              DONE
            </button>
          </div>

          <button onClick={handleReset} className="px-3 py-2 text-sm text-gray-500 hover:text-white">Reset</button>
        </div>

        {/* Mode toggle */}
        <div className="flex gap-0 bg-gray-900 rounded p-1">
          <button
            onClick={() => setSettings({ mode: 'SOLOQ' as DraftMode })}
            className={`px-3 py-1.5 rounded text-xs font-bold transition-colors ${(settings.mode || 'SOLOQ') === 'SOLOQ' ? 'bg-amber-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}
          >
            SoloQ
          </button>
          <button
            onClick={() => setSettings({ mode: 'CLASH' as DraftMode })}
            className={`px-3 py-1.5 rounded text-xs font-bold transition-colors ${settings.mode === 'CLASH' ? 'bg-purple-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}
          >
            Clash
          </button>
        </div>
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
                  onClick={() => { handleSlotClick('BLUE', i, true); if (ban) setPinnedChampion(ban); }}
                  draggable={true}
                  onDragStart={() => handleDragStart('BLUE', i, true)}
                  onDragOver={handleDragOver}
                  onDrop={() => handleBanDrop('BLUE', i)}
                  onDragEnd={handleDragEnd}
                  onMouseEnter={() => { setHoveredSlot({side: 'BLUE', index: i, isBan: true}); if (ban) setHoveredChampion(ban); }}
                  onMouseLeave={() => { setHoveredSlot(null); setHoveredChampion(null); }}
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
                  onClick={() => { handleSlotClick('BLUE', i, false); if (pick.champion) setPinnedChampion(pick.champion); }}
                  draggable={true}
                  onDragStart={() => handleDragStart('BLUE', i, false)}
                  onDragOver={handleDragOver}
                  onDrop={() => handlePickDrop('BLUE', i)}
                  onDragEnd={handleDragEnd}
                  onMouseEnter={() => { setHoveredSlot({side: 'BLUE', index: i, isBan: false}); if (pick.champion) setHoveredChampion(pick.champion); }}
                  onMouseLeave={() => { setHoveredSlot(null); setHoveredChampion(null); }}
                  className={`h-[calc((100vh-16rem)/5)] rounded overflow-hidden relative border ${isActive ? `ring-2 ${phaseColorClass}` : 'border-gray-900'} flex items-center ${isDragging ? 'opacity-50' : ''} ${hasChampion ? 'cursor-move' : 'cursor-pointer'}`}>
                  {pick.champion ? (
                    <>
                      <img src={getChampionSplashUrl(pick.champion)} alt={pick.champion} className="w-full h-full object-cover object-center pointer-events-none" />
                      {settings.side === 'BLUE' && (
                        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                          <RoleIcon role={pick.role} size={48} className="opacity-70 drop-shadow-lg" />
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="w-full h-full bg-gray-950 flex items-center justify-center border border-gray-900">
                      {settings.side === 'BLUE' && <RoleIcon role={pick.role} size={36} className="text-gray-800" />}
                    </div>
                  )}
                  {/* Clash: IGN input overlay at bottom of slot */}
                  {settings.mode === 'CLASH' && (
                    <div className="absolute bottom-0 left-0 right-0 bg-black/80 flex items-center gap-1.5 px-2 py-1.5" onClick={e => e.stopPropagation()} onMouseDown={e => e.stopPropagation()}>
                      {clashIgnStatus[`BLUE-${i}`] === 'loaded' ? (
                        <div className="flex items-center gap-1 min-w-0 w-full">
                          <CheckCircle size={10} className="shrink-0 text-green-400" />
                          <span className="text-[11px] text-green-300 font-mono truncate flex-1">{clashIgnNames[`BLUE-${i}`]}</span>
                          <button onClick={e => { e.stopPropagation(); resetClashSlot('BLUE', i); }} onMouseDown={e => e.stopPropagation()} className="shrink-0 text-gray-500 hover:text-red-400 transition-colors"><X size={10} /></button>
                        </div>
                      ) : (
                        <>
                          <input
                            type="text"
                            value={clashBlueIgns[i]}
                            onChange={e => setClashBlueIgns(prev => { const n = [...prev]; n[i] = e.target.value; return n; })}
                            onMouseDown={e => e.stopPropagation()}
                            onClick={e => e.stopPropagation()}
                            onFocus={e => e.stopPropagation()}
                            onKeyDown={e => { e.stopPropagation(); if (e.key === 'Enter') handleClashIgnLoad('BLUE', i); }}
                            placeholder="Name#TAG"
                            className="flex-1 min-w-0 bg-transparent text-[11px] text-gray-300 placeholder-gray-600 outline-none"
                          />
                          {clashIgnStatus[`BLUE-${i}`] === 'loading' && <Loader2 size={10} className="shrink-0 text-gray-500 animate-spin" />}
                          {clashIgnStatus[`BLUE-${i}`] === 'error' && <AlertCircle size={10} className="shrink-0 text-red-400" />}
                        </>
                      )}
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* CENTER - Statistics Bar, Champion Picker and LLM Box */}
        <div className={`flex-1 flex flex-col border-l border-r ${phaseColorClass} min-w-0`}>
          <div className="px-3 pt-2 pb-1 border-b border-gray-900 flex items-center gap-2">
            {/* SoloQ: Name#TAG loader / Clash: Load All button */}
            <div className="flex items-center gap-1 flex-1 min-w-0">
              {settings.mode === 'CLASH' ? (
                <>
                  <button
                    onClick={handleLoadAll}
                    className="shrink-0 px-3 py-1 rounded text-[11px] font-medium bg-purple-700 hover:bg-purple-600 text-white transition-colors"
                  >
                    Load All
                  </button>
                  <span className="text-[10px] text-gray-600">Enter IGNs in each slot, then Load All</span>
                </>
              ) : (
                <>
                  <input
                    type="text"
                    value={sidInput}
                    onChange={e => { setSidInput(e.target.value); setSidStatus('idle'); }}
                    onKeyDown={e => e.key === 'Enter' && handleSidLoad()}
                    placeholder="Name#TAG"
                    className="flex-1 min-w-0 bg-gray-950 border border-gray-800 rounded px-2 py-1 text-[11px] text-gray-300 placeholder-gray-700 focus:outline-none focus:border-amber-500/50"
                  />
                  <button
                    onClick={handleSidLoad}
                    disabled={sidStatus === 'loading' || !sidInput.trim()}
                    className="shrink-0 px-2 py-1 rounded text-[11px] font-medium bg-gray-800 hover:bg-gray-700 text-gray-300 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  >
                    {sidStatus === 'loading' ? <Loader2 size={12} className="animate-spin" /> : 'Load'}
                  </button>
                  {sidStatus === 'loaded' && (
                    <span className="shrink-0 flex items-center gap-1 text-[10px]">
                      <CheckCircle size={10} className="text-green-400 shrink-0" />
                      {summonerInfo && <span className="font-mono text-amber-400 tracking-tight">{summonerInfo.gameName}</span>}
                    </span>
                  )}
                  {sidStatus === 'error' && (
                    <span className="shrink-0 flex items-center gap-1 text-[10px] text-red-400">
                      <AlertCircle size={10} /> not found
                    </span>
                  )}
                  {sidStatus === 'idle' && profCount > 0 && (
                    <span className="text-[10px] text-gray-600">Pool: {profCount} champs</span>
                  )}
                </>
              )}
            </div>

          </div>
          {/* Statistics Bar - Only visible when draft is complete */}
          {draftPhase === 'COMPLETE' && (
            <div className="h-20 bg-gradient-to-r from-black/90 via-gray-900/80 to-black/90 border-b-2 border-amber-500/30 px-6 flex items-center justify-between">
              <div className="flex items-center gap-8">
                {/* Lane Matchup */}
                <div className="text-xs">
                  <div className="text-gray-500 uppercase tracking-wider font-bold mb-1">Lane Matchup</div>
                  <div className="flex items-center gap-2">
                    <span className="text-gray-400">{settings.role}:</span>
                    <div className={`font-bold text-lg ${
                      draftStats?.lane_matchup.win_rate && draftStats.lane_matchup.win_rate >= 52 ? 'text-green-400' :
                      draftStats?.lane_matchup.win_rate && draftStats.lane_matchup.win_rate <= 48 ? 'text-red-400' : 'text-gray-400'
                    }`}>
                      {draftStats?.lane_matchup.win_rate ? `${draftStats.lane_matchup.win_rate}%` : '--'}
                    </div>
                    <span className="text-xs text-gray-600">
                      {draftStats?.lane_matchup.games ? `(${draftStats.lane_matchup.games} games)` : 'WR'}
                    </span>
                  </div>
                </div>

                <div className="w-px h-12 bg-gray-800"></div>

                {/* Overall Team Win % */}
                <div className="text-xs">
                  <div className="text-gray-500 uppercase tracking-wider font-bold mb-1">Comp Win %</div>
                  <div className="flex items-center gap-2">
                    <div className="text-blue-400 font-bold text-lg">
                      {draftStats?.comp_win.your_team ? `${draftStats.comp_win.your_team}%` : '50%'}
                    </div>
                    <span className="text-gray-600">vs</span>
                    <div className="text-red-400 font-bold text-lg">
                      {draftStats?.comp_win.enemy_team ? `${draftStats.comp_win.enemy_team}%` : '50%'}
                    </div>
                  </div>
                </div>

                <div className="w-px h-12 bg-gray-800"></div>

                {/* Synergy Score */}
                <div className="text-xs">
                  <div className="text-gray-500 uppercase tracking-wider font-bold mb-1">Synergy Score</div>
                  <div className="flex items-center gap-1">
                    <div className="w-20 h-2 bg-gray-800 rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-green-500 to-emerald-400"
                        style={{width: `${(draftStats?.synergy.your_team.score || 5) * 10}%`}}
                      ></div>
                    </div>
                    <span className="text-green-400 font-mono text-sm ml-1">
                      {draftStats?.synergy.your_team.score ? `${draftStats.synergy.your_team.score}/10` : '5/10'}
                    </span>
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
                      <span className="text-white font-mono text-sm">
                        {draftStats?.damage_split.your_team.ad !== undefined ? `${Math.round(draftStats.damage_split.your_team.ad)}%` : '50%'}
                      </span>
                    </div>
                    <div className="flex items-center gap-1">
                      <div className="w-3 h-3 bg-blue-500 rounded"></div>
                      <span className="text-gray-400 text-xs">AP</span>
                      <span className="text-white font-mono text-sm">
                        {draftStats?.damage_split.your_team.ap !== undefined ? `${Math.round(draftStats.damage_split.your_team.ap)}%` : '50%'}
                      </span>
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
                onDrop={handleDropOnCenter}
                onMouseLeave={() => setHoveredChampion(null)}>
                {championGrid}
              </div>
            </div>
          )}

          {/* Recommendations + AI Analysis box */}
          <div
            className={`${draftPhase === 'COMPLETE' ? 'flex-1' : 'h-1/2'} bg-black/90 border-t-2 ${phaseColorClass} p-3 flex flex-col`}
            onDragOver={handleDragOver}
            onDrop={handleDropOnCenter}>
            <div className="flex items-center justify-between mb-2">
              <div className="text-xs text-gray-600 uppercase tracking-wider font-bold">Recommendations</div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-gray-700 font-mono">
                  {modelType === 'frontend_onnx_only' ? 'ONNX' : ''}
                </span>
                {draftPhase === 'COMPLETE' && (
                  <>
                    {isLoadingAnalysis && <Loader2 className="w-3 h-3 animate-spin text-gray-500" />}
                    <button
                      onClick={() => fetchLLMAnalysis()}
                      disabled={isLoadingAnalysis}
                      className="text-[10px] px-2 py-0.5 rounded bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                    >
                      Explain
                    </button>
                  </>
                )}
              </div>
            </div>
            <div className="flex-1 text-base text-gray-400 overflow-y-auto custom-scrollbar">
              <div className="space-y-2">

                {/* Recommended Picks/Bans — always visible once ONNX loads */}
                {sortedChampions.length > 0 && draftPhase !== 'COMPLETE' && (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-xs text-amber-500 uppercase tracking-wider font-bold">
                        {draftPhase === 'BAN' ? 'Recommended Bans' : `Recommended Picks · ${currentSlotRole}`}
                      </div>
                      {draftPhase === 'PICK' && matchupInfo && (
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] text-gray-500">
                            {matchupInfo.matchup_type === 'counter' ? `vs ${matchupInfo.matchup_champion}` : 'Blind'}
                          </span>
                          <select
                            value={matchupOverride || ''}
                            onChange={(e) => setMatchupOverride(e.target.value || null)}
                            className="text-[10px] bg-gray-800 border border-gray-600 rounded px-1.5 py-0.5 text-gray-300 cursor-pointer"
                          >
                            <option value="">Auto</option>
                            {Object.entries(matchupInfo.all_enemy_roles || {}).map(([champ, role]) => (
                              <option key={champ} value={champ}>{champ} ({role})</option>
                            ))}
                            <option value="__blind__">Blind</option>
                          </select>
                        </div>
                      )}
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {sortedChampions
                        .filter(c => c.available && !allBannedPicked.has(c.name))
                        .slice(0, 5)
                        .map((champ, idx) => {
                          return (
                            <button
                              key={idx}
                              onClick={() => handleChampionSelect(champ.name)}
                              className="flex items-center gap-1.5 rounded px-2 py-1.5 border transition-all cursor-pointer bg-gray-800/90 border-gray-700 hover:border-amber-500 hover:bg-gray-700/90"
                            >
                              <img src={getChampionImageUrl(champ.name, latestPatch)} alt={champ.name} className="w-6 h-6 rounded" />
                              <span className="text-sm text-gray-200 font-medium">{champ.name}</span>
                              <span className="text-[10px] text-gray-500">#{idx + 1}</span>
                            </button>
                          );
                        })}
                    </div>
                  </div>
                )}

                {/* Stats transparency — shows hovered champion, or last picked/pinned champion */}
                {(() => {
                  const activeChamp = hoveredChampion ?? pinnedChampion;
                  if (!activeChamp) return null;
                  const displayChamp = sortedChampions.find(c => c.name === activeChamp)
                    ?? champInfoCache.current[activeChamp]
                    // Fallback for bans / champions never in ONNX results (zeroed out after being banned)
                    ?? (allChampions.includes(activeChamp) ? {
                      id: activeChamp, name: activeChamp, key: '', score: 0,
                      available: false, in_user_pool: false, user_proficiency: null,
                      win_rate: 0.5, pick_rate: 0, roles: [],
                    } as ScoredChampion : null);
                  if (!displayChamp) return null;
                  const rank = sortedChampions.findIndex(c => c.name === displayChamp.name) + 1;
                  const label = hoveredChampion
                    ? 'Hovered'
                    : draftPhase === 'COMPLETE' ? 'Your Pick' : 'Last Picked';
                  // Always read proficiency fresh from localStorage so it updates immediately
                  // after IGN load without needing to re-run ONNX (critical in COMPLETE phase)
                  const freshProf = (() => {
                    try {
                      const saved = JSON.parse(localStorage.getItem('deeplol_proficiencies') || '{}');
                      return displayChamp.key ? (saved[displayChamp.key] ?? null) : null;
                    } catch { return null; }
                  })();
                  const inPool = freshProf != null || displayChamp.in_user_pool;
                  const roleGames: number = freshProf?.games ?? displayChamp.role_games ?? 0;
                  const roleWR: number | undefined = freshProf
                    ? freshProf.win_rate / 100
                    : displayChamp.role_win_rate;
                  return (
                    <div className="pt-2 border-t border-gray-700">
                      <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1 font-bold">
                        {label} · {displayChamp.target_role || settings.role}
                      </div>
                      <div className="bg-gray-900/60 rounded p-2">
                        <div className="flex items-center gap-2 mb-1.5">
                          <img src={getChampionImageUrl(displayChamp.name, latestPatch)} alt={displayChamp.name} className="w-8 h-8 rounded" />
                          <div>
                            <div className="text-gray-200 font-semibold text-sm">{displayChamp.name}</div>
                          </div>
                        </div>
                        <div className="flex gap-1.5 text-center text-xs">
                          {rank > 0 && (
                            <div className="flex-1 bg-gray-800/50 rounded p-1.5">
                              <div className="text-amber-400 font-bold">#{rank}</div>
                              <div className="text-[9px] text-gray-500">Model Rank</div>
                            </div>
                          )}
                          {inPool && roleGames > 0 ? (
                            <>
                              <div className="flex-1 bg-gray-800/50 rounded p-1.5">
                                <div className="text-blue-400 font-bold">{roleGames}</div>
                                <div className="text-[9px] text-gray-500">Your Games</div>
                              </div>
                              <div className="flex-1 bg-gray-800/50 rounded p-1.5">
                                <div className="text-green-400 font-bold">
                                  {roleWR ? `${(roleWR * 100).toFixed(0)}%` : '—'}
                                </div>
                                <div className="text-[9px] text-gray-500">Your WR</div>
                              </div>
                            </>
                          ) : (
                            <div className="flex-1 bg-gray-800/50 rounded p-1.5 flex items-center justify-center">
                              <span className="text-[9px] text-gray-600">
                                {inPool ? 'No pool data' : 'Not in your pool'}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })()}

                {/* op.gg build link — shown when hovering or a champion is pinned */}
                {(hoveredChampion || pinnedChampion) && (() => {
                  const active = hoveredChampion ?? pinnedChampion!;
                  const champ = sortedChampions.find(c => c.name === active)
                    ?? champInfoCache.current[active]
                    ?? (allChampions.includes(active) ? { name: active } as ScoredChampion : null);
                  if (!champ) return null;
                  const role = champ.target_role || settings.role;
                  return (
                    <div className="pt-1.5">
                      <a
                        href={getOpGGUrl(champ.name, role)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center justify-between w-full px-2 py-1.5 rounded bg-gray-900/80 border border-gray-800 hover:border-amber-500/40 hover:bg-gray-800/80 transition-colors group"
                      >
                        <div className="flex items-center gap-1.5">
                          <img src={getChampionImageUrl(champ.name, latestPatch)} alt={champ.name} className="w-4 h-4 rounded" />
                          <span className="text-[10px] text-gray-400 group-hover:text-gray-200">{champ.name} builds</span>
                        </div>
                        <div className="flex items-center gap-1">
                          <span className="text-[9px] text-gray-600 font-bold uppercase">op.gg</span>
                          <ExternalLink size={9} className="text-gray-600 group-hover:text-amber-400" />
                        </div>
                      </a>
                    </div>
                  );
                })()}

                {/* LLM explanation — only when user clicks Explain */}
                {llmAnalysis && (
                  <div className="pt-2 border-t border-gray-700">
                    <p className="text-gray-100 leading-relaxed text-[15px] whitespace-pre-line">{llmAnalysis.analysis}</p>
                    <div className="text-[9px] text-gray-700 pt-1">{llmAnalysis.model} · {llmAnalysis.source}</div>
                  </div>
                )}

                {/* Draft complete placeholder */}
                {draftPhase === 'COMPLETE' && (
                  <div className="text-center mt-6">
                    <p className="text-gray-500 font-bold mb-1">Draft Complete</p>
                    {!llmAnalysis && <p className="text-xs text-gray-700">Click Explain for AI summary.</p>}
                  </div>
                )}

                {/* ONNX still loading */}
                {sortedChampions.length === 0 && draftPhase !== 'COMPLETE' && (
                  <div className="flex items-center gap-2 text-gray-600 text-sm">
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Loading recommendations...</span>
                  </div>
                )}
              </div>
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
                  onClick={() => { handleSlotClick('RED', i, true); if (ban) setPinnedChampion(ban); }}
                  draggable={true}
                  onDragStart={() => handleDragStart('RED', i, true)}
                  onDragOver={handleDragOver}
                  onDrop={() => handleBanDrop('RED', i)}
                  onDragEnd={handleDragEnd}
                  onMouseEnter={() => { setHoveredSlot({side: 'RED', index: i, isBan: true}); if (ban) setHoveredChampion(ban); }}
                  onMouseLeave={() => { setHoveredSlot(null); setHoveredChampion(null); }}
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
                  onClick={() => { handleSlotClick('RED', i, false); if (pick.champion) setPinnedChampion(pick.champion); }}
                  draggable={true}
                  onDragStart={() => handleDragStart('RED', i, false)}
                  onDragOver={handleDragOver}
                  onDrop={() => handlePickDrop('RED', i)}
                  onDragEnd={handleDragEnd}
                  onMouseEnter={() => { setHoveredSlot({side: 'RED', index: i, isBan: false}); if (pick.champion) setHoveredChampion(pick.champion); }}
                  onMouseLeave={() => { setHoveredSlot(null); setHoveredChampion(null); }}
                  className={`h-[calc((100vh-16rem)/5)] rounded overflow-hidden relative border ${isActive ? `ring-2 ${phaseColorClass}` : 'border-gray-900'} flex items-center ${isDragging ? 'opacity-50' : ''} ${hasChampion ? 'cursor-move' : 'cursor-pointer'}`}>
                  {pick.champion ? (
                    <>
                      <img src={getChampionSplashUrl(pick.champion)} alt={pick.champion} className="w-full h-full object-cover object-center pointer-events-none" />
                      {settings.side === 'RED' && (
                        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                          <RoleIcon role={pick.role} size={48} className="opacity-70 drop-shadow-lg" />
                        </div>
                      )}
                    </>
                  ) : (
                    <div className="w-full h-full bg-gray-950 flex items-center justify-center border border-gray-900">
                      {settings.side === 'RED' && <RoleIcon role={pick.role} size={36} className="text-gray-800" />}
                    </div>
                  )}
                  {/* Clash: IGN input overlay at bottom of slot */}
                  {settings.mode === 'CLASH' && (
                    <div className="absolute bottom-0 left-0 right-0 bg-black/80 flex items-center gap-1.5 px-2 py-1.5" onClick={e => e.stopPropagation()} onMouseDown={e => e.stopPropagation()}>
                      {clashIgnStatus[`RED-${i}`] === 'loaded' ? (
                        <div className="flex items-center gap-1 min-w-0 w-full">
                          <CheckCircle size={10} className="shrink-0 text-green-400" />
                          <span className="text-[11px] text-green-300 font-mono truncate flex-1">{clashIgnNames[`RED-${i}`]}</span>
                          <button onClick={e => { e.stopPropagation(); resetClashSlot('RED', i); }} onMouseDown={e => e.stopPropagation()} className="shrink-0 text-gray-500 hover:text-red-400 transition-colors"><X size={10} /></button>
                        </div>
                      ) : (
                        <>
                          <input
                            type="text"
                            value={clashRedIgns[i]}
                            onChange={e => setClashRedIgns(prev => { const n = [...prev]; n[i] = e.target.value; return n; })}
                            onMouseDown={e => e.stopPropagation()}
                            onClick={e => e.stopPropagation()}
                            onFocus={e => e.stopPropagation()}
                            onKeyDown={e => { e.stopPropagation(); if (e.key === 'Enter') handleClashIgnLoad('RED', i); }}
                            placeholder="Name#TAG"
                            className="flex-1 min-w-0 bg-transparent text-[11px] text-gray-300 placeholder-gray-600 outline-none"
                          />
                          {clashIgnStatus[`RED-${i}`] === 'loading' && <Loader2 size={10} className="shrink-0 text-gray-500 animate-spin" />}
                          {clashIgnStatus[`RED-${i}`] === 'error' && <AlertCircle size={10} className="shrink-0 text-red-400" />}
                        </>
                      )}
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
