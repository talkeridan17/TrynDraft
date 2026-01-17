# TrynDraft System Architecture

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                          Frontend                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  DraftPage  │  │ ProfilePage │  │  LoginPage  │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          │                                       │
│                  ┌───────┴───────┐                               │
│                  │  Zustand Store │                              │
│                  │  (State Mgmt)  │                              │
│                  └───────┬───────┘                               │
│                          │                                       │
│                  ┌───────┴───────┐                               │
│                  │   API Client   │                              │
│                  │   (Axios)      │                              │
│                  └───────┬───────┘                               │
└──────────────────────────┼───────────────────────────────────────┘
                           │ HTTP/REST
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                          Backend (FastAPI)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │   /users    │  │  /champions │  │   /drafts   │               │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘               │
│         │                │                │                       │
│         └────────────────┼────────────────┘                       │
│                          │                                        │
│         ┌────────────────┼────────────────┐                       │
│         │                │                │                       │
│         ▼                ▼                ▼                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐               │
│  │  Database   │  │ Data Dragon │  │ LLM Service │               │
│  │ (SQLite/PG) │  │    API      │  │ (HuggingFace)│              │
│  └─────────────┘  └─────────────┘  └─────────────┘               │
└──────────────────────────────────────────────────────────────────┘
```

## Component Details

### Frontend Components
- **DraftPage**: Main draft interface with pick/ban slots
- **ProfilePage**: User settings and champion pool
- **LoginPage**: Authentication (login/register)
- **Zustand Store**: Centralized state management
- **API Client**: Axios-based HTTP client

### Backend Services
- **Users API**: Authentication, profiles, preferences
- **Champions API**: Champion data from Data Dragon
- **Drafts API**: Draft session management
- **LLM Service**: AI-powered draft analysis

### External Services
- **Data Dragon**: Champion images and data (Riot)
- **Community Dragon**: Role and rank icons
- **HuggingFace**: LLM inference (Mistral 7B)
