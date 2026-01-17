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

**Current Version:** 0.4.0-alpha  
**Last Updated:** 2026-01-16

---

## What is TrynDraft?

TrynDraft is an intelligent drafting assistant for League of Legends that combines multiple AI technologies to provide optimal draft recommendations:

- **Neural Network**: 50-feature PyTorch model analyzing champion statistics, matchups, synergies, and team compositions
- **LLM Analysis**: Strategic commentary and gameplans powered by Mistral 7B
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

### User Profiles & Champion Pools
- Save your champion pool with proficiency ratings
- Set your main role and rank for tailored recommendations
- Profile picture customization with champion splash art
- Preferences auto-populate when entering draft

### Draft Interface
- Clean, intuitive drag-and-drop interface
- Ban and pick phases with visual indicators
- Phase toggle (BAN/PICK/COMPLETE)
- Guest mode for quick access without account

---

## Tech Stack

### Frontend
- React 19 + TypeScript + Vite
- Zustand (state management)
- TailwindCSS + Lucide Icons
- Axios for API calls

### Backend
- FastAPI (Python 3.12)
- SQLAlchemy 2.0 + SQLite/PostgreSQL
- JWT Authentication (bcrypt)
- PyTorch for neural network
- HuggingFace Inference API (Mistral 7B)

### Data & ML
- Riot API (champion stats, match data)
- Data Dragon (champion images, icons)
- Community Dragon (role/rank icons)
- PyTorch Neural Network (50-feature model)

### Deployment
- Docker + docker-compose
- Nginx reverse proxy
- PostgreSQL + Redis (production)
- Environment-based configuration

---

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+
- Docker & Docker Compose (for production)

### 1. Clone the Repository
```bash
git clone https://github.com/talkeridan17/TrynDraft.git
cd TrynDraft
```

### 2. Set Up Environment Variables
```bash
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit `backend/.env`:
```bash
SECRET_KEY=<generate-with: openssl rand -hex 32>
DATABASE_URL=sqlite:///./tryndraft.db
RIOT_API_KEY=<your-riot-api-key>  # Optional
HF_TOKEN=<your-huggingface-token>  # Optional
```

### 3. Start Backend
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

### 4. Start Frontend
```bash
cd frontend
npm install
npm run dev
```

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## Docker Deployment

```bash
# Build and start all services
docker-compose up -d --build

# Run migrations
docker-compose exec backend alembic upgrade head

# Seed champion data
docker-compose exec backend python scripts/seed_champions.py
```

---

## Project Structure

```
TrynDraft/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    # API routes
│   │   ├── core/                # Configuration
│   │   ├── services/            # Business logic
│   │   ├── models.py            # Database models
│   │   └── schemas.py           # Pydantic schemas
│   ├── scripts/                 # Utility scripts
│   └── requirements.txt
├── frontend/
│   ├── public/                  # Static assets
│   │   └── logo.svg             # TrynDraft logo
│   └── src/
│       ├── components/          # React components
│       ├── pages/               # Page components
│       ├── store/               # Zustand store
│       └── utils/               # Utilities
├── docs/                        # Documentation
├── planning/                    # Planning documents
└── docker-compose.yml
```

---

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Submit a pull request

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
