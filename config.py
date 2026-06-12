import os

# ─── Environment Variables (set in Render) ────────────────────────────────────
TOKEN          = os.environ.get("TOKEN", "")
SECRET_KEY     = os.environ.get("SECRET_KEY", "change-me-in-render")
OWNER_EMAIL    = os.environ.get("OWNER_EMAIL", "owner@example.com")
OWNER_PASSWORD = os.environ.get("OWNER_PASSWORD", "changeme123")

# ─── Firebase Config (stored here; all other settings live in Firebase) ───────
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyPlaceholderKeyReplaceWithRealKey",
    "authDomain": "web-massaging-589b7.firebaseapp.com",
    "databaseURL": "https://web-massaging-589b7-default-rtdb.firebaseio.com",
    "projectId": "web-massaging-589b7",
    "storageBucket": "web-massaging-589b7.firebasestorage.app",
    "messagingSenderId": "000000000000",
    "appId": "1:000000000000:web:000000000000000000000000",
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
    "logo_url":       "https://i.imgur.com/placeholder_logo.png",
    "favicon_url":    "https://i.imgur.com/placeholder_favicon.png",
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
