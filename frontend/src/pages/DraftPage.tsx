import { useState } from 'react';
import { GameModeSelector } from '../components/drafting/GameModeSelector';
import { DraftControls } from '../components/drafting/DraftControls';
import { TeamDisplay } from '../components/drafting/TeamDisplay';
import { DraftAssistantPanel } from '../components/drafting/DraftAssistantPanel';
import { ChampionPicker } from '../components/drafting/ChampionPicker';
import { useDraftStore } from '../store/useDraftStore';

export const DraftPage: React.FC = () => {
  const {
    settings,
    selections,
    currentTurn,
    availablePatches,
    setGameMode,
    setTeamSide,
    setRole,
    setElo,
    setRegion,
    setPatch,
    setPhase,
    nextTurn,
    addBan,
    addPick,
    removePick,
    movePick,
    resetDraft,
  } = useDraftStore();

  const [currentPicker, setCurrentPicker] = useState<{
    side: 'BLUE' | 'RED';
    position: number;
    isBanPhase: boolean;
    pickIndex: number;
  }>({
    side: 'BLUE',
    position: 0,
    isBanPhase: true,
    pickIndex: 1,
  });

  // Global picker indicator component
  const PickerIndicator = () => (
    <div className="fixed top-20 right-4 bg-black/80 backdrop-blur-sm border border-yellow-500 rounded-lg p-4 z-50 shadow-xl">
      <div className="flex items-center space-x-3">
        <div className={`w-3 h-3 rounded-full ${currentPicker.side === 'BLUE' ? 'bg-blue-500' : 'bg-red-500'}`}></div>
        <div>
          <div className="text-white font-bold">
            {currentPicker.isBanPhase ? 'Banning' : 'Picking'} • Turn {currentPicker.pickIndex}
          </div>
          <div className="text-yellow-300 text-sm">
            {currentPicker.side} Team • Position {currentPicker.position + 1}
          </div>
        </div>
      </div>
    </div>
  );

  const handleChampionSelected = (champion: string) => {
    if (currentPicker.isBanPhase) {
      addBan(champion, currentPicker.side);
    } else {
      const picks = currentPicker.side === 'BLUE' ? selections.picks.blue : selections.picks.red;
      const currentRole = picks[currentPicker.position]?.role || 'FILL';
      addPick(champion, currentRole, currentPicker.side);
    }
    
    // Move to next picker
    handleNextPicker();
  };

  const handleRemovePick = (index: number, side: 'BLUE' | 'RED') => {
    removePick(index, side);
  };

  const handleMovePick = (fromIndex: number, toIndex: number, side: 'BLUE' | 'RED') => {
    movePick(fromIndex, toIndex, side);
  };

  const handleSelectChampion = (position: number, side: 'BLUE' | 'RED') => {
    setCurrentPicker({
      side,
      position,
      isBanPhase: settings.phase === 'BAN',
      pickIndex: currentPicker.pickIndex,
    });
  };

  const handleNextPicker = () => {
    const { side, isBanPhase, pickIndex } = currentPicker;
    
    if (isBanPhase) {
      if (pickIndex < 10) {
        const nextSide = side === 'BLUE' ? 'RED' : 'BLUE';
        const nextPosition = Math.floor(pickIndex / 2);
        setCurrentPicker({
          side: nextSide,
          position: nextPosition,
          isBanPhase: true,
          pickIndex: pickIndex + 1,
        });
      } else {
        // Switch to pick phase
        setCurrentPicker({
          side: 'BLUE',
          position: 0,
          isBanPhase: false,
          pickIndex: 11,
        });
        setPhase('PICK');
      }
    } else {
      if (pickIndex < 20) {
        // Standard pick order
        const pickOrder = [
          { side: 'BLUE' as const, position: 0 },
          { side: 'RED' as const, position: 0 },
          { side: 'RED' as const, position: 1 },
          { side: 'BLUE' as const, position: 1 },
          { side: 'BLUE' as const, position: 2 },
          { side: 'RED' as const, position: 2 },
          { side: 'RED' as const, position: 3 },
          { side: 'BLUE' as const, position: 3 },
          { side: 'BLUE' as const, position: 4 },
          { side: 'RED' as const, position: 4 },
        ];
        const nextStep = pickOrder[pickIndex - 11];
        setCurrentPicker({
          side: nextStep.side,
          position: nextStep.position,
          isBanPhase: false,
          pickIndex: pickIndex + 1,
        });
      }
    }
    nextTurn();
  };

  const handlePreviousPicker = () => {
    const { pickIndex } = currentPicker;
    
    if (pickIndex > 1) {
      if (pickIndex === 11) {
        // Switch back to ban phase
        setCurrentPicker({
          side: 'RED',
          position: 4,
          isBanPhase: true,
          pickIndex: 10,
        });
        setPhase('BAN');
      } else {
        setCurrentPicker({
          ...currentPicker,
          pickIndex: pickIndex - 1,
        });
      }
    }
  };

  return (
    <div className="space-y-4 h-screen flex flex-col">
      <PickerIndicator />
      
      {/* Compact Header Section */}
      <div className="space-y-3">
        <div className="flex justify-center">
          <GameModeSelector
            currentMode={settings.mode}
            onModeChange={setGameMode}
          />
        </div>
        
        <DraftControls
          side={settings.side}
          role={settings.role}
          elo={settings.elo}
          region={settings.region}
          patch={settings.patch}
          availablePatches={availablePatches}
          phase={settings.phase}
          onSideChange={setTeamSide}
          onRoleChange={setRole}
          onEloChange={setElo}
          onRegionChange={setRegion}
          onPatchChange={setPatch}
          onPhaseChange={setPhase}
          onReset={resetDraft}
        />
      </div>

      {/* Main Draft Area */}
      <div className="grid grid-cols-12 gap-4 flex-1" style={{ height: 'calc(100vh - 250px)' }}>
        {/* Blue Team */}
        <div className="col-span-4">
          <TeamDisplay
            side="BLUE"
            picks={selections.picks.blue}
            bans={selections.bans.blue}
            phase={settings.phase}
            isUserSide={settings.side === 'BLUE'}
            onSelectChampion={(position) => handleSelectChampion(position, 'BLUE')}
            onRemovePick={(index) => handleRemovePick(index, 'BLUE')}
            onMovePick={(fromIndex, toIndex) => handleMovePick(fromIndex, toIndex, 'BLUE')}
            currentPicker={currentPicker}
          />
        </div>

        {/* Center Panel */}
        <div className="col-span-4 flex flex-col space-y-4">
          {/* Champion Picker */}
          <div className="flex-1">
            <ChampionPicker
              currentSide={currentPicker.side}
              isBanPhase={currentPicker.isBanPhase}
              pickIndex={currentPicker.pickIndex}
              onSelect={handleChampionSelected}
              onNext={handleNextPicker}
              onPrevious={handlePreviousPicker}
            />
          </div>

          {/* LLM Analysis */}
          <div className="flex-1">
            <DraftAssistantPanel
              phase={settings.phase}
              currentTurn={currentTurn}
            />
          </div>
        </div>

        {/* Red Team */}
        <div className="col-span-4">
          <TeamDisplay
            side="RED"
            picks={selections.picks.red}
            bans={selections.bans.red}
            phase={settings.phase}
            isUserSide={settings.side === 'RED'}
            onSelectChampion={(position) => handleSelectChampion(position, 'RED')}
            onRemovePick={(index) => handleRemovePick(index, 'RED')}
            onMovePick={(fromIndex, toIndex) => handleMovePick(fromIndex, toIndex, 'RED')}
            currentPicker={currentPicker}
          />
        </div>
      </div>
    </div>
  );
};