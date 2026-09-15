# Raigulus Raid Bot

Discord sign-up + progression bot for Division 2 Dark Hours and Iron Horse raids.

## Structure

```
bot.py               entrypoint - loads cogs, inits DB, syncs commands
state.py             shared in-memory state for active (in-progress) raids
db.py                async SQLite persistence (aiosqlite) for clear/no-show counts
cogs/
  raid_core.py       /raid - creation, thread, Join/Leave buttons, waitlist
  progression.py     /raid-complete, /raid-revoke-clear, rank roles
data/
  raid_bot.db         created automatically on first run (gitignored)
```

Only finalized results (clears, no-shows, evidence log) are persisted to
SQLite. Live roster state before a raid is marked complete stays in memory -
if the bot restarts mid-raid, just re-run `/raid`.

## Commands

- `/raid <dark-hours|iron-horse> [time]` - creates a thread + roster embed
  with Join/Leave buttons (8-cap, auto waitlist + promotion). Requires the
  **Raid Host** role.
- `/raid-complete <evidence screenshot>` - run inside the raid's thread.
  Opens a select menu to pick who actually attended; selected players get
  +1 clear (logged with the screenshot as proof), everyone else on the
  roster gets +1 no-show. Requires **Raid Host** or **Raid Mod**.
- `/raid-revoke-clear <member> <raid>` - removes that player's most recent
  logged clear, in case the evidence turns out to be fake/disputed.
  Requires **Raid Mod**.

Rank roles (`{Raid} Rookie` at 3+, `Veteran` at 10+, `Master` at 25+ clears)
are created and assigned automatically as counts change.

## First-run setup

`Raid Host` and `Raid Mod` roles are auto-created on the server the first
time the bot comes online, if they don't already exist. Assign them to
whoever should be allowed to host/moderate raids.

## Test locally on Windows

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
$env:DISCORD_TOKEN="your_bot_token_here"
python bot.py
```

Invite the bot first (see checklist below) and make sure it can create
public threads in the channel you run `/raid` in.

## Bot setup checklist (Discord Developer Portal)

1. Under your EDI application → Bot → make sure the token is fresh
   (regenerate if it was ever committed to a repo in plaintext).
2. Privileged Gateway Intents: leave "Message Content Intent" OFF - not
   needed, everything here is slash-command + button/select based.
3. OAuth2 → URL Generator → scopes: `bot`, `applications.commands`.
   Bot permissions: `Send Messages`, `Create Public Threads`,
   `Send Messages in Threads`, `Read Message History`, `Embed Links`,
   `Manage Roles` (needed to auto-create/assign rank + Raid Host/Mod roles).
4. Open the generated URL, invite it to the Raigulus server.
5. Note: the bot's own role must sit **above** the rank/Raid Host/Raid Mod
   roles in the server's role list, or role assignment will silently fail.

## Deploy on the Linux Docker host

1. Copy this whole `raigulus-raid-bot/` folder next to your existing
   `local-ai-intelligence-pipeline` compose setup.
2. Create `raigulus-raid-bot/.env` from `.env.example` with the real
   token (gitignored - never commit it).
3. Merge `docker-compose.snippet.yml` into your existing
   `docker-compose.yml` as a new service. The `data/` volume keeps the
   SQLite DB across rebuilds.
4. `docker compose up -d --build raigulus-raid-bot`
5. Check logs: `docker compose logs -f raigulus-raid-bot` - look for
   "slash commands synced."

## Next up (per the agreed roadmap)

3. `/lfg` - list all currently open raid threads + free slots
4. Scheduling & reminders - ping roster N minutes before raid time,
   recurring raid support
5. Gamification - `/raid-leaderboard`, weekly streaks, no-show restrictions
6. Site integration - export clear/leaderboard data to raigulus-site
