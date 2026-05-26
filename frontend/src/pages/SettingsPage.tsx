import { useEffect, useMemo, useState } from 'react';
import { Users, Trophy, Save, UserRound } from 'lucide-react';
import { useDraftStore } from '../store/useDraftStore';
import { recommendationService } from '../utils/api';

type GameMode = 'SOLOQ' | 'CLASH';
type RoleType = 'TOP' | 'JUNGLE' | 'MID' | 'ADC' | 'SUPPORT' | 'FLEX';
type SettingsTab = 'soloq' | 'clash';

const ROLES: RoleType[] = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];

interface RoleBoundId {
  role: RoleType;
  riot_id: string;
}

interface PlayerSettings {
  mode: GameMode;
  role: RoleType;
  soloRiotIds: string[];
  clashBlueByRole: RoleBoundId[];
  clashRedByRole: RoleBoundId[];
  clashEnemyUnknown: boolean;
  deeplolRegion: string;
  deeplolSeason: number;
}

const emptyRoleRows = (): RoleBoundId[] => ROLES.map((role) => ({ role, riot_id: '' }));

const defaultSettings: PlayerSettings = {
  mode: 'SOLOQ',
  role: 'TOP',
  soloRiotIds: [],
  clashBlueByRole: emptyRoleRows(),
  clashRedByRole: emptyRoleRows(),
  clashEnemyUnknown: false,
  deeplolRegion: 'NA1',
  deeplolSeason: 27,
};

const parseLines = (raw: string) => raw.split(/\n|,/).map(s => s.trim()).filter(Boolean);

const clearDeeplolProficiencies = () => {
  localStorage.removeItem('deeplol_proficiencies');
};

export const SettingsPage: React.FC = () => {
  const { settings, setSettings } = useDraftStore();

  const [mode, setMode] = useState<GameMode>((settings.mode as GameMode) || 'SOLOQ');
  const [role, setRole] = useState<RoleType>(settings.role || 'TOP');
  const [soloRaw, setSoloRaw] = useState('');
  const [blueByRole, setBlueByRole] = useState<RoleBoundId[]>(emptyRoleRows());
  const [redByRole, setRedByRole] = useState<RoleBoundId[]>(emptyRoleRows());
  const [enemyUnknown, setEnemyUnknown] = useState(false);
  const [deeplolRegion, setDeeplolRegion] = useState('NA1');
  const [deeplolSeason, setDeeplolSeason] = useState(27);
  const [deeplolStatus, setDeeplolStatus] = useState('');
  const [isLoadingDeeplol, setIsLoadingDeeplol] = useState(false);
  const [savedSnapshot, setSavedSnapshot] = useState<string>('');
  const [activeTab, setActiveTab] = useState<SettingsTab>('soloq');

  useEffect(() => {
    try {
      const raw = localStorage.getItem('tryndraft_player_settings');
      if (!raw) {
        setSavedSnapshot(JSON.stringify(defaultSettings));
        return;
      }
      const parsed = JSON.parse(raw);
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const normalizedRows = (rows: any): RoleBoundId[] => {
        const out = emptyRoleRows();
        if (Array.isArray(rows)) {
          for (const row of rows) {
            const idx = out.findIndex((r) => r.role === row.role);
            if (idx !== -1) out[idx].riot_id = String(row.riot_id || '').trim();
          }
        }
        return out;
      };

      const loaded: PlayerSettings = {
        mode: parsed.mode === 'CLASH' ? 'CLASH' : 'SOLOQ',
        role: ROLES.includes(parsed.role) ? parsed.role : 'TOP',
        soloRiotIds: Array.isArray(parsed.soloRiotIds) ? parsed.soloRiotIds : [],
        clashBlueByRole: normalizedRows(parsed.clashBlueByRole),
        clashRedByRole: normalizedRows(parsed.clashRedByRole),
        clashEnemyUnknown: !!parsed.clashEnemyUnknown,
        deeplolRegion: typeof parsed.deeplolRegion === 'string' ? parsed.deeplolRegion : 'NA1',
        deeplolSeason: Number(parsed.deeplolSeason || 27),
      };

      setMode(loaded.mode);
      setRole(loaded.role);
      setSoloRaw(loaded.soloRiotIds.join('\n'));
      setBlueByRole(loaded.clashBlueByRole);
      setRedByRole(loaded.clashRedByRole);
      setEnemyUnknown(loaded.clashEnemyUnknown);
      setDeeplolRegion(loaded.deeplolRegion);
      setDeeplolSeason(loaded.deeplolSeason);
      setSavedSnapshot(JSON.stringify(loaded));

      setSettings({ mode: loaded.mode, role: loaded.role });
    } catch {
      setSavedSnapshot(JSON.stringify(defaultSettings));
    }
  }, [setSettings]);

  const currentSnapshot = useMemo(() => {
    const current: PlayerSettings = {
      mode,
      role,
      soloRiotIds: parseLines(soloRaw),
      clashBlueByRole: blueByRole.map((x) => ({ ...x, riot_id: x.riot_id.trim() })),
      clashRedByRole: redByRole.map((x) => ({ ...x, riot_id: x.riot_id.trim() })),
      clashEnemyUnknown: enemyUnknown,
      deeplolRegion: deeplolRegion.trim().toUpperCase() || 'NA1',
      deeplolSeason: Number(deeplolSeason || 27),
    };
    return JSON.stringify(current);
  }, [mode, role, soloRaw, blueByRole, redByRole, enemyUnknown, deeplolRegion, deeplolSeason]);

  const hasUnsavedChanges = currentSnapshot !== savedSnapshot;

  const handleSave = () => {
    const value = JSON.parse(currentSnapshot) as PlayerSettings;

    // Check if Riot IDs have changed - if so, clear champion proficiencies
    const savedData = JSON.parse(savedSnapshot || '{}') as PlayerSettings;
    const savedIds = new Set([
      ...(savedData.soloRiotIds || []),
      ...(savedData.clashBlueByRole?.map((x) => x.riot_id).filter(Boolean) || []),
      ...(savedData.clashRedByRole?.map((x) => x.riot_id).filter(Boolean) || []),
    ]);
    const currentIds = new Set([
      ...value.soloRiotIds,
      ...value.clashBlueByRole.map((x) => x.riot_id).filter(Boolean),
      ...value.clashRedByRole.map((x) => x.riot_id).filter(Boolean),
    ]);

    // Clear proficiencies if any IDs were removed (current is subset of saved but not equal)
    const idsRemoved = [...savedIds].some((id) => !currentIds.has(id));
    if (idsRemoved) {
      clearDeeplolProficiencies();
    }

    localStorage.setItem('tryndraft_player_settings', JSON.stringify(value));
    setSettings({ mode: value.mode, role: value.role });
    setSavedSnapshot(currentSnapshot);
  };

  const setRoleId = (team: 'BLUE' | 'RED', role: RoleType, riotId: string) => {
    const setter = team === 'BLUE' ? setBlueByRole : setRedByRole;
    const source = team === 'BLUE' ? blueByRole : redByRole;
    setter(source.map((x) => (x.role === role ? { ...x, riot_id: riotId } : x)));
  };

  const handleLoadFromDeeplol = async () => {
    const ids = mode === 'SOLOQ'
      ? parseLines(soloRaw)
      : [
        ...blueByRole.map((x) => x.riot_id.trim()).filter(Boolean),
        ...(enemyUnknown ? [] : redByRole.map((x) => x.riot_id.trim()).filter(Boolean)),
      ];
    if (ids.length === 0) {
      setDeeplolStatus('Add at least one Riot ID first.');
      return;
    }
    setIsLoadingDeeplol(true);
    setDeeplolStatus('Loading from Deeplol...');
    try {
      const res = await recommendationService.fetchDeeplolProficienciesByRiotIds(ids, deeplolRegion, deeplolSeason);
      setDeeplolStatus(`Loaded ${res.imported} champion proficiency entries.`);
    } catch {
      setDeeplolStatus('Failed to load from Deeplol.');
    } finally {
      setIsLoadingDeeplol(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-gray-950 pt-24 pb-8 px-8">
      <div className="w-full h-full bg-black border border-gray-800 rounded-lg p-8 flex flex-col overflow-hidden">
        <div className="flex items-center justify-between pb-6 border-b border-gray-800 mb-6">
          <div>
            <h1 className="text-3xl font-bold text-white">Settings</h1>
            <p className="text-gray-400 mt-1">Manage draft mode and Riot IDs (role-bound for Clash).</p>
          </div>
          <button
            onClick={handleSave}
            disabled={!hasUnsavedChanges}
            className={`px-6 py-3 rounded-lg font-semibold transition-all flex items-center gap-2 ${hasUnsavedChanges ? 'bg-amber-500 hover:bg-amber-600 text-black' : 'bg-gray-800 text-gray-600 cursor-not-allowed'
              }`}
          >
            <Save size={16} />
            Save Changes
          </button>
        </div>

        <div className="flex items-center gap-4 mb-6 border-b border-gray-800 pb-4">
          <button
            onClick={() => setActiveTab('soloq')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition-all ${activeTab === 'soloq' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/50' : 'text-gray-400 hover:text-gray-200'}`}
          >
            <Trophy size={18} />
            Solo Queue
          </button>
          <button
            onClick={() => setActiveTab('clash')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold transition-all ${activeTab === 'clash' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/50' : 'text-gray-400 hover:text-gray-200'}`}
          >
            <Users size={18} />
            Clash
          </button>
        </div>

        <div className="flex-1 overflow-y-auto pr-2">
          {activeTab === 'soloq' ? (
            <div className="space-y-6">
              <section className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-4">
                  <UserRound size={20} className="text-amber-500" />
                  <h2 className="text-white font-semibold">Primary Role</h2>
                </div>
                <div className="flex gap-2 flex-wrap">
                  {ROLES.map((r) => (
                    <button
                      key={r}
                      onClick={() => { setRole(r); setMode('SOLOQ'); }}
                      className={`px-4 py-2 text-sm rounded-lg border transition-all ${role === r ? 'border-amber-500 text-amber-400 bg-amber-500/10' : 'border-gray-700 text-gray-400 hover:border-gray-600'}`}
                    >
                      {r}
                    </button>
                  ))}
                </div>
              </section>

              <section className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                <h2 className="text-white font-semibold mb-2">Your Riot IDs</h2>
                <p className="text-xs text-gray-500 mb-3">Enter your Riot IDs (one per line). The first entry is your primary account.</p>
                <textarea
                  value={soloRaw}
                  onChange={(e) => { setSoloRaw(e.target.value); setMode('SOLOQ'); }}
                  rows={6}
                  placeholder={'GameName#NA1\nAnotherSmurf#NA1'}
                  className="w-full bg-black border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:border-amber-500 focus:outline-none"
                />
              </section>

              <section className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                <h2 className="text-white font-semibold mb-3">Load Champion Proficiencies</h2>
                <div className="flex items-center gap-2 mb-3">
                  <input
                    value={deeplolRegion}
                    onChange={(e) => setDeeplolRegion(e.target.value.toUpperCase())}
                    placeholder="Region (NA1, EUW1, KR...)"
                    className="w-40 bg-black border border-gray-700 rounded px-2 py-1 text-sm text-gray-200"
                  />
                  <input
                    type="number"
                    value={deeplolSeason}
                    onChange={(e) => setDeeplolSeason(Number(e.target.value || 27))}
                    className="w-28 bg-black border border-gray-700 rounded px-2 py-1 text-sm text-gray-200"
                  />
                  <button
                    onClick={handleLoadFromDeeplol}
                    disabled={isLoadingDeeplol}
                    className="px-3 py-1.5 rounded bg-cyan-700 hover:bg-cyan-600 disabled:opacity-40 text-white text-sm"
                  >
                    {isLoadingDeeplol ? 'Loading...' : 'Load from Deeplol'}
                  </button>
                  {deeplolStatus && <span className="text-xs text-cyan-300">{deeplolStatus}</span>}
                </div>
                <p className="text-xs text-gray-500">Uses the same flow as Python: Riot ID lookup to puu_id to champion-stat to role stats extraction.</p>
              </section>
            </div>
          ) : (
            <div className="space-y-6">
              <section className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                <h2 className="text-white font-semibold mb-4">Team Riot IDs By Role</h2>
                <div className="grid grid-cols-3 gap-2 text-xs text-gray-500 mb-3 px-1">
                  <div>Role</div>
                  <div className="text-blue-400">Blue Team Riot ID</div>
                  <div className="text-red-400">Red Team Riot ID</div>
                </div>
                <div className="space-y-2">
                  {ROLES.map((r) => (
                    <div key={r} className="grid grid-cols-3 gap-2 items-center">
                      <div className="text-sm text-gray-200 px-1 font-medium">{r}</div>
                      <input
                        value={blueByRole.find((x) => x.role === r)?.riot_id || ''}
                        onChange={(e) => { setRoleId('BLUE', r, e.target.value); setMode('CLASH'); }}
                        placeholder={`${r} blue`}
                        className="bg-black border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200 focus:border-blue-500 focus:outline-none"
                      />
                      <input
                        value={redByRole.find((x) => x.role === r)?.riot_id || ''}
                        onChange={(e) => { setRoleId('RED', r, e.target.value); setMode('CLASH'); }}
                        disabled={enemyUnknown}
                        placeholder={`${r} red`}
                        className="bg-black border border-gray-700 rounded px-2 py-1.5 text-sm text-gray-200 disabled:opacity-40 focus:border-red-500 focus:outline-none"
                      />
                    </div>
                  ))}
                </div>
                <label className="flex items-center gap-2 mt-4 text-sm text-gray-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={enemyUnknown}
                    onChange={(e) => setEnemyUnknown(e.target.checked)}
                    className="rounded border-gray-600"
                  />
                  Enemy team unknown
                </label>
              </section>

              <section className="bg-gray-900 border border-gray-800 rounded-lg p-4">
                <h2 className="text-white font-semibold mb-3">Load Champion Proficiencies</h2>
                <div className="flex items-center gap-2 mb-3">
                  <input
                    value={deeplolRegion}
                    onChange={(e) => setDeeplolRegion(e.target.value.toUpperCase())}
                    placeholder="Region (NA1, EUW1, KR...)"
                    className="w-40 bg-black border border-gray-700 rounded px-2 py-1 text-sm text-gray-200"
                  />
                  <input
                    type="number"
                    value={deeplolSeason}
                    onChange={(e) => setDeeplolSeason(Number(e.target.value || 27))}
                    className="w-28 bg-black border border-gray-700 rounded px-2 py-1 text-sm text-gray-200"
                  />
                  <button
                    onClick={handleLoadFromDeeplol}
                    disabled={isLoadingDeeplol}
                    className="px-3 py-1.5 rounded bg-cyan-700 hover:bg-cyan-600 disabled:opacity-40 text-white text-sm"
                  >
                    {isLoadingDeeplol ? 'Loading...' : 'Load from Deeplol'}
                  </button>
                  {deeplolStatus && <span className="text-xs text-cyan-300">{deeplolStatus}</span>}
                </div>
                <p className="text-xs text-gray-500">Uses the same flow as Python: Riot ID lookup to puu_id to champion-stat to role stats extraction.</p>
              </section>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
