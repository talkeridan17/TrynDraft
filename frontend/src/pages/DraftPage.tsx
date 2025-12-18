import { GameModeSelector } from '../components/drafting/GameModeSelector';
import { DraftControls } from '../components/drafting/DraftControls';
import { TeamDisplay } from '../components/drafting/TeamDisplay';
import { ChampionPicker } from '../components/drafting/ChampionPicker';
import { useDraftStore } from '../store/useDraftStore';
import { LLMAnalysisBox } from '../components/drafting/LLMAnalysisBox';
import { useEffect, useState } from 'react';
import { championService } from '../utils/api';

// Simple DraftRulesService for now - you'll need to expand this
class DraftRulesService {
  private bans: Set<string> = new Set();
  private picks: Set<string> = new Set();
  
  private mode: string;
  
  constructor(mode: string) {
    this.mode = mode;
  }

  addBan(champion: string) {
    this.bans.add(champion);
  }

  addPick(champion: string) {
    this.picks.add(champion);
  }

  get_available_champions(allChampions: string[]): string[] {
    // Filter out banned and picked champions
    return allChampions.filter(champ => 
      !this.bans.has(champ) && !this.picks.has(champ)
    );
  }

  reset() {
    this.bans.clear();
    this.picks.clear();
  }
}

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
    previousTurn,
    addBan,
    removeBan,
    addPick,
    removePick,
    movePick,
    resetDraft,
    getCurrentPicker,
  } = useDraftStore();

  const currentPicker = getCurrentPicker();
  
  // Add state for LLM Analysis
  const [availableChampions, setAvailableChampions] = useState<string[]>([]);
  const [topRecommendation, setTopRecommendation] = useState<string>('Analyzing...');
  const [draftRules, setDraftRules] = useState<DraftRulesService | null>(null);
  const [allChampions, setAllChampions] = useState<string[]>([]);

  // Load all champions on mount
  useEffect(() => {
    const loadChampions = async () => {
      try {
        const championsData = await championService.getAll();
        // Extract champion names from the data
        const championNames = championsData.map((champ: any) => champ.name || champ);
        setAllChampions(championNames);
      } catch (error) {
        console.error('Failed to load champions:', error);
        // Use mock champions as fallback
        const mockChamps = [
          "Aatrox", "Ahri", "Akali", "Alistar", "Amumu", "Anivia", "Annie", "Aphelios",
          "Ashe", "Aurelion Sol", "Azir", "Bard", "Blitzcrank", "Brand", "Braum",
          "Caitlyn", "Camille", "Cassiopeia", "Cho'Gath", "Corki", "Darius", "Diana",
          "Draven", "Dr. Mundo", "Ekko", "Elise", "Evelynn", "Ezreal", "Fiddlesticks",
          "Fiora", "Fizz", "Galio", "Gangplank", "Garen", "Gnar", "Gragas", "Graves",
          "Hecarim", "Heimerdinger", "Illaoi", "Irelia", "Ivern", "Janna", "Jarvan IV",
          "Jax", "Jayce", "Jhin", "Jinx", "Kai'Sa", "Kalista", "Karma", "Karthus",
          "Kassadin", "Katarina", "Kayle", "Kayn", "Kennen", "Kha'Zix", "Kindred",
          "Kled", "Kog'Maw", "LeBlanc", "Lee Sin", "Leona", "Lillia", "Lissandra",
          "Lucian", "Lulu", "Lux", "Malphite", "Malzahar", "Maokai", "Master Yi",
          "Miss Fortune", "Mordekaiser", "Morgana", "Nami", "Nasus", "Nautilus",
          "Neeko", "Nidalee", "Nocturne", "Nunu & Willump", "Olaf", "Orianna",
          "Ornn", "Pantheon", "Poppy", "Pyke", "Qiyana", "Quinn", "Rakan", "Rammus",
          "Rek'Sai", "Rell", "Renekton", "Rengar", "Riven", "Rumble", "Ryze",
          "Samira", "Sejuani", "Senna", "Seraphine", "Sett", "Shaco", "Shen",
          "Shyvana", "Singed", "Sion", "Sivir", "Skarner", "Sona", "Soraka",
          "Swain", "Sylas", "Syndra", "Tahm Kench", "Taliyah", "Talon", "Taric",
          "Teemo", "Thresh", "Tristana", "Trundle", "Tryndamere", "Twisted Fate",
          "Twitch", "Udyr", "Urgot", "Varus", "Vayne", "Veigar", "Vel'Koz",
          "Vex", "Vi", "Viego", "Viktor", "Vladimir", "Volibear", "Warwick",
          "Wukong", "Xayah", "Xerath", "Xin Zhao", "Yasuo", "Yone", "Yorick",
          "Yuumi", "Zac", "Zed", "Zeri", "Ziggs", "Zilean", "Zoe", "Zyra"
        ];
        setAllChampions(mockChamps);
      }
    };
    
    loadChampions();
  }, []);

  // Initialize draft rules based on game mode
  useEffect(() => {
    const rules = new DraftRulesService(settings.mode);
    setDraftRules(rules);
  }, [settings.mode]);

  // Update available champions when picks/bans change
  useEffect(() => {
    if (!draftRules || allChampions.length === 0) return;
    
    // Reset and update rules
    draftRules.reset();
    
    // Update rules with current bans
    selections.bans.blue.forEach(ban => draftRules.addBan(ban));
    selections.bans.red.forEach(ban => draftRules.addBan(ban));
    
    // Update rules with current picks
    selections.picks.blue
      .filter(p => p.champion)
      .forEach(p => draftRules.addPick(p.champion));
    selections.picks.red
      .filter(p => p.champion)
      .forEach(p => draftRules.addPick(p.champion));
    
    // Get available champions
    const available = draftRules.get_available_champions(allChampions);
    setAvailableChampions(available);
    
    // Set top recommendation (for now, first available)
    // TODO: Add better recommendation logic based on role, team comp, etc.
    if (available.length > 0) {
      setTopRecommendation(available[0]);
    } else {
      setTopRecommendation('No champions available');
    }
  }, [selections, draftRules, allChampions]);

  // Global picker indicator component
  const PickerIndicator = () => {
    if (!currentPicker) return null;
    
    return (
      <div className="fixed top-20 right-4 bg-black/80 backdrop-blur-sm border border-yellow-500 rounded-lg p-4 z-50 shadow-xl">
        <div className="flex items-center space-x-3">
          <div className={`w-3 h-3 rounded-full ${currentPicker.side === 'BLUE' ? 'bg-blue-500' : 'bg-red-500'}`}></div>
          <div>
            <div className="text-white font-bold">
              {currentPicker.isBan ? 'Banning' : 'Picking'} • Turn {currentTurn + 1}/20
            </div>
            <div className="text-yellow-300 text-sm">
              {currentPicker.side} Team • Position {currentPicker.position + 1}
            </div>
          </div>
        </div>
      </div>
    );
  };

  const handleChampionSelected = (champion: string) => {
    if (!currentPicker) return;
    
    if (currentPicker.isBan) {
      addBan(champion, currentPicker.side);
    } else {
      const picks = currentPicker.side === 'BLUE' ? selections.picks.blue : selections.picks.red;
      const currentRole = picks[currentPicker.position]?.role || 'FILL';
      addPick(champion, currentRole, currentPicker.side);
    }
    
    // Move to next turn
    nextTurn();
  };

  const handleRemovePick = (index: number, side: 'BLUE' | 'RED') => {
    removePick(index, side);
  };

  const handleMovePick = (fromIndex: number, toIndex: number, side: 'BLUE' | 'RED') => {
    movePick(fromIndex, toIndex, side);
  };

  const handleRemoveBan = (ban: string, side: 'BLUE' | 'RED') => {
    removeBan(ban, side);
  };

  const handleSelectChampion = (position: number, side: 'BLUE' | 'RED') => {
    // Find the turn for this position
    let targetTurn = -1;
    
    // Check ban phase
    for (let i = 0; i < 10; i++) {
      const sideForTurn = i % 2 === 0 ? 'BLUE' : 'RED';
      const positionForTurn = Math.floor(i / 2);
      if (sideForTurn === side && positionForTurn === position) {
        targetTurn = i;
        break;
      }
    }
    
    // Check pick phase
    if (targetTurn === -1) {
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
      
      for (let i = 0; i < pickOrder.length; i++) {
        if (pickOrder[i].side === side && pickOrder[i].position === position) {
          targetTurn = i + 10;
          break;
        }
      }
    }
    
    if (targetTurn !== -1) {
      useDraftStore.getState().setTurn(targetTurn);
    }
  };

  const handleNextPicker = () => {
    nextTurn();
  };

  const handlePreviousPicker = () => {
    previousTurn();
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
            onRemoveBan={(ban) => handleRemoveBan(ban, 'BLUE')}
            currentPicker={currentPicker ? { side: currentPicker.side, position: currentPicker.position } : undefined}
          />
        </div>

        {/* Center Panel */}
        <div className="col-span-4 flex flex-col space-y-4">
          {/* Champion Picker */}
          <div className="flex-1">
            <ChampionPicker
              currentSide={currentPicker?.side || 'BLUE'}
              isBanPhase={currentPicker?.isBan || true}
              pickIndex={currentTurn + 1}
              onSelect={handleChampionSelected}
              onNext={handleNextPicker}
              onPrevious={handlePreviousPicker}
            />
          </div>

          {/* LLM Analysis - Updated to use LLMAnalysisBox */}
          <div className="flex-1">
            <LLMAnalysisBox
              draftState={{
                phase: settings.phase,
                turn: currentTurn,
                picks: selections.picks,
                bans: selections.bans
              }}
              availableChampions={availableChampions}
              topRecommendation={topRecommendation}
              isLoading={availableChampions.length === 0 && allChampions.length > 0}
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
            onRemoveBan={(ban) => handleRemoveBan(ban, 'RED')}
            currentPicker={currentPicker ? { side: currentPicker.side, position: currentPicker.position } : undefined}
          />
        </div>
      </div>
    </div>
  );
};