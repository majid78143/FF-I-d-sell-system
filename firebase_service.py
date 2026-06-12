"""
firebase_service.py
All Firebase Realtime Database and Storage operations.
"""

import json
import time
import datetime
import logging
import requests
from functools import lru_cache
from config import FIREBASE_DATABASE_URL, DEFAULT_BRANDING, DEFAULT_SETTINGS

logger = logging.getLogger(__name__)


def _db_url(path: str) -> str:
    """Build a Firebase REST URL."""
    path = path.strip("/")
    return f"{FIREBASE_DATABASE_URL}/{path}.json"


def fb_get(path: str, default=None):
    """Read from Firebase Realtime DB (REST, no auth)."""
    try:
        r = requests.get(_db_url(path), timeout=10)
        if r.status_code == 200:
            data = r.json()
            return data if data is not None else default
    except Exception as e:
        logger.error(f"[Firebase GET] {path}: {e}")
    return default


def fb_set(path: str, data) -> bool:
    """Write (PUT) to Firebase Realtime DB."""
    try:
        r = requests.put(_db_url(path), json=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        logger.error(f"[Firebase SET] {path}: {e}")
        return False


def fb_push(path: str, data) -> str | None:
    """Push (POST) a new child to Firebase and return its key."""
    try:
        r = requests.post(_db_url(path), json=data, timeout=10)
        if r.status_code == 200:
            return r.json().get("name")
    except Exception as e:
        logger.error(f"[Firebase PUSH] {path}: {e}")
    return None


def fb_patch(path: str, data) -> bool:
    """Update (PATCH) specific fields at path."""
    try:
        r = requests.patch(_db_url(path), json=data, timeout=10)
        return r.status_code == 200
    except Exception as e:
        logger.error(f"[Firebase PATCH] {path}: {e}")
        return False


def fb_delete(path: str) -> bool:
    """Delete a node from Firebase."""
    try:
        r = requests.delete(_db_url(path), timeout=10)
        return r.status_code == 200
    except Exception as e:
        logger.error(f"[Firebase DELETE] {path}: {e}")
        return False


# ─── Branding ─────────────────────────────────────────────────────────────────

def get_branding() -> dict:
    data = fb_get("settings/branding", {})
    branding = {**DEFAULT_BRANDING, **data}
    return branding


def set_branding(data: dict) -> bool:
    return fb_patch("settings/branding", data)


# ─── Settings ─────────────────────────────────────────────────────────────────

def get_settings() -> dict:
    data = fb_get("settings/general", {})
    return {**DEFAULT_SETTINGS, **data}


def update_settings(data: dict) -> bool:
    return fb_patch("settings/general", data)


# ─── Users ────────────────────────────────────────────────────────────────────

def get_user_by_email(email: str) -> dict | None:
    users = fb_get("users", {}) or {}
    for uid, u in users.items():
        if u.get("email", "").lower() == email.lower():
            return {**u, "id": uid}
    return None


def get_user_by_discord(discord_id: str) -> dict | None:
    users = fb_get("users", {}) or {}
    for uid, u in users.items():
        if str(u.get("discord_id", "")) == str(discord_id):
            return {**u, "id": uid}
    return None


def get_user_by_id(uid: str) -> dict | None:
    u = fb_get(f"users/{uid}")
    if u:
        return {**u, "id": uid}
    return None


def create_user(data: dict) -> str | None:
    data["created_at"] = _ts()
    data["role"] = data.get("role", "user")
    return fb_push("users", data)


def update_user(uid: str, data: dict) -> bool:
    return fb_patch(f"users/{uid}", data)


def get_all_users() -> list:
    users = fb_get("users", {}) or {}
    return [{"id": k, **v} for k, v in users.items()]


# ─── Announcements ────────────────────────────────────────────────────────────

def get_announcements(limit: int = 20) -> list:
    data = fb_get("announcements", {}) or {}
    items = [{"id": k, **v} for k, v in data.items()]
    items.sort(key=lambda x: x.get("created_at", 0), reverse=True)
    return items[:limit]


def create_announcement(data: dict) -> str | None:
    data["created_at"] = _ts()
    return fb_push("announcements", data)


def update_announcement(ann_id: str, data: dict) -> bool:
    return fb_patch(f"announcements/{ann_id}", data)


def delete_announcement(ann_id: str) -> bool:
    return fb_delete(f"announcements/{ann_id}")


# ─── Partners ─────────────────────────────────────────────────────────────────

def get_partners() -> list:
    data = fb_get("partners", {}) or {}
    return [{"id": k, **v} for k, v in data.items()]


def create_partner(data: dict) -> str | None:
    data["created_at"] = _ts()
    return fb_push("partners", data)


def update_partner(pid: str, data: dict) -> bool:
    return fb_patch(f"partners/{pid}", data)


def delete_partner(pid: str) -> bool:
    return fb_delete(f"partners/{pid}")


# ─── Support Servers ──────────────────────────────────────────────────────────

def get_support_servers() -> list:
    data = fb_get("support_servers", {}) or {}
    return [{"id": k, **v} for k, v in data.items()]


# ─── Guilds ───────────────────────────────────────────────────────────────────

def get_guilds(limit: int = 50) -> list:
    data = fb_get("guilds", {}) or {}
    items = [{"id": k, **v} for k, v in data.items()]
    items.sort(key=lambda x: x.get("member_count", 0), reverse=True)
    return items[:limit]


def get_guild(guild_id: str) -> dict | None:
    g = fb_get(f"guilds/{guild_id}")
    if g:
        return {**g, "id": guild_id}
    return None


def upsert_guild(guild_id: str, data: dict) -> bool:
    return fb_patch(f"guilds/{guild_id}", data)


# ─── API Configurations ───────────────────────────────────────────────────────

def get_apis() -> list:
    data = fb_get("api_configs", {}) or {}
    return [{"id": k, **v} for k, v in data.items()]


def get_api(api_id: str) -> dict | None:
    a = fb_get(f"api_configs/{api_id}")
    if a:
        return {**a, "id": api_id}
    return None


def create_api_config(data: dict) -> str | None:
    data["created_at"] = _ts()
    data["enabled"] = data.get("enabled", True)
    return fb_push("api_configs", data)


def update_api_config(api_id: str, data: dict) -> bool:
    return fb_patch(f"api_configs/{api_id}", data)


def delete_api_config(api_id: str) -> bool:
    return fb_delete(f"api_configs/{api_id}")


# ─── Request Queue ────────────────────────────────────────────────────────────

def enqueue_request(tool: str, params: dict, user_id: str = "anonymous") -> str | None:
    data = {
        "tool":      tool,
        "params":    params,
        "user_id":   user_id,
        "status":    "pending",
        "created_at": _ts(),
        "result":    None,
    }
    return fb_push("request_queue", data)


def get_queue_item(req_id: str) -> dict | None:
    item = fb_get(f"request_queue/{req_id}")
    if item:
        return {**item, "id": req_id}
    return None


def update_queue_item(req_id: str, data: dict) -> bool:
    return fb_patch(f"request_queue/{req_id}", data)


def get_pending_requests() -> list:
    data = fb_get("request_queue", {}) or {}
    items = [{"id": k, **v} for k, v in data.items() if v.get("status") == "pending"]
    items.sort(key=lambda x: x.get("created_at", 0))
    return items


# ─── Like Sender ──────────────────────────────────────────────────────────────

def get_like_log_today() -> dict:
    today = datetime.date.today().isoformat()
    return fb_get(f"like_logs/{today}", {}) or {}


def log_like_sent(uid: str, region: str) -> bool:
    today = datetime.date.today().isoformat()
    entry = {
        "uid":    uid,
        "region": region,
        "ts":     _ts(),
    }
    key = fb_push(f"like_logs/{today}", entry)
    return key is not None


def count_likes_today() -> int:
    return len(get_like_log_today())


def uid_liked_today(uid: str) -> bool:
    log = get_like_log_today()
    return any(v.get("uid") == uid for v in log.values())


def reset_like_cache() -> bool:
    today = datetime.date.today().isoformat()
    return fb_delete(f"like_logs/{today}")


# ─── Visit Logs ───────────────────────────────────────────────────────────────

def log_visit(uid: str, region: str) -> bool:
    today = datetime.date.today().isoformat()
    entry = {"uid": uid, "region": region, "ts": _ts()}
    return fb_push(f"visit_logs/{today}", entry) is not None


# ─── General Logs ─────────────────────────────────────────────────────────────

def add_log(category: str, data: dict) -> bool:
    data["ts"] = _ts()
    key = fb_push(f"logs/{category}", data)
    return key is not None


def get_logs(category: str, limit: int = 100) -> list:
    data = fb_get(f"logs/{category}", {}) or {}
    items = [{"id": k, **v} for k, v in data.items()]
    items.sort(key=lambda x: x.get("ts", 0), reverse=True)
    return items[:limit]


# ─── Site Stats ───────────────────────────────────────────────────────────────

def get_stats() -> dict:
    users    = fb_get("users", {}) or {}
    guilds   = fb_get("guilds", {}) or {}
    partners = fb_get("partners", {}) or {}
    anns     = fb_get("announcements", {}) or {}
    return {
        "total_users":    len(users),
        "total_guilds":   len(guilds),
        "total_partners": len(partners),
        "announcements":  len(anns),
        "like_uses_today": count_likes_today(),
    }


# ─── AI Logs ──────────────────────────────────────────────────────────────────

def log_ai_message(user_id: str, message: str, reply: str) -> bool:
    return add_log("ai", {"user_id": user_id, "message": message, "reply": reply})


# ─── Helper ───────────────────────────────────────────────────────────────────

def _ts() -> int:
    return int(time.time())
