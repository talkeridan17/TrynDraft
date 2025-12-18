// Utility functions for getting images from Data Dragon
// These will be replaced with actual API calls to our backend

export const getRankIcon = (elo: string): string => {
  // Will come from backend API
  return `/api/ranks/${elo.toLowerCase()}`;
};

export const getRoleIcon = (role: string): string => {
  // Will come from backend API
  return `/api/roles/${role.toLowerCase()}`;
};

export const getChampionImage = (championName: string, patch?: string): string => {
  // This will be replaced with backend API call
  // For now, use Data Dragon directly
  const normalizedName = championName.replace(/[^a-zA-Z]/g, '');
  const version = patch || '14.1.1';
  return `https://ddragon.leagueoflegends.com/cdn/${version}/img/champion/${normalizedName}.png`;
};

export const getChampionLoadingImage = (championName: string): string => {
  const normalizedName = championName.replace(/[^a-zA-Z]/g, '');
  return `https://ddragon.leagueoflegends.com/cdn/img/champion/loading/${normalizedName}_0.jpg`;
};

export const getChampionSplashImage = (championName: string): string => {
  const normalizedName = championName.replace(/[^a-zA-Z]/g, '');
  return `https://ddragon.leagueoflegends.com/cdn/img/champion/splash/${normalizedName}_0.jpg`;
};

// Fallback champion data until API is ready
export const MOCK_CHAMPIONS = [
  'Aatrox', 'Ahri', 'Akali', 'Alistar', 'Amumu', 'Anivia', 'Annie', 'Aphelios',
  'Ashe', 'Aurelion Sol', 'Azir', 'Bard', 'Blitzcrank', 'Brand', 'Braum',
  'Caitlyn', 'Camille', 'Cassiopeia', 'ChoGath', 'Corki', 'Darius', 'Diana',
  'Draven', 'Dr. Mundo', 'Ekko', 'Elise', 'Evelynn', 'Ezreal', 'Fiddlesticks',
  'Fiora', 'Fizz', 'Galio', 'Gangplank', 'Garen', 'Gnar', 'Gragas', 'Graves',
  'Hecarim', 'Heimerdinger', 'Illaoi', 'Irelia', 'Ivern', 'Janna', 'Jarvan IV',
  'Jax', 'Jayce', 'Jhin', 'Jinx', 'KaiSa', 'Kalista', 'Karma', 'Karthus',
  'Kassadin', 'Katarina', 'Kayle', 'Kayn', 'Kennen', 'KhaZix', 'Kindred',
  'Kled', 'KogMaw', 'LeBlanc', 'Lee Sin', 'Leona', 'Lillia', 'Lissandra',
  'Lucian', 'Lulu', 'Lux', 'Malphite', 'Malzahar', 'Maokai', 'Master Yi',
  'Miss Fortune', 'Mordekaiser', 'Morgana', 'Nami', 'Nasus', 'Nautilus',
  'Neeko', 'Nidalee', 'Nocturne', 'Nunu & Willump', 'Olaf', 'Orianna',
  'Ornn', 'Pantheon', 'Poppy', 'Pyke', 'Qiyana', 'Quinn', 'Rakan', 'Rammus',
  'RekSai', 'Rell', 'Renekton', 'Rengar', 'Riven', 'Rumble', 'Ryze',
  'Samira', 'Sejuani', 'Senna', 'Seraphine', 'Sett', 'Shaco', 'Shen',
  'Shyvana', 'Singed', 'Sion', 'Sivir', 'Skarner', 'Sona', 'Soraka',
  'Swain', 'Sylas', 'Syndra', 'Tahm Kench', 'Taliyah', 'Talon', 'Taric',
  'Teemo', 'Thresh', 'Tristana', 'Trundle', 'Tryndamere', 'Twisted Fate',
  'Twitch', 'Udyr', 'Urgot', 'Varus', 'Vayne', 'Veigar', 'VelKoz',
  'Vex', 'Vi', 'Viego', 'Viktor', 'Vladimir', 'Volibear', 'Warwick',
  'Wukong', 'Xayah', 'Xerath', 'Xin Zhao', 'Yasuo', 'Yone', 'Yorick',
  'Yuumi', 'Zac', 'Zed', 'Zeri', 'Ziggs', 'Zilean', 'Zoe', 'Zyra'
];