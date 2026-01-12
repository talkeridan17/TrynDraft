# Frontend Architecture Documentation

**Last Updated:** 2026-01-11

---

## 1. Technology Stack

### Core Framework
- **React 19** - Latest with concurrent features
- **TypeScript** - Type safety and better IDE support
- **Vite** - Fast build tool and dev server

### State Management
- **Zustand** - Lightweight state management
  - Used for: Draft state, user settings, champion data
  - Persisted to localStorage for draft persistence
  - Simple API, no boilerplate

### Styling
- **TailwindCSS 3.4** - Utility-first CSS framework
  - Custom color palette (amber/gold accents)
  - Dark theme optimized
  - Responsive utilities

### Routing
- **React Router v6** - Client-side routing
  - Routes: `/draft`, `/profile`, `/login`, `/register`
  - Protected routes with auth checking

### HTTP Client
- **Axios** - Promise-based HTTP client
  - Configured with base URL
  - Request/response interceptors for auth
  - Automatic JWT token injection

---

## 2. Project Structure

```
frontend/
├── public/
│   └── vite.svg              # Favicon (to be replaced)
├── src/
│   ├── components/
│   │   ├── common/           # Reusable components
│   │   │   └── RoleIcon.tsx  # Role icon display
│   │   ├── drafting/         # Draft-specific components (unused currently)
│   │   └── layout/           # Layout components
│   │       └── Header.tsx    # App header with auth status
│   ├── pages/
│   │   ├── DraftPage.tsx     # Main draft interface (700+ lines)
│   │   ├── LoginPage.tsx     # Login form
│   │   ├── ProfilePage.tsx   # User profile/settings (empty)
│   │   └── RegisterPage.tsx  # Registration form (placeholder)
│   ├── store/
│   │   └── useDraftStore.ts  # Zustand store for draft state
│   ├── utils/
│   │   ├── api.ts            # Axios instance + API service functions
│   │   └── patch.ts          # Helper functions for patch data
│   ├── App.tsx               # Main app component with routes
│   ├── index.css             # Global styles + Tailwind imports
│   └── main.tsx              # React entry point
├── .env.example              # Environment variable template
├── package.json              # Dependencies
├── tailwind.config.js        # Tailwind configuration
├── tsconfig.json             # TypeScript configuration
└── vite.config.ts            # Vite configuration
```

---

## 3. State Management (Zustand)

### Draft Store (`useDraftStore.ts`)

**Purpose:** Manages all draft-related state (picks, bans, settings, turn tracking)

**State Structure:**
```typescript
interface DraftState {
  // Settings
  settings: {
    side: 'BLUE' | 'RED';
    role: RoleType;
    elo: string;
    region: string;
    patch: string;
  };

  // Turn tracking
  currentTurn: number;  // 0-19 (20 total turns), -1 when complete

  // Bans (5 per team)
  bans: {
    blue: string[];  // ["Aatrox", "Ahri", ...]
    red: string[];
  };

  // Picks (5 per team)
  picks: {
    blue: Pick[];  // [{ champion: "Aatrox", role: "TOP" }, ...]
    red: Pick[];
  };

  // Draft ID (for backend sync)
  draftId: string | null;

  // All available champions (loaded from API)
  allChampions: string[];

  // Actions
  setSettings(settings: Partial<Settings>): void;
  setCurrentTurn(turn: number): void;
  setBan(side: TeamSide, index: number, champion: string): void;
  setPick(side: TeamSide, index: number, pick: Pick): void;
  resetDraft(): void;
  loadChampions(): Promise<void>;
  getCurrentPicker(): { side: TeamSide; position: number; isBan: boolean } | null;
  getTakenChampions(): Set<string>;
  isChampionAvailable(champion: string): boolean;
}
```

**Persistence:**
```typescript
// Persisted to localStorage
persist(
  (set, get) => ({ /* state */ }),
  {
    name: 'tryndraft-draft-state',
    partialize: (state) => ({
      settings: state.settings,
      currentTurn: state.currentTurn,
      bans: state.bans,
      picks: state.picks,
      draftId: state.draftId,
      // Don't persist allChampions - fetch fresh every time
    }),
  }
)
```

**Key Functions:**

#### `getCurrentPicker()`
Returns which slot is currently active based on turn number.

Turn mapping:
- 0-4: User team bans
- 5-9: Enemy team bans
- 10-19: Picks (alternating, standard draft order)
  - 10: Blue pick 1
  - 11: Red pick 1
  - 12: Red pick 2
  - 13: Blue pick 2
  - etc.
- -1: Draft complete

#### `getTakenChampions()`
Returns Set of all already picked or banned champions for duplicate checking.

#### `isChampionAvailable(champion)`
Checks if champion is not banned and not already picked.

---

## 4. API Integration (`utils/api.ts`)

### Axios Configuration
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 10000,
});
```

### Request Interceptor (Auth)
```typescript
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});
```

### Response Interceptor (Error Handling)
```typescript
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Unauthorized - clear token and redirect to login
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

### Service Functions

#### Champion Service
```typescript
export const championService = {
  getAll: async (): Promise<string[]> => {
    // Fetches all champion names from backend
    // Falls back to Data Dragon if backend fails
    // Falls back to hardcoded list if Data Dragon fails
  },

  getImageUrl: async (championName: string): Promise<string> => {
    // Returns champion splash art URL
  },

  getRoleIcon: async (role: string): Promise<string> => {
    // Returns role icon URL from Community Dragon
  },

  getRankIcon: async (rank: string): Promise<string> => {
    // Returns rank emblem URL
  },

  getLatestVersion: async (): Promise<string> => {
    // Returns current patch version
  },
};
```

#### Auth Service
```typescript
export const authService = {
  login: async (username: string, password: string) => {
    // POST /users/login
    // Stores access_token in localStorage
  },

  register: async (userData: any) => {
    // POST /users/register
  },

  logout: () => {
    // Clear localStorage token
  },

  getCurrentUser: async () => {
    // GET /users/me
  },

  updateUser: async (userData: any) => {
    // PUT /users/me
  },

  // Champion Pool Management
  getChampionPool: async () => {
    // GET /users/me/champion-pool
  },

  addToChampionPool: async (championData) => {
    // POST /users/me/champion-pool
  },

  removeFromChampionPool: async (championName: string) => {
    // DELETE /users/me/champion-pool/{championName}
  },

  updateChampionProficiency: async (championName: string, proficiency: number) => {
    // PUT /users/me/champion-pool/{championName}
  },
};
```

#### Draft Service
```typescript
export const draftService = {
  create: async (draftData: any) => {
    // POST /drafts
  },

  get: async (draftId: string) => {
    // GET /drafts/{draftId}
  },

  update: async (draftId: string, draftData: any) => {
    // PUT /drafts/{draftId}
  },

  addBan: async (draftId: string, champion: string, side: string) => {
    // POST /drafts/{draftId}/ban
  },

  addPick: async (draftId: string, champion: string, role: string, side: string) => {
    // POST /drafts/{draftId}/pick
  },

  getUserDrafts: async () => {
    // GET /drafts (user's draft history)
  },

  getGameplan: async (draftState: any) => {
    // POST /llm/analyze
    // Returns LLM-generated strategic analysis
  },

  getStatistics: async (draftId: string) => {
    // GET /drafts/{draftId}/statistics
    // Returns win rates, matchup data, etc.
  },
};
```

---

## 5. Main Components

### DraftPage Component

**File:** `src/pages/DraftPage.tsx` (700+ lines - needs refactoring)

**Purpose:** Main draft interface where users build their draft

**Key Features:**
1. **Phase System** - BAN/PICK/DONE toggle with color coding
2. **Draft Boards** - Blue team (left), Red team (right)
3. **Champion Picker** - Center panel with search and filtering
4. **LLM Analysis Box** - Bottom panel, expands when draft complete
5. **Statistics Bar** - Shows when draft complete (placeholders)
6. **Settings Bar** - Top header with role/rank selection

**Local State:**
```typescript
const [latestPatch, setLatestPatch] = useState('16.1.1');
const [search, setSearch] = useState('');
const [draftPhase, setDraftPhase] = useState<'BAN' | 'PICK' | 'COMPLETE'>('BAN');
const [shouldAdvanceCursor, setShouldAdvanceCursor] = useState(false);
const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
const [draggedSide, setDraggedSide] = useState<'BLUE' | 'RED' | null>(null);
const [draggedIsBan, setDraggedIsBan] = useState(false);
const [hoveredSlot, setHoveredSlot] = useState<...>(null);
const [draggedChampion, setDraggedChampion] = useState<string | null>(null);

const manualPhaseChangeRef = useRef(false);  // Tracks manual phase changes
```

**Key Functions:**

#### `handleChampionSelect(champion: string)`
- Adds champion to currently active slot
- Advances cursor to next unfilled slot
- Updates Zustand store

#### `handleSlotClick(side, position, isBan)`
- Manually selects a draft slot
- If in COMPLETE phase, switches back to appropriate phase
- Sets currentTurn in store

#### `findNextUnfilledSlot()`
- Scans draft state to find next empty slot
- Follows official LoL draft order
- Sets turn to -1 if all slots filled

#### `handleDragStart(side, index, isBan)`
- Initiates drag operation
- Stores dragged slot information

#### `handleBanDrop(side, index)` / `handlePickDrop(side, index)`
- Handles drop onto ban/pick slots
- Swaps champions if source slot has one
- Validates team restrictions (can't pick from enemy bans)

**Phase Auto-Advancement:**
```typescript
useEffect(() => {
  // Skip if manual phase change
  if (manualPhaseChangeRef.current) {
    manualPhaseChangeRef.current = false;
    return;
  }

  const totalBans = /* count filled bans */;
  const totalPicks = /* count filled picks */;

  // Auto-switch to COMPLETE when all slots filled
  if (totalBans === 10 && totalPicks === 10 && draftPhase !== 'COMPLETE') {
    setDraftPhase('COMPLETE');
  }
  // Auto-switch to PICK when bans done
  else if (totalBans === 10 && totalPicks < 10 && draftPhase !== 'PICK') {
    setDraftPhase('PICK');
  }
  // Revert to BAN if unfilled bans
  else if (totalBans < 10 && draftPhase === 'PICK') {
    setDraftPhase('BAN');
  }
}, [bans, picks, draftPhase]);
```

**Performance Considerations:**
- Large component (700+ lines) - should be split
- Many re-renders on state changes
- Could benefit from `useMemo` for filtered champions
- Drag-and-drop state could be extracted to custom hook

---

### Header Component

**File:** `src/components/layout/Header.tsx`

**Purpose:** Top navigation bar with auth status

**Features:**
- Logo (links to /draft)
- Navigation links (Draft, Settings/Profile)
- User status display
  - If authenticated: username + "Authenticated" badge
  - If not: "Guest" + "Limited" badge
- Login/Logout button

**State:**
```typescript
const [isAuthenticated, setIsAuthenticated] = useState(false);
const [username, setUsername] = useState('');
```

**Auth Check:**
```typescript
useEffect(() => {
  const checkAuth = async () => {
    const token = localStorage.getItem('access_token');
    if (token) {
      setIsAuthenticated(true);
      try {
        const user = await authService.getCurrentUser();
        if (user) {
          setUsername(user.username || 'User');
        }
      } catch (error) {
        // Token invalid
        setIsAuthenticated(false);
        localStorage.removeItem('access_token');
      }
    }
  };
  checkAuth();
}, [location]);
```

---

### RoleIcon Component

**File:** `src/components/common/RoleIcon.tsx`

**Purpose:** Display role icons (TOP, JUNGLE, MID, ADC, SUPPORT)

**Implementation:**
```typescript
export const RoleIcon: React.FC<{ role: RoleType; size?: number; className?: string }> = ({
  role,
  size = 20,
  className = ''
}) => {
  const roleMap = {
    'TOP': 'top',
    'JUNGLE': 'jungle',
    'MID': 'middle',
    'ADC': 'bottom',
    'SUPPORT': 'utility',
    'FILL': 'fill'
  };

  const roleName = roleMap[role] || 'fill';
  const iconUrl = `https://raw.communitydragon.org/pbe/plugins/rcp-fe-lol-champ-select/global/default/svg/position-${roleName}.svg`;

  return <img src={iconUrl} alt={role} width={size} height={size} className={className} />;
};
```

---

### LoginPage Component

**File:** `src/pages/LoginPage.tsx`

**Purpose:** User authentication form

**Features:**
- Username/password inputs
- "Remember me" checkbox (unused)
- Login button
- Link to register page
- Error message display
- Redirects to /draft on successful login

**Implementation:**
```typescript
const handleSubmit = async (e: React.FormEvent) => {
  e.preventDefault();
  setError('');
  setLoading(true);

  try {
    await authService.login(username, password);
    navigate('/draft');
  } catch (err: any) {
    setError(err.response?.data?.detail || 'Login failed');
  } finally {
    setLoading(false);
  }
};
```

---

### ProfilePage Component

**File:** `src/pages/ProfilePage.tsx`

**Purpose:** User settings and champion pool management

**Current State:** Skeleton only (mostly empty)

**Planned Features:**
1. **User Info Section**
   - Display username, email
   - Edit profile button
   - Change password

2. **Champion Pool Management**
   - Multi-select champion picker
   - Proficiency ratings (1-5 stars) per champion
   - Role assignment per champion
   - Add/remove champions

3. **Preferences**
   - Preferred roles (drag to reorder)
   - Playstyle settings:
     - Aggressive ↔ Defensive (slider)
     - Early game ↔ Late game
     - Team fight ↔ Split push
   - Default rank for drafts

4. **Draft History**
   - List of past drafts
   - Click to view/analyze
   - Delete drafts

**Needs Implementation:** This is the NEXT PRIORITY

---

## 6. Styling System (TailwindCSS)

### Color Palette
```javascript
// tailwind.config.js
theme: {
  extend: {
    colors: {
      amber: {
        500: '#F59E0B',  // Main accent color
        600: '#D97706',
      },
      gray: {
        900: '#111827',  // Dark background
        800: '#1F2937',
        700: '#374151',
      },
    },
  },
}
```

### Common Patterns

**Button Styles:**
```tsx
// Primary button
<button className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-black font-medium rounded-lg transition-all">
  Button
</button>

// Secondary button
<button className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white font-medium rounded-lg transition-all border border-gray-700">
  Button
</button>
```

**Card Styles:**
```tsx
<div className="bg-gray-900 border border-gray-800 rounded-lg p-6">
  Card content
</div>
```

**Input Styles:**
```tsx
<input
  className="w-full px-4 py-2 bg-gray-950 border border-gray-800 rounded text-white text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
/>
```

---

## 7. Routing & Navigation

### Route Configuration
```typescript
// App.tsx
<BrowserRouter>
  <Routes>
    <Route path="/" element={<Navigate to="/draft" replace />} />
    <Route path="/draft" element={<DraftPage />} />
    <Route path="/profile" element={<ProfilePage />} />
    <Route path="/login" element={<LoginPage />} />
    <Route path="/register" element={<RegisterPage />} />
  </Routes>
</BrowserRouter>
```

**Protected Routes (TODO):**
```typescript
// Future: Wrap routes that require auth
<Route
  path="/profile"
  element={
    <ProtectedRoute>
      <ProfilePage />
    </ProtectedRoute>
  }
/>
```

---

## 8. Performance Optimizations (Needed)

### Current Issues
1. **Large component re-renders** - DraftPage re-renders on every state change
2. **No memoization** - Filtered champion list recalculated every render
3. **No code splitting** - All components loaded upfront
4. **No lazy loading** - All routes loaded immediately

### Recommended Optimizations

#### 1. Memoize Expensive Computations
```typescript
const filteredChampions = useMemo(() => {
  return allChampions.filter(champ =>
    champ.toLowerCase().includes(search.toLowerCase()) &&
    isChampionAvailable(champ)
  );
}, [allChampions, search, bans, picks]);
```

#### 2. Split DraftPage Component
```
DraftPage
├─ DraftHeader (settings bar)
├─ DraftBoard (team board)
│  ├─ BanSlots
│  └─ PickSlots
├─ ChampionPicker
└─ AnalysisPanel
```

#### 3. Lazy Load Routes
```typescript
const ProfilePage = lazy(() => import('./pages/ProfilePage'));
const LoginPage = lazy(() => import('./pages/LoginPage'));

<Routes>
  <Route path="/profile" element={<Suspense fallback={<Loading />}><ProfilePage /></Suspense>} />
</Routes>
```

#### 4. Virtualize Long Lists
```typescript
// Use react-window for champion picker (170 champions)
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={filteredChampions.length}
  itemSize={60}
>
  {({ index, style }) => (
    <ChampionItem champion={filteredChampions[index]} style={style} />
  )}
</FixedSizeList>
```

---

## 9. Testing Strategy (Not Implemented Yet)

### Unit Tests (Vitest)
```typescript
// useDraftStore.test.ts
describe('Draft Store', () => {
  it('should initialize with default state', () => {
    const { result } = renderHook(() => useDraftStore());
    expect(result.current.currentTurn).toBe(0);
    expect(result.current.bans.blue).toHaveLength(5);
  });

  it('should add ban correctly', () => {
    const { result } = renderHook(() => useDraftStore());
    act(() => {
      result.current.setBan('BLUE', 0, 'Aatrox');
    });
    expect(result.current.bans.blue[0]).toBe('Aatrox');
  });
});
```

### Component Tests (React Testing Library)
```typescript
// DraftPage.test.tsx
describe('DraftPage', () => {
  it('should render draft interface', () => {
    render(<DraftPage />);
    expect(screen.getByText('Blue Team')).toBeInTheDocument();
    expect(screen.getByText('Red Team')).toBeInTheDocument();
  });

  it('should select champion when clicked', async () => {
    render(<DraftPage />);
    const champion = screen.getByText('Aatrox');
    fireEvent.click(champion);
    await waitFor(() => {
      expect(screen.getByTestId('ban-slot-0')).toHaveTextContent('Aatrox');
    });
  });
});
```

### E2E Tests (Playwright)
```typescript
// draft.spec.ts
test('complete draft flow', async ({ page }) => {
  await page.goto('/draft');

  // Ban phase
  await page.click('text=Aatrox');
  await page.click('text=Ahri');
  // ... ban 10 champions

  // Verify switched to pick phase
  await expect(page.locator('.phase-toggle')).toHaveText('PICK');

  // Pick phase
  await page.click('text=Jinx');
  // ... pick 10 champions

  // Verify draft complete
  await expect(page.locator('.phase-toggle')).toHaveText('DONE');
  await expect(page.locator('.statistics-bar')).toBeVisible();
});
```

---

## 10. Future Improvements

### Short Term (Next 2 Weeks)
- [ ] Implement Profile/Settings page
- [ ] Add loading skeletons during API calls
- [ ] Add toast notifications for actions
- [ ] Refactor DraftPage into smaller components
- [ ] Add error boundaries

### Medium Term (1-2 Months)
- [ ] Add keyboard shortcuts (Undo, Search, Quick pick)
- [ ] Add tooltips with champion info on hover
- [ ] Implement draft history page
- [ ] Add mobile responsive design
- [ ] Optimize performance (memoization, lazy loading)

### Long Term (3+ Months)
- [ ] Multi-user live drafts (WebSocket)
- [ ] Advanced analytics dashboard
- [ ] Draft replay/review system
- [ ] Integration with Riot LCU API (local client)
- [ ] Voice commands for hands-free drafting

---

**Last Updated:** 2026-01-11
**Author:** Claude AI Assistant
**Version:** 0.3.0-alpha
