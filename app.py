"""
app.py  –  Flask web application
All API calls flow through Firebase → Discord Bot → Firebase → Website
"""

import os
import time
import hashlib
import logging
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for,
    session, jsonify, abort, flash
)
import firebase_service as db
from config import SECRET_KEY, OWNER_EMAIL, OWNER_PASSWORD, DEBUG

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = not DEBUG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REGIONS = ["IND", "BR", "SG", "RU", "ID", "TW", "US", "VN", "TH", "ME", "PK", "CIS", "BD"]
POLL_TIMEOUT = 30   # seconds to wait for bot response
POLL_INTERVAL = 1   # seconds between polls


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


def get_ctx() -> dict:
    """Context injected into every template."""
    branding  = db.get_branding()
    settings  = db.get_settings()
    user_id   = session.get("user_id")
    user_role = session.get("role", "guest")
    return {
        "branding":  branding,
        "settings":  settings,
        "user_id":   user_id,
        "user_role": user_role,
        "logged_in": user_id is not None,
        "is_admin":  user_role in ("admin", "owner"),
        "is_owner":  user_role == "owner",
    }


def poll_for_result(req_id: str, timeout: int = POLL_TIMEOUT) -> dict | None:
    """Poll Firebase until the bot sets status=done or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        item = db.get_queue_item(req_id)
        if item and item.get("status") == "done":
            return item.get("result")
        if item and item.get("status") == "error":
            return {"error": item.get("error_message", "Bot returned an error")}
        time.sleep(POLL_INTERVAL)
    return {"error": "Request timed out. The bot may be offline."}


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") not in ("admin", "owner"):
            abort(403)
        return f(*args, **kwargs)
    return decorated


def owner_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "owner":
            abort(403)
        return f(*args, **kwargs)
    return decorated


# ─── Context processor ────────────────────────────────────────────────────────

@app.context_processor
def inject_globals():
    return get_ctx()


# ─── Public Pages ─────────────────────────────────────────────────────────────

@app.route("/")
def index():
    announcements = db.get_announcements(5)
    partners      = db.get_partners()
    guilds        = db.get_guilds(6)
    stats         = db.get_stats()
    support       = db.get_support_servers()
    return render_template(
        "index.html",
        announcements=announcements,
        partners=partners,
        guilds=guilds,
        stats=stats,
        support_servers=support,
    )


@app.route("/tools")
def tools():
    return render_template("tools.html")


@app.route("/guilds")
def guilds_page():
    guilds = db.get_guilds(50)
    return render_template("guilds.html", guilds=guilds)


@app.route("/guilds/<guild_id>")
def guild_detail(guild_id):
    guild = db.get_guild(guild_id)
    if not guild:
        abort(404)
    return render_template("guild_detail.html", guild=guild)


@app.route("/partners")
def partners_page():
    partners = db.get_partners()
    return render_template("partners.html", partners=partners)


@app.route("/announcements")
def announcements_page():
    anns = db.get_announcements(50)
    return render_template("announcements.html", announcements=anns)


@app.route("/support")
def support_page():
    servers = db.get_support_servers()
    return render_template("support.html", support_servers=servers)


@app.route("/aichat")
def aichat():
    settings = db.get_settings()
    return render_template("aichat.html", ai_enabled=settings.get("ai_enabled", True))


# ─── Auth ─────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        # Owner login
        if email == OWNER_EMAIL.lower() and password == OWNER_PASSWORD:
            session["user_id"]   = "owner"
            session["role"]      = "owner"
            session["email"]     = email
            session["username"]  = "Owner"
            db.add_log("security", {"event": "owner_login", "ip": _get_ip()})
            return redirect(url_for("admin_dashboard"))

        # Regular user
        user = db.get_user_by_email(email)
        if user and user.get("password_hash") == _hash_pw(password):
            if not user.get("active", True):
                flash("Your account has been disabled.", "error")
                return render_template("login.html")
            session["user_id"]  = user["id"]
            session["role"]     = user.get("role", "user")
            session["email"]    = email
            session["username"] = user.get("username", "User")
            db.add_log("security", {"event": "login", "user_id": user["id"], "ip": _get_ip()})
            next_url = request.args.get("next", url_for("index"))
            return redirect(next_url)

        flash("Invalid email or password.", "error")
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    settings = db.get_settings()
    if not settings.get("registration_open", True):
        flash("Registration is currently closed.", "info")
        return redirect(url_for("login"))

    if request.method == "POST":
        email    = request.form.get("email", "").strip().lower()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm_password", "")

        if not email or not username or not password:
            flash("All fields are required.", "error")
            return render_template("register.html")
        if password != confirm:
            flash("Passwords do not match.", "error")
            return render_template("register.html")
        if len(password) < 6:
            flash("Password must be at least 6 characters.", "error")
            return render_template("register.html")
        if db.get_user_by_email(email):
            flash("Email already registered.", "error")
            return render_template("register.html")

        uid = db.create_user({
            "email":         email,
            "username":      username,
            "password_hash": _hash_pw(password),
            "role":          "user",
            "active":        True,
            "provider":      "email",
        })
        if uid:
            session["user_id"]  = uid
            session["role"]     = "user"
            session["email"]    = email
            session["username"] = username
            db.add_log("security", {"event": "register", "user_id": uid, "ip": _get_ip()})
            flash("Account created successfully!", "success")
            return redirect(url_for("index"))

        flash("Registration failed. Please try again.", "error")
    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ─── Tools ────────────────────────────────────────────────────────────────────

@app.route("/tools/profile", methods=["GET", "POST"])
def tool_profile():
    result = None
    if request.method == "POST":
        uid    = request.form.get("uid", "").strip()
        region = request.form.get("region", "IND")
        if uid:
            req_id = db.enqueue_request("profile", {"uid": uid, "region": region},
                                         session.get("user_id", "anonymous"))
            result = poll_for_result(req_id)
            db.add_log("tools", {"tool": "profile", "uid": uid, "region": region,
                                  "user_id": session.get("user_id", "anon")})
    return render_template("tools/profile.html", result=result, regions=REGIONS)


@app.route("/tools/player-search", methods=["GET", "POST"])
def tool_player_search():
    result = None
    if request.method == "POST":
        name   = request.form.get("name", "").strip()
        region = request.form.get("region", "IND")
        if name:
            req_id = db.enqueue_request("player_search", {"name": name, "region": region},
                                         session.get("user_id", "anonymous"))
            result = poll_for_result(req_id)
    return render_template("tools/player_search.html", result=result, regions=REGIONS)


@app.route("/tools/guild-search", methods=["GET", "POST"])
def tool_guild_search():
    result = None
    if request.method == "POST":
        name   = request.form.get("name", "").strip()
        region = request.form.get("region", "IND")
        if name:
            req_id = db.enqueue_request("guild_search", {"name": name, "region": region},
                                         session.get("user_id", "anonymous"))
            result = poll_for_result(req_id)
    return render_template("tools/guild_search.html", result=result, regions=REGIONS)


@app.route("/tools/uid-info", methods=["GET", "POST"])
def tool_uid_info():
    result = None
    if request.method == "POST":
        uid    = request.form.get("uid", "").strip()
        region = request.form.get("region", "IND")
        if uid:
            req_id = db.enqueue_request("uid_info", {"uid": uid, "region": region},
                                         session.get("user_id", "anonymous"))
            result = poll_for_result(req_id)
    return render_template("tools/uid_info.html", result=result, regions=REGIONS)


@app.route("/tools/region-checker", methods=["GET", "POST"])
def tool_region_checker():
    result = None
    if request.method == "POST":
        uid = request.form.get("uid", "").strip()
        if uid:
            req_id = db.enqueue_request("region_check", {"uid": uid},
                                         session.get("user_id", "anonymous"))
            result = poll_for_result(req_id)
    return render_template("tools/region_checker.html", result=result)


@app.route("/tools/like-sender", methods=["GET", "POST"])
def tool_like_sender():
    settings = db.get_settings()
    result   = None
    error    = None

    if request.method == "POST":
        if not settings.get("like_sender_enabled", True):
            error = "Like Sender is currently disabled."
        else:
            uid    = request.form.get("uid", "").strip()
            region = request.form.get("region", "IND")

            if not uid:
                error = "Please enter a valid UID."
            elif db.uid_liked_today(uid):
                error = "This UID has already received likes today."
            elif db.count_likes_today() >= settings.get("like_sender_daily_limit", 20):
                error = "Daily limit reached. Please try again tomorrow."
            else:
                req_id = db.enqueue_request("like_send", {"uid": uid, "region": region},
                                             session.get("user_id", "anonymous"))
                result = poll_for_result(req_id)
                if result and not result.get("error"):
                    db.log_like_sent(uid, region)
                    db.add_log("likes", {"uid": uid, "region": region,
                                          "user_id": session.get("user_id", "anon")})

    likes_today = db.count_likes_today()
    daily_limit = settings.get("like_sender_daily_limit", 20)
    return render_template("tools/like_sender.html",
                           result=result, error=error,
                           likes_today=likes_today, daily_limit=daily_limit,
                           regions=REGIONS)


@app.route("/tools/id-visits", methods=["GET", "POST"])
def tool_id_visits():
    settings = db.get_settings()
    result   = None
    error    = None

    if request.method == "POST":
        if not settings.get("id_visits_enabled", True):
            error = "ID Visits is currently disabled."
        else:
            uid    = request.form.get("uid", "").strip()
            region = request.form.get("region", "IND")
            if uid:
                req_id = db.enqueue_request("id_visits", {"uid": uid, "region": region},
                                             session.get("user_id", "anonymous"))
                result = poll_for_result(req_id)
                if result and not result.get("error"):
                    db.log_visit(uid, region)
                    db.add_log("visits", {"uid": uid, "region": region,
                                           "user_id": session.get("user_id", "anon")})
    return render_template("tools/id_visits.html", result=result, error=error, regions=REGIONS)


@app.route("/tools/guild-rankings")
def tool_guild_rankings():
    guilds = db.get_guilds(50)
    return render_template("tools/guild_rankings.html", guilds=guilds)


@app.route("/tools/player-rankings")
def tool_player_rankings():
    req_id = db.enqueue_request("player_rankings", {})
    result = poll_for_result(req_id, timeout=15)
    return render_template("tools/player_rankings.html", result=result)


# ─── AI Chat API ──────────────────────────────────────────────────────────────

@app.route("/api/ai/chat", methods=["POST"])
def api_ai_chat():
    settings = db.get_settings()
    if not settings.get("ai_enabled", True):
        return jsonify({"error": "AI assistant is currently disabled."}), 503

    data    = request.get_json(force=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Empty message"}), 400

    req_id = db.enqueue_request("ai_chat", {
        "message":  message,
        "provider": settings.get("ai_provider", "openai"),
        "model":    settings.get("ai_model", "gpt-3.5-turbo"),
        "prompt":   settings.get("ai_prompt", "You are a helpful Free Fire gaming assistant."),
    }, session.get("user_id", "anonymous"))

    result = poll_for_result(req_id, timeout=30)
    if result and not result.get("error"):
        db.log_ai_message(session.get("user_id", "anon"), message, result.get("reply", ""))
    return jsonify(result or {"error": "No response"})


# ─── Admin Panel ──────────────────────────────────────────────────────────────

@app.route("/admin")
@admin_required
def admin_dashboard():
    stats    = db.get_stats()
    settings = db.get_settings()
    branding = db.get_branding()
    recent_logs = db.get_logs("tools", 20)
    return render_template("admin/dashboard.html",
                           stats=stats, settings=settings,
                           branding=branding, recent_logs=recent_logs)


@app.route("/admin/settings", methods=["GET", "POST"])
@owner_required
def admin_settings():
    if request.method == "POST":
        form = request.form
        new_settings = {
            "like_sender_enabled":    form.get("like_sender_enabled") == "on",
            "like_sender_daily_limit": int(form.get("like_sender_daily_limit", 20)),
            "id_visits_enabled":      form.get("id_visits_enabled") == "on",
            "ai_enabled":             form.get("ai_enabled") == "on",
            "ai_provider":            form.get("ai_provider", "openai"),
            "ai_model":               form.get("ai_model", "gpt-3.5-turbo"),
            "ai_prompt":              form.get("ai_prompt", ""),
            "ads_enabled":            form.get("ads_enabled") == "on",
            "ads_smart_link":         form.get("ads_smart_link", ""),
            "ads_popup":              form.get("ads_popup") == "on",
            "ads_social_bar":         form.get("ads_social_bar") == "on",
            "ads_banner":             form.get("ads_banner") == "on",
            "maintenance_mode":       form.get("maintenance_mode") == "on",
            "registration_open":      form.get("registration_open") == "on",
        }
        db.update_settings(new_settings)
        db.add_log("admin", {"event": "settings_updated", "by": session.get("user_id")})
        flash("Settings saved.", "success")
        return redirect(url_for("admin_settings"))
    settings = db.get_settings()
    return render_template("admin/settings.html", settings=settings)


@app.route("/admin/branding", methods=["GET", "POST"])
@owner_required
def admin_branding():
    if request.method == "POST":
        form = request.form
        db.set_branding({
            "site_name":      form.get("site_name", ""),
            "logo_url":       form.get("logo_url", ""),
            "favicon_url":    form.get("favicon_url", ""),
            "footer_text":    form.get("footer_text", ""),
            "primary_color":  form.get("primary_color", "#0070f3"),
            "secondary_color":form.get("secondary_color", "#7928ca"),
        })
        db.add_log("admin", {"event": "branding_updated", "by": session.get("user_id")})
        flash("Branding saved.", "success")
        return redirect(url_for("admin_branding"))
    branding = db.get_branding()
    return render_template("admin/branding.html", branding=branding)


@app.route("/admin/users")
@admin_required
def admin_users():
    users = db.get_all_users()
    return render_template("admin/users.html", users=users)


@app.route("/admin/users/<uid>/toggle", methods=["POST"])
@admin_required
def admin_toggle_user(uid):
    user = db.get_user_by_id(uid)
    if user:
        db.update_user(uid, {"active": not user.get("active", True)})
        db.add_log("admin", {"event": "user_toggled", "uid": uid, "by": session.get("user_id")})
    return redirect(url_for("admin_users"))


@app.route("/admin/users/<uid>/role", methods=["POST"])
@owner_required
def admin_set_role(uid):
    role = request.form.get("role", "user")
    if role in ("user", "admin"):
        db.update_user(uid, {"role": role})
        db.add_log("admin", {"event": "role_changed", "uid": uid, "role": role,
                               "by": session.get("user_id")})
    return redirect(url_for("admin_users"))


@app.route("/admin/apis", methods=["GET"])
@admin_required
def admin_apis():
    apis = db.get_apis()
    return render_template("admin/apis.html", apis=apis)


@app.route("/admin/apis/add", methods=["POST"])
@owner_required
def admin_add_api():
    data = {
        "name":    request.form.get("name", ""),
        "tool":    request.form.get("tool", ""),
        "url":     request.form.get("url", ""),
        "method":  request.form.get("method", "GET"),
        "headers": request.form.get("headers", "{}"),
        "params":  request.form.get("params", "{}"),
        "enabled": True,
        "notes":   request.form.get("notes", ""),
    }
    db.create_api_config(data)
    db.add_log("admin", {"event": "api_added", "name": data["name"], "by": session.get("user_id")})
    flash("API configuration added.", "success")
    return redirect(url_for("admin_apis"))


@app.route("/admin/apis/<api_id>/edit", methods=["POST"])
@owner_required
def admin_edit_api(api_id):
    data = {
        "name":    request.form.get("name", ""),
        "tool":    request.form.get("tool", ""),
        "url":     request.form.get("url", ""),
        "method":  request.form.get("method", "GET"),
        "headers": request.form.get("headers", "{}"),
        "params":  request.form.get("params", "{}"),
        "notes":   request.form.get("notes", ""),
    }
    db.update_api_config(api_id, data)
    flash("API updated.", "success")
    return redirect(url_for("admin_apis"))


@app.route("/admin/apis/<api_id>/toggle", methods=["POST"])
@owner_required
def admin_toggle_api(api_id):
    api = db.get_api(api_id)
    if api:
        db.update_api_config(api_id, {"enabled": not api.get("enabled", True)})
    return redirect(url_for("admin_apis"))


@app.route("/admin/apis/<api_id>/delete", methods=["POST"])
@owner_required
def admin_delete_api(api_id):
    db.delete_api_config(api_id)
    flash("API deleted.", "success")
    return redirect(url_for("admin_apis"))


@app.route("/admin/announcements", methods=["GET", "POST"])
@admin_required
def admin_announcements():
    if request.method == "POST":
        data = {
            "title":   request.form.get("title", ""),
            "content": request.form.get("content", ""),
            "type":    request.form.get("type", "info"),
            "author":  session.get("username", "Admin"),
            "active":  True,
        }
        db.create_announcement(data)
        flash("Announcement created.", "success")
        return redirect(url_for("admin_announcements"))
    anns = db.get_announcements(50)
    return render_template("admin/announcements.html", announcements=anns)


@app.route("/admin/announcements/<ann_id>/delete", methods=["POST"])
@admin_required
def admin_delete_announcement(ann_id):
    db.delete_announcement(ann_id)
    return redirect(url_for("admin_announcements"))


@app.route("/admin/partners", methods=["GET", "POST"])
@admin_required
def admin_partners():
    if request.method == "POST":
        data = {
            "name":         request.form.get("name", ""),
            "description":  request.form.get("description", ""),
            "invite_link":  request.form.get("invite_link", ""),
            "icon_url":     request.form.get("icon_url", ""),
            "member_count": int(request.form.get("member_count", 0)),
            "category":     request.form.get("category", "partner"),
        }
        db.create_partner(data)
        flash("Partner added.", "success")
        return redirect(url_for("admin_partners"))
    partners = db.get_partners()
    return render_template("admin/partners.html", partners=partners)


@app.route("/admin/partners/<pid>/delete", methods=["POST"])
@admin_required
def admin_delete_partner(pid):
    db.delete_partner(pid)
    return redirect(url_for("admin_partners"))


@app.route("/admin/logs")
@admin_required
def admin_logs():
    category = request.args.get("category", "tools")
    logs = db.get_logs(category, 100)
    categories = ["tools", "likes", "visits", "security", "admin", "ai", "errors"]
    return render_template("admin/logs.html", logs=logs,
                           current_category=category, categories=categories)


@app.route("/admin/likes/reset", methods=["POST"])
@owner_required
def admin_reset_likes():
    db.reset_like_cache()
    db.add_log("admin", {"event": "like_cache_reset", "by": session.get("user_id")})
    flash("Like sender cache reset.", "success")
    return redirect(url_for("admin_settings"))


# ─── Internal Bot Webhook ─────────────────────────────────────────────────────

@app.route("/internal/bot-webhook", methods=["POST"])
def bot_webhook():
    """Called by the Discord bot to sync data to the site."""
    key  = request.headers.get("X-Bot-Key", "")
    if key != SECRET_KEY:
        abort(403)
    data = request.get_json(force=True) or {}
    action = data.get("action")

    if action == "announcement":
        db.create_announcement(data.get("payload", {}))
    elif action == "partner":
        db.create_partner(data.get("payload", {}))
    elif action == "branding":
        db.set_branding(data.get("payload", {}))
    elif action == "settings":
        db.update_settings(data.get("payload", {}))

    return jsonify({"ok": True})


# ─── API Status ───────────────────────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    return jsonify(db.get_stats())


@app.route("/api/branding")
def api_branding():
    return jsonify(db.get_branding())


# ─── Error handlers ───────────────────────────────────────────────────────────

@app.errorhandler(403)
def e403(e):
    return render_template("errors/403.html"), 403


@app.errorhandler(404)
def e404(e):
    return render_template("errors/404.html"), 404


@app.errorhandler(500)
def e500(e):
    db.add_log("errors", {"error": str(e), "path": request.path})
    return render_template("errors/500.html"), 500


# ─── Maintenance middleware ────────────────────────────────────────────────────

@app.before_request
def check_maintenance():
    exempt = ["/admin", "/login", "/logout", "/api", "/internal", "/static"]
    if any(request.path.startswith(p) for p in exempt):
        return
    settings = db.get_settings()
    if settings.get("maintenance_mode") and session.get("role") != "owner":
        return render_template("errors/maintenance.html"), 503


def _get_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr)
