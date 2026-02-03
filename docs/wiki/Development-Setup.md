# Development Setup

This guide walks you through setting up TrynDraft for local development.

## Prerequisites

| Requirement | Version | Check Command |
|-------------|---------|---------------|
| Python | 3.12+ | `python --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| Git | Any | `git --version` |

## Automated Setup (Recommended)

The fastest way to get started:

```bash
# Clone the repository
git clone https://github.com/your-username/TrynDraft.git
cd TrynDraft

# Run the setup script (installs everything)
./scripts/setup-dev.sh

# Start both servers
./scripts/start-dev.sh
```

**That's it!** Open http://localhost:5173 in your browser.

### Available Scripts

| Script | Description |
|--------|-------------|
| `./scripts/setup-dev.sh` | Full development environment setup |
| `./scripts/start-dev.sh` | Start both backend and frontend servers |
| `./scripts/stop-dev.sh` | Stop all development servers |

---

## Manual Setup

If you prefer manual setup or the scripts don't work on your system:

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/TrynDraft.git
cd TrynDraft
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env with your settings (see Environment Variables below)

# Initialize database
python -c "from app.database import engine, Base; Base.metadata.create_all(bind=engine)"

# Seed champion data
python scripts/seed_champions.py

# Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: http://localhost:8000
API docs at: http://localhost:8000/docs

### 3. Frontend Setup

Open a new terminal:

```bash
cd frontend

# Install dependencies
npm install

# Create environment file
cp .env.example .env
# Edit if needed (usually defaults work)

# Start development server
npm run dev
```

Frontend will be available at: http://localhost:5173

## Environment Variables

### Backend (.env)

```bash
# Database (SQLite for development)
DATABASE_URL=sqlite:///./tryndraft.db

# Security (generate with: openssl rand -hex 32)
SECRET_KEY=your-secret-key-here

# LLM Configuration
USE_HUGGINGFACE_API=false    # Set to true only when needed (costs money!)
HF_TOKEN=your-huggingface-token

# Optional: Riot API (for stats scraping)
RIOT_API_KEY=your-riot-api-key

# CORS (comma-separated origins)
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

### Frontend (.env)

```bash
VITE_API_URL=http://localhost:8000
```

## Important Notes

### LLM API Costs

The HuggingFace API is **disabled by default** (`USE_HUGGINGFACE_API=false`) to prevent accidental charges during development. When disabled, the system uses a rule-based fallback that provides role-specific advice.

Only enable the API when you need real LLM responses:
```bash
USE_HUGGINGFACE_API=true
```

### Database

- **Development**: SQLite (zero configuration, file-based)
- **Production**: PostgreSQL (requires separate setup)

The SQLite database file (`tryndraft.db`) is created automatically in the backend directory.

### Running Tests

```bash
# Backend tests
cd backend
pytest
pytest --cov=app  # with coverage

# Frontend tests
cd frontend
npm test
npm run test:coverage  # with coverage
```

### Code Quality

```bash
# Frontend linting
cd frontend
npm run lint
npm run lint:fix  # auto-fix issues

# Backend formatting
cd backend
black app/
flake8 app/
```

## Common Issues

### "Module not found" errors (Python)
Ensure your virtual environment is activated:
```bash
source .venv/bin/activate  # macOS/Linux
```

### "CORS error" in browser
Check that your backend CORS_ORIGINS includes your frontend URL:
```bash
CORS_ORIGINS=http://localhost:5173
```

### Database migrations
If you change models, create a migration:
```bash
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

### Champion images not loading
Ensure you have internet access. Images load from Riot's Data Dragon CDN.

## Project Structure

```
TrynDraft/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    # API routes
│   │   ├── services/            # Business logic
│   │   ├── models.py            # Database models
│   │   └── main.py              # FastAPI app
│   ├── scripts/                 # Utility scripts
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── pages/               # Page components
│   │   ├── store/               # Zustand state
│   │   └── utils/               # Utilities
│   └── package.json
├── planning/                    # Project documentation
└── docs/                        # User documentation
```

## Next Steps

- Read the [User Guide](User-Guide) to understand how to use TrynDraft
- Review [Contributing](Contributing) guidelines before making changes
- Check [Branching Standards](Branching-Standards) for Git workflow

---

**Need help?** Open an issue on GitHub or ask in Discussions.
