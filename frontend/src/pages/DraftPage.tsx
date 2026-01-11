import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useDraftStore } from '../store/useDraftStore';
import { getLatestPatch, getChampionImageUrl, getChampionSplashUrl } from '../utils/patch';
import { Search, X, Sword, Settings } from 'lucide-react';
import { RoleIcon } from '../components/common/RoleIcon';
import type { RoleType } from '../store/useDraftStore';

const ROLES: RoleType[] = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];
const RANKS = ['IRON', 'BRONZE', 'SILVER', 'GOLD', 'PLATINUM', 'EMERALD', 'DIAMOND', 'MASTER', 'GRANDMASTER', 'CHALLENGER'];

export const DraftPage: React.FC = () => {
  const {
    settings,
    bans,
    picks,
    currentTurn,
    setSettings,
    setCurrentTurn,
    nextTurn,
    addBan,
    addPick,
    resetDraft,
    getCurrentPicker,
    allChampions,
    loadChampions,
    movePick,
  } = useDraftStore();

  const [latestPatch, setLatestPatch] = useState('16.1.1');
  const [search, setSearch] = useState('');
  const [isBanPhase, setIsBanPhase] = useState(true);
  const [shouldAdvanceCursor, setShouldAdvanceCursor] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [draggedSide, setDraggedSide] = useState<'BLUE' | 'RED' | null>(null);
  const [hoveredSlot, setHoveredSlot] = useState<{side: 'BLUE' | 'RED', index: number} | null>(null);
  const [draggedChampion, setDraggedChampion] = useState<string | null>(null);

  const currentPicker = getCurrentPicker();

  useEffect(() => {
    if (allChampions.length === 0) {
      loadChampions();
    }

    getLatestPatch().then(version => {
      setLatestPatch(version);
      setSettings({ patch: version });
    });
  }, []);

  useEffect(() => {
    setIsBanPhase(currentTurn < 10);
  }, [currentTurn]);

  // Auto-advance cursor after champion selection
  useEffect(() => {
    if (shouldAdvanceCursor) {
      findNextUnfilledSlot();
      setShouldAdvanceCursor(false);
    }
  }, [bans, picks, shouldAdvanceCursor]);

  // Keyboard handler for clearing slots
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.key === 'Backspace' || e.key === 'Delete') && hoveredSlot) {
        e.preventDefault();
        const pickList = hoveredSlot.side === 'BLUE' ? picks.blue : picks.red;
        if (pickList[hoveredSlot.index]?.champion) {
          // Clear the champion from the slot
          addPick('', pickList[hoveredSlot.index].role, hoveredSlot.side, hoveredSlot.index);
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [hoveredSlot, picks]);

  // Remove banned and picked champions from available list
  const allBannedPicked = [...bans.blue, ...bans.red, ...picks.blue.map(p => p.champion).filter(Boolean), ...picks.red.map(p => p.champion).filter(Boolean)];

  const filteredChamps = allChampions
    .filter(champ => {
      const matchesSearch = champ.toLowerCase().includes(search.toLowerCase());
      const isAvailable = !allBannedPicked.includes(champ);
      return matchesSearch && isAvailable;
    })
    .sort((a, b) => a.localeCompare(b));

  const handleChampionSelect = (champion: string) => {
    if (!currentPicker) return;

    if (currentPicker.isBan) {
      // Place ban in the EXACT slot that's currently selected
      addBan(champion, currentPicker.side, currentPicker.position);
    } else {
      // Place pick in the EXACT slot that's currently selected
      const currentPicks = currentPicker.side === 'BLUE' ? picks.blue : picks.red;
      const currentRole = currentPicks[currentPicker.position]?.role || 'TOP';
      addPick(champion, currentRole, currentPicker.side, currentPicker.position);
    }

    // Trigger cursor advance on next render
    setShouldAdvanceCursor(true);
    setSearch('');
  };

  const findNextUnfilledSlot = () => {
    // Ban phase sequence (turns 0-9)
    const banSequence = [
      { side: 'BLUE', pos: 0 }, { side: 'RED', pos: 0 },
      { side: 'BLUE', pos: 1 }, { side: 'RED', pos: 1 },
      { side: 'BLUE', pos: 2 }, { side: 'RED', pos: 2 },
      { side: 'BLUE', pos: 3 }, { side: 'RED', pos: 3 },
      { side: 'BLUE', pos: 4 }, { side: 'RED', pos: 4 },
    ];

    // Pick phase sequence (turns 10-19)
    const pickSequence = [
      { side: 'BLUE', pos: 0 }, { side: 'RED', pos: 0 }, { side: 'RED', pos: 1 }, { side: 'BLUE', pos: 1 },
      { side: 'BLUE', pos: 2 }, { side: 'RED', pos: 2 }, { side: 'RED', pos: 3 }, { side: 'BLUE', pos: 3 },
      { side: 'BLUE', pos: 4 }, { side: 'RED', pos: 4 },
    ];

    // Check bans first (turns 0-9)
    for (let i = 0; i < banSequence.length; i++) {
      const slot = banSequence[i];
      const banList = slot.side === 'BLUE' ? bans.blue : bans.red;
      if (!banList[slot.pos]) {
        setCurrentTurn(i);
        return;
      }
    }

    // Then check picks (turns 10-19)
    for (let i = 0; i < pickSequence.length; i++) {
      const slot = pickSequence[i];
      const pickList = slot.side === 'BLUE' ? picks.blue : picks.red;
      if (!pickList[slot.pos]?.champion) {
        setCurrentTurn(10 + i);
        return;
      }
    }

    // If all filled, stay at current position
  };

  const handleSlotClick = (side: 'BLUE' | 'RED', position: number, isBan: boolean) => {
    if (isBan) {
      const turn = side === 'BLUE' ? position * 2 : position * 2 + 1;
      setCurrentTurn(turn);
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

  const handleDragStart = (side: 'BLUE' | 'RED', index: number) => {
    // Allow dragging on both sides for flexibility
    setDraggedIndex(index);
    setDraggedSide(side);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
  };

  const handleDrop = (side: 'BLUE' | 'RED', targetIndex: number) => {
    // If dragging a champion from selector
    if (draggedChampion) {
      const pickList = side === 'BLUE' ? picks.blue : picks.red;
      addPick(draggedChampion, pickList[targetIndex].role, side, targetIndex);
      setDraggedChampion(null);
      setShouldAdvanceCursor(true);
      return;
    }

    // If dragging from a slot
    if (draggedIndex === null || draggedSide === null) return;

    // Only allow dropping on the same side it was dragged from
    if (draggedSide !== side) return;

    if (draggedIndex !== targetIndex) {
      movePick(draggedIndex, targetIndex, side);
    }

    setDraggedIndex(null);
    setDraggedSide(null);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
    setDraggedSide(null);
    setDraggedChampion(null);
  };

  // Handle dragging champion back to center selector to clear slot
  const handleDropOnCenter = (e: React.DragEvent) => {
    e.preventDefault();
    if (draggedIndex !== null && draggedSide !== null) {
      const pickList = draggedSide === 'BLUE' ? picks.blue : picks.red;
      if (pickList[draggedIndex]?.champion) {
        // Clear the champion from the slot
        addPick('', pickList[draggedIndex].role, draggedSide, draggedIndex);

        // Move cursor to the now-empty slot
        const pickOrder = [
          { side: 'BLUE', pos: 0 }, { side: 'RED', pos: 0 }, { side: 'RED', pos: 1 }, { side: 'BLUE', pos: 1 },
          { side: 'BLUE', pos: 2 }, { side: 'RED', pos: 2 }, { side: 'RED', pos: 3 }, { side: 'BLUE', pos: 3 },
          { side: 'BLUE', pos: 4 }, { side: 'RED', pos: 4 },
        ];
        const turnIndex = pickOrder.findIndex(p => p.side === draggedSide && p.pos === draggedIndex);
        if (turnIndex !== -1) setCurrentTurn(10 + turnIndex);
      }
    }
    setDraggedIndex(null);
    setDraggedSide(null);
  };

  const phaseColor = isBanPhase ? 'red' : 'blue';
  const phaseColorClass = isBanPhase ? 'border-red-500/30' : 'border-blue-500/30';

  return (
    <div className="h-screen w-screen bg-black flex flex-col overflow-hidden">
      {/* Top Header */}
      <header className="h-20 bg-black/90 backdrop-blur border-b border-gray-900 flex items-center justify-between px-8">
        <Link to="/draft" className="flex items-center gap-2">
          <Sword size={22} className="text-amber-500" />
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
              const rankIconUrl = `https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-shared-components/global/default/${rankLower}.png`;
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
            <button onClick={() => { setCurrentTurn(0); }} className={`px-4 py-2 rounded text-sm font-bold ${isBanPhase ? 'bg-red-500 text-white' : 'text-gray-600'}`}>BAN</button>
            <button onClick={() => { setCurrentTurn(10); }} className={`px-4 py-2 rounded text-sm font-bold ${!isBanPhase ? 'bg-blue-500 text-white' : 'text-gray-600'}`}>PICK</button>
          </div>

          <button onClick={resetDraft} className="px-3 py-2 text-sm text-gray-500 hover:text-white">Reset</button>
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
              const isActive = currentPicker?.side === 'BLUE' && currentPicker?.isBan && currentPicker?.position === i;
              return (
                <button key={i} onClick={() => handleSlotClick('BLUE', i, true)}
                  className={`w-12 h-12 rounded border ${isActive ? `ring-2 ${phaseColorClass}` : 'border-gray-900'} ${ban ? 'bg-gray-900' : 'bg-black'}`}>
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
              const isActive = currentPicker?.side === 'BLUE' && !currentPicker?.isBan && currentPicker?.position === i;
              const isDragging = draggedIndex === i && draggedSide === 'BLUE';
              const hasChampion = !!pick.champion;
              return (
                <button
                  key={i}
                  onClick={() => handleSlotClick('BLUE', i, false)}
                  draggable={hasChampion}
                  onDragStart={() => handleDragStart('BLUE', i)}
                  onDragOver={handleDragOver}
                  onDrop={() => handleDrop('BLUE', i)}
                  onDragEnd={handleDragEnd}
                  onMouseEnter={() => setHoveredSlot({side: 'BLUE', index: i})}
                  onMouseLeave={() => setHoveredSlot(null)}
                  className={`h-[calc((100vh-16rem)/5)] rounded overflow-hidden relative border ${isActive ? `ring-2 ${phaseColorClass}` : 'border-gray-900'} flex items-center ${isDragging ? 'opacity-50' : ''} ${hasChampion ? 'cursor-move' : 'cursor-pointer'}`}>
                  {pick.champion ? (
                    <img src={getChampionSplashUrl(pick.champion)} alt={pick.champion} className="w-full h-full object-cover object-center pointer-events-none" />
                  ) : (
                    <div className="w-full h-full bg-gray-950 flex items-center justify-center border border-gray-900">
                      <RoleIcon role={pick.role} size={24} className="text-gray-800" />
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* CENTER - Champion Picker and LLM Box */}
        <div className={`flex-1 flex flex-col border-l border-r ${phaseColorClass} min-w-0`}>
          {/* Champion Picker - Top Half */}
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
                {filteredChamps.map(champ => (
                  <button
                    key={champ}
                    onClick={() => handleChampionSelect(champ)}
                    draggable={true}
                    onDragStart={() => setDraggedChampion(champ)}
                    onDragEnd={handleDragEnd}
                    className="aspect-square rounded overflow-hidden relative group hover:scale-105 hover:z-10 transition-transform border border-gray-900 hover:border-amber-500 cursor-grab active:cursor-grabbing">
                    <img src={getChampionImageUrl(champ, latestPatch)} alt={champ} className="w-full h-full object-cover pointer-events-none" />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/90 to-transparent opacity-0 group-hover:opacity-100 transition-opacity flex items-end justify-center pb-1 pointer-events-none">
                      <span className="text-white font-bold text-[10px] uppercase tracking-wide">{champ}</span>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* LLM Box - Bottom Half */}
          <div className={`h-1/2 bg-black/90 border-t-2 ${phaseColorClass} p-4 flex flex-col`}>
            <div className="text-xs text-gray-600 uppercase tracking-wider font-bold mb-2">AI Analysis</div>
            <div className="flex-1 text-sm text-gray-400">
              {isBanPhase ? `${bans.blue.length + bans.red.length}/10 bans` : `${picks.blue.filter(p => p.champion).length + picks.red.filter(p => p.champion).length}/10 picks`}
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
              const isActive = currentPicker?.side === 'RED' && currentPicker?.isBan && currentPicker?.position === i;
              return (
                <button key={i} onClick={() => handleSlotClick('RED', i, true)}
                  className={`w-12 h-12 rounded border ${isActive ? `ring-2 ${phaseColorClass}` : 'border-gray-900'} ${ban ? 'bg-gray-900' : 'bg-black'}`}>
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
              const isActive = currentPicker?.side === 'RED' && !currentPicker?.isBan && currentPicker?.position === i;
              const isDragging = draggedIndex === i && draggedSide === 'RED';
              const hasChampion = !!pick.champion;
              return (
                <button
                  key={i}
                  onClick={() => handleSlotClick('RED', i, false)}
                  draggable={hasChampion}
                  onDragStart={() => handleDragStart('RED', i)}
                  onDragOver={handleDragOver}
                  onDrop={() => handleDrop('RED', i)}
                  onDragEnd={handleDragEnd}
                  onMouseEnter={() => setHoveredSlot({side: 'RED', index: i})}
                  onMouseLeave={() => setHoveredSlot(null)}
                  className={`h-[calc((100vh-16rem)/5)] rounded overflow-hidden relative border ${isActive ? `ring-2 ${phaseColorClass}` : 'border-gray-900'} flex items-center ${isDragging ? 'opacity-50' : ''} ${hasChampion ? 'cursor-move' : 'cursor-pointer'}`}>
                  {pick.champion ? (
                    <img src={getChampionSplashUrl(pick.champion)} alt={pick.champion} className="w-full h-full object-cover object-center pointer-events-none" />
                  ) : (
                    <div className="w-full h-full bg-gray-950 flex items-center justify-center border border-gray-900">
                      <RoleIcon role={pick.role} size={24} className="text-gray-800" />
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
