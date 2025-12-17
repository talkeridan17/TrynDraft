# Technology Stack Research

## Core Decisions

### Backend Framework
**Options:**
1. **FastAPI (Python)**
   - Pros: Async, auto-docs, easy, great for ML/data
   - Cons: Python ecosystem

2. **Express + TypeScript (Node.js)**
   - Pros: Full-stack JS, faster for I/O
   - Cons: Callback hell without careful setup

**Decision:** FastAPI

### Database
**Options:**
1. **PostgreSQL** - Robust, JSON support
2. **SQLite** - For prototyping
3. **MongoDB** - If heavy on unstructured data

**Decision:** PostgreSQL for production, SQLite for local dev

### Frontend
**Already decided:** React + TypeScript + Vite