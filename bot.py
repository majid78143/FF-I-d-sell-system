"""
bot.py  –  Discord Bot
Handles all Free Fire API calls, processes the Firebase request queue,
and exposes slash commands for admin control.
"""

import os
import json
import time
import asyncio
import logging
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks

import firebase_service as db
from config import TOKEN, SECRET_KEY

logger = logging.getLogger(__name__)

# ─── Bot Setup ────────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

REGIONS = ["IND", "BR", "SG", "RU", "ID", "TW", "US", "VN", "TH", "ME", "PK", "CIS", "BD"]

# ─── API Helper ───────────────────────────────────────────────────────────────

async def call_api(api_id: str, params: dict) -> dict:
    """Load API config from Firebase and make the HTTP call."""
    api = db.get_api(api_id)
    if not api or not api.get("enabled"):
        return {"error": f"API '{api_id}' not found or disabled"}
    try:
        url     = api["url"].format(**params)
        method  = api.get("method", "GET").upper()
        headers = json.loads(api.get("headers", "{}"))
        extra   = json.loads(api.get("params", "{}"))
        merged  = {**extra, **params}

        async with aiohttp.ClientSession() as session:
            if method == "POST":
                async with session.post(url, json=merged, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    return await r.json()
            else:
                async with session.get(url, params=merged, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as r:
                    return await r.json()
    except Exception as e:
        logger.error(f"[API call] {api_id}: {e}")
        return {"error": str(e)}


async def freefire_api(endpoint: str, params: dict) -> dict:
    """Generic Free Fire API call – tool keys stored in Firebase api_configs."""
    apis = db.get_apis()
    tool_api = next((a for a in apis if a.get("tool") == endpoint and a.get("enabled")), None)
    if not tool_api:
        return {"error": f"No enabled API configured for tool '{endpoint}'"}
    return await call_api(tool_api["id"], params)


# ─── Queue Processor ─────────────────────────────────────────────────────────

@tasks.loop(seconds=2)
async def process_queue():
    """Poll Firebase for pending requests and dispatch them."""
    try:
        pending = db.get_pending_requests()
        for item in pending:
            req_id = item["id"]
            tool   = item.get("tool")
            params = item.get("params", {})

            # Mark in-progress
            db.update_queue_item(req_id, {"status": "processing"})

            try:
                result = await dispatch_tool(tool, params)
                db.update_queue_item(req_id, {"status": "done", "result": result})
            except Exception as e:
                db.update_queue_item(req_id, {
                    "status": "error",
                    "error_message": str(e),
                })
                db.add_log("errors", {"tool": tool, "req_id": req_id, "error": str(e)})
    except Exception as e:
        logger.error(f"[Queue] {e}")


async def dispatch_tool(tool: str, params: dict) -> dict:
    if tool == "profile":
        return await freefire_api("profile", params)
    elif tool == "player_search":
        return await freefire_api("player_search", params)
    elif tool == "guild_search":
        return await freefire_api("guild_search", params)
    elif tool == "uid_info":
        return await freefire_api("uid_info", params)
    elif tool == "region_check":
        return await freefire_api("region_check", params)
    elif tool == "like_send":
        return await freefire_api("like_send", params)
    elif tool == "id_visits":
        return await freefire_api("id_visits", params)
    elif tool == "player_rankings":
        return await freefire_api("player_rankings", params)
    elif tool == "ai_chat":
        return await handle_ai_chat(params)
    else:
        return {"error": f"Unknown tool: {tool}"}


async def handle_ai_chat(params: dict) -> dict:
    """AI chat via configured provider."""
    settings  = db.get_settings()
    provider  = params.get("provider", settings.get("ai_provider", "openai"))
    model     = params.get("model", settings.get("ai_model", "gpt-3.5-turbo"))
    system_p  = params.get("prompt", settings.get("ai_prompt", "You are a Free Fire assistant."))
    message   = params.get("message", "")

    apis = db.get_apis()
    ai_api = next((a for a in apis if a.get("tool") == "ai_chat" and a.get("enabled")), None)
    if not ai_api:
        return {"error": "AI API not configured. Add an API with tool=ai_chat in the admin panel."}

    try:
        headers = json.loads(ai_api.get("headers", "{}"))
        url     = ai_api["url"]
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_p},
                {"role": "user",   "content": message},
            ],
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(url, json=payload, headers=headers,
                              timeout=aiohttp.ClientTimeout(total=30)) as r:
                data = await r.json()
                reply = (data.get("choices", [{}])[0]
                             .get("message", {})
                             .get("content", "No reply."))
                return {"reply": reply}
    except Exception as e:
        return {"error": str(e)}


# ─── Bot Events ───────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    logger.info(f"Bot logged in as {bot.user} ({bot.user.id})")
    try:
        synced = await tree.sync()
        logger.info(f"Synced {len(synced)} slash commands")
    except Exception as e:
        logger.error(f"Sync failed: {e}")
    process_queue.start()


@bot.event
async def on_guild_join(guild: discord.Guild):
    db.upsert_guild(str(guild.id), {
        "name":         guild.name,
        "icon_url":     str(guild.icon.url) if guild.icon else "",
        "member_count": guild.member_count,
        "owner_id":     str(guild.owner_id),
        "joined_at":    int(time.time()),
    })
    db.add_log("guilds", {"event": "join", "guild_id": str(guild.id), "name": guild.name})


@bot.event
async def on_guild_remove(guild: discord.Guild):
    db.add_log("guilds", {"event": "leave", "guild_id": str(guild.id), "name": guild.name})


# ─── Slash Commands ───────────────────────────────────────────────────────────

# /announcement
@tree.command(name="announcement", description="Post an announcement to the website")
@app_commands.describe(
    title="Announcement title",
    content="Announcement content",
    ann_type="Type: info / warning / success / danger",
)
async def cmd_announcement(interaction: discord.Interaction,
                            title: str, content: str,
                            ann_type: str = "info"):
    if not await _is_admin(interaction):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)

    db.create_announcement({
        "title":   title,
        "content": content,
        "type":    ann_type,
        "author":  str(interaction.user),
        "active":  True,
    })
    db.add_log("announcements", {"event": "created", "title": title,
                                   "by": str(interaction.user.id)})
    embed = discord.Embed(title="✅ Announcement Posted", color=0x00b894)
    embed.add_field(name="Title",   value=title,    inline=False)
    embed.add_field(name="Content", value=content,  inline=False)
    embed.add_field(name="Type",    value=ann_type, inline=True)
    await interaction.response.send_message(embed=embed)


# /partner
@tree.command(name="partner", description="Manage partner servers")
@app_commands.describe(
    action="Action: add / edit / remove",
    name="Server name",
    description="Short description",
    invite_link="Discord invite URL",
    icon_url="Server icon URL",
    member_count="Member count",
    partner_id="Partner ID (for edit/remove)",
)
async def cmd_partner(interaction: discord.Interaction,
                       action: str,
                       name: str = "",
                       description: str = "",
                       invite_link: str = "",
                       icon_url: str = "",
                       member_count: int = 0,
                       partner_id: str = ""):
    if not await _is_admin(interaction):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)

    action = action.lower()
    if action == "add":
        pid = db.create_partner({
            "name": name, "description": description,
            "invite_link": invite_link, "icon_url": icon_url,
            "member_count": member_count, "category": "partner",
        })
        await interaction.response.send_message(
            embed=_ok_embed(f"Partner **{name}** added. ID: `{pid}`"))

    elif action == "edit" and partner_id:
        db.update_partner(partner_id, {
            "name": name, "description": description,
            "invite_link": invite_link, "icon_url": icon_url,
            "member_count": member_count,
        })
        await interaction.response.send_message(
            embed=_ok_embed(f"Partner `{partner_id}` updated."))

    elif action == "remove" and partner_id:
        db.delete_partner(partner_id)
        await interaction.response.send_message(
            embed=_ok_embed(f"Partner `{partner_id}` removed."))
    else:
        await interaction.response.send_message("❌ Invalid action or missing arguments.", ephemeral=True)


# /theme
@tree.command(name="theme", description="Update website branding / theme")
@app_commands.describe(
    site_name="Website name",
    logo_url="Logo URL",
    favicon_url="Favicon URL",
    primary_color="Primary hex color e.g. #0070f3",
    secondary_color="Secondary hex color",
    footer_text="Footer text",
)
async def cmd_theme(interaction: discord.Interaction,
                     site_name: str = "", logo_url: str = "",
                     favicon_url: str = "", primary_color: str = "",
                     secondary_color: str = "", footer_text: str = ""):
    if not await _is_owner(interaction):
        return await interaction.response.send_message("❌ Owner only.", ephemeral=True)

    payload = {}
    if site_name:      payload["site_name"]      = site_name
    if logo_url:       payload["logo_url"]        = logo_url
    if favicon_url:    payload["favicon_url"]     = favicon_url
    if primary_color:  payload["primary_color"]   = primary_color
    if secondary_color:payload["secondary_color"] = secondary_color
    if footer_text:    payload["footer_text"]     = footer_text

    db.set_branding(payload)
    db.add_log("admin", {"event": "branding_updated_via_bot", "by": str(interaction.user.id)})
    await interaction.response.send_message(embed=_ok_embed("Branding updated and synced to website."))


# /api
@tree.command(name="api", description="Manage API configurations")
@app_commands.describe(
    action="Action: list / add / enable / disable / delete",
    api_id="API ID (for enable/disable/delete)",
    name="API name (for add)",
    tool="Tool name (for add)",
    url="API URL (for add)",
)
async def cmd_api(interaction: discord.Interaction,
                   action: str, api_id: str = "",
                   name: str = "", tool: str = "", url: str = ""):
    if not await _is_owner(interaction):
        return await interaction.response.send_message("❌ Owner only.", ephemeral=True)

    action = action.lower()
    if action == "list":
        apis = db.get_apis()
        if not apis:
            return await interaction.response.send_message("No APIs configured.", ephemeral=True)
        lines = [f"`{a['id']}` | {a.get('name','?')} | {a.get('tool','?')} | {'✅' if a.get('enabled') else '❌'}"
                 for a in apis]
        embed = discord.Embed(title="API Configurations", description="\n".join(lines), color=0x0070f3)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    elif action == "add":
        new_id = db.create_api_config({"name": name, "tool": tool, "url": url,
                                         "method": "GET", "headers": "{}", "params": "{}"})
        await interaction.response.send_message(embed=_ok_embed(f"API `{name}` added. ID: `{new_id}`"))

    elif action == "enable" and api_id:
        db.update_api_config(api_id, {"enabled": True})
        await interaction.response.send_message(embed=_ok_embed(f"API `{api_id}` enabled."))

    elif action == "disable" and api_id:
        db.update_api_config(api_id, {"enabled": False})
        await interaction.response.send_message(embed=_ok_embed(f"API `{api_id}` disabled."))

    elif action == "delete" and api_id:
        db.delete_api_config(api_id)
        await interaction.response.send_message(embed=_ok_embed(f"API `{api_id}` deleted."))
    else:
        await interaction.response.send_message("❌ Invalid action.", ephemeral=True)


# /likes
@tree.command(name="likes", description="Manage Like Sender settings")
@app_commands.describe(
    action="Action: status / enable / disable / reset / setlimit",
    limit="New daily limit (for setlimit)",
)
async def cmd_likes(interaction: discord.Interaction, action: str, limit: int = 0):
    if not await _is_owner(interaction):
        return await interaction.response.send_message("❌ Owner only.", ephemeral=True)

    action = action.lower()
    settings = db.get_settings()
    if action == "status":
        today = db.count_likes_today()
        daily = settings.get("like_sender_daily_limit", 20)
        enabled = settings.get("like_sender_enabled", True)
        embed = discord.Embed(title="Like Sender Status", color=0x00b894 if enabled else 0xe17055)
        embed.add_field(name="Status",      value="✅ Enabled" if enabled else "❌ Disabled")
        embed.add_field(name="Today",       value=f"{today}/{daily}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
    elif action == "enable":
        db.update_settings({"like_sender_enabled": True})
        await interaction.response.send_message(embed=_ok_embed("Like Sender enabled."))
    elif action == "disable":
        db.update_settings({"like_sender_enabled": False})
        await interaction.response.send_message(embed=_ok_embed("Like Sender disabled."))
    elif action == "reset":
        db.reset_like_cache()
        await interaction.response.send_message(embed=_ok_embed("Like cache reset for today."))
    elif action == "setlimit" and limit > 0:
        db.update_settings({"like_sender_daily_limit": limit})
        await interaction.response.send_message(embed=_ok_embed(f"Daily limit set to {limit}."))
    else:
        await interaction.response.send_message("❌ Invalid action.", ephemeral=True)


# /logs
@tree.command(name="logs", description="View recent logs from website")
@app_commands.describe(
    category="Category: tools / likes / visits / security / admin / ai / errors",
    limit="Number of entries (max 10)",
)
async def cmd_logs(interaction: discord.Interaction, category: str = "tools", limit: int = 5):
    if not await _is_admin(interaction):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)

    limit = min(limit, 10)
    logs  = db.get_logs(category, limit)
    if not logs:
        return await interaction.response.send_message(f"No logs in `{category}`.", ephemeral=True)

    embed = discord.Embed(title=f"Logs: {category}", color=0x6c5ce7)
    for log in logs[:limit]:
        ts = log.get("ts", 0)
        text = " | ".join(f"{k}={v}" for k, v in log.items()
                          if k not in ("id", "ts") and v)
        embed.add_field(name=f"<t:{ts}:R>", value=text[:100] or "—", inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# /admin (permission management)
@tree.command(name="admin", description="Grant or revoke admin role for a user")
@app_commands.describe(
    action="Action: grant / revoke",
    discord_id="Discord user ID",
)
async def cmd_admin(interaction: discord.Interaction, action: str, discord_id: str):
    if not await _is_owner(interaction):
        return await interaction.response.send_message("❌ Owner only.", ephemeral=True)

    user = db.get_user_by_discord(discord_id)
    if not user:
        return await interaction.response.send_message(
            f"❌ No website account linked to Discord ID `{discord_id}`.", ephemeral=True)

    role = "admin" if action.lower() == "grant" else "user"
    db.update_user(user["id"], {"role": role})
    db.add_log("admin", {"event": f"admin_{action}", "discord_id": discord_id,
                           "by": str(interaction.user.id)})
    await interaction.response.send_message(
        embed=_ok_embed(f"User `{discord_id}` role set to `{role}`."))


# /branding
@tree.command(name="branding", description="View current website branding")
async def cmd_branding(interaction: discord.Interaction):
    if not await _is_admin(interaction):
        return await interaction.response.send_message("❌ No permission.", ephemeral=True)
    b = db.get_branding()
    embed = discord.Embed(title="Website Branding", color=0x0070f3)
    for k, v in b.items():
        embed.add_field(name=k, value=str(v)[:100], inline=True)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# /page
@tree.command(name="page", description="Toggle maintenance mode or registration")
@app_commands.describe(
    page="Option: maintenance / registration",
    state="on or off",
)
async def cmd_page(interaction: discord.Interaction, page: str, state: str):
    if not await _is_owner(interaction):
        return await interaction.response.send_message("❌ Owner only.", ephemeral=True)

    enabled = state.lower() in ("on", "true", "1", "enable", "enabled")
    key_map = {
        "maintenance": "maintenance_mode",
        "registration": "registration_open",
    }
    key = key_map.get(page.lower())
    if not key:
        return await interaction.response.send_message("❌ Unknown page option.", ephemeral=True)

    db.update_settings({key: enabled})
    await interaction.response.send_message(
        embed=_ok_embed(f"`{page}` set to `{'on' if enabled else 'off'}`."))


# /permission
@tree.command(name="permission", description="List bot owner/admin permissions")
async def cmd_permission(interaction: discord.Interaction):
    if not await _is_owner(interaction):
        return await interaction.response.send_message("❌ Owner only.", ephemeral=True)
    embed = discord.Embed(title="Permission Levels", color=0xfdcb6e)
    embed.add_field(name="Owner",  value="Full control (env OWNER_EMAIL)", inline=False)
    embed.add_field(name="Admin",  value="Announcements, partners, logs",  inline=False)
    embed.add_field(name="User",   value="Tools, AI, profile lookup",      inline=False)
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ─── Permission helpers ───────────────────────────────────────────────────────

OWNER_ID = "1464697383467356316"

async def _is_owner(interaction: discord.Interaction) -> bool:
    return str(interaction.user.id) == OWNER_ID


async def _is_admin(interaction: discord.Interaction) -> bool:
    if str(interaction.user.id) == OWNER_ID:
        return True

    user = db.get_user_by_discord(str(interaction.user.id))
    return user is not None and user.get("role") in ("admin", "owner")


def _ok_embed(msg: str) -> discord.Embed:
    return discord.Embed(description=f"✅ {msg}", color=0x00b894)


# ─── Entry point ─────────────────────────────────────────────────────────────

def run_bot():
    if not TOKEN:
        logger.warning("TOKEN not set – bot will not start.")
        return
    bot.run(TOKEN, log_handler=None)
