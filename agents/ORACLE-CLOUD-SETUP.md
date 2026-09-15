# Oracle Cloud Free Tier - Raid Bot Deployment

## Instance Details (ACTIVE - Sep 14 2026)
- **Name:** raigulus-raid-bot
- **Region:** Germany Central (Frankfurt) - eu-frankfurt-1
- **Shape:** VM.Standard.A1.Flex (ARM) - 1 OCPU, 6 GB memory
- **Image:** Ubuntu (ARM-compatible)
- **Availability Domain:** AD-1, Fault Domain: FD-1
- **Compartment:** Raigulus (root)
- **Status:** RUNNING ✅
- **Note:** A1.Flex is ARM architecture - Docker images must be ARM-compatible

## Previous Instance (TERMINATED)
- **Shape:** VM.Standard.E2.1.Micro (x86, 1 core, 1 GB RAM)
- **Public IP:** 158.180.18.220 (no longer valid)
- **Status:** Terminated

## Networking (New Instance)
- **Public IP:** 130.61.182.172
- **Private IP:** 10.0.0.243

## SSH Access
- **Username:** ubuntu
- **Private Key:** `C:\Users\dekim\.ssh\oracle_keys\ssh-key-2026-09-14.key`
- **Public Key:** `C:\Users\dekim\.ssh\oracle_keys\ssh-key-2026-09-14.key.pub`
- **SSH Command:** `ssh -i "C:\Users\dekim\.ssh\oracle_keys\ssh-key-2026-09-14.key" ubuntu@130.61.182.172`

## Docker Installed
- **Version:** Docker 29.8.0
- **Docker Compose:** v5.5.1
- **User added to docker group** ✅

## Bot Files Uploaded ✅
- All files uploaded via SCP from Windows to `~/raid-bot/`
- SCP command: `scp -i "C:\Users\dekim\.ssh\oracle_keys\ssh-key-2026-09-14.key" -r "C:\Users\dekim\OneDrive\Belgeler\raid-bot-skeleton\*" ubuntu@130.61.182.172:~/raid-bot/`

## Next Steps
1. SSH back in: `ssh -i "C:\Users\dekim\.ssh\oracle_keys\ssh-key-2026-09-14.key" ubuntu@130.61.182.172`
2. Create .env file with DISCORD_TOKEN and DATABASE_URL
3. Run: `cd ~/raid-bot/ && docker-compose up -d --build`
4. Check logs: `docker-compose logs -f`

## Deployment Status: ✅ COMPLETE
- Bot is running and connected to Discord (EDI#1088)
- Slash commands synced
- Bot runs 24/7 on Oracle Cloud Free Tier

## Update (Sep 14 2026) - Modular Refactor
- Migrated from monolithic bot.py to cog-based architecture
- New files: db.py (aiosqlite async), state.py (in-memory), cogs/raid_core.py, cogs/progression.py
- Removed PostgreSQL dependency, using async SQLite via aiosqlite
- Added PYTHONUNBUFFERED=1 for proper log output
- Container: raid-bot-raigulus-raid-bot-1

## Setup Progress
- [x] Oracle Cloud account created
- [x] VM instance created
- [x] Public IP assigned (Ephemeral)
- [x] SSH connection verified
- [ ] Docker installed
- [ ] Docker Compose installed
- [ ] Bot files uploaded
- [ ] .env configured
- [ ] Bot running via docker-compose

## Docker Installation Commands
```bash
sudo dnf update -y
sudo dnf install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker opc
# Logout and login again for group changes to take effect
```

## Docker Compose Installation
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

## Bot Files to Upload
- `bot.py` - Main bot with Discord commands
- `config.py` - Configuration (env vars)
- `database.py` - SQLAlchemy engine
- `models.py` - ORM models (UserProfile, Raid, RaidMember)
- `requirements.txt` - discord.py, sqlalchemy, psycopg2-binary
- `Dockerfile` - Python 3.12 container
- `docker-compose.yml` - Bot + PostgreSQL (or SQLite for 1GB RAM)
- `.env.example` - Template for secrets

## Upload Methods
### Option 1: SCP from Windows
```powershell
scp -i "C:\Users\dekim\.ssh\oracle_keys\ssh-key-2026-09-14.key" -r "C:\Users\dekim\OneDrive\Belgeler\raid-bot-skeleton\*" opc@158.180.18.220:~/
```

### Option 2: Git clone (if pushed to GitHub)
```bash
git clone https://github.com/raigulus/raid-bot.git
```

## Post-Upload Steps
1. SSH into instance
2. `cd raid-bot-skeleton` (or wherever files are)
3. Create `.env` file with Discord token
4. `docker-compose up -d`
5. Check logs: `docker-compose logs -f`

## Important Notes
- 1GB RAM = use SQLite instead of PostgreSQL to save resources
- Discord token must be set in .env file
- Bot auto-creates 8 Discord roles on first boot
- Raid Host role must be assigned manually to initial hosts
- Guild invite: discord.gg/xj8jnS3Gkh
- Loot channel ID: 1528506012900917268
- Loot role: @&1532384877557846057
