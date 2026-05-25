# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 0.5.x   | :white_check_mark: |
| < 0.5   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability, please report it by emailing **security@tryndraft.com** (or open a private issue on GitHub).

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and work to address the issue promptly.

---

## Security Measures

### Authentication & Authorization

#### JWT Tokens
- Tokens signed with HS256 algorithm using `SECRET_KEY`
- Token expiration: 24 hours (configurable)
- Tokens stored in localStorage (frontend)
- All authenticated endpoints require valid Bearer token

#### Password Security
- Passwords hashed using bcrypt with salt rounds
- Minimum password length: 6 characters (production: recommend 12+)
- Password never logged or stored in plaintext

### API Security

#### CORS Configuration
- Strict origin checking via `CORS_ORIGINS` environment variable
- Credentials mode enabled for authenticated requests
- Only specified origins can access the API

#### Rate Limiting (Planned)
- API rate limiting via Redis (production)
- Per-user and per-IP limits
- Prevents brute force and DoS attacks

#### Input Validation
- All inputs validated via Pydantic schemas
- SQL injection prevented by SQLAlchemy ORM
- XSS prevention via React's default escaping

### Data Protection

#### Sensitive Data
- API keys stored only in environment variables
- `.env` files excluded from version control
- Database credentials never committed

#### Database
- SQLite for development (local only)
- PostgreSQL for production (with SSL)
- Regular backups recommended

### Third-Party Services

#### Riot API
- API key stored in `RIOT_API_KEY` environment variable
- Rate limits respected per Riot's guidelines
- No user data sent to Riot (read-only access)

#### HuggingFace
- API token stored in `HF_TOKEN` environment variable
- Disabled by default (`USE_HUGGINGFACE_API=false`) to prevent charges
- Draft state data sent for analysis (no PII)

---

## Environment Variables

### Required Secrets (NEVER commit these)

```bash
# Generate with: openssl rand -hex 32
SECRET_KEY=your-256-bit-secret-key

# Riot Developer Portal
RIOT_API_KEY=your-riot-api-key

# HuggingFace (if using LLM)
HF_TOKEN=your-huggingface-token
```

### Recommended .gitignore Entries

```
# Environment files
.env
.env.local
.env.*.local
backend/.env
frontend/.env

# Database
*.db
*.sqlite

# Logs
logs/*.log
*.log
```

---

## Development vs Production

### Development Mode
- `DEBUG=True` enabled
- SQLite database
- HuggingFace API disabled by default
- CORS allows localhost origins

### Production Mode
- `DEBUG=False`
- PostgreSQL with SSL
- HuggingFace API enabled (if configured)
- CORS restricted to production domain
- HTTPS enforced via reverse proxy

---

## Known Limitations (Alpha)

1. **Hardcoded fallback SECRET_KEY**: Ensure you set a custom `SECRET_KEY` in production
2. **No rate limiting**: Implement Redis-based rate limiting before public deployment
3. **No email verification**: User registration doesn't verify email addresses
4. **Session management**: Consider implementing refresh tokens for better security

---

## Security Checklist for Deployment

- [ ] Generate unique `SECRET_KEY` with `openssl rand -hex 32`
- [ ] Set `DEBUG=False` in production
- [ ] Configure HTTPS via reverse proxy (nginx)
- [ ] Set restrictive CORS origins
- [ ] Use PostgreSQL with SSL connection
- [ ] Set up Redis for rate limiting and sessions
- [ ] Enable log rotation for audit trails
- [ ] Implement backup strategy for database
- [ ] Review and rotate API keys periodically

---

## Dependencies

We regularly update dependencies to patch security vulnerabilities. Key dependencies:

- **FastAPI**: Modern, fast web framework with automatic validation
- **SQLAlchemy**: ORM with parameterized queries (SQL injection safe)
- **bcrypt**: Industry-standard password hashing
- **python-jose**: JWT handling with proper cryptographic operations
- **React**: XSS-safe by default with JSX escaping

Run `pip list --outdated` and `npm outdated` regularly to check for updates.

---

## Contact

For security concerns, contact:
- Email: security@tryndraft.com
- GitHub: Open a private security advisory

**Last Updated:** 2026-01-26
