# Raigulus Raid Bot — Implementation Plan

## Context
Division 2 Dark Hours & Iron Horse raid sign-up bot for the Raigulus Discord server. Phase 1 skeleton exists (`raid-bot-skeleton/bot.py`) with basic `/raid` command, thread creation, Join/Leave buttons, 8-person cap, and waitlist. Now expanding to Phase 2 (persistence + roles) and Phase 3 (reputation + proof system).

## Tech Decisions
- **Language**: Python + discord.py (consistent with site scripts, skeleton already Python)
- **Database**: PostgreSQL (scalable, Docker-friendly) via SQLAlchemy + Alembic migrations
- **Hosting**: Docker on Linux server (user has existing docker-compose setup for `local-ai-intelligence-pipeline`)
- **Bot type**: Persistent connection (discord.py gateway), always-on container with `restart: unless-stopped`

## Architecture

### Project Structure
```
raigulus-raid-bot/
├── bot.py                  # Entry point, bot setup, event handlers
├── config.py               # Environment vars, raid configs
├── database.py             # SQLAlchemy engine, session, models
├── models.py               # ORM: Raid, RaidMember, UserProfile
├── views/
│   ├── raid_view.py        # Join/Leave buttons + Mark Complete
│   └── profile_view.py     # /profile display
├── cogs/
│   ├── raid.py             # /raid command, thread creation
│   ├── profile.py          # /profile, /leaderboard
│   └── admin.py            # /revoke-clear, role management
├── migrations/             # Alembic schema migrations
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

### Database Schema

#### `user_profiles`
| Column | Type | Notes |
|--------|------|-------|
| user_id | BIGINT PK | Discord user ID |
| dh_clears | INT default 0 | Dark Hours clear count |
| dh_no_shows | INT default 0 | Dark Hours no-show count |
| ih_clears | INT default 0 | Iron Horse clear count |
| ih_no_shows | INT default 0 | Iron Horse no-show count |
| reputation | FLOAT computed | clears / (clears + no_shows) |
| created_at | TIMESTAMP | First seen |

#### `raids`
| Column | Type | Notes |
|--------|------|-------|
| raid_id | SERIAL PK | Auto-increment |
| message_id | BIGINT UNIQUE | Discord message ID (roster embed) |
| thread_id | BIGINT | Discord thread ID |
| channel_id | BIGINT | Parent channel |
| raid_type | ENUM | 'dark-hours' / 'iron-horse' |
| host_id | BIGINT FK | Who created it |
| scheduled_time | TEXT nullable | e.g. "21:00 CET" |
| status | ENUM | 'open' / 'confirmed' / 'completed' / 'cancelled' |
| screenshot_url | TEXT nullable | Post-raid proof attachment URL |
| completed_at | TIMESTAMP nullable | When marked complete |

#### `raid_members`
| Column | Type | Notes |
|--------|------|-------|
| id | SERIAL PK | |
| raid_id | INT FK | → raids.raid_id |
| user_id | BIGINT | Discord user ID |
| status | ENUM | 'roster' / 'waitlist' / 'confirmed' / 'no_show' |
| joined_at | TIMESTAMP | |

## Phase 2 — Persistence + Roles

### 2.1 PostgreSQL + SQLAlchemy
- Set up SQLAlchemy models matching schema above
- Alembic for migrations
- Bot startup: create tables if not exist
- Migrate `active_raids` dict → database reads/writes

### 2.2 Persistent Raid State
- `/raid` creates row in `raids` + `raid_members` tables
- Bot restart: reload active raids from DB (status='open'), rebuild views
- Join/Leave button handlers write to `raid_members` table
- Waitlist promotion logic unchanged, just persisted

### 2.3 Raid Host Role Gate
- `/raid` command gated by `@app_commands.checks.has_role("Raid Host")`
- Bot auto-creates "Raid Host" and "Raid Mod" roles on first boot if missing
- Join/Leave remains open to everyone

### 2.4 Rank Roles (per raid type)
On every clear confirmation, bot recalculates and assigns:

| Clears | Role Name |
|--------|-----------|
| 3+ | `DH Rookie` / `IH Rookie` |
| 10+ | `DH Veteran` / `IH Veteran` |
| 25+ | `DH Master` / `IH Master` |

- Bot auto-creates these 6 roles on first boot (color-coded: green→blue→gold)
- On tier-up: remove old role, add new role, send congratulations message
- `member.add_roles()` / `member.remove_roles()`

## Phase 3 — Reputation + Proof

### 3.1 Mark Complete Flow
1. Host clicks "✅ Mark Complete" button on roster embed
2. Bot opens a modal asking for screenshot attachment (drag & drop)
3. If screenshot not provided → warning modal, but allowed with extra confirmation ("Are you sure? No proof = vulnerable to revoke")
4. Host selects which members actually showed up (checkbox list from roster)
5. Unselected members get `no_show_count += 1`
6. Selected members get `clear_count += 1`
7. Screenshot saved as attachment URL in `raids.screenshot_url`
8. Raid status → 'completed'
9. Rank roles recalculated for all confirmed members

### 3.2 Anti-Troll Safeguards
- **Screenshot proof**: Post-raid completion screen required (squad list + timer visible)
- **Roster warning**: If confirmed count < 8, extra friction prompt
- **Revoke mechanism**: `/revoke-clear @user raid_type` — only "Raid Mod" role can use
  - Decrements clear_count by 1
  - Logs the revoke action
  - Screenshot evidence available for manual review

### 3.3 Reputation System
- Formula: `reputation = clears / (clears + no_shows)`
- Displayed as percentage (e.g. "92% reliability")
- `/profile [@user]` — shows own stats or another user's
- `/leaderboard` — top players by clear count
- Future: low-reputation users auto-moved to waitlist bottom (optional, not MVP)

### 3.4 No-Show Detection
- When raid status → 'completed', any roster member NOT confirmed by host gets `no_show_count += 1`
- Waitlist members who weren't promoted don't count as no-shows

## Channels & Roles (Discord Setup)

### Roles (auto-created by bot)
- `Raid Host` — Can create raids (`/raid` command)
- `Raid Mod` — Can revoke clears (`/revoke-clear`)
- `DH Rookie` / `DH Veteran` / `DH Master` — Dark Hours clear ranks
- `IH Rookie` / `IH Veteran` / `IH Master` — Iron Horse clear ranks

### Channels (manual setup by admin)
- `#raid-signups` — Where `/raid` command is used, threads auto-created here
- `#raid-history` — Optional: bot posts completed raid summaries here

## Implementation Order

### Step 1: Project setup + Database
- Initialize repo with proper structure
- Set up SQLAlchemy + Alembic
- Create all models
- Dockerfile + docker-compose.yml
- `.env.example` with `DISCORD_TOKEN` + `DATABASE_URL`

### Step 2: Persistent raid state
- Refactor `bot.py` to use database instead of `active_raids` dict
- Raid creation writes to DB
- Join/Leave writes to DB
- Bot restart recovery: reload active raids

### Step 3: Raid Host role gate
- Add role check to `/raid` command
- Auto-create roles on `on_ready`
- Error handling for unauthorized users

### Step 4: Mark Complete flow
- Add "✅ Mark Complete" button to raid embed (host only)
- Confirmation modal for screenshot
- Member selection checkboxes
- Clear/no-show counting
- Screenshot attachment storage

### Step 5: Rank roles
- Clear count calculation on each completion
- Role creation on first boot
- Auto-assign/remove on tier change
- Congratulations embed on rank-up

### Step 6: Profile + Leaderboard
- `/profile [@user]` command
- `/leaderboard` command
- Reputation calculation
- Stats embed with rank roles shown

### Step 7: Revoke mechanism
- `/revoke-clear` command (Raid Mod only)
- Clear count decrement
- Audit log

### Step 8: Polish + Deploy
- Error handling edge cases
- Rate limiting on buttons
- Docker deployment on Linux server
- Test with real raids

## Deployment

### Local Development
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
$env:DISCORD_TOKEN="token"
$env:DATABASE_URL="sqlite:///raid_bot.db"
python bot.py
```

### Production (Docker on Linux)
1. Copy `raigulus-raid-bot/` next to existing docker-compose
2. Create `.env` with `DISCORD_TOKEN` + `DATABASE_URL=postgresql://user:pass@db:5432/raid_bot`
3. Merge service into docker-compose.yml
4. `docker compose up -d --build raigulus-raid-bot`
5. `docker compose logs -f raigulus-raid-bot`

## Success Criteria
- [ ] Bot creates threads with roster embed on `/raid`
- [ ] Join/Leave buttons work, waitlist auto-promotes
- [ ] Raid state persists across bot restarts
- [ ] Raid Host role gates the `/raid` command
- [ ] Mark Complete flow records clears with screenshot proof
- [ ] Rank roles auto-assigned based on clear count
- [ ] /profile shows stats and reputation
- [ ] Revoke mechanism works for Raid Mods
- [ ] Docker container runs 24/7 on Linux server
