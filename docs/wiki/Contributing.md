# Contributing to TrynDraft

Thank you for your interest in contributing to TrynDraft! This guide will help you get started.

## Ways to Contribute

### Report Bugs
Found something broken? Open a GitHub Issue with:
- Clear description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable

### Suggest Features
Have an idea? Open a GitHub Discussion with:
- What problem it solves
- How you envision it working
- Any implementation ideas

### Submit Code
Ready to code? Follow the process below.

---

## Development Process

### 1. Fork and Clone

```bash
# Fork the repo on GitHub, then:
git clone https://github.com/YOUR-USERNAME/TrynDraft.git
cd TrynDraft
```

### 2. Set Up Development Environment

See [Development Setup](Development-Setup) for detailed instructions.

### 3. Create a Branch

**Always branch from `dev`**, never from `main`:

```bash
git checkout dev
git pull origin dev
git checkout -b feat/your-feature-name
```

Use the correct branch prefix (see [Branching Standards](Branching-Standards)):
- `feat/*` - New features
- `bug/*` - Bug fixes
- `task/*` - Refactors, documentation, chores

### 4. Make Your Changes

- Follow the code standards below
- Write tests if adding new functionality
- Update documentation if needed

### 5. Commit Your Changes

Use conventional commit messages:

```bash
git commit -m "feat: add champion filter by role"
git commit -m "fix: resolve cursor position bug"
git commit -m "docs: update API documentation"
```

### 6. Push and Create PR

```bash
git push origin feat/your-feature-name
```

Then create a Pull Request on GitHub:
- **Target branch**: `dev` (not `main`)
- Fill out the PR template
- Link any related issues

---

## Code Standards

### Python (Backend)

```python
# Use type hints
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

- Follow PEP 8 style guide
- Use type hints for function signatures
- Write docstrings for public functions
- Keep functions under 50 lines when possible
- Format with `black`: `black app/`
- Lint with `flake8`: `flake8 app/`

### TypeScript (Frontend)

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

- Use TypeScript strict mode
- Define interfaces for all props and state
- Use functional components with hooks
- Avoid `any` type
- Lint with `npm run lint`

### CSS/Styling

- Use TailwindCSS utility classes
- Avoid custom CSS unless necessary
- Follow mobile-first responsive design
- Use semantic color classes from design system

---

## Pull Request Checklist

Before submitting your PR, ensure:

- [ ] Branch is up to date with `dev`
- [ ] Code follows project style guidelines
- [ ] Tests added/updated for new functionality
- [ ] Documentation updated if needed
- [ ] No `console.log` or debug statements
- [ ] No hardcoded secrets or credentials
- [ ] Linting passes (`npm run lint`, `flake8`)
- [ ] Tests pass (`pytest`, `npm test`)

---

## Review Process

1. **Automated checks**: CI runs tests and linting
2. **Code review**: A maintainer reviews your code
3. **Feedback**: Address any requested changes
4. **Merge**: Once approved, your PR is merged to `dev`
5. **Release**: Periodically, `dev` is merged to `main` for releases

---

## Getting Help

- **Questions**: Open a GitHub Discussion
- **Bugs**: Open a GitHub Issue
- **Real-time**: Contact maintainers

---

## Code of Conduct

- Be respectful and inclusive
- Provide constructive feedback
- Help others learn and grow
- Focus on the code, not the person

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing!**
