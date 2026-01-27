# Branching Standards

This document outlines our Git workflow and branch naming conventions.

## Branch Structure

```
main (production)
  │
  └── dev (development)
        │
        ├── feat/new-feature
        ├── bug/fix-something
        └── task/documentation
```

## Protected Branches

These branches have protection rules and require pull requests:

| Branch | Purpose | Merge Target |
|--------|---------|--------------|
| `main` | Production-ready code. Deployed to production. | N/A (release only) |
| `dev` | Development branch. All feature work merges here first. | `main` |

### Protection Rules

**`main` branch:**
- Requires pull request with approval
- No direct pushes allowed
- Must be up to date before merging
- Only merged from `dev` during releases

**`dev` branch:**
- Requires pull request with approval
- No direct pushes allowed
- All feature/bug/task branches merge here

## Working Branches

Create branches from `dev` using these naming conventions:

| Pattern | Purpose | Examples |
|---------|---------|----------|
| `feat/*` | New features | `feat/champion-filter`, `feat/dark-mode` |
| `bug/*` | Bug fixes | `bug/cursor-position-fix`, `bug/login-error` |
| `task/*` | Tasks, refactors, docs | `task/update-readme`, `task/refactor-api` |

### Branch Naming Rules

- Use lowercase letters
- Separate words with hyphens
- Keep names short but descriptive
- Include ticket number if applicable: `feat/123-champion-filter`

**Good examples:**
```
feat/champion-pool-management
bug/llm-timeout-handling
task/update-dependencies
feat/42-clickable-recommendations
```

**Bad examples:**
```
feature/ChampionFilter      # Don't use camelCase
fix_login                   # Don't use underscores
new-stuff                   # Too vague
bug/fix                     # Not descriptive
```

## Workflow

### Starting New Work

```bash
# 1. Start from dev
git checkout dev
git pull origin dev

# 2. Create your branch
git checkout -b feat/your-feature-name

# 3. Make commits
git add .
git commit -m "feat: add champion filter"

# 4. Push to remote
git push origin feat/your-feature-name

# 5. Create PR to dev on GitHub
```

### Keeping Your Branch Updated

```bash
# If dev has new changes while you're working
git checkout dev
git pull origin dev
git checkout feat/your-feature-name
git merge dev
# Or use rebase:
git rebase dev
```

### After PR is Merged

```bash
# Clean up your local branch
git checkout dev
git pull origin dev
git branch -d feat/your-feature-name
```

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>: <description>

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `style` | Code style (formatting, no logic change) |
| `refactor` | Code refactoring |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks |

### Examples

```bash
feat: add champion search filter
fix: resolve cursor position bug in draft
docs: update API documentation
refactor: simplify draft state management
test: add unit tests for NN service
chore: update dependencies
```

### Breaking Changes

For breaking changes, add `!` after the type:

```bash
feat!: change API response format
```

Or add a footer:

```bash
refactor: rename user endpoints

BREAKING CHANGE: /users/me is now /users/profile
```

## Release Process

1. **Feature Freeze**: Stop merging new features to `dev`
2. **Testing**: QA on `dev` branch
3. **Version Bump**: Update version numbers
4. **Merge to Main**: Create PR from `dev` to `main`
5. **Tag Release**: Create Git tag `v1.2.3`
6. **Deploy**: Automated deployment from `main`

```bash
# Creating a release tag
git checkout main
git pull origin main
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

## Hotfix Process

For urgent production fixes:

```bash
# 1. Branch from main
git checkout main
git pull origin main
git checkout -b bug/critical-fix

# 2. Fix and commit
git commit -m "fix: critical security issue"

# 3. PR to main (expedited review)
# 4. After merge, also merge main back to dev
git checkout dev
git merge main
git push origin dev
```

## Quick Reference

| I want to... | Command |
|--------------|---------|
| Start new feature | `git checkout dev && git pull && git checkout -b feat/name` |
| Start bug fix | `git checkout dev && git pull && git checkout -b bug/name` |
| Update my branch | `git checkout dev && git pull && git checkout my-branch && git merge dev` |
| Push my branch | `git push origin my-branch-name` |
| Delete local branch | `git branch -d branch-name` |
| See all branches | `git branch -a` |

---

**Questions?** Ask in GitHub Discussions or contact a maintainer.
