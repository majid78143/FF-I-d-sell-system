import os

# ─── Environment Variables (set in Render) ────────────────────────────────────
TOKEN          = os.environ.get("TOKEN", "")
SECRET_KEY     = os.environ.get("SECRET_KEY", "change-me-in-render")
OWNER_EMAIL    = os.environ.get("OWNER_EMAIL", "owner@example.com")
OWNER_PASSWORD = os.environ.get("OWNER_PASSWORD", "changeme123")

# ─── Firebase Config (stored here; all other settings live in Firebase) ───────
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyD3ML9k7RSbeoVze0su8PoE69llfgeqr1k",
    "authDomain": "codeforge-d3aa2.firebaseapp.com",
    "databaseURL": "https://codeforge-d3aa2-default-rtdb.firebaseio.com",
    "projectId": "codeforge-d3aa2",
    "storageBucket": "https://codeforge-d3aa2-default-rtdb.firebaseio.com",
    "messagingSenderId": "907268826856",
    "appId": "1:907268826856:web:aedb8eb1c674bad9ab4b5d",
}

FIREBASE_DATABASE_URL = FIREBASE_CONFIG["databaseURL"]
FIREBASE_STORAGE_BUCKET = FIREBASE_CONFIG["storageBucket"]

# Path to your Firebase service account JSON (optional for server-side admin)
# Place as firebase_credentials.json in project root, or set GOOGLE_APPLICATION_CREDENTIALS
FIREBASE_CREDENTIALS_PATH = os.environ.get(
    "GOOGLE_APPLICATION_CREDENTIALS", "firebase_credentials.json"
)

# ─── App Settings ─────────────────────────────────────────────────────────────
DEBUG = os.environ.get("DEBUG", "false").lower() == "true"
PORT  = int(os.environ.get("PORT", 5000))

# ─── Default Branding (overridden by Firebase) ────────────────────────────────
DEFAULT_BRANDING = {
    "site_name":      "FreeFire Hub",
    "logo_url":       "https://i.supaimg.com/9ec0882f-b6ce-4a93-a2bd-61aad960c7c2/f2301d04-9fb5-44da-8eb4-0a189525ca3e.png",
    "favicon_url":    "https://i.supaimg.com/9ec0882f-b6ce-4a93-a2bd-61aad960c7c2/f2301d04-9fb5-44da-8eb4-0a189525ca3e.png",
    "footer_text":    "© 2025 FreeFire Hub. All rights reserved.",
    "primary_color":  "#0070f3",
    "secondary_color":"#7928ca",
}

# ─── Default Settings (overridden by Firebase) ────────────────────────────────
DEFAULT_SETTINGS = {
    "like_sender_enabled":    True,
    "like_sender_daily_limit": 20,
    "id_visits_enabled":      True,
    "ai_enabled":             True,
    "ai_provider":            "openai",
    "ai_model":               "gpt-3.5-turbo",
    "ai_prompt":              "You are a helpful Free Fire gaming assistant.",
    "ads_enabled":            False,
    "ads_smart_link":         "",
    "ads_popup":              False,
    "ads_social_bar":         False,
    "ads_banner":             False,
    "premium_enabled":        False,
    "maintenance_mode":       False,
    "registration_open":      True,
}
