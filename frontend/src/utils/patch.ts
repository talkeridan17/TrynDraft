/**
 * Fetch the latest League of Legends patch version from Riot Data Dragon
 */
export async function getLatestPatch(): Promise<string> {
  try {
    const response = await fetch('https://ddragon.leagueoflegends.com/api/versions.json');
    const versions = await response.json();
    return versions[0]; // First item is the latest version
  } catch (error) {
    console.error('Failed to fetch latest patch:', error);
    return '16.2.1'; // Fallback to current known patch
  }
}

/**
 * Normalize champion name for Data Dragon API
 * Riot's API uses specific formats without apostrophes or periods
 */
function normalizeChampionId(championId: string): string {
  // Special cases that don't follow standard rules - check first
  const specialCases: Record<string, string> = {
    'Wukong': 'MonkeyKing',
    'Nunu & Willump': 'Nunu',
    'Renata Glasc': 'Renata',
    // Apostrophe names with different rules
    "Rek'Sai": 'RekSai',
    "Kog'Maw": 'KogMaw',
    // Special capitalization
    'LeBlanc': 'Leblanc',
  };

  if (specialCases[championId]) {
    return specialCases[championId];
  }

  // Step 1: Remove apostrophes, periods, and ampersands
  let normalized = championId
    .replace(/['\u2019\u2018]/g, '')  // Remove all apostrophe types
    .replace(/\./g, '')                // Remove periods (Dr. Mundo -> DrMundo)
    .replace(/&/g, '');                // Remove ampersands

  // Step 2: Handle spaces
  // For multi-word names, we need to:
  // - Remove spaces but keep PascalCase (Aurelion Sol -> AurelionSol)
  // - For names with apostrophes, lowercase letter after apostrophe was (Bel'Veth -> Belveth)

  // Check if this champion had an apostrophe in original name
  const hadApostrophe = /['\u2019\u2018]/.test(championId);

  if (hadApostrophe) {
    // For apostrophe names: remove spaces and lowercase the capital after where apostrophe was
    // Bel'Veth -> BelVeth -> Belveth
    // Cho'Gath -> ChoGath -> Chogath
    // Kai'Sa -> KaiSa -> Kaisa
    // Kha'Zix -> KhaZix -> Khazix
    // Vel'Koz -> VelKoz -> Velkoz
    normalized = normalized
      .replace(/\s+/g, '')  // Remove spaces
      .replace(/([a-z])([A-Z])/g, (_match, lower, upper) => {
        // Lowercase the capital letter that comes after a lowercase letter
        return lower + upper.toLowerCase();
      });
  } else {
    // For regular multi-word names: just remove spaces, keep PascalCase
    // Aurelion Sol -> AurelionSol
    // Lee Sin -> LeeSin
    // Master Yi -> MasterYi
    // Miss Fortune -> MissFortune
    // Twisted Fate -> TwistedFate
    // Xin Zhao -> XinZhao
    // Dr. Mundo -> DrMundo (period already removed)
    // Jarvan IV -> JarvanIV
    // Tahm Kench -> TahmKench
    normalized = normalized.replace(/\s+/g, '');
  }

  return normalized;
}

/**
 * Get champion square icon URL (for picker grid)
 */
export function getChampionImageUrl(championId: string, patch?: string): string {
  const version = patch || '16.2.1';
  const normalized = normalizeChampionId(championId);
  return `https://ddragon.leagueoflegends.com/cdn/${version}/img/champion/${normalized}.png`;
}

/**
 * Get champion splash art URL (for draft slots - full size)
 * These are 1215x717 images showing full champion artwork
 */
export function getChampionSplashUrl(championId: string): string {
  const normalized = normalizeChampionId(championId);
  // Splash art format: ChampionName_0.jpg (0 = default skin)
  return `https://ddragon.leagueoflegends.com/cdn/img/champion/splash/${normalized}_0.jpg`;
}

/**
 * Get champion loading screen URL (alternative - 308x560, vertical)
 */
export function getChampionLoadingUrl(championId: string): string {
  const normalized = normalizeChampionId(championId);
  return `https://ddragon.leagueoflegends.com/cdn/img/champion/loading/${normalized}_0.jpg`;
}
