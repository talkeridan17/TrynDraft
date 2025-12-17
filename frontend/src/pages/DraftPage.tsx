import React, { useState } from 'react';
import { GameModeSelector } from '../components/drafting/GameModeSelector';
import { DraftControls } from '../components/drafting/DraftControls';
import { TeamDisplay } from '../components/drafting/TeamDisplay';
import { DraftAssistantPanel } from '../components/drafting/DraftAssistantPanel';
import { ChampionSearch } from '../components/drafting/ChampionSearch';
import { useDraftStore } from '../store/useDraftStore';

export const DraftPage: React.FC = () => {
  const {
    settings,
    selections,
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
    resetDraft,
  } = useDraftStore();

  const [selectedPosition, setSelectedPosition] = useState<number | null>(null);
  const [showChampionSearch, setShowChampionSearch] = useState(false);

  const handleSelectChampion = (position: number) => {
    setSelectedPosition(position);
    setShowChampionSearch(true);
  };

  const handleChampionSelected = (champion: string) => {
    if (selectedPosition !== null) {
      if (settings.phase === 'BAN') {
        addBan(champion, settings.side);
      } else {
        addPick(champion, settings.role, settings.side);
      }
      setSelectedPosition(null);
      setShowChampionSearch(false);
    }
  };

  const handleRemovePick = (index: number) => {
    removePick(index, settings.side);
  };

  const handleRemoveBan = (index: number, side: 'BLUE' | 'RED') => {
    // Temporary - we'll implement proper ban removal later
    console.log(`Remove ${side} ban at index:`, index);
  };

  return (
    <div className="space-y-6">
      {/* Game Mode Selector */}
      <GameModeSelector
        currentMode={settings.mode}
        onModeChange={setGameMode}
      />

      {/* Draft Controls */}
      <DraftControls
        side={settings.side}
        role={settings.role}
        elo={settings.elo}
        region={settings.region}
        patch={settings.patch}
        availablePatches={availablePatches}
        phase={settings.phase}
        currentTurn={settings.currentTurn}
        onSideChange={setTeamSide}
        onRoleChange={setRole}
        onEloChange={setElo}
        onRegionChange={setRegion}
        onPatchChange={setPatch}
        onPhaseChange={setPhase}
        onNextTurn={nextTurn}
        onReset={resetDraft}
      />

      {/* Main Draft Area */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Blue Team */}
        <div>
          <TeamDisplay
            side="BLUE"
            picks={selections.picks.blue}
            bans={selections.bans.blue}
            phase={settings.phase}
            onSelectChampion={handleSelectChampion}
            onRemovePick={handleRemovePick}
            onRemoveBan={(index) => handleRemoveBan(index, 'BLUE')}
          />
        </div>

        {/* Center Panel - LLM & Recommendations */}
        <div className="lg:col-span-1">
          <DraftAssistantPanel
            gameMode={settings.mode}
            phase={settings.phase}
            currentTurn={settings.currentTurn}
            bluePicks={selections.picks.blue}
            redPicks={selections.picks.red}
            blueBans={selections.bans.blue}
            redBans={selections.bans.red}
          />
        </div>

        {/* Red Team */}
        <div>
          <TeamDisplay
            side="RED"
            picks={selections.picks.red}
            bans={selections.bans.red}
            phase={settings.phase}
            onSelectChampion={handleSelectChampion}
            onRemovePick={handleRemovePick}
            onRemoveBan={(index) => handleRemoveBan(index, 'RED')}
          />
        </div>
      </div>

      {/* Champion Search Modal */}
      {showChampionSearch && (
        <ChampionSearch
          onSelect={handleChampionSelected}
          onClose={() => {
            setShowChampionSearch(false);
            setSelectedPosition(null);
          }}
        />
      )}
    </div>
  );
};