import { X, Shield, Sword, GripVertical } from 'lucide-react';
import { useState, useEffect } from 'react';
import { championService } from '../../utils/api';

interface TeamDisplayProps {
  side: 'BLUE' | 'RED';
  picks: Array<{ champion: string; role: string }>;
  bans: string[];
  phase: 'BAN' | 'PICK';
  isUserSide: boolean;
  onSelectChampion: (position: number) => void;
  onRemovePick: (position: number) => void;
  onMovePick: (fromIndex: number, toIndex: number) => void;
  onRemoveBan: (ban: string) => void;
  currentPicker?: {
    side: 'BLUE' | 'RED';
    position: number;
  };
}

export const TeamDisplay: React.FC<TeamDisplayProps> = ({
  side,
  picks,
  bans,
  phase,
  isUserSide,
  currentPicker,
  onSelectChampion,
  onRemovePick,
  onMovePick,
  onRemoveBan,
}) => {
  const [draggingIndex, setDraggingIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [roleIcons, setRoleIcons] = useState<Record<string, string>>({});
  const [championImages, setChampionImages] = useState<Record<string, string>>({});

  const isBlue = side === 'BLUE';
  const sideColor = isBlue ? 'border-blue-500/40' : 'border-red-500/40';
  const glowColor = isBlue ? 'shadow-[0_0_30px_rgba(59,130,246,0.3)]' : 'shadow-[0_0_30px_rgba(239,68,68,0.3)]';

  // Load role icons
  useEffect(() => {
    const loadRoleIcons = async () => {
      const icons: Record<string, string> = {};
      const roles = ['TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT', 'FILL'];
      
      for (const role of roles) {
        try {
          const icon = await championService.getRoleIcon(role);
          icons[role] = icon;
        } catch (error) {
          console.error(`Failed to load icon for role ${role}:`, error);
        }
      }
      
      setRoleIcons(icons);
    };
    
    loadRoleIcons();
  }, []);

  // Load champion images
  useEffect(() => {
    const loadChampionImages = async () => {
      const images: Record<string, string> = {};
      
      // Load images for picks
      for (const pick of picks) {
        if (pick.champion && !images[pick.champion]) {
          try {
            const url = await championService.getImageUrl(pick.champion);
            images[pick.champion] = url;
          } catch (error) {
            console.error(`Failed to load image for ${pick.champion}:`, error);
          }
        }
      }
      
      // Load images for bans
      for (const ban of bans) {
        if (ban && !images[ban]) {
          try {
            const url = await championService.getImageUrl(ban);
            images[ban] = url;
          } catch (error) {
            console.error(`Failed to load image for ban ${ban}:`, error);
          }
        }
      }
      
      setChampionImages(images);
    };
    
    loadChampionImages();
  }, [picks, bans]);

  const getChampionImage = (championName: string) => {
    return championImages[championName] || `https://ddragon.leagueoflegends.com/cdn/14.4.1/img/champion/${championName.replace(/[^a-zA-Z]/g, '')}.png`;
  };

  const getRoleIcon = (role: string) => {
    return roleIcons[role] || role.charAt(0);
  };

  const handleDragStart = (e: React.DragEvent, index: number) => {
    if (!picks[index].champion) return;
    setDraggingIndex(index);
    e.dataTransfer.setData('text/plain', index.toString());
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    setDragOverIndex(index);
  };

  const handleDragLeave = () => {
    setDragOverIndex(null);
  };

  const handleDrop = (e: React.DragEvent, dropIndex: number) => {
    e.preventDefault();
    const dragIndex = parseInt(e.dataTransfer.getData('text/plain'));
    
    if (!isNaN(dragIndex) && dragIndex !== dropIndex && picks[dragIndex].champion) {
      onMovePick(dragIndex, dropIndex);
    }
    
    setDraggingIndex(null);
    setDragOverIndex(null);
  };

  const handleImageError = (e: React.SyntheticEvent<HTMLImageElement>, text: string) => {
    const target = e.target as HTMLImageElement;
    target.style.display = 'none';
    const fallback = document.createElement('div');
    fallback.className = 'w-full h-full flex items-center justify-center bg-gradient-to-br from-primary-600/30 to-secondary-600/30 rounded-lg font-bold text-white';
    fallback.textContent = text.substring(0, 2);
    if (target.parentNode) {
      target.parentNode.appendChild(fallback);
    }
  };

  const showBans = phase === 'PICK' && bans.length > 0;

  return (
    <div className={`relative border-2 ${sideColor} rounded-2xl p-4 ${isUserSide ? glowColor : ''} h-full`}>
      {/* Side Indicator */}
      <div className="absolute -top-3 left-4">
        <div className={`flex items-center space-x-2 px-3 py-1 rounded-full ${isBlue ? 'bg-blue-900/80' : 'bg-red-900/80'}`}>
          {isBlue ? <Shield size={14} className="text-blue-300" /> : <Sword size={14} className="text-red-300" />}
          <span className={`text-sm font-medium ${isBlue ? 'text-blue-300' : 'text-red-300'}`}>
            {side} {isUserSide && '(You)'} • {phase}
          </span>
        </div>
      </div>

      {/* Bans Display with Images */}
      {showBans && (
        <div className="mb-4">
          <div className="text-xs text-gray-400 mb-2">Bans ({bans.length}/5):</div>
          <div className="flex flex-wrap gap-2">
            {bans.map((ban, index) => (
              <div key={index} className="relative group">
                <div className="flex items-center px-2 py-1.5 bg-white/5 rounded-lg group hover:bg-white/10 transition-colors">
                  <div className="w-6 h-6 rounded overflow-hidden mr-2">
                    <img
                      src={getChampionImage(ban)}
                      alt={ban}
                      className="w-full h-full object-cover opacity-50"
                      onError={(e) => handleImageError(e, ban)}
                    />
                  </div>
                  <span className="text-sm text-gray-300">{ban}</span>
                </div>
                {isUserSide && (
                  <button
                    onClick={() => onRemoveBan(ban)}
                    className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-white text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-600"
                    title="Remove ban"
                  >
                    ×
                  </button>
                )}
              </div>
            ))}
            {bans.length < 5 && isUserSide && (
              <div className="text-xs text-gray-500 italic">
                {5 - bans.length} more bans available
              </div>
            )}
          </div>
        </div>
      )}

      {/* Picks */}
      <div className="space-y-2">
        {picks.map((pick, index) => {
          const isDragging = draggingIndex === index;
          const isDragOver = dragOverIndex === index;
          const isCurrentPick = currentPicker && 
            currentPicker.side === side && 
            currentPicker.position === index;

          return (
            <div
              key={index}
              className={`flex items-center justify-between p-3 rounded-xl transition-all relative cursor-pointer ${
                pick.champion
                  ? 'bg-white/5 hover:bg-white/10'
                  : 'bg-white/2 hover:bg-white/5 border-2 border-dashed border-white/20'
              } ${isDragging ? 'opacity-50' : ''} ${isDragOver ? 'ring-2 ring-primary-500' : ''}
              ${isCurrentPick ? 'ring-2 ring-yellow-500 ring-offset-2 ring-offset-gray-900 animate-pulse' : ''}`}
              onClick={() => !pick.champion && onSelectChampion?.(index)}
              draggable={isUserSide && !!pick.champion}
              onDragStart={(e) => handleDragStart(e, index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, index)}
            >
              {/* Current picker indicator */}
              {isCurrentPick && (
                <div className="absolute -top-2 -right-2 w-4 h-4 bg-yellow-500 rounded-full animate-pulse"></div>
              )}

              <div className="flex items-center space-x-3 w-full">
                {/* Drag Handle */}
                {isUserSide && pick.champion && (
                  <div className="cursor-grab active:cursor-grabbing">
                    <GripVertical size={16} className="text-gray-500" />
                  </div>
                )}

                {/* Role Badge with Icon */}
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${
                  pick.role === 'FILL' 
                    ? 'bg-gray-700/50' 
                    : isBlue ? 'bg-blue-500/20' : 'bg-red-500/20'
                }`}>
                  <div className="w-6 h-6 flex items-center justify-center text-lg">
                    {getRoleIcon(pick.role)}
                  </div>
                </div>

                {/* Champion Display */}
                <div className="min-w-0 flex-1">
                  {pick.champion ? (
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-lg overflow-hidden">
                        <img
                          src={getChampionImage(pick.champion)}
                          alt={pick.champion}
                          className="w-full h-full object-cover"
                          onError={(e) => handleImageError(e, pick.champion)}
                        />
                      </div>
                      <div>
                        <div className="font-semibold text-white">{pick.champion}</div>
                        <div className="text-xs text-gray-400">Position {index + 1} • {pick.role}</div>
                      </div>
                    </div>
                  ) : (
                    <div className="text-gray-500 text-center">
                      {isCurrentPick ? 'Click to pick champion' : 'Empty slot'}
                    </div>
                  )}
                </div>
              </div>

              {/* Remove button for filled slots */}
              {isUserSide && pick.champion && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onRemovePick(index);
                  }}
                  className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-400/10 rounded-lg ml-2"
                  title="Remove champion"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};