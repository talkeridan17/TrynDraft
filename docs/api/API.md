# TrynDraft API Documentation

Base URL: `http://localhost:8000/api/v1`

## Authentication

Most endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <access_token>
```

### POST /users/register
Create a new user account.

**Request Body:**
```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "password123",
  "summoner_name": "SummonerName",
  "region": "NA"
}
```

**Response:** `201 Created`
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "username"
}
```

### POST /users/login
Authenticate and receive JWT token.

**Request Body:** (form-urlencoded)
```
username=username&password=password123
```

**Response:** `200 OK`
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer"
}
```

---

## User Endpoints

### GET /users/me
Get current user profile.

**Response:**
```json
{
  "id": "uuid",
  "email": "user@example.com",
  "username": "username",
  "summoner_name": "SummonerName",
  "region": "NA",
  "preferences": {
    "preferred_roles": ["MID"],
    "rank": "PLATINUM",
    "profile_picture": "Ahri"
  }
}
```

### PUT /users/me/preferences
Update user preferences.

**Request Body:**
```json
{
  "preferred_roles": ["MID", "TOP"],
  "rank": "DIAMOND",
  "profile_picture": "Tryndamere"
}
```

---

## Champion Pool

### GET /users/me/champion-pool
Get user's champion pool.

**Response:**
```json
[
  {
    "id": "uuid",
    "champion_name": "Tryndamere",
    "playstyles": ["splitpush", "teamfight"],
    "proficiency": 5
  }
]
```

### POST /users/me/champion-pool
Add champion to pool.

**Request Body:**
```json
{
  "champion_name": "Tryndamere",
  "playstyles": ["splitpush"],
  "proficiency": 3
}
```

### PUT /users/me/champion-pool/{champion_id}
Update champion in pool.

### DELETE /users/me/champion-pool/{champion_id}
Remove champion from pool.

---

## Champions

### GET /champions/
Get all champions.

**Response:**
```json
[
  {"id": "Aatrox", "name": "Aatrox"},
  {"id": "Ahri", "name": "Ahri"}
]
```

### GET /champions/version/latest
Get latest patch version.

**Response:**
```json
{
  "version": "16.1.1"
}
```

---

## Drafts

### POST /drafts
Create a new draft session.

### GET /drafts/{draft_id}
Get draft details.

### POST /drafts/{draft_id}/ban
Add a ban to the draft.

### POST /drafts/{draft_id}/pick
Add a pick to the draft.

---

## LLM Analysis

### POST /llm/analyze
Get AI analysis of draft state.

**Request Body:**
```json
{
  "draftState": {
    "bans": {"blue": [...], "red": [...]},
    "picks": {"blue": [...], "red": [...]},
    "settings": {"elo": "PLATINUM", "role": "MID"}
  }
}
```

**Response:**
```json
{
  "analysis": "Strategic analysis text...",
  "blueTeamPower": 52,
  "redTeamPower": 48,
  "recommendations": [...]
}
```
