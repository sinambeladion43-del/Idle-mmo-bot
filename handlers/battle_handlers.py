import time
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_player, create_player, update_player,
    add_war, get_war_history, get_all_buildings
)
from game_data import ATTACK_COOLDOWN, LOOT_PERCENT, BUILDINGS, exp_needed


def _fmt_time(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}j {m}m"
    return f"{m}m {s}d"


async def _ensure_player(update: Update):
    user = update.effective_user
    await create_player(user.id, user.username or user.first_name)
    return await get_player(user.id)


async def _get_effective_stats(player):
    buildings = await get_all_buildings(player["user_id"])
    now = int(time.time())
    active = {b["name"]: b["level"] for b in buildings if b["finish_time"] <= now and b["level"] > 0}
    atk = player["attack_pow"]
    def_ = player["defense_pow"]
    max_hp = player["max_hp"]
    for bname, lvl in active.items():
        bdata = BUILDINGS.get(bname, {})
        for stat, bonus in bdata.get("stat_bonus", {}).items():
            if stat == "attack_pow":
                atk += bonus * lvl
            elif stat == "defense_pow":
                def_ += bonus * lvl
            elif stat == "max_hp":
                max_hp += bonus * lvl
    return atk, def_, max_hp


# ──────────────────────────────────────────────
async def attack(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    attacker = await _ensure_player(update)
    if attacker["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    if not ctx.args:
        await update.message.reply_text(
            "⚔️ *Cara Menyerang:*\n`/attack @username`",
            parse_mode="Markdown"
        )
        return

    target_username = ctx.args[0].lstrip("@")

    import aiosqlite, os
    DB_PATH = os.environ.get("DB_PATH", "./game.db")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM players WHERE username=? AND is_banned=0", (target_username,)
        ) as cur:
            defender = await cur.fetchone()

    if not defender:
        await update.message.reply_text(
            f"❌ Pemain *{target_username}* tidak ditemukan atau di-ban.",
            parse_mode="Markdown"
        )
        return

    if defender["user_id"] == attacker["user_id"]:
        await update.message.reply_text("😅 Kamu tidak bisa menyerang diri sendiri!")
        return

    # Cooldown check
    now = int(time.time())
    recent_wars = await get_war_history(attacker["user_id"], 20)
    for w in recent_wars:
        if w["attacker_id"] == attacker["user_id"] and w["defender_id"] == defender["user_id"]:
            if now - w["timestamp"] < ATTACK_COOLDOWN:
                remaining = ATTACK_COOLDOWN - (now - w["timestamp"])
                await update.message.reply_text(
                    f"⏰ Cooldown! Tunggu *{_fmt_time(remaining)}* lagi.",
                    parse_mode="Markdown"
                )
                return

    atk_power, _, _ = await _get_effective_stats(attacker)
    _, def_power, _ = await _get_effective_stats(defender)

    atk_roll = atk_power + attacker["attack_pow"] + random.randint(1, 20)
    def_roll = def_power + defender["defense_pow"] + random.randint(1, 20)

    attacker_wins = atk_roll > def_roll
    loot_gold = 0
    exp_gain = 0

    if attacker_wins:
        loot_gold = int(defender["gold"] * LOOT_PERCENT)
        exp_gain = 20 + defender["level"] * 5
        new_exp = attacker["exp"] + exp_gain
        new_level = attacker["level"]
        while new_exp >= exp_needed(new_level):
            new_exp -= exp_needed(new_level)
            new_level += 1
        await update_player(attacker["user_id"], gold=attacker["gold"] + loot_gold, exp=new_exp, level=new_level)
        await update_player(defender["user_id"], gold=max(0, defender["gold"] - loot_gold))
        result = "attacker_win"
    else:
        dmg = max(5, def_roll - atk_roll)
        new_hp = max(1, attacker["hp"] - dmg)
        exp_gain = 5
        new_exp = attacker["exp"] + exp_gain
        new_level = attacker["level"]
        while new_exp >= exp_needed(new_level):
            new_exp -= exp_needed(new_level)
            new_level += 1
        await update_player(attacker["user_id"], hp=new_hp, exp=new_exp, level=new_level)
        result = "defender_win"

    await add_war(
        attacker["user_id"], defender["user_id"],
        attacker["username"], defender["username"],
        result, atk_roll, def_roll, loot_gold
    )

    # ── Hasil untuk penyerang ──────────────────
    if attacker_wins:
        text = (
            f"⚔️ *HASIL PERTEMPURAN*\n\n"
            f"🏆 *MENANG!*\n\n"
            f"👤 {attacker['username']} (ATK: {atk_roll})\n"
            f"  vs\n"
            f"👤 {defender['username']} (DEF: {def_roll})\n\n"
            f"💰 Loot: +{loot_gold:,} Gold\n"
            f"✨ EXP : +{exp_gain}"
        )
    else:
        dmg = max(5, def_roll - atk_roll)
        text = (
            f"⚔️ *HASIL PERTEMPURAN*\n\n"
            f"💀 *KALAH!*\n\n"
            f"👤 {attacker['username']} (ATK: {atk_roll})\n"
            f"  vs\n"
            f"👤 {defender['username']} (DEF: {def_roll})\n\n"
            f"❤️ HP berkurang -{dmg}\n"
            f"✨ EXP : +{exp_gain}\n\n"
            f"💡 Upgrade Barracks & Wall untuk jadi lebih kuat!"
        )

    await update.message.reply_text(text, parse_mode="Markdown")

    # ── 🔔 Notifikasi ke defender via DM ──────
    try:
        if attacker_wins:
            notif = (
                f"🚨 *KAMU DISERANG!*\n\n"
                f"⚔️ *{attacker['username']}* menyerang kamu!\n\n"
                f"💀 Kamu *KALAH*\n"
                f"💸 Gold hilang: -{loot_gold:,}\n\n"
                f"💡 Balas dendam: `/attack @{attacker['username']}`\n"
                f"🛡️ Perkuat defense: `/build wall`"
            )
        else:
            notif = (
                f"🛡️ *SERANGAN BERHASIL DIHADANG!*\n\n"
                f"⚔️ *{attacker['username']}* mencoba menyerangmu!\n\n"
                f"🏆 Kamu *MENANG* mempertahankan diri!\n"
                f"Gold aman terlindungi ✅"
            )
        await ctx.bot.send_message(defender["user_id"], notif, parse_mode="Markdown")
    except Exception:
        pass  # User mungkin belum pernah start bot


# ──────────────────────────────────────────────
async def defend(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    atk, def_, max_hp = await _get_effective_stats(player)
    text = (
        f"🛡️ *PERTAHANAN: {player['username']}*\n\n"
        f"❤️ HP      : {player['hp']}/{max_hp}\n"
        f"⚔️ Attack  : {atk}\n"
        f"🛡️ Defense : {def_}\n"
        f"⭐ Level   : {player['level']}\n\n"
        f"💡 Upgrade *barracks* untuk +Attack\n"
        f"💡 Upgrade *wall* untuk +Defense"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ──────────────────────────────────────────────
async def war_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    wars = await get_war_history(player["user_id"], 10)
    if not wars:
        await update.message.reply_text(
            "📜 Belum ada riwayat pertempuran.\nGunakan `/attack @username` untuk mulai!",
            parse_mode="Markdown"
        )
        return

    lines = ["📜 *RIWAYAT PERTEMPURAN*\n"]
    for w in wars:
        import datetime
        dt = datetime.datetime.fromtimestamp(w["timestamp"]).strftime("%d/%m %H:%M")
        if w["attacker_id"] == player["user_id"]:
            icon = "⚔️" if w["result"] == "attacker_win" else "💀"
            lines.append(f"{icon} [{dt}] Serang {w['defender_name']} — Loot: {w['loot_gold']}🪙")
        else:
            icon = "🛡️" if w["result"] == "defender_win" else "😱"
            lines.append(f"{icon} [{dt}] Diserang {w['attacker_name']} — Loot: -{w['loot_gold']}🪙")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def battle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("⚔️ Gunakan `/attack @username` untuk menyerang!", parse_mode="Markdown")
