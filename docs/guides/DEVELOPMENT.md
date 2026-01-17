# TrynDraft Development Guide

## Development Environment Setup

### Prerequisites
- Python 3.12+
- Node.js 18+
- Git

### Backend Setup
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend Setup
```bash
cd frontend
npm install
```

### Environment Variables
Copy the example files:
```bash
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

---

## Running the Application

### Backend
```bash
cd backend
source .venv/bin/activate
python -m uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm run dev
```

---

## Project Architecture

### Backend Structure
```
backend/
├── app/
│   ├── api/v1/endpoints/   # REST API endpoints
│   │   ├── champions.py    # Champion data
│   │   ├── drafts.py       # Draft sessions
│   │   ├── llm.py          # AI analysis
│   │   └── users.py        # User management
│   ├── core/
│   │   └── config.py       # App configuration
│   ├── services/
│   │   ├── data_dragon.py  # Riot Data Dragon API
│   │   ├── draft_logic.py  # Draft recommendations
│   │   └── llm_service.py  # LLM integration
│   ├── models.py           # SQLAlchemy models
│   ├── schemas.py          # Pydantic schemas
│   └── auth.py             # JWT authentication
└── scripts/                # Utility scripts
```

### Frontend Structure
```
frontend/src/
├── components/
│   ├── common/             # Shared components
│   ├── drafting/           # Draft-specific components
│   └── layout/             # Header, Layout
├── pages/
│   ├── DraftPage.tsx       # Main draft interface
│   ├── ProfilePage.tsx     # User settings
│   └── LoginPage.tsx       # Authentication
├── store/
│   └── useDraftStore.ts    # Zustand state management
└── utils/
    ├── api.ts              # API client
    └── patch.ts            # Version utilities
```

---

## Database

### Models
- **User**: Account information, authentication
- **UserPreferences**: Role, rank, profile picture
- **UserChampionPool**: Champion pool with proficiency
- **Champion**: Champion data from Data Dragon
- **Draft**: Draft session state

### Migrations
```bash
cd backend
alembic revision --autogenerate -m "description"
alembic upgrade head
```

---

## API Development

### Adding a New Endpoint
1. Create or edit file in `backend/app/api/v1/endpoints/`
2. Define Pydantic schemas in `schemas.py`
3. Add route to `backend/app/api/v1/__init__.py`
4. Update API documentation

### Authentication
Use the `get_current_user` dependency:
```python
from app.auth import get_current_user

@router.get("/protected")
async def protected_route(current_user = Depends(get_current_user)):
    return {"user": current_user.username}
```

---

## Frontend Development

### State Management
Using Zustand for global state:
```typescript
import { useDraftStore } from '../store/useDraftStore';

const { settings, setSettings } = useDraftStore();
```

### API Calls
Using the centralized API client:
```typescript
import { authService, championService } from '../utils/api';

const user = await authService.getCurrentUser();
const champions = await championService.getAll();
```

---

## Testing

### Backend Tests
```bash
cd backend
pytest tests/ -v
```

### Frontend Tests
```bash
cd frontend
npm test
```

---

## Code Style

### Python
- Use Black for formatting
- Follow PEP 8
- Type hints for all functions

### TypeScript
- ESLint + Prettier
- Functional components with hooks
- Proper typing (no `any` where avoidable)
