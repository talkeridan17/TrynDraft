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
  // Try all known field names, including nested objects
  const rawTier = (
    si.tier ?? si.league_tier ?? si.soloq_tier ?? si.solo_tier ?? si.rank ??
    si.soloq?.tier ?? si.solo_queue?.tier ?? si.ranked?.tier ?? ''
  ).toString().trim();
  // Convert numeric tier to string name
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
let tagIndexPromise: Promise<{
  validTags: Set<string>;
  champToId: Map<string, number>;
  champTags: Map<string, string[]>;
}> | null = null;

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
        // Inject role hint at the target slot so the model knows which lane to fill
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
  // Firefox/JSEP stability: force pure WASM runtime path.
  // Avoid threaded-jsep execution crashes like "f.$c is null".
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

    // Explicitly provide external data to avoid filesystem-based lookup in browser.
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

export async function fetchAndStoreDeeplolByRiotIds(
  riotIds: string[],
  region: string = 'NA1',
  season: number = 27
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

    // Store summoner info from the summoner endpoint immediately (before champStats check)
    try {
      const si = puuidResponse?.summoner_basic_info_dict || puuidResponse?.summoner || {};
      const { tier: validTier, division } = extractTierDivision(si);
      // eslint-disable-next-line no-console
      console.log('[Deeplol] summoner info keys:', Object.keys(si), '| tier:', validTier, '| division:', division);
      localStorage.setItem('tryndraft_summoner_info', JSON.stringify({
        gameName: parsed.gameName, tagLine: parsed.tagLine, tier: validTier, division,
      }));
    } catch { /* ignore */ }

    const champStats = await fetchDeeplolCandidate(
      `${base}/summoner/champion-stat?puu_id=${encodeURIComponent(puuId)}&season=${encodeURIComponent(String(season))}&platform_id=${encodeURIComponent(platformId)}`
    );
    if (!champStats) continue;

    // If champStats has rank data that summoner endpoint lacked, update stored info
    try {
      const ci = champStats?.summoner_basic_info_dict || champStats?.summoner || {};
      const stored = JSON.parse(localStorage.getItem('tryndraft_summoner_info') || '{}');
      if (!stored.tier && ci) {
        const { tier: validTier, division } = extractTierDivision(ci);
        // eslint-disable-next-line no-console
        console.log('[Deeplol] champStats tier fallback:', validTier, '| keys:', Object.keys(ci));
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

function parseChampionTagsCsv(csvText: string, validTagSet: Set<string>): Map<string, string[]> {
  const lines = csvText.split('\n');
  const map = new Map<string, Map<string, number>>();
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    if (!line) continue;
    const firstComma = line.indexOf(',');
    if (firstComma <= 0) continue;
    const champion = line.slice(0, firstComma).trim();
    // eslint-disable-next-line no-useless-escape
    const tagMatch = line.match(/\"\\[(.*?)\\]\"/);  // intentional escapes for CSV format
    if (!tagMatch) continue;
    const raw = tagMatch[1].trim();
    if (!raw) continue;
    const tags = raw
      .split(',')
      .map((t) => t.trim().replace(/^'+|'+$/g, ''))
      .filter((t) => t && validTagSet.has(t));
    if (!tags.length) continue;
    if (!map.has(champion)) map.set(champion, new Map<string, number>());
    const counter = map.get(champion)!;
    for (const tag of tags) {
      counter.set(tag, (counter.get(tag) || 0) + 1);
    }
  }
  const out = new Map<string, string[]>();
  for (const [champ, counter] of map.entries()) {
    const sorted = [...counter.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8).map(([tag]) => tag);
    out.set(champ, sorted);
  }
  return out;
}

async function loadModelTagIndex() {
  if (tagIndexPromise) return tagIndexPromise;
  tagIndexPromise = (async () => {
    const [tagsResp, champToIdResp, csvResp] = await Promise.all([
      fetch('/models/tags.json'),
      fetch('/models/champ_to_id.json'),
      fetch('/models/champion_tags.csv'),
    ]);
    const tagsJson = tagsResp.ok ? await tagsResp.json() : [];
    const champToIdJson = champToIdResp.ok ? await champToIdResp.json() : {};
    const csvText = csvResp.ok ? await csvResp.text() : '';
    const validTags = new Set<string>(Array.isArray(tagsJson) ? tagsJson : []);
    const champToId = new Map<string, number>();
    Object.entries(champToIdJson || {}).forEach(([k, v]) => champToId.set(k, Number(v)));
    const champTags = parseChampionTagsCsv(csvText, validTags);
    return { validTags, champToId, champTags };
  })();
  return tagIndexPromise;
}

export function setLLMModel(modelId: string) {
  const mapped = LEGACY_MODEL_MAP[modelId] || modelId;
  const valid = (mapped in LLM_MODELS) ? mapped : DEFAULT_LLM_MODEL;
  localStorage.setItem('explainability_llm_model', valid);
  // Terminate existing worker so next call loads the new model
  if (_llmWorker) { _llmWorker.terminate(); _llmWorker = null; }
}

function resolveStoredLLMModel(): string {
  const raw = localStorage.getItem('explainability_llm_model') || DEFAULT_LLM_MODEL;
  // Migrate old onnx-community models to Xenova equivalents
  const mapped = LEGACY_MODEL_MAP[raw] || raw;
  const valid = (mapped in LLM_MODELS) ? mapped : DEFAULT_LLM_MODEL;
  if (valid !== raw) {
    localStorage.setItem('explainability_llm_model', valid);
    // eslint-disable-next-line no-console
    console.log('Migrated LLM model from', raw, 'to', valid);
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

// LLM runs in a Web Worker so it never blocks the main thread.
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
  const { champion_ids, sides, phases, lanes, event_types } = buildEventArrays(input, dd);

  const turn = Math.max(0, Math.min(19, input.turn));
  // During PICK phase, unmask the target slot so the model can attend to its lane hint.
  // During BAN phase, keep original >= mask (no role to hint).
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
    // Session may be poisoned after low-level wasm runtime fault; recreate once.
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
      // Only boost if champion's stored role matches the current draft slot role
      const profRoleNorm = prof?.role ? (DEEPLOL_ROLE_MAP[prof.role.toLowerCase()] ?? null) : null;
      const roleMatch = !profRoleNorm || profRoleNorm === (input.role || '').toUpperCase();
      const profAdj = (prof && roleMatch && input.phase !== 'BAN') ? (prof.proficiency * 0.1) : 0;
      const score = x.p + profAdj;
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
  const tagIndex = await loadModelTagIndex();

  const top5 = args.topChampions.slice(0, 5).map((c, i) => {
    const prof = c.proficiency ? `games=${c.proficiency.games}, wr=${c.proficiency.win_rate.toFixed(1)}%, ai=${c.proficiency.ai_score.toFixed(1)}` : 'no deeplol profile data';
    const tags = (tagIndex.champTags.get(c.name) || []).slice(0, 5).join(', ') || 'none';
    const champId = tagIndex.champToId.get(c.name);
    return `${i + 1}. ${c.name} (softmax=${(c.softmax * 100).toFixed(2)}%, ${prof}, model_champion_id=${champId ?? 'unknown'}, tag_index_evidence=[${tags}])`;
  }).join('\n');

  const prompt = `System: You are a League of Legends draft assistant. Use ONLY the provided evidence.

Candidate:
${top5}

Role: ${args.draftState.role}
Phase: ${args.draftState.phase}

Instruction: For each candidate, write 1 short sentence using their tag_index_evidence. If tags are "none", mention they are a high-confidence model pick.

Example Format:
1. Champion: Explanation.
2. Champion: Explanation.

Assistant:
1.`;

  try {
    const text = await runLLMInWorker(prompt, current, args.isUserTurn ? 160 : 96);
    return { analysis: text, model: current, source: 'frontend_llm_rag' };
  } catch (err) {
    console.error('LLM explainability error:', err);
    const quick = args.topChampions.slice(0, 3).map(c => c.name).join(', ');
    return {
      analysis: `Error: ${err instanceof Error ? err.message : String(err)}. Model-first picks: ${quick}.`,
      model: `${current} (fallback)`,
      source: 'frontend_fallback',
    };
  }
}
