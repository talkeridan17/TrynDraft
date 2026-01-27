# Contributing to TrynDraft

Thank you for your interest in contributing to TrynDraft! This document provides guidelines for contributing to the project.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Set up the development environment** (see [README.md](README.md))
4. **Create a branch** for your work

## Branch Strategy

### Protected Branches
The following branches are protected and require pull requests:

| Branch | Purpose |
|--------|---------|
| `main` | Production-ready code. Deployed to production. |
| `dev` | Development branch. All PRs merge here first. |

### Working Branches
Create branches from `dev` using these naming conventions:

| Pattern | Purpose | Example |
|---------|---------|---------|
| `feat/*` | New features | `feat/champion-filter` |
| `bug/*` | Bug fixes | `bug/cursor-position-fix` |
| `task/*` | Tasks, refactors, docs | `task/update-readme` |

### Workflow

```
main (production)
  │
  └── dev (development)
        │
        ├── feat/new-feature
        ├── bug/fix-something
        └── task/documentation
```

1. **Create branch from `dev`**: `git checkout dev && git pull && git checkout -b feat/your-feature`
2. **Make your changes** with clear commits
3. **Push to your fork**: `git push origin feat/your-feature`
4. **Create PR to `dev`** (not `main`)
5. **After review**, merge to `dev`
6. **Periodically**, `dev` is merged to `main` for releases

## Commit Messages

Use conventional commits:
```
feat: add champion search filter
fix: resolve cursor position bug in draft
docs: update API documentation
refactor: simplify draft state management
test: add unit tests for NN service
chore: update dependencies
```

## Pull Requests

### Creating a PR
1. Target the `dev` branch (not `main`)
2. Fill out the PR template with:
   - Summary of changes
   - Related issues
   - Testing performed
3. Ensure all tests pass
4. Request review from maintainers

### PR Checklist
- [ ] Branch is up to date with `dev`
- [ ] Code follows project style guidelines
- [ ] Tests added/updated for new functionality
- [ ] Documentation updated if needed
- [ ] No console.log or debug statements
- [ ] No hardcoded secrets or credentials

## Code Standards

### Python (Backend)
- Follow PEP 8 style guide
- Use type hints for function signatures
- Write docstrings for public functions
- Keep functions under 50 lines when possible

```python
def get_champion_stats(champion_name: str, patch: str) -> Optional[ChampionStats]:
    """
    Fetch champion statistics for a specific patch.

    Args:
        champion_name: The champion's display name
        patch: The game patch version (e.g., "14.24")

    Returns:
        ChampionStats object or None if not found
    """
    ...
```

### TypeScript (Frontend)
- Use TypeScript strict mode
- Define interfaces for all props and state
- Use functional components with hooks
- Avoid `any` type when possible

```typescript
interface ChampionCardProps {
  champion: ScoredChampion;
  onClick: (name: string) => void;
  isSelected: boolean;
}

export const ChampionCard: React.FC<ChampionCardProps> = ({
  champion,
  onClick,
  isSelected
}) => {
  // ...
};
```

### CSS/Styling
- Use TailwindCSS utility classes
- Avoid custom CSS unless necessary
- Follow mobile-first responsive design
- Use semantic color classes from design system

## Testing

### Backend Tests
```bash
cd backend
source .venv/bin/activate
pytest
pytest --cov=app  # with coverage
```

### Frontend Tests
```bash
cd frontend
npm test
npm run test:coverage  # with coverage
```

### What to Test
- API endpoints (happy path + error cases)
- State management functions
- Complex business logic
- User interactions

## Project Structure

### Adding a New API Endpoint
1. Create route in `backend/app/api/v1/endpoints/`
2. Add Pydantic schemas in `backend/app/schemas.py`
3. Implement business logic in `backend/app/services/`
4. Register route in `backend/app/api/v1/router.py`
5. Update API client in `frontend/src/utils/api.ts`

### Adding a New Page
1. Create page component in `frontend/src/pages/`
2. Add route in `frontend/src/App.tsx`
3. Update navigation in `Header.tsx` if needed

### Adding a New Component
1. Create component in appropriate directory:
   - `components/common/` - Shared components
   - `components/drafting/` - Draft-specific
   - `components/layout/` - Layout components
2. Export from index file if applicable

## Common Tasks

### Database Migrations
```bash
cd backend
source .venv/bin/activate
alembic revision --autogenerate -m "Description of changes"
alembic upgrade head
```

### Updating Dependencies
```bash
# Backend
pip install --upgrade package-name
pip freeze > requirements.txt

# Frontend
npm update package-name
```

### Running Linters
```bash
# Frontend
cd frontend
npm run lint
npm run lint:fix  # auto-fix

# Backend
cd backend
flake8 app/
black app/
```

## Environment Setup

### Required Environment Variables
See [README.md](README.md#environment-variables-reference) for full list.

### Development Mode
- Set `USE_HUGGINGFACE_API=false` to avoid API charges
- Use SQLite database for local development
- CORS allows localhost origins

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions
- Reach out to maintainers for guidance

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing!**
