import { useState, useEffect } from 'react';

interface RoleIconProps {
  role: string;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const RoleIcon: React.FC<RoleIconProps> = ({ role, size = 'md', className = '' }) => {
  const [iconUrl, setIconUrl] = useState<string>('');
  const [showFallback, setShowFallback] = useState(false);
  
  const sizeClasses = {
    sm: 'w-4 h-4',
    md: 'w-6 h-6',
    lg: 'w-8 h-8',
  };

  useEffect(() => {
    // TODO: Fetch actual icon from backend
    setIconUrl('');
  }, [role]);

  if (showFallback || !iconUrl) {
    return (
      <div className={`${sizeClasses[size]} flex items-center justify-center bg-gray-700 rounded font-bold text-white ${className}`}>
        {role.charAt(0)}
      </div>
    );
  }

  return (
    <img
      src={iconUrl}
      alt={role}
      className={`${sizeClasses[size]} ${className}`}
      onError={() => setShowFallback(true)}
    />
  );
};