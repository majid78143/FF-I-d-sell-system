# FreeFire Hub — Complete Platform

A production-ready Flask website + Discord Bot platform for Free Fire services.  
Single repository, single Render deployment, shared Firebase backend.

---

## Quick Start (Render)

1. Push this project to a GitHub/GitLab repo.
2. Create a new **Web Service** on Render pointing to your repo.
3. Set **Start Command**: `python start.py`
4. Add the required environment variables (see below).
5. Deploy.

---

## Required Environment Variables

Set these in Render → Environment:

| Variable | Description |
|---|---|
| `TOKEN` | Discord Bot token (from Discord Developer Portal) |
| `SECRET_KEY` | Flask session secret — any long random string |
| `OWNER_EMAIL` | Email used to log in as Owner at `/login` |
| `OWNER_PASSWORD` | Password for the Owner account |

---

## Optional Environment Variables

| Variable | Description | Default |
|---|---|---|
| `PORT` | Web server port | `5000` |
| `DEBUG` | Set `true` for Flask debug mode | `false` |
| `GOOGLE_APPLICATION_CREDENTIALS` | Path to Firebase service account JSON | `firebase_credentials.json` |
| `GUNICORN_WORKERS` | Number of Gunicorn worker processes | `2` |

---

## File Reference

### `config.py` — Firebase, App, Default Branding & Settings
- **Firebase settings**: `FIREBASE_CONFIG` dict → `databaseURL`, `storageBucket`, `projectId`
- **Default branding**: `DEFAULT_BRANDING` — site name, logo URL, favicon URL, colors, footer text
- **Default settings**: `DEFAULT_SETTINGS` — like sender limit, AI toggle, ads, maintenance mode
- **Environment variables**: `TOKEN`, `SECRET_KEY`, `OWNER_EMAIL`, `OWNER_PASSWORD`

> ⚠️ Replace `"apiKey": "AIzaSyPlaceholderKeyReplaceWithRealKey"` in `FIREBASE_CONFIG` with your real Firebase Web API key.

---

### `firebase_service.py` — All Firebase Operations
- Handles all reads/writes to Firebase Realtime Database
- Used by both `app.py` (Flask website) and `bot.py` (Discord bot)
- No direct API calls from the website — all tool results flow through Firebase

---

### `app.py` — Flask Website
- All website routes and page rendering
- **API flow**: Website → Firebase request queue → (bot processes) → Firebase result → Website
- Admin panel at `/admin` (owner or admin role required)
- Owner panel features at `/admin/settings`, `/admin/branding`, `/admin/apis`

---

### `bot.py` — Discord Bot
- **Discord settings**: Reads `TOKEN` from environment
- Processes Firebase request queue every 2 seconds
- Slash commands: `/announcement`, `/partner`, `/theme`, `/api`, `/likes`, `/logs`, `/admin`, `/branding`, `/page`, `/permission`
- **Bot log channels**: Send logs directly to Discord using `db.add_log()` — extend `bot.py` to forward logs to a Discord channel

---

### `start.py` — Startup Script
- Starts Flask (via Gunicorn in production, Flask dev server if `DEBUG=true`) in one thread
- Starts Discord bot in a second thread
- Single process — compatible with Render's free/paid tiers

---

## Settings Reference

All settings below live in **Firebase** after first boot (overridable from Owner Panel at `/admin/settings`):

### Like Sender Settings
- File: `config.py` → `DEFAULT_SETTINGS`
- Key: `like_sender_enabled` (bool), `like_sender_daily_limit` (int, default 20)
- Override: Owner Panel → Settings → Like Sender, or Discord `/likes setlimit <n>`

### ID Visits Settings
- Key: `id_visits_enabled` (bool)
- Override: Owner Panel → Settings → ID Visits

### AI Assistant Settings
- Key: `ai_enabled`, `ai_provider`, `ai_model`, `ai_prompt`
- **Important**: You must add an API config with `tool=ai_chat` in the API Management panel.
  - For OpenAI: URL = `https://api.openai.com/v1/chat/completions`, Headers = `{"Authorization": "Bearer YOUR_KEY", "Content-Type": "application/json"}`
- Override: Owner Panel → Settings → AI Assistant

### Ads (Adsterra) Settings
- Key: `ads_enabled`, `ads_smart_link`, `ads_popup`, `ads_social_bar`, `ads_banner`
- Override: Owner Panel → Settings → Ads
- Replace the Adsterra script URLs in `templates/base.html` with your real Adsterra codes

### Maintenance Mode
- Key: `maintenance_mode` (bool)
- Override: Owner Panel → Settings or Discord `/page maintenance on`

### Registration
- Key: `registration_open` (bool)
- Override: Owner Panel → Settings or Discord `/page registration off`

---

## Branding Settings

All branding is stored in Firebase and loaded dynamically on every page request.

| Setting | Where to change |
|---|---|
| **Logo URL** | Owner Panel → Branding, or Discord `/theme logo_url <url>` |
| **Favicon URL** | Owner Panel → Branding, or Discord `/theme favicon_url <url>` |
| **Site Name** | Owner Panel → Branding |
| **Primary Color** | Owner Panel → Branding |
| **Secondary Color** | Owner Panel → Branding |
| **Footer Text** | Owner Panel → Branding |
| Default values | `config.py` → `DEFAULT_BRANDING` |

---

## Discord Settings

| Setting | Where to change |
|---|---|
| **Bot token** | Environment variable `TOKEN` |
| **Bot slash commands** | `bot.py` → `@tree.command(...)` blocks |
| **Queue poll interval** | `bot.py` → `@tasks.loop(seconds=2)` |
| **Owner detection** | Link Discord account to website account with `role=owner` in Firebase |

---

## Firebase Settings

Located in `config.py` → `FIREBASE_CONFIG`:

```python
FIREBASE_CONFIG = {
    "apiKey": "YOUR_REAL_KEY_HERE",          # ← Replace this
    "databaseURL": "https://web-massaging-589b7-default-rtdb.firebaseio.com",
    "storageBucket": "web-massaging-589b7.firebasestorage.app",
    "projectId": "web-massaging-589b7",
    ...
}
```

Firebase Realtime Database structure:
- `users/` — user accounts
- `guilds/` — Discord guild data
- `partners/` — partner server entries
- `announcements/` — announcements
- `request_queue/` — tool request queue (website → bot)
- `api_configs/` — API configurations (managed from admin panel)
- `settings/general` — platform settings
- `settings/branding` — branding settings
- `like_logs/` — daily like sender usage
- `visit_logs/` — ID visits log
- `logs/` — general platform logs

> **Security**: The REST API is used without Firebase Auth tokens for simplicity. For production, set your Firebase Realtime Database rules to require auth, and use the Firebase Admin SDK with a service account JSON (`firebase_credentials.json`).

---

## API Management

All Free Fire tool APIs are configured from the **Owner Panel → API Management** (`/admin/apis`).

Each API config has:
- **Name**: Human-readable label
- **Tool key**: maps to a tool (e.g. `profile`, `like_send`, `ai_chat`)
- **URL**: API endpoint, with `{uid}`, `{region}`, `{name}` placeholders
- **Method**: GET or POST
- **Headers**: JSON object (e.g. `{"Authorization": "Bearer TOKEN"}`)
- **Extra Params**: Additional fixed parameters

Example for a profile lookup API:
```
Tool: profile
URL:  https://your-ff-api.com/player?uid={uid}&region={region}
Headers: {"key": "your-api-key"}
```

You can also add/remove/enable/disable APIs via Discord: `/api list`, `/api enable <id>`, etc.

---

## Admin System

- **Owner** logs in with `OWNER_EMAIL` / `OWNER_PASSWORD` env vars
- **Admins** are granted via Discord `/admin grant <discord_id>` — the Discord user must first register on the website with the same Discord ID linked
- **Permissions**: Owner > Admin > User
  - Owner: all settings, branding, APIs, user roles
  - Admin: announcements, partners, logs, view users

---

## Premium System

Disabled by default. Enable later:
- Key: `premium_enabled` in Firebase `settings/general`
- Razorpay integration: add Razorpay script and payment routes to `app.py`

---

## Project Structure

```
freefire-platform/
├── app.py                  Flask website (all routes)
├── bot.py                  Discord bot (queue processor + slash commands)
├── start.py                Unified startup (Flask + Bot)
├── config.py               Firebase config, env vars, defaults
├── firebase_service.py     All Firebase read/write operations
├── requirements.txt        Python dependencies
├── Procfile                Render start command
├── README.md               This file
├── templates/
│   ├── base.html           Base layout (navbar, footer, flash messages)
│   ├── index.html          Homepage
│   ├── tools.html          Tools directory
│   ├── tools/              Individual tool pages
│   │   ├── profile.html
│   │   ├── player_search.html
│   │   ├── guild_search.html
│   │   ├── uid_info.html
│   │   ├── region_checker.html
│   │   ├── like_sender.html
│   │   ├── id_visits.html
│   │   ├── guild_rankings.html
│   │   └── player_rankings.html
│   ├── guilds.html
│   ├── guild_detail.html
│   ├── partners.html
│   ├── announcements.html
│   ├── support.html
│   ├── aichat.html
│   ├── login.html
│   ├── register.html
│   ├── admin/              Admin panel pages
│   │   ├── dashboard.html
│   │   ├── settings.html
│   │   ├── branding.html
│   │   ├── users.html
│   │   ├── apis.html
│   │   ├── announcements.html
│   │   ├── partners.html
│   │   └── logs.html
│   └── errors/
│       ├── 403.html
│       ├── 404.html
│       ├── 500.html
│       └── maintenance.html
└── static/
    ├── css/
    │   └── main.css        All styles (responsive, mobile-first)
    └── js/
        ├── main.js         Core JS (navbar, forms, loading states)
        ├── animations.js   Count-up, fade-in, particle hero
        └── aichat.js       AI chat interface logic
```

---

## Deployment Checklist

- [ ] Replace `apiKey` placeholder in `config.py` with your real Firebase Web API key
- [ ] Set `TOKEN`, `SECRET_KEY`, `OWNER_EMAIL`, `OWNER_PASSWORD` in Render environment
- [ ] Configure at least one API per tool in Owner Panel → API Management
- [ ] Add the Discord bot to your server; run `/api list` to verify it's working
- [ ] Add support servers via the admin panel or Firebase directly
- [ ] Test the Like Sender end-to-end: website → Firebase → bot → Firebase → result
- [ ] Optionally set Firebase Security Rules to restrict writes to authenticated admin users
