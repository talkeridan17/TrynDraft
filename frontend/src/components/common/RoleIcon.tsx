interface RoleIconProps {
  role: 'TOP' | 'JUNGLE' | 'MID' | 'ADC' | 'SUPPORT' | 'FILL';
  size?: number;
  className?: string;
}

export const RoleIcon: React.FC<RoleIconProps> = ({ role, size = 20, className = '' }) => {
  const roleMap: Record<string, string> = {
    'TOP': 'top',
    'JUNGLE': 'jungle',
    'MID': 'middle',
    'ADC': 'bottom',
    'SUPPORT': 'utility',
    'FILL': 'fill'
  };

  const roleName = roleMap[role] || 'fill';
  const iconUrl = `https://raw.communitydragon.org/pbe/plugins/rcp-fe-lol-champ-select/global/default/svg/position-${roleName}.svg`;

  return (
    <img
      src={iconUrl}
      alt={role}
      width={size}
      height={size}
      className={className}
      style={{ width: size, height: size }}
    />
  );
};
