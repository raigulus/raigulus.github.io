# Raigulus Raid Bot — Phase 2

Discord sign-up bot for Division 2 Dark Hours and Iron Horse raids.

## What it does

### Phase 1 (MVP)
- `/raid` slash command → choose Dark Hours or Iron Horse, optional time
- Opens a dedicated thread per raid
- Posts a roster embed with Join / Leave buttons
- 8-person cap, automatic waitlist, auto-promotion when a slot opens

### Phase 2 (New)
- **Persistent storage** — PostgreSQL database, raids survive bot restarts
- **Raid Host role** — Only users with this role can create raids
- **Rank roles** — Auto-assigned based on clear count:
  - 3+ clears → Rookie
  - 10+ clears → Veteran
  - 25+ clears → Master
- Separate ranks for Dark Hours and Iron Horse

### Phase 3 (New)
- **Mark Complete** — Host confirms who showed up, screenshot proof
- **Reputation system** — clears / (clears + no_shows) ratio
- **/profile** — View your own or another agent's stats
- **/leaderboard** — Top agents by clear count
- **/revoke-clear** — Raid Mod can revoke fraudulent clears

## Commands

| Command | Description | Permission |
|---------|-------------|------------|
| `/raid <type> [time]` | Create a raid sign-up thread | Raid Host |
| `/profile [user]` | View raid stats | Everyone |
| `/leaderboard` | Top agents by clears | Everyone |
| `/revoke-clear <user> <type>` | Revoke a clear | Raid Mod |

## Roles (auto-created by bot)

- `Raid Host` — Can create raids
- `Raid Mod` — Can revoke clears
- `DH Rookie` / `DH Veteran` / `DH Master` — Dark Hours ranks
- `IH Rookie` / `IH Veteran` / `IH Master` — Iron Horse ranks

## Test locally on Windows

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
$env:DISCORD_TOKEN="your_bot_token_here"
$env:DATABASE_URL="sqlite:///raid_bot.db"
python bot.py
```

## Deploy on Linux (Docker)

1. Copy `raigulus-raid-bot/` next to your existing docker-compose
2. Create `.env` from `.env.example` with real token and DB password
3. `docker compose up -d --build raigulus-raid-bot`
4. Check logs: `docker compose logs -f raigulus-raid-bot`

## Bot setup checklist (Discord Developer Portal)

1. Bot → make sure token is fresh
2. Privileged Gateway Intents: leave "Message Content Intent" OFF
3. OAuth2 → URL Generator → scopes: `bot`, `applications.commands`
4. Bot permissions: `Send Messages`, `Create Public Threads`, `Send Messages in Threads`, `Read Message History`, `Embed Links`, `Manage Roles`
5. Open the generated URL, invite to Raigulus server
