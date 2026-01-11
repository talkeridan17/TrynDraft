import { Award, Trophy, Crown, Gem, Sparkles } from 'lucide-react';

interface RankIconProps {
  rank: 'IRON' | 'BRONZE' | 'SILVER' | 'GOLD' | 'PLATINUM' | 'EMERALD' | 'DIAMOND' | 'MASTER' | 'GRANDMASTER' | 'CHALLENGER';
  size?: number;
  className?: string;
}

const getRankColor = (rank: string) => {
  const colors = {
    IRON: 'text-gray-500',
    BRONZE: 'text-amber-700',
    SILVER: 'text-gray-400',
    GOLD: 'text-yellow-500',
    PLATINUM: 'text-teal-400',
    EMERALD: 'text-emerald-400',
    DIAMOND: 'text-blue-400',
    MASTER: 'text-purple-400',
    GRANDMASTER: 'text-red-400',
    CHALLENGER: 'text-yellow-300'
  };
  return colors[rank as keyof typeof colors] || 'text-gray-400';
};

export const RankIcon: React.FC<RankIconProps> = ({ rank, size = 20, className = '' }) => {
  const color = getRankColor(rank);
  const iconProps = {
    size,
    className: `${color} ${className}`,
    strokeWidth: 2.5,
    fill: 'currentColor'
  };

  // Different icons for different tiers
  if (rank === 'CHALLENGER') {
    return <Crown {...iconProps} />;
  }
  if (rank === 'GRANDMASTER' || rank === 'MASTER') {
    return <Trophy {...iconProps} />;
  }
  if (rank === 'DIAMOND' || rank === 'EMERALD') {
    return <Gem {...iconProps} />;
  }
  if (rank === 'PLATINUM' || rank === 'GOLD') {
    return <Sparkles {...iconProps} />;
  }

  return <Award {...iconProps} />;
};
