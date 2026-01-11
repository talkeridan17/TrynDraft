# TrynDraft - AI-Powered League of Legends Drafting Assistant

> Smart drafting tool with neural network recommendations, LLM-powered continuous commentary, and real-time champion statistics.

<img src="https://img.shields.io/badge/Status-Production_Ready-brightgreen" alt="Status"/> <img src="https://img.shields.io/badge/Python-3.12-blue" alt="Python"/> <img src="https://img.shields.io/badge/React-19-blue" alt="React"/> <img src="https://img.shields.io/badge/FastAPI-Latest-teal" alt="FastAPI"/>

---

## 🎯 What is TrynDraft?

TrynDraft is an intelligent drafting assistant for League of Legends that combines multiple AI technologies to provide the best possible draft recommendations:

- **Neural Network (50-feature PyTorch model)**: Analyzes champion statistics, matchups, synergies, and team compositions to score champions
- **LLM Commentary (Mistral 7B)**: Provides continuous strategic analysis throughout the draft with gameplans for both teams
- **Real-time Champion Stats**: Scraped from Riot API with win rates, pick rates, ban rates, and matchup data
- **User Champion Pool**: Personalized recommendations based on your proficiency and playstyle

---

## ✨ **Key Features**

### 🤖 **AI-Powered Recommendations**
- **50-feature Neural Network** evaluates champions based on:
  - Base stats (attack, defense, magic, difficulty)
  - Meta statistics (win rate, pick rate, ban rate)
  - User proficiency and champion pool
  - Matchup win rates against enemy picks
  - Synergy with ally picks
  - Team composition balance

### 💬 **Continuous LLM Commentary**
- **Real-time analysis** at every stage of the draft
- **Team power assessment** with advantage calculator
- **Strategic gameplans** for both Blue and Red teams
- **Win conditions** and composition strengths/weaknesses
- Fine-tunable on MOBAFire/LoLalytics text data

### 📊 **Live Champion Statistics**
- Riot API integration for up-to-date champion data
- Win rates, pick rates, ban rates per patch
- Matchup statistics (champion vs champion)
- Synergy data (best teammates)
- Role-specific performance metrics

### 👤 **User Profiles & Champion Pools**
- Save your champion pool with proficiency ratings
- Recommendations filtered to champions you can play
- Track your draft history
- Customizable preferences (role, elo, playstyle)

---

## 🛠️ **Tech Stack**

**Frontend:**
- React 19 + TypeScript + Vite
- Zustand (state management)
- TailwindCSS + Lucide Icons
- Axios for API calls

**Backend:**
- FastAPI (Python 3.12)
- SQLAlchemy 2.0 + PostgreSQL/SQLite
- JWT Authentication (bcrypt)
- PyTorch for neural network
- HuggingFace Inference API (Mistral 7B)

**Data & ML:**
- Riot API (champion stats, match data)
- BeautifulSoup (web scraping MOBAFire, LoLalytics)
- PyTorch Neural Network (50-feature model)
- LLM fine-tuning on scraped textual data

**Deployment:**
- Docker + docker-compose
- Nginx reverse proxy
- PostgreSQL + Redis
- Environment-based configuration

---

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.12+
- Node.js 18+
- Docker & Docker Compose (for production)
- Riot API Key (optional, for live stats)
- HuggingFace API Token (optional, for LLM)

### **1. Clone the Repository**
```bash
git clone https://github.com/talkeridan17/TrynDraft.git
cd TrynDraft
```

### **2. Set Up Environment Variables**

Create `.env` files from examples:
```bash
# Root directory
cp .env.example .env

# Backend
cp backend/.env.example backend/.env

# Frontend
cp frontend/.env.example frontend/.env
```

**Edit `backend/.env`** with your secrets:
```bash
SECRET_KEY=<generate-with: openssl rand -hex 32>
DATABASE_URL=sqlite:///./tryndraft.db  # or PostgreSQL URL
REDIS_URL=redis://localhost:6379
RIOT_API_KEY=<your-riot-api-key>  # Get from https://developer.riotgames.com
HF_TOKEN=<your-huggingface-token>  # Get from https://huggingface.co/settings/tokens
DEBUG=True
CORS_ORIGINS=["http://localhost:5173","http://localhost:3000"]
```

### **3. Local Development Setup**

**Backend:**
```bash
cd backend

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
make install

# Run database migrations
make migrate

# Seed champion data from Data Dragon
make seed

# (Optional) Scrape champion statistics from Riot API
make scrape-stats

# Start development server
make run
```

Backend will run at `http://localhost:8000`
API docs available at `http://localhost:8000/docs`

**Frontend:**
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will run at `http://localhost:5173`

---

## 🐳 **Docker Deployment (Production)**

### **1. Configure Environment**

Update `.env`, `backend/.env`, and `frontend/.env` with production values:
- Set `DEBUG=False`
- Use PostgreSQL: `DATABASE_URL=postgresql://user:password@db:5432/tryndraft`
- Set strong `SECRET_KEY` and `POSTGRES_PASSWORD`
- Update `CORS_ORIGINS` to your production domain

### **2. Build and Run**

```bash
# Build and start all services
docker-compose up -d --build

# Check status
docker-compose ps

# View logs
docker-compose logs -f
```

Services:
- **Frontend**: `http://localhost`
- **Backend**: `http://localhost/api`
- **PostgreSQL**: `localhost:5432`
- **Redis**: `localhost:6379`

### **3. Initialize Database**

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Seed champion data
docker-compose exec backend python scripts/seed_champions.py
```

---

## 📚 **Advanced Features**

### **Scraping Training Data for LLM Fine-Tuning**

Collect textual data from MOBAFire and LoLalytics to fine-tune the LLM:

```bash
cd backend

# Test with 5 champions
make scrape-training-test

# Scrape all champions (takes ~30-60 minutes)
make scrape-training
```

This creates:
- `training_data/scraped_data.json` - Raw scraped content
- `training_data/prepared_data.jsonl` - Formatted for fine-tuning

**Fine-Tuning Steps:**
1. Review `training_data/prepared_data.jsonl`
2. Upload to HuggingFace or your fine-tuning platform
3. Fine-tune Llama 3 or Mistral on this data
4. Update `FINE_TUNED_MODEL_ID` in `.env`
5. Uncomment API call in `LLMAnalysisBox.tsx` (line 59-64)

### **Collecting Champion Statistics**

Scrape real-time statistics from Riot API:

```bash
cd backend

# Requires RIOT_API_KEY in .env
make scrape-stats
```

This populates the database with:
- Win rates, pick rates, ban rates
- Role-specific performance
- Matchup data (counters)
- Synergy data (best teammates)

### **Neural Network Training**

The 50-feature neural network is pre-configured with rule-based fallback. To train with actual data:

1. Collect champion statistics (see above)
2. The model auto-trains when sufficient data is available
3. Model checkpoints saved to `backend/models/draft_nn.pth`

---

## 📖 **User Guide**

### **Creating an Account**
1. Go to `/login`
2. Click "Sign Up"
3. Enter email, username, password
4. Optionally add your League summoner name

### **Setting Up Your Champion Pool**
1. Go to `/profile`
2. Add champions you're comfortable playing
3. Set proficiency levels (1-5 stars)
4. Mark favorites for quick access

### **Using the Draft Tool**
1. Go to `/draft`
2. Select your team side (Blue/Red)
3. Choose your role and rank
4. Start banning and picking champions
5. View recommendations in the center panel
6. Read LLM analysis for strategic insights

### **Understanding Recommendations**
- **Top Recommendation**: Best champion for current situation
- **Draft Advantage**: Which team is ahead (Blue vs Red power)
- **Strategic Analysis**: LLM explanation of current draft state
- **Gameplans**: Win conditions for both teams
- **Score**: Neural network confidence (0-100%)
- **Reason**: Why this champion is recommended

---

## 🧪 **Testing**

```bash
# Backend tests
cd backend
pytest tests/ -v --cov=app

# Frontend tests
cd frontend
npm test
```

---

## 📋 **Makefile Commands**

**Backend:**
```bash
make help            # Show all available commands
make install         # Install Python dependencies
make run             # Start development server
make migrate         # Run database migrations
make seed            # Seed champion data
make scrape-stats    # Scrape Riot API statistics
make scrape-training # Scrape MOBAFire/LoLalytics for LLM training
make test            # Run tests
make clean           # Remove Python cache files
make format          # Format code with black
make lint            # Lint code with ruff
```

**Frontend:**
```bash
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build
npm test             # Run tests
npm run lint         # Lint code
```

---

## 🔧 **Troubleshooting**

### **Database Connection Issues**
- Ensure PostgreSQL is running: `docker-compose ps`
- Check `DATABASE_URL` in `.env`
- Run migrations: `make migrate`

### **Riot API Rate Limits**
- Free tier: 20 requests/sec, 100 requests/2 minutes
- Use `make scrape-stats` with delays between requests
- Consider upgrading to Production API key

### **LLM Not Working**
- Check `HF_TOKEN` in `.env`
- Verify HuggingFace API is accessible
- Fallback to rule-based analysis if API fails
- Fine-tune your own model for better results

### **Frontend Not Connecting to Backend**
- Ensure backend is running on port 8000
- Check `VITE_API_BASE_URL` in `frontend/.env`
- Verify CORS origins in `backend/app/main.py`

---

## 🤝 **Contributing**

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Submit a pull request

---

## 📄 **License**

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

## ⚠️ **Disclaimer**

TrynDraft isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing League of Legends. League of Legends and Riot Games are trademarks or registered trademarks of Riot Games, Inc. League of Legends © Riot Games, Inc.

---

## 🙏 **Acknowledgments**

- **Riot Games** for the Riot API and Data Dragon
- **HuggingFace** for LLM inference API
- **Community Dragon** for champion and role icons
- **MOBAFire** and **LoLalytics** for community data

---

## 📞 **Support**

- **Issues**: [GitHub Issues](https://github.com/talkeridan17/TrynDraft/issues)
- **Discussions**: [GitHub Discussions](https://github.com/talkeridan17/TrynDraft/discussions)
- **Email**: [your-email@example.com]

---

**Built with ❤️ by [Idan Talker](https://github.com/talkeridan17)**
