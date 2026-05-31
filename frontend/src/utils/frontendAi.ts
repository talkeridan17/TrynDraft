/* eslint-disable @typescript-eslint/no-explicit-any */

const STRICT_DRAFT_MODEL_URL = '/models/model.onnx';
const STRICT_DRAFT_EXTERNAL_DATA_URL = '/models/model.onnx.data';

const NO_BAN_ID = 999;
const MIN_GAMES = 3;

const LLM_MODELS = {
  'onnx-community/Qwen2.5-0.5B-Instruct': { label: 'Qwen2.5 0.5B (Fastest)', higher: false },
  'onnx-community/Qwen2.5-1.5B-Instruct': { label: 'Qwen2.5 1.5B (Balanced)', higher: true },
  'onnx-community/SmolLM2-135M-Instruct': { label: 'SmolLM2 135M (Ultra-light)', higher: false },
  'onnx-community/Llama-3.2-1B-Instruct': { label: 'Llama 3.2 1B (High Quality)', higher: true },
} as const;

const DEFAULT_LLM_MODEL = 'onnx-community/Qwen2.5-0.5B-Instruct';
const LEGACY_MODEL_MAP: Record<string, string> = {
  'HuggingFaceTB/SmolLM2-1.7B-Instruct': 'onnx-community/Qwen2.5-1.5B-Instruct',
  'Qwen/Qwen2.5-0.5B-Instruct': 'onnx-community/Qwen2.5-0.5B-Instruct',
  'Qwen/Qwen2.5-1.5B-Instruct': 'onnx-community/Qwen2.5-1.5B-Instruct',
  'Xenova/Qwen2.5-0.5B-Instruct': 'onnx-community/Qwen2.5-0.5B-Instruct',
  'Xenova/Qwen2.5-1.5B-Instruct': 'onnx-community/Qwen2.5-1.5B-Instruct',
  'onnx-community/Qwen2-0.5B-Instruct-ONNX': 'onnx-community/Qwen2.5-0.5B-Instruct',
};

const SOLOQ_SEQUENCE: Array<[number, number, number]> = [
  [0, 1, 0], [0, 1, 0], [1, 1, 0], [1, 1, 0], [0, 1, 0], [1, 1, 0], [0, 2, 0], [1, 2, 0], [0, 2, 0], [1, 2, 0],
  [0, 1, 1], [1, 1, 1], [1, 1, 1], [0, 1, 1], [0, 1, 1], [1, 1, 1], [1, 2, 1], [0, 2, 1], [0, 2, 1], [1, 2, 1],
];

const CLASH_SEQUENCE: Array<[number, number, number]> = [
  [0, 1, 0], [1, 1, 0], [0, 1, 0], [1, 1, 0], [0, 1, 0], [1, 1, 0],
  [0, 1, 1], [1, 1, 1], [1, 1, 1], [0, 1, 1], [0, 1, 1], [1, 1, 1],
  [0, 2, 0], [1, 2, 0], [0, 2, 0], [1, 2, 0],
  [1, 2, 1], [0, 2, 1], [0, 2, 1], [1, 2, 1],
];

type Proficiency = { games: number; win_rate: number; ai_score: number; proficiency: number; role?: string };
type DraftInput = {
  phase: 'BAN' | 'PICK' | 'COMPLETE';
  turn: number;
  role: string;
  user_role?: string;
  is_user_slot?: boolean;
  mode?: 'SOLOQ' | 'CLASH';
  solo_riot_id?: string;
  clash_blue_ids?: string[];
  clash_red_ids?: string[];
  clash_blue_by_role?: Array<{ role: string; riot_id: string }>;
  clash_red_by_role?: Array<{ role: string; riot_id: string }>;
  clash_enemy_unknown?: boolean;
  bans_blue: string[];
  bans_red: string[];
  picks_blue: Array<{ champion: string; role: string }>;
  picks_red: Array<{ champion: string; role: string }>;
};

// Maps Deeplol role strings to our canonical role names
const DEEPLOL_ROLE_MAP: Record<string, string> = {
  top: 'TOP', jungle: 'JUNGLE', middle: 'MID', bot: 'ADC', supporter: 'SUPPORT',
};

// Deeplol sometimes returns tier as an integer index
const TIER_ID_MAP: Record<string, string> = {
  '0': 'UNRANKED', '1': 'IRON', '2': 'BRONZE', '3': 'SILVER',
  '4': 'GOLD', '5': 'PLATINUM', '6': 'EMERALD', '7': 'DIAMOND',
  '8': 'MASTER', '9': 'GRANDMASTER', '10': 'CHALLENGER',
};

function extractTierDivision(si: any): { tier: string | null; division: string | null } {
  const divMap: Record<string, string> = { '1': 'I', '2': 'II', '3': 'III', '4': 'IV' };
  const rawTier = (
    si.tier ?? si.league_tier ?? si.soloq_tier ?? si.solo_tier ?? si.rank ??
    si.soloq?.tier ?? si.solo_queue?.tier ?? si.ranked?.tier ?? ''
  ).toString().trim();
  const tierStr = TIER_ID_MAP[rawTier] ?? rawTier;
  const validTier = tierStr && !['UNRANKED', 'NONE', ''].includes(tierStr.toUpperCase())
    ? tierStr.toUpperCase()
    : null;
  const rawDiv = si.division ?? si.league_division ?? si.soloq?.division ?? null;
  const division = rawDiv !== null ? (divMap[String(rawDiv)] ?? String(rawDiv).toUpperCase()) : null;
  return { tier: validTier, division };
}


let ddCache: any = null;
let ortLoadPromise: Promise<any> | null = null;
let ortSessionPromise: Promise<any> | null = null;
// role_affinity.json: { "champId": { "MID": 0.998, "TOP": 0.001, ... } }
let roleAffinityPromise: Promise<Map<number, Record<string, number>>> | null = null;

async function loadDataDragon() {
  if (ddCache) return ddCache;
  const versions = await fetch('https://ddragon.leagueoflegends.com/api/versions.json').then(r => r.json());
  const version = versions[0];
  const champJson = await fetch(`https://ddragon.leagueoflegends.com/cdn/${version}/data/en_US/champion.json`).then(r => r.json());
  const champions = Object.values(champJson.data) as Array<any>;
  const byName = new Map<string, any>();
  const byKey = new Map<number, any>();
  champions.forEach((c) => {
    byName.set(c.name, c);
    byKey.set(Number(c.key), c);
  });
  ddCache = { version, byName, byKey, champions };
  return ddCache;
}

function softmax(values: number[]): number[] {
  const max = Math.max(...values);
  const exps = values.map(v => Math.exp(v - max));
  const sum = exps.reduce((a, b) => a + b, 0);
  return exps.map(v => v / Math.max(sum, 1e-9));
}

function laneToId(role?: string): number {
  const map: Record<string, number> = { TOP: 0, JUNGLE: 1, MID: 2, MIDDLE: 2, ADC: 3, BOTTOM: 3, SUPPORT: 4, UTILITY: 4 };
  return map[(role || '').toUpperCase()] ?? 5;
}

function buildEventArrays(input: DraftInput, dd: any) {
  const champion_ids = Array<number>(20).fill(0);
  const sequence = input.mode === 'CLASH' ? CLASH_SEQUENCE : SOLOQ_SEQUENCE;
  const sides = sequence.map(s => s[0]);
  const phases = sequence.map(s => s[1]);
  const event_types = sequence.map(s => s[2]);
  const lanes = Array<number>(20).fill(5);

  const seenBan = { 0: 0, 1: 0 } as Record<number, number>;
  const seenPick = { 0: 0, 1: 0 } as Record<number, number>;

  for (let slot = 0; slot < sequence.length; slot++) {
    const [side, , eventType] = sequence[slot];
    const isPick = eventType === 1;
    if (isPick) {
      const idx = seenPick[side];
      const pick = side === 0 ? input.picks_blue[idx] : input.picks_red[idx];
      seenPick[side] += 1;
      if (!pick?.champion) {
        if (input.phase === 'PICK' && slot === Math.max(0, Math.min(19, input.turn))) {
          lanes[slot] = laneToId(pick?.role || input.role);
        }
        continue;
      }
      const champ = dd.byName.get(pick.champion);
      champion_ids[slot] = champ ? Number(champ.key) : 0;
      lanes[slot] = laneToId(pick.role);
    } else {
      const idx = seenBan[side];
      const ban = side === 0 ? input.bans_blue[idx] : input.bans_red[idx];
      seenBan[side] += 1;
      if (!ban) continue;
      const champ = dd.byName.get(ban);
      champion_ids[slot] = champ ? Number(champ.key) : NO_BAN_ID;
      lanes[slot] = 5;
    }
  }

  return { champion_ids, sides, phases, lanes, event_types };
}

async function loadOrt() {
  if (ortLoadPromise) return ortLoadPromise;
  ortLoadPromise = new Promise((resolve, reject) => {
    if ((window as any).ort) { resolve((window as any).ort); return; }
    const script = document.createElement('script');
    script.src = 'https://cdn.jsdelivr.net/npm/onnxruntime-web/dist/ort.min.js';
    script.async = true;
    script.crossOrigin = 'anonymous';
    script.onload = () => resolve((window as any).ort);
    script.onerror = (e) => { ortLoadPromise = null; reject(e); };
    document.head.appendChild(script);
  });
  const ort = await ortLoadPromise;
  ort.env.wasm.proxy = false;
  ort.env.wasm.numThreads = 1;
  ort.env.wasm.simd = true;
  return ort;
}

async function loadDraftSession() {
  if (ortSessionPromise) return ortSessionPromise;
  ortSessionPromise = (async () => {
    const ort = await loadOrt();
    const [onnxResp, dataResp] = await Promise.all([
      fetch(STRICT_DRAFT_MODEL_URL, { mode: 'cors' }),
      fetch(STRICT_DRAFT_EXTERNAL_DATA_URL, { mode: 'cors' }),
    ]);
    if (!onnxResp.ok) throw new Error(`Failed to fetch ${STRICT_DRAFT_MODEL_URL} (${onnxResp.status})`);
    if (!dataResp.ok) throw new Error(`Failed to fetch ${STRICT_DRAFT_EXTERNAL_DATA_URL} (${dataResp.status})`);

    const [onnxBuffer, dataBuffer] = await Promise.all([
      onnxResp.arrayBuffer(),
      dataResp.arrayBuffer(),
    ]);
    const data = new Uint8Array(dataBuffer);

    const externalData = [
      { path: 'model.onnx.data', data },
      { path: './model.onnx.data', data },
      { path: '"model.onnx.data"', data },
      // eslint-disable-next-line no-useless-escape
      { path: '\"model.onnx.data\"', data },
    ];

    return await ort.InferenceSession.create(onnxBuffer, {
      executionProviders: ['wasm'],
      externalData,
    });
  })();
  return ortSessionPromise;
}

// Call this when the draft is complete to free the ONNX model from WASM memory.
// The session will be recreated on the next draft if needed.
export function releaseOnnxSession() {
  ortSessionPromise = null;
}

function getSavedProficiencies(): Record<string, Proficiency> {
  try {
    return JSON.parse(localStorage.getItem('deeplol_proficiencies') || '{}');
  } catch {
    return {};
  }
}

function saveProficiencies(map: Record<string, Proficiency>) {
  localStorage.setItem('deeplol_proficiencies', JSON.stringify(map));
}

function computeProficiency(games: number, winRate: number, aiScore: number): number {
  const gamesScore = Math.min(Math.log1p(games) / Math.log1p(50), 1.0);
  const wrScore = Math.max(0.0, Math.min((winRate - 35.0) / 30.0, 1.0));
  const aiNorm = Math.max(0.0, Math.min(aiScore / 100.0, 1.0));
  return Number((0.5 * aiNorm + 0.3 * wrScore + 0.2 * gamesScore).toFixed(4));
}

function upsertDeeplolEntries(parsed: any): { imported: number } {
  const out: Record<string, Proficiency> = getSavedProficiencies();
  const VALID_ROLES = new Set(['top', 'jungle', 'middle', 'bot', 'supporter']);

  const addOne = (entry: any, role?: string) => {
    const cid = Number(entry?.champion_id);
    const games = Number(entry?.games ?? 0);
    const win_rate = Number(entry?.win_rate ?? 0);
    const ai_score = Number(entry?.ai_score ?? 0);
    if (!Number.isFinite(cid) || games < MIN_GAMES) return;
    const prof = computeProficiency(games, win_rate, ai_score);
    const existing = out[String(cid)];
    if (!existing || prof >= existing.proficiency) {
      out[String(cid)] = { games, win_rate, ai_score, proficiency: prof, role };
    }
  };

  if (Array.isArray(parsed)) {
    parsed.forEach((x) => addOne(x));
  } else if (parsed && typeof parsed === 'object') {
    Object.entries(parsed).forEach(([role, entries]: [string, any]) => {
      if (!VALID_ROLES.has(role.toLowerCase()) || !Array.isArray(entries)) return;
      entries.forEach((x) => addOne(x, role.toLowerCase()));
    });
  }

  saveProficiencies(out);
  return { imported: Object.keys(out).length };
}

export function importDeeplolJson(raw: string): { imported: number } {
  return upsertDeeplolEntries(JSON.parse(raw));
}

async function fetchDeeplolCandidate(url: string): Promise<any | null> {
  try {
    const r = await fetch(url, { mode: 'cors' });
    if (!r.ok) return null;
    return await r.json();
  } catch {
    return null;
  }
}

function normalizeRegion(regionStr: string): string {
  const regionMap: Record<string, string> = {
    na: 'NA1', na1: 'NA1',
    euw: 'EUW1', euw1: 'EUW1',
    eune: 'EUN1', eun1: 'EUN1',
    kr: 'KR',
    br: 'BR1', br1: 'BR1',
    jp: 'JP1', jp1: 'JP1',
    lan: 'LA1', la1: 'LA1',
    las: 'LA2', la2: 'LA2',
    oce: 'OC1', oc1: 'OC1',
    tr: 'TR1', tr1: 'TR1',
    ru: 'RU',
  };
  const normalized = (regionStr || 'NA1').toLowerCase();
  return regionMap[normalized] || regionStr.toUpperCase();
}

function parseRiotId(riotId: string): { gameName: string; tagLine: string } | null {
  const parts = riotId.trim().split('#');
  if (parts.length < 2) return null;
  const tagLine = parts.pop() || '';
  const gameName = parts.join('#');
  if (!gameName || !tagLine) return null;
  return { gameName, tagLine };
}

function actualStats(inputDict: any) {
  const impDict = inputDict?.counter_champion_stats?.total?.enemy_champion_stats || {};
  const final: Record<string, Array<{ champion_id: number; games: number; win_rate: number; ai_score: number }>> = {
    Top: [], Jungle: [], Middle: [], Bot: [], Supporter: [],
  };
  for (const key of Object.keys(impDict)) {
    if (!final[key]) continue;
    const championsList = Array.isArray(impDict[key]) ? impDict[key] : [];
    for (const championSet of championsList) {
      if (!championSet || championSet.champion_id === 0) continue;
      final[key].push({
        champion_id: championSet.champion_id,
        games: Number(championSet.games || 0),
        win_rate: Number(championSet.win_rate || 0),
        ai_score: Number(championSet.ai_score || 0),
      });
    }
  }
  return final;
}

async function detectDeeplolSeason(base: string, puuId: string, platformId: string): Promise<number> {
  for (let s = 35; s >= 25; s--) {
    const data = await fetchDeeplolCandidate(
      `${base}/summoner/champion-stat?puu_id=${encodeURIComponent(puuId)}&season=${s}&platform_id=${encodeURIComponent(platformId)}`
    );
    const stats = data ? actualStats(data) : null;
    if (stats && Object.values(stats).some(arr => arr.length > 0)) return s;
  }
  return 27;
}

export async function fetchAndStoreDeeplolByRiotIds(
  riotIds: string[],
  region: string = 'NA1',
  season: number = 0
): Promise<{ imported: number; source: string; found: boolean }> {
  const base = 'https://b2c-api-cdn.deeplol.gg';
  const platformId = normalizeRegion(region);
  let imported = Object.keys(getSavedProficiencies()).length;
  let found = false;

  for (const rawId of riotIds) {
    const parsed = parseRiotId(rawId);
    if (!parsed) continue;

    const puuidResponse = await fetchDeeplolCandidate(
      `${base}/summoner/summoner?riot_id_name=${encodeURIComponent(parsed.gameName)}&riot_id_tag_line=${encodeURIComponent(parsed.tagLine)}&platform_id=${encodeURIComponent(platformId)}`
    );
    const puuId = puuidResponse?.summoner_basic_info_dict?.puu_id || puuidResponse?.summoner?.puu_id;
    if (!puuId) continue;
    found = true;

    try {
      const si = puuidResponse?.summoner_basic_info_dict || puuidResponse?.summoner || {};
      const { tier: validTier, division } = extractTierDivision(si);
      localStorage.setItem('tryndraft_summoner_info', JSON.stringify({
        gameName: parsed.gameName, tagLine: parsed.tagLine, tier: validTier, division,
      }));
    } catch { /* ignore */ }

    const resolvedSeason = season > 0 ? season : await detectDeeplolSeason(base, puuId, platformId);
    const champStats = await fetchDeeplolCandidate(
      `${base}/summoner/champion-stat?puu_id=${encodeURIComponent(puuId)}&season=${encodeURIComponent(String(resolvedSeason))}&platform_id=${encodeURIComponent(platformId)}`
    );
    if (!champStats) continue;

    try {
      const ci = champStats?.summoner_basic_info_dict || champStats?.summoner || {};
      const stored = JSON.parse(localStorage.getItem('tryndraft_summoner_info') || '{}');
      if (!stored.tier && ci) {
        const { tier: validTier, division } = extractTierDivision(ci);
        if (validTier) {
          stored.tier = validTier;
          stored.division = division;
          localStorage.setItem('tryndraft_summoner_info', JSON.stringify(stored));
        }
      }
    } catch { /* ignore */ }

    const parsedStats = actualStats(champStats);
    imported = upsertDeeplolEntries(parsedStats).imported;
  }

  return { imported, source: base, found };
}


async function loadRoleAffinity(): Promise<Map<number, Record<string, number>>> {
  if (roleAffinityPromise) return roleAffinityPromise;
  roleAffinityPromise = (async () => {
    const out = new Map<number, Record<string, number>>();
    try {
      const resp = await fetch('/models/role_affinity.json');
      if (!resp.ok) return out;
      const raw: Record<string, Record<string, number>> = await resp.json();
      for (const [idStr, roles] of Object.entries(raw)) {
        out.set(Number(idStr), roles);
      }
    } catch { /* silently degrade if file missing */ }
    return out;
  })();
  return roleAffinityPromise;
}


export function setLLMModel(modelId: string) {
  const mapped = LEGACY_MODEL_MAP[modelId] || modelId;
  const valid = (mapped in LLM_MODELS) ? mapped : DEFAULT_LLM_MODEL;
  localStorage.setItem('explainability_llm_model', valid);
  if (_llmWorker) { _llmWorker.terminate(); _llmWorker = null; }
}

function resolveStoredLLMModel(): string {
  const raw = localStorage.getItem('explainability_llm_model') || DEFAULT_LLM_MODEL;
  const mapped = LEGACY_MODEL_MAP[raw] || raw;
  const valid = (mapped in LLM_MODELS) ? mapped : DEFAULT_LLM_MODEL;
  if (valid !== raw) {
    localStorage.setItem('explainability_llm_model', valid);
  }
  return valid;
}

export function getLLMModelOptions() {
  const current = resolveStoredLLMModel();
  return {
    current,
    options: Object.entries(LLM_MODELS).map(([id, x]) => ({ id, ...x })),
  };
}

let _llmWorker: Worker | null = null;

function getLLMWorker(): Worker {
  if (!_llmWorker) {
    _llmWorker = new Worker(
      new URL('../workers/llm.worker.ts', import.meta.url),
      { type: 'module' }
    );
  }
  return _llmWorker;
}

function runLLMInWorker(prompt: string, modelId: string, maxNewTokens: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const worker = getLLMWorker();
    const requestId = Date.now() + Math.random();

    const handler = (e: MessageEvent) => {
      if (e.data.requestId !== requestId) return;
      if (e.data.type === 'result' || e.data.type === 'error') {
        worker.removeEventListener('message', handler);
      }
      if (e.data.type === 'result') resolve(e.data.text as string);
      else if (e.data.type === 'error') reject(new Error(e.data.message as string));
    };

    worker.addEventListener('message', handler);
    worker.postMessage({ type: 'generate', requestId, prompt, modelId, maxNewTokens });
  });
}

export async function runFrontendRanking(input: DraftInput) {
  const dd = await loadDataDragon();
  const profByKey = getSavedProficiencies();
  const session = await loadDraftSession();
  const ort = await loadOrt();
  const roleAffinity = await loadRoleAffinity();
  const { champion_ids, sides, phases, lanes, event_types } = buildEventArrays(input, dd);

  const turn = Math.max(0, Math.min(19, input.turn));
  const target_mask = Array.from({ length: 20 }, (_, i) => {
    if (i < turn) return 0;
    if (i === turn && input.phase === 'PICK') return 0;
    return 1;
  });

  const feeds: Record<string, any> = {
    champion_ids: new ort.Tensor('int64', BigInt64Array.from(champion_ids.map(BigInt)), [1, 20]),
    sides: new ort.Tensor('int64', BigInt64Array.from(sides.map(BigInt)), [1, 20]),
    phases: new ort.Tensor('int64', BigInt64Array.from(phases.map(BigInt)), [1, 20]),
    lanes: new ort.Tensor('int64', BigInt64Array.from(lanes.map(BigInt)), [1, 20]),
    event_types: new ort.Tensor('int64', BigInt64Array.from(event_types.map(BigInt)), [1, 20]),
    domain: new ort.Tensor('int64', BigInt64Array.from([BigInt(1)]), [1]),
    target_mask: new ort.Tensor('bool', Uint8Array.from(target_mask), [1, 20]),
  };

  let output: any;
  try {
    output = await session.run(feeds);
  } catch {
    ortSessionPromise = null;
    const freshSession = await loadDraftSession();
    output = await freshSession.run(feeds);
  }
  const outName = session.outputNames?.[0] || 'pick_ban_logits';
  const logitsTensor = output[outName] || output.pick_ban_logits;
  const logits = Array.from(logitsTensor.data as Float32Array);

  const taken = new Set<number>();
  [...input.bans_blue, ...input.bans_red].filter(Boolean).forEach((name) => {
    const c = dd.byName.get(name);
    if (c) taken.add(Number(c.key));
  });
  [...input.picks_blue, ...input.picks_red].forEach((p) => {
    const c = dd.byName.get(p.champion);
    if (c) taken.add(Number(c.key));
  });

  const masked = logits.map((v, idx) => (idx === 0 || idx === NO_BAN_ID || taken.has(idx)) ? -1e9 : v);
  const probs = softmax(masked);

  const scored = probs
    .map((p, idx) => ({ id: idx, p }))
    .filter((x) => {
      if (x.p <= 0 || !dd.byKey.has(x.id)) return false;
      return true;
    })
    .map((x) => {
      const champ = dd.byKey.get(x.id);
      const prof = profByKey[String(x.id)] || null;
      const profRoleNorm = prof?.role ? (DEEPLOL_ROLE_MAP[prof.role.toLowerCase()] ?? null) : null;
      const roleMatch = !profRoleNorm || profRoleNorm === (input.role || '').toUpperCase();
      const profAdj = (prof && roleMatch && input.phase !== 'BAN' && !!input.is_user_slot) ? (prof.proficiency * 0.1) : 0;

      const affinityMap = roleAffinity.get(x.id);
      const targetRole = (input.role || '').toUpperCase();
      const ROLE_TO_AFFINITY: Record<string, string> = { ADC: 'BOT', BOTTOM: 'BOT', MIDDLE: 'MID' };
      const affKey = ROLE_TO_AFFINITY[targetRole] ?? targetRole;
      let affinityMult = 1.0;
      if (input.phase === 'PICK' && affinityMap) {
        affinityMult = affinityMap[affKey] ?? 0;
      }
      const primaryRole = affinityMap
        ? Object.entries(affinityMap).sort((a, b) => b[1] - a[1])[0]?.[0] ?? null
        : null;
      const affinityScore = affinityMap?.[affKey] ?? null;

      const score = x.p * affinityMult + profAdj;
      return {
        id: String(champ.id),
        name: champ.name,
        key: champ.key,
        score,
        softmax: x.p,
        available: true,
        in_user_pool: !!prof,
        user_proficiency: prof ? Number((prof.proficiency * 5).toFixed(2)) : null,
        win_rate: prof ? prof.win_rate / 100 : 0.5,
        pick_rate: Math.min(1, x.p * 8),
        roles: [input.role],
        role_win_rate: prof ? prof.win_rate / 100 : 0.5,
        role_games: prof?.games || 0,
        role_kda: null,
        target_role: input.role,
        primary_role: primaryRole,
        role_affinity: affinityScore,
        proficiency_data: prof,
      };
    })
    .sort((a, b) => b.score - a.score);

  return {
    model_type: 'frontend_onnx_only',
    champions: scored,
    softmaxTop5: scored.slice(0, 5).map((c) => ({ champion: c.name, softmax: c.softmax, proficiency: c.proficiency_data || null })),
  };
}

export async function runFrontendExplainability(args: {
  draftState: DraftInput;
  topChampions: Array<{ name: string; softmax: number; proficiency: Proficiency | null }>;
  isUserTurn?: boolean;
  onStream?: (text: string) => void;
}) {
  const { current } = getLLMModelOptions();

  // Build champion-specific gameplan prompt for COMPLETE phase
  const role = args.draftState.role;
  const ds = args.draftState as any; // DraftState has side field even if DraftInput doesn't declare it
  const side: string = ds.side || 'BLUE';
  const ROLE_ORDER = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'];
  const userPos = ROLE_ORDER.indexOf(role);
  const userPicks: Array<{ champion: string; role: string }> =
    side === 'BLUE' ? args.draftState.picks_blue : args.draftState.picks_red;
  const enemyPicks: Array<{ champion: string; role: string }> =
    side === 'BLUE' ? args.draftState.picks_red : args.draftState.picks_blue;

  const userChampion = userPicks.find(p => p.role === role)?.champion
    || userPicks[userPos]?.champion
    || args.topChampions[0]?.name
    || 'Unknown';

  const laneOpponent = enemyPicks.find(p => p.role === role)?.champion;
  const allies = userPicks.filter(p => p.champion && p.champion !== userChampion).map(p => `${p.champion} (${p.role})`).join(', ') || 'unknown allies';
  const enemies = enemyPicks.filter(p => p.champion).map(p => `${p.champion} (${p.role})`).join(', ') || 'unknown enemies';

  const isJungle = role === 'JUNGLE';
  const laneContext = isJungle
    ? `Allies to consider ganking for: ${allies}. Enemy carries to track: ${enemies}.`
    : `Lane opponent: ${laneOpponent || 'unknown'}. Enemy team: ${enemies}.`;

  const paragraph2Instruction = isJungle
    ? `Paragraph 2: Specific early pathing route for ${userChampion} in this game — which side to start, first clear, which ally lanes to prioritize for ganks based on their champions and the enemy composition.`
    : `Paragraph 2: Laning phase advice for ${userChampion} against ${laneOpponent || 'this opponent'} — key trade patterns, power spikes, when to push or freeze, and how to use the rest of the enemy team composition to make decisions.`;

  const prompt = `You are a professional League of Legends coach. Write a concise gameplan for this player.

Player: ${userChampion} (${role})
${laneContext}
Bans: ${[...args.draftState.bans_blue, ...args.draftState.bans_red].filter(Boolean).join(', ') || 'none'}

Paragraph 1: General win condition and gameplan for ${userChampion} in this specific draft — power spikes, macro strategy, team fight role, and when this composition is strongest.
${paragraph2Instruction}

Write exactly 2 paragraphs. Be specific to these champions. No bullet points. Start directly with the first paragraph.`;

  try {
    const text = await runLLMInWorker(prompt, current, 400);
    // Terminate worker after inference to free model weights (~250-750MB) from memory
    if (_llmWorker) { _llmWorker.terminate(); _llmWorker = null; }
    return { analysis: text, model: current, source: 'frontend_llm_rag' };
  } catch (err) {
    if (_llmWorker) { _llmWorker.terminate(); _llmWorker = null; }
    console.error('LLM explainability error:', err);
    return {
      analysis: `LLM analysis unavailable (${err instanceof Error ? err.message.slice(0, 80) : 'load error'}). This feature requires a stable connection and may not work in all browsers. Your draft data is saved.`,
      model: `${current} (unavailable)`,
      source: 'frontend_fallback',
    };
  }
}
