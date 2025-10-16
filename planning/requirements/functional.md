# Functional Requirements (EARS Format)

## System Mode Management

**WHILE** the system is operational,  
**WHEN** the user selects a game mode,  
**THE SYSTEM SHALL** apply the corresponding color scheme:

- Swift mode: #00CC00 (green)
- Draft mode: #0066FF (blue)
- Ranked mode: #FF4444 (red)
- ARAM mode: #FFAA00 (yellow)
- Flex mode: #8844FF (purple)
- Clash mode: #FF6600 (orange)
- Custom mode: #888888 (gray)
- Pro mode: #000000 (black)

**WHEN** the system starts,  
**THE SYSTEM SHALL** automatically detect the current game patch.

## Draft State Management

**WHILE** in a draft session,  
**WHEN** a pick or ban occurs,  
**THE SYSTEM SHALL** update the current draft state in real-time.

**WHEN** opponent data is publicly available,  
**THE SYSTEM SHALL** retrieve and display opponent win rates and champion history.

## User Management

**WHEN** a user accesses the system for the first time,  
**THE SYSTEM SHALL** provide guest access with default settings.

**WHEN** a user creates an account,  
**THE SYSTEM SHALL** persist user preferences and champion pools.

**WHEN** a user authenticates with Riot credentials,  
**THE SYSTEM SHALL** automatically import relevant game data.

## Recommendation Engine

**WHILE** in draft phase,  
**WHEN** enemy champions are selected,  
**THE SYSTEM SHALL** provide champion recommendations based on:

- 1v1 matchup win rates (±5% accuracy)
- Team composition synergy scores
- Current meta tier lists (updated per patch)
- User's champion proficiency

**THE SYSTEM SHALL** calculate and display team composition metrics including:

- AD/AP ratio balance
- Crowd Control score
- Early/Late game composition analysis
- Frontline/Backline distribution
