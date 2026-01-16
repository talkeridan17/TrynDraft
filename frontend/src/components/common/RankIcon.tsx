interface RankIconProps {
  rank: string; // IRON, BRONZE, SILVER, GOLD, PLATINUM, EMERALD, DIAMOND, MASTER, GRANDMASTER, CHALLENGER
  size?: number;
  className?: string;
}

export const RankIcon: React.FC<RankIconProps> = ({ rank, size = 32, className = '' }) => {
  // Map rank names to Community Dragon URLs
  const rankMap: Record<string, string> = {
    'IRON': 'iron',
    'BRONZE': 'bronze',
    'SILVER': 'silver',
    'GOLD': 'gold',
    'PLATINUM': 'platinum',
    'EMERALD': 'emerald',
    'DIAMOND': 'diamond',
    'MASTER': 'master',
    'GRANDMASTER': 'grandmaster',
    'CHALLENGER': 'challenger'
  };

  const rankName = rankMap[rank.toUpperCase()] || 'iron';
  // Using Community Dragon ranked emblems
  const iconUrl = `https://raw.communitydragon.org/latest/plugins/rcp-fe-lol-static-assets/global/default/images/ranked-emblem/emblem-${rankName}.png`;

  return (
    <img
      src={iconUrl}
      alt={rank}
      width={size}
      height={size}
      className={className}
      style={{ width: size, height: size }}
    />
  );
};
