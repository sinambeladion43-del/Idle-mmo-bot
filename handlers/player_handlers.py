import time
from telegram import Update
from telegram.ext import ContextTypes
from database import (
    get_player, create_player, update_player, get_top_players
)
from game_data import DAILY_REWARD, DAILY_COOLDOWN, exp_needed, RESOURCE_EMOJI


def _fmt_time(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}j {m}m"
    return f"{m}m {s}d"


def _escape(text: str) -> str:
    """Escape karakter spesial Markdown Telegram v1."""
    for ch in ["_", "*", "[", "]", "`"]:
        text = text.replace(ch, f"\\{ch}")
    return text


async def _ensure_player(update: Update):
    user = update.effective_user
    await create_player(user.id, user.username or user.first_name)
    return await get_player(user.id)


# ──────────────────────────────────────────────
async def profile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    next_exp = exp_needed(player["level"])
    bar_fill = int((player["exp"] / next_exp) * 10)
    bar = "█" * bar_fill + "░" * (10 - bar_fill)
    name = _escape(player["username"])

    text = (
        f"👤 *Profil: {name}*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⭐ Level   : {player['level']}\n"
        f"📊 EXP     : {player['exp']}/{next_exp}\n"
        f"[{bar}]\n"
        f"❤️ HP       : {player['hp']}/{player['max_hp']}\n"
        f"⚔️ Attack   : {player['attack_pow']}\n"
        f"🛡️ Defense  : {player['defense_pow']}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"🪙 Gold     : {player['gold']:,}\n"
        f"🪵 Wood     : {player['wood']:,}\n"
        f"🪨 Stone    : {player['stone']:,}\n"
        f"🌾 Food     : {player['food']:,}\n"
        f"⚔️ Iron     : {player['iron']:,}\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ──────────────────────────────────────────────
async def inventory(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    name = _escape(player["username"])
    text = (
        f"🎒 *Inventory: {name}*\n\n"
        f"🪙 Gold  : {player['gold']:,}\n"
        f"🪵 Wood  : {player['wood']:,}\n"
        f"🪨 Stone : {player['stone']:,}\n"
        f"🌾 Food  : {player['food']:,}\n"
        f"⚔️ Iron  : {player['iron']:,}\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ──────────────────────────────────────────────
async def daily(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    now = int(time.time())
    elapsed = now - player["last_daily"]

    if elapsed < DAILY_COOLDOWN:
        remaining = DAILY_COOLDOWN - elapsed
        await update.message.reply_text(
            f"⏰ Daily sudah diklaim!\n"
            f"Coba lagi dalam *{_fmt_time(remaining)}*",
            parse_mode="Markdown"
        )
        return

    await update_player(
        player["user_id"],
        gold=player["gold"]   + DAILY_REWARD["gold"],
        wood=player["wood"]   + DAILY_REWARD["wood"],
        stone=player["stone"] + DAILY_REWARD["stone"],
        food=player["food"]   + DAILY_REWARD["food"],
        last_daily=now,
    )

    text = (
        "🎁 *Daily Reward Diklaim!*\n\n"
        f"🪙 +{DAILY_REWARD['gold']} Gold\n"
        f"🪵 +{DAILY_REWARD['wood']} Wood\n"
        f"🪨 +{DAILY_REWARD['stone']} Stone\n"
        f"🌾 +{DAILY_REWARD['food']} Food\n\n"
        "Kembali besok untuk reward berikutnya! 🔄"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ──────────────────────────────────────────────
async def leaderboard(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    players = await get_top_players(10)
    if not players:
        await update.message.reply_text("Belum ada pemain terdaftar.")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = ["🏆 *LEADERBOARD TOP 10*\n"]
    for i, p in enumerate(players):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = _escape(p["username"])
        lines.append(f"{medal} {name} — Lv.{p['level']} ({p['exp']} EXP)")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
