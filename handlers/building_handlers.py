import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_player, create_player, update_player,
    get_building, get_all_buildings, upsert_building
)
from game_data import BUILDINGS, MAX_COLLECT_HOURS, exp_needed


def _fmt_time(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}j {m}m"
    if m:
        return f"{m}m {s}d"
    return f"{s}d"


async def _ensure_player(update: Update):
    user = update.effective_user
    await create_player(user.id, user.username or user.first_name)
    return await get_player(user.id)


# ──────────────────────────────────────────────
async def list_buildings(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    lines = ["🏘️ *DAFTAR BANGUNAN*\n"]
    now = int(time.time())
    for bname, bdata in BUILDINGS.items():
        row = await get_building(player["user_id"], bname)
        lvl = row["level"] if row else 0
        max_lvl = bdata["max_level"]
        emoji = bdata["emoji"]
        status = ""
        if row and row["finish_time"] > now:
            remaining = row["finish_time"] - now
            status = f" ⏳ ({_fmt_time(remaining)})"
        lines.append(
            f"{emoji} *{bname.title()}* — Lv.{lvl}/{max_lvl}{status}\n"
            f"   _{bdata['description']}_"
        )

    lines.append("\n📌 Gunakan `/build [nama]` untuk membangun/upgrade")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ──────────────────────────────────────────────
async def build(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    args = ctx.args
    if not args:
        # Show building menu
        kb = []
        row = []
        for bname, bdata in BUILDINGS.items():
            row.append(InlineKeyboardButton(
                f"{bdata['emoji']} {bname.title()}",
                callback_data=f"build_{bname}"
            ))
            if len(row) == 2:
                kb.append(row)
                row = []
        if row:
            kb.append(row)

        await update.message.reply_text(
            "🏗️ *Pilih bangunan yang ingin dibangun/upgrade:*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    bname = args[0].lower()
    await _do_build(update, player, bname)


async def build_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    bname = query.data.replace("build_", "")
    user = update.effective_user
    await create_player(user.id, user.username or user.first_name)
    player = await get_player(user.id)
    await _do_build(query, player, bname, is_callback=True)


async def _do_build(update_or_query, player, bname: str, is_callback=False):
    async def reply(text, **kwargs):
        if is_callback:
            await update_or_query.edit_message_text(text, **kwargs)
        else:
            await update_or_query.message.reply_text(text, **kwargs)

    if bname not in BUILDINGS:
        await reply(
            f"❌ Bangunan *{bname}* tidak ditemukan.\n\n"
            f"Bangunan tersedia: {', '.join(BUILDINGS.keys())}",
            parse_mode="Markdown"
        )
        return

    bdata = BUILDINGS[bname]
    row = await get_building(player["user_id"], bname)
    current_lvl = row["level"] if row else 0
    now = int(time.time())

    # Check if already building
    if row and row["finish_time"] > now:
        remaining = row["finish_time"] - now
        await reply(
            f"⏳ *{bname.title()}* sedang dalam proses konstruksi!\n"
            f"Selesai dalam: *{_fmt_time(remaining)}*",
            parse_mode="Markdown"
        )
        return

    if current_lvl >= bdata["max_level"]:
        await reply(
            f"✅ *{bname.title()}* sudah di level maksimum (Lv.{bdata['max_level']})!",
            parse_mode="Markdown"
        )
        return

    next_lvl = current_lvl + 1
    cost = bdata["cost"](next_lvl)

    # Check resources
    for res, amt in cost.items():
        if player[res] < amt:
            cost_lines = "\n".join(f"  • {r}: {a:,}" for r, a in cost.items())
            await reply(
                f"❌ *Resource tidak cukup!*\n\n"
                f"Dibutuhkan untuk *{bname.title()}* Lv.{next_lvl}:\n{cost_lines}\n\n"
                f"Gunakan `/collect` untuk ambil resource produksi.",
                parse_mode="Markdown"
            )
            return

    # Deduct resources and start building
    updates = {res: player[res] - amt for res, amt in cost.items()}
    build_time = bdata["build_time"](next_lvl)
    finish_at = now + build_time

    await update_player(player["user_id"], **updates)
    await upsert_building(player["user_id"], bname, next_lvl, finish_at)

    cost_lines = "\n".join(f"  • {r}: -{a:,}" for r, a in cost.items())
    await reply(
        f"🏗️ *Konstruksi dimulai!*\n\n"
        f"{bdata['emoji']} *{bname.title()}* → Lv.{next_lvl}\n"
        f"⏱️ Selesai dalam: *{_fmt_time(build_time)}*\n\n"
        f"Resource digunakan:\n{cost_lines}\n\n"
        f"Cek progress dengan /status",
        parse_mode="Markdown"
    )


# ──────────────────────────────────────────────
async def status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    buildings = await get_all_buildings(player["user_id"])
    now = int(time.time())

    in_progress = [b for b in buildings if b["finish_time"] > now]
    completed = [b for b in buildings if b["finish_time"] <= now and b["level"] > 0]

    if not in_progress and not completed:
        await update.message.reply_text(
            "🏗️ Belum ada bangunan.\nGunakan `/build` untuk mulai membangun!",
            parse_mode="Markdown"
        )
        return

    lines = ["🏗️ *STATUS BANGUNAN*\n"]
    if in_progress:
        lines.append("⏳ *Sedang Dibangun:*")
        for b in in_progress:
            remaining = b["finish_time"] - now
            bdata = BUILDINGS.get(b["name"], {})
            emoji = bdata.get("emoji", "🏛️")
            lines.append(f"  {emoji} {b['name'].title()} Lv.{b['level']} — ⏳ {_fmt_time(remaining)}")
        lines.append("")

    if completed:
        lines.append("✅ *Bangunan Aktif:*")
        for b in completed:
            bdata = BUILDINGS.get(b["name"], {})
            emoji = bdata.get("emoji", "🏛️")
            lines.append(f"  {emoji} {b['name'].title()} — Lv.{b['level']}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ──────────────────────────────────────────────
async def collect(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    now = int(time.time())
    last = player["last_collect"] or player["created_at"] or now
    hours_passed = min((now - last) / 3600, MAX_COLLECT_HOURS)

    if hours_passed < 0.016:  # < 1 minute
        await update.message.reply_text(
            "⏰ Terlalu cepat! Resource baru terkumpul setelah beberapa menit."
        )
        return

    buildings = await get_all_buildings(player["user_id"])
    active = {b["name"]: b["level"] for b in buildings if b["finish_time"] <= now and b["level"] > 0}

    gained = {}
    for bname, lvl in active.items():
        bdata = BUILDINGS.get(bname, {})
        for res, rate in bdata.get("produces", {}).items():
            amount = int(rate * lvl * hours_passed)
            if amount > 0:
                gained[res] = gained.get(res, 0) + amount

    if not gained:
        await update.message.reply_text(
            "😅 Tidak ada resource yang bisa dikumpulkan.\n"
            "Pastikan kamu punya bangunan aktif seperti `/build farm`.",
            parse_mode="Markdown"
        )
        return

    # Apply stat bonuses from buildings
    stat_updates = {}
    for bname, lvl in active.items():
        bdata = BUILDINGS.get(bname, {})
        for stat, bonus in bdata.get("stat_bonus", {}).items():
            total_bonus = bonus * lvl
            current_val = player[stat]
            # Only apply if building was just finished (check if stat needs update)
            # For simplicity, we'll recalculate and set correct values
            stat_updates[stat] = total_bonus

    updates = {res: player[res] + amt for res, amt in gained.items()}
    updates["last_collect"] = now

    await update_player(player["user_id"], **updates)

    lines = [f"📦 *Resource Dikumpulkan!* ({hours_passed:.1f} jam)\n"]
    for res, amt in gained.items():
        from game_data import RESOURCE_EMOJI
        emoji = RESOURCE_EMOJI.get(res, "•")
        lines.append(f"{emoji} +{amt:,} {res.title()}")

    lines.append(f"\n💡 Bangunan aktif: {len(active)}")
    if hours_passed >= MAX_COLLECT_HOURS:
        lines.append(f"⚠️ Resource sudah penuh ({MAX_COLLECT_HOURS}j)! Kumpulkan lebih sering.")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
