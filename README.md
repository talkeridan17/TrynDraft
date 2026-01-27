# TrynDraft - AI-Powered League of Legends Drafting Assistant

> Smart drafting tool with neural network recommendations, LLM-powered strategic analysis, and real-time champion statistics.

<p align="center">
  <img src="frontend/public/logo.svg" alt="TrynDraft Logo" width="80" height="80" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Status-Alpha_Development-yellow" alt="Status"/>
  <img src="https://img.shields.io/badge/Python-3.12-blue" alt="Python"/>
  <img src="https://img.shields.io/badge/React-19-blue" alt="React"/>
  <img src="https://img.shields.io/badge/FastAPI-Latest-teal" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/TypeScript-5.6-blue" alt="TypeScript"/>
  <img src="https://img.shields.io/badge/TailwindCSS-3.4-06B6D4" alt="TailwindCSS"/>
</p>

**Current Version:** 0.5.0-alpha
**Last Updated:** 2026-01-26

---

## What is TrynDraft?

TrynDraft is an intelligent drafting assistant for League of Legends that combines multiple AI technologies to provide optimal draft recommendations:

- **Neural Network**: 50-feature PyTorch model analyzing champion statistics, matchups, synergies, and team compositions
- **LLM Analysis**: Strategic commentary and gameplans powered by Qwen2.5-72B (via HuggingFace)
- **Real-time Stats**: Live champion data from Riot API including win rates, pick rates, and matchup data
- **User Profiles**: Personalized recommendations based on your champion pool and preferences

---

## Key Features

### AI-Powered Recommendations
- 50-feature neural network evaluating champions based on:
  - Base stats (attack, defense, magic, difficulty)
  - Meta statistics (win rate, pick rate, ban rate)
  - User proficiency and champion pool
  - Matchup win rates against enemy picks
  - Synergy with ally picks
  - Team composition balance

### LLM Strategic Analysis
- Real-time analysis at every draft stage
- Team power assessment with advantage calculator
- Strategic gameplans for both Blue and Red teams
- Win conditions and composition analysis
- Role-specific recommendations (e.g., jungle bans suggest jungle champions)

### User Profiles & Champion Pools
- Save your champion pool with proficiency ratings (1-5 stars)
- Set your main role and rank for tailored recommendations
- Profile picture customization with champion splash art
- Preferences auto-populate when entering draft

### Draft Interface
- Clean, intuitive drag-and-drop interface
- Ban and pick phases with visual indicators
- Clickable champion suggestions in LLM analysis
- Guest mode for quick access without account
- Game mode selection (Ranked/Clash/Pro)

---

## Tech Stack

### Frontend
- React 19 + TypeScript + Vite
- Zustand (state management with persist middleware)
- TailwindCSS + Lucide Icons
- Axios for API calls

### Backend
- FastAPI (Python 3.12)
- SQLAlchemy 2.0 + SQLite (dev) / PostgreSQL (prod)
- JWT Authentication (bcrypt + python-jose)
- PyTorch for neural network
- HuggingFace Inference API (Qwen2.5-72B)

### Data & ML
- Riot API (champion stats, match data)
- Data Dragon (champion images, icons)
- Community Dragon (role/rank icons)
- PyTorch Neural Network (50-feature model)
- BeautifulSoup + aiohttp (web scraping for training data)

### Deployment
- Docker + docker-compose
- Nginx reverse proxy
- PostgreSQL + Redis (production)
- Environment-based configuration

---

## Developer Setup (New Contributors)

### Prerequisites
- Python 3.12+
- Node.js 18+ (recommend using nvm)
- Git
- Docker & Docker Compose (optional, for production testing)

### 1. Clone the Repository
```bash
git clone https://github.com/talkeridan17/TrynDraft.git
cd TrynDraft
```

### 2. Backend Setup
```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from example or create new)
cat > .env << 'EOF'
# Database (SQLite for local development)
DATABASE_URL=sqlite:///./tryndraft.db

# Security - generate your own secret key
SECRET_KEY=your-secret-key-change-me

# Riot API (optional - get from developer.riotgames.com)
RIOT_API_KEY=your-riot-api-key

# HuggingFace (optional - disabled by default to avoid charges)
HF_TOKEN=your-huggingface-token
USE_HUGGINGFACE_API=false  # Set to true when ready for production

# CORS origins
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]

# Debug mode
DEBUG=True
EOF

# Initialize database
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)"

# Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Create .env file
echo "VITE_API_URL=http://localhost:8000" > .env

# Start development server
npm run dev
```

### 4. Access the Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs (Swagger UI)
- **Alternative API Docs**: http://localhost:8000/redoc (ReDoc)

### 5. Seed Initial Data (Optional)
```bash
cd backend
source .venv/bin/activate

# Sync champions from Data Dragon
python scripts/seed_champions.py
```

---

## Development Workflow

### Branch Strategy
- `main` - Production-ready code
- `dev` - Development branch (merge PRs here)
- Feature branches: `feature/your-feature-name`
- Bug fixes: `fix/bug-description`

### Running Tests
```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Style
- **Python**: Follow PEP 8, use type hints
- **TypeScript**: ESLint + Prettier (configured)
- **Commits**: Use conventional commits (feat:, fix:, docs:, etc.)

### Common Commands
```bash
# Backend
cd backend && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000  # Start server
alembic upgrade head                        # Run migrations
alembic revision --autogenerate -m "msg"    # Create migration

# Frontend
cd frontend
npm run dev          # Start dev server
npm run build        # Production build
npm run lint         # Run ESLint
```

---

## Environment Variables Reference

### Backend (.env)
| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | Database connection string |
| `SECRET_KEY` | Yes | JWT signing key (generate with `openssl rand -hex 32`) |
| `RIOT_API_KEY` | No | Riot API key for live data |
| `HF_TOKEN` | No | HuggingFace API token for LLM |
| `USE_HUGGINGFACE_API` | No | Enable/disable HuggingFace API (default: false) |
| `CORS_ORIGINS` | No | Allowed CORS origins (JSON array) |
| `DEBUG` | No | Enable debug mode (default: false) |
| `REDIS_URL` | No | Redis URL for caching (production) |

### Frontend (.env)
| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | Yes | Backend API URL |

---

## Project Structure

```
TrynDraft/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    # API routes (users, champions, drafts, etc.)
│   │   ├── core/                # Configuration (settings, security)
│   │   ├── services/            # Business logic
│   │   │   ├── llm_service.py   # LLM analysis & scraping
│   │   │   ├── llm_prompts.py   # Prompt templates
│   │   │   ├── draft_nn_service.py  # Neural network
│   │   │   └── data_dragon.py   # Riot data fetching
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── auth.py              # JWT authentication
│   │   └── database.py          # Database connection
│   ├── alembic/                 # Database migrations
│   ├── scripts/                 # Utility scripts
│   ├── logs/                    # Log files (gitignored)
│   └── requirements.txt
├── frontend/
│   ├── public/                  # Static assets
│   │   └── logo.svg             # TrynDraft logo
│   └── src/
│       ├── components/          # React components
│       │   ├── common/          # Shared components
│       │   ├── drafting/        # Draft-specific components
│       │   └── layout/          # Layout components
│       ├── pages/               # Page components
│       │   ├── DraftPage.tsx    # Main draft interface
│       │   ├── ProfilePage.tsx  # User profile
│       │   ├── SettingsPage.tsx # Game settings
│       │   └── LoginPage.tsx    # Authentication
│       ├── store/               # Zustand store
│       │   └── useDraftStore.ts # Draft state management
│       └── utils/               # Utilities
│           ├── api.ts           # API client
│           └── patch.ts         # Data Dragon helpers
├── planning/                    # Planning documents
│   ├── research/                # Technical research
│   ├── requirements/            # Feature requirements
│   └── user-stories/            # User stories
├── logs/                        # Scraper logs (gitignored)
├── docker-compose.yml           # Docker deployment
├── SECURITY.md                  # Security documentation
└── README.md                    # This file
```

---

## Docker Deployment (Production)

```bash
# Build and start all services
docker-compose up -d --build

# Run migrations
docker-compose exec backend alembic upgrade head

# Seed champion data
docker-compose exec backend python scripts/seed_champions.py

# View logs
docker-compose logs -f backend
docker-compose logs -f frontend
```

---

## Troubleshooting

### Common Issues

**Backend won't start:**
- Check Python version: `python --version` (need 3.12+)
- Ensure virtual environment is activated
- Check `.env` file exists and has valid values

**Frontend won't start:**
- Check Node version: `node --version` (need 18+)
- Run `npm install` to ensure dependencies are installed
- Check `VITE_API_URL` in `.env`

**Database errors:**
- Delete `tryndraft.db` and restart to recreate
- Run migrations: `alembic upgrade head`

**HuggingFace billing:**
- Set `USE_HUGGINGFACE_API=false` in backend `.env` to use rule-based analysis (free)
- Only enable when ready for production testing

**CORS errors:**
- Check `CORS_ORIGINS` in backend `.env` includes your frontend URL

---

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch from `dev`
3. Make your changes
4. Write/update tests
5. Submit a pull request to `dev`

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

## Disclaimer

TrynDraft isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing League of Legends. League of Legends and Riot Games are trademarks or registered trademarks of Riot Games, Inc.

---

## Acknowledgments

- **Riot Games** for the Riot API and Data Dragon
- **HuggingFace** for LLM inference API
- **Community Dragon** for champion and role icons
- **MOBAFire** and **LoLalytics** for community data

---

**Built by [Idan Talker](https://github.com/talkeridan17)**
