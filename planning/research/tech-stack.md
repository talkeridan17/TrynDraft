# Technology Stack Research

## Current Implementation (v0.5.0-alpha)

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| **FastAPI** | 0.104+ | Web framework, async API |
| **Python** | 3.12+ | Runtime |
| **SQLAlchemy** | 2.0+ | ORM, database abstraction |
| **SQLite** | - | Development database |
| **PostgreSQL** | 15+ | Production database |
| **Pydantic** | 2.5+ | Data validation, schemas |
| **bcrypt** | - | Password hashing |
| **python-jose** | - | JWT authentication |
| **PyTorch** | 2.0+ | Neural network model |
| **aiohttp** | 3.9+ | Async HTTP client |
| **BeautifulSoup4** | - | Web scraping |
| **httpx** | - | HuggingFace API client |

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| **React** | 19 | UI framework |
| **TypeScript** | 5.6+ | Type safety |
| **Vite** | 7+ | Build tool, dev server |
| **Zustand** | 5+ | State management |
| **TailwindCSS** | 3.4+ | Styling |
| **Lucide React** | - | Icons |
| **Axios** | - | HTTP client |
| **React Router** | 7+ | Routing |

### AI/ML Services

| Technology | Purpose | Status |
|------------|---------|--------|
| **PyTorch NN** | Champion recommendations | Implemented (50-feature model) |
| **HuggingFace API** | LLM analysis (Qwen2.5-72B) | Implemented (disabled by default) |
| **Rule-based fallback** | Free alternative to LLM | Implemented |

### External APIs

| API | Purpose | Authentication |
|-----|---------|----------------|
| **Riot API** | Champion stats, match data | API key |
| **Data Dragon** | Champion images, patch data | None (public) |
| **Community Dragon** | Role icons, assets | None (public) |

### DevOps

| Technology | Purpose |
|------------|---------|
| **Docker** | Containerization |
| **docker-compose** | Multi-container orchestration |
| **Nginx** | Reverse proxy (production) |
| **Redis** | Caching, sessions (production) |

---

## Architecture Decisions

### Backend Framework: FastAPI
**Why:**
- Native async support for API calls
- Automatic OpenAPI documentation
- Pydantic integration for validation
- Python ecosystem for ML/data science

### Database: SQLite (dev) / PostgreSQL (prod)
**Why:**
- SQLite: Zero-config local development
- PostgreSQL: Production-ready, JSON support, full-text search

### State Management: Zustand
**Why:**
- Simple, lightweight (vs Redux)
- TypeScript-first
- Built-in persistence middleware
- No boilerplate

### Styling: TailwindCSS
**Why:**
- Utility-first, rapid prototyping
- No CSS file management
- Consistent design system
- Small production bundle

### LLM: HuggingFace Inference API
**Why:**
- No infrastructure to manage
- Access to multiple models (Qwen, Mistral, etc.)
- Pay-per-use (disable during dev)
- Easy to switch models

---

## Performance Considerations

### Frontend
- Champion images lazy-loaded from Data Dragon CDN
- Zustand persist uses localStorage
- Debounced API calls (300-500ms)
- AbortController for cancelled requests

### Backend
- Async endpoints with FastAPI
- Database connection pooling
- Champion data cached in memory
- NN predictions batched when possible

### API Optimization
- Champions sorted server-side
- Only top 80 champions scored through NN
- LLM calls disabled during development

---

## Security Stack

| Component | Technology |
|-----------|------------|
| Authentication | JWT (HS256) |
| Password Hashing | bcrypt |
| API Security | CORS, rate limiting (planned) |
| Input Validation | Pydantic schemas |
| SQL Injection | SQLAlchemy ORM |
| XSS Prevention | React JSX escaping |

---

## Future Considerations

1. **Redis caching** - Champion stats, LLM responses
2. **WebSocket** - Real-time draft sync (multiplayer)
3. **Model fine-tuning** - Custom LoL-trained LLM
4. **CDN** - Static assets, champion images
5. **Monitoring** - Sentry, application metrics

---

**Last Updated:** 2026-01-26
