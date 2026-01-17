# TrynDraft Database Schema

## Entity Relationship Diagram

```
┌─────────────────────┐
│       users         │
├─────────────────────┤
│ id (PK)             │
│ email               │
│ username            │
│ hashed_password     │
│ summoner_name       │
│ region              │
│ created_at          │
└──────────┬──────────┘
           │
           │ 1:1
           ▼
┌─────────────────────┐
│  user_preferences   │
├─────────────────────┤
│ id (PK)             │
│ user_id (FK)        │
│ preferred_roles     │
│ rank                │
│ profile_picture     │
└─────────────────────┘
           │
           │ 1:N
           ▼
┌─────────────────────┐
│ user_champion_pool  │
├─────────────────────┤
│ id (PK)             │
│ user_id (FK)        │
│ champion_name       │
│ playstyles          │
│ proficiency         │
│ created_at          │
└─────────────────────┘


┌─────────────────────┐
│     champions       │
├─────────────────────┤
│ id (PK)             │
│ riot_id             │
│ name                │
│ title               │
│ tags                │
│ stats               │
│ image_url           │
└─────────────────────┘


┌─────────────────────┐
│       drafts        │
├─────────────────────┤
│ id (PK)             │
│ user_id (FK)        │
│ blue_bans           │
│ red_bans            │
│ blue_picks          │
│ red_picks           │
│ current_phase       │
│ created_at          │
│ completed_at        │
└─────────────────────┘
```

## Table Descriptions

### users
Stores user account information and authentication data.

### user_preferences
Stores user preferences (main role, rank, profile picture).
One-to-one relationship with users.

### user_champion_pool
Stores champions the user plays with proficiency ratings.
Many-to-one relationship with users.

### champions
Stores champion data from Data Dragon.
Includes base stats, tags, and image URLs.

### drafts
Stores draft sessions with picks and bans.
Can be associated with a user or anonymous (guest).
