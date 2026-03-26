import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_player, create_player, update_player,
    get_kingdom, create_kingdom, update_kingdom,
    get_kingdom_members
)
from game_data import RESOURCES, RESOURCE_EMOJI, KINGDOM_CONTRIBUTE_MIN


async def _ensure_player(update: Update):
    user = update.effective_user
    await create_player(user.id, user.username or user.first_name)
    return await get_player(user.id)


async def _get_or_create_kingdom(update: Update):
    """Get kingdom for this group, auto-create if missing."""
    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        return None

    kingdom = await get_kingdom(chat.id)
    if not kingdom:
        admin_id = update.effective_user.id
        name = f"Kingdom of {chat.title or 'Unknown'}"
        kid = await create_kingdom(chat.id, name, admin_id)
        kingdom = await get_kingdom(chat.id)
    return kingdom


# ──────────────────────────────────────────────
async def kingdom(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text(
            "🏰 *Kingdom hanya tersedia di Group Telegram!*\n\n"
            "Tambahkan bot ke group dan ketik /kingdom di sana.",
            parse_mode="Markdown"
        )
        return

    kd = await _get_or_create_kingdom(update)
    if not kd:
        await update.message.reply_text("❌ Gagal memuat kingdom.")
        return

    members = await get_kingdom_members(kd["id"])
    member_count = len(members)

    text = (
        f"🏰 *{kd['name']}*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⭐ Level   : {kd['level']}\n"
        f"👥 Member  : {member_count}\n"
        f"💸 Pajak   : {kd['tax_rate']}%\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"*Kas Kerajaan:*\n"
        f"🪙 Gold    : {kd['gold']:,}\n"
        f"🪵 Wood    : {kd['wood']:,}\n"
        f"🪨 Stone   : {kd['stone']:,}\n"
        f"🌾 Food    : {kd['food']:,}\n"
        f"⚔️ Iron   : {kd['iron']:,}\n\n"
        f"💡 Sumbangkan resource: `/contribute gold 500`"
    )

    kb = [[
        InlineKeyboardButton("👥 Member", callback_data="kingdom_members"),
        InlineKeyboardButton("📊 Stats", callback_data="kingdom_stats"),
    ]]
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ──────────────────────────────────────────────
async def contribute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text(
            "🏰 Command ini hanya tersedia di Group Telegram!",
            parse_mode="Markdown"
        )
        return

    if not ctx.args or len(ctx.args) < 2:
        await update.message.reply_text(
            "📦 *Cara Berkontribusi:*\n"
            "`/contribute [resource] [jumlah]`\n\n"
            "Contoh: `/contribute gold 500`\n"
            f"Resource: {', '.join(RESOURCES)}",
            parse_mode="Markdown"
        )
        return

    res = ctx.args[0].lower()
    if res not in RESOURCES:
        await update.message.reply_text(
            f"❌ Resource tidak valid.\nPilih dari: {', '.join(RESOURCES)}"
        )
        return

    try:
        amount = int(ctx.args[1])
    except ValueError:
        await update.message.reply_text("❌ Jumlah harus berupa angka.")
        return

    if amount < KINGDOM_CONTRIBUTE_MIN:
        await update.message.reply_text(
            f"❌ Minimum kontribusi: {KINGDOM_CONTRIBUTE_MIN}"
        )
        return

    if player[res] < amount:
        await update.message.reply_text(
            f"❌ {res.title()} kamu tidak cukup!\n"
            f"Kamu punya: {player[res]:,} | Dibutuhkan: {amount:,}"
        )
        return

    kd = await _get_or_create_kingdom(update)
    if not kd:
        await update.message.reply_text("❌ Kingdom tidak ditemukan.")
        return

    # Deduct from player, add to kingdom
    await update_player(player["user_id"], **{res: player[res] - amount})
    await update_kingdom(chat.id, **{res: kd[res] + amount})

    emoji = RESOURCE_EMOJI.get(res, "•")
    await update.message.reply_text(
        f"✅ *Kontribusi Berhasil!*\n\n"
        f"{emoji} +{amount:,} {res.title()} → 🏰 {kd['name']}\n\n"
        f"Terima kasih sudah membantu kerajaan! 🙏",
        parse_mode="Markdown"
    )


# ──────────────────────────────────────────────
async def kadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text("🏰 Command ini hanya di Group Telegram!")
        return

    kd = await _get_or_create_kingdom(update)
    if not kd:
        await update.message.reply_text("❌ Kingdom tidak ditemukan.")
        return

    # Check if user is kingdom admin or officer
    user = update.effective_user
    chat_member = await ctx.bot.get_chat_member(chat.id, user.id)
    is_admin = chat_member.status in ("administrator", "creator") or kd["admin_id"] == user.id

    if not is_admin and player.get("role") not in ("officer", "kadmin"):
        await update.message.reply_text("🚫 Kamu bukan admin kerajaan!")
        return

    if not ctx.args:
        await update.message.reply_text(
            "⚙️ *Kingdom Admin Commands:*\n\n"
            "`/kadmin setname [nama]` — Ganti nama kerajaan\n"
            "`/kadmin settax [0-20]` — Set pajak kerajaan\n"
            "`/kadmin promote @user` — Jadikan Officer\n"
            "`/kadmin kick @user` — Keluarkan dari kerajaan\n"
            "`/kadmin announce [pesan]` — Umumkan ke group",
            parse_mode="Markdown"
        )
        return

    cmd = ctx.args[0].lower()

    if cmd == "setname":
        if len(ctx.args) < 2:
            await update.message.reply_text("❌ Format: `/kadmin setname [nama]`", parse_mode="Markdown")
            return
        new_name = " ".join(ctx.args[1:])
        if len(new_name) > 50:
            await update.message.reply_text("❌ Nama maksimal 50 karakter.")
            return
        await update_kingdom(chat.id, name=new_name)
        await update.message.reply_text(f"✅ Nama kerajaan diubah menjadi: *{new_name}*", parse_mode="Markdown")

    elif cmd == "settax":
        if len(ctx.args) < 2:
            await update.message.reply_text("❌ Format: `/kadmin settax [0-20]`", parse_mode="Markdown")
            return
        try:
            rate = int(ctx.args[1])
        except ValueError:
            await update.message.reply_text("❌ Pajak harus berupa angka 0-20.")
            return
        if not 0 <= rate <= 20:
            await update.message.reply_text("❌ Pajak harus antara 0 dan 20%.")
            return
        await update_kingdom(chat.id, tax_rate=rate)
        await update.message.reply_text(f"✅ Pajak kerajaan diatur ke *{rate}%*", parse_mode="Markdown")

    elif cmd == "announce":
        if len(ctx.args) < 2:
            await update.message.reply_text("❌ Format: `/kadmin announce [pesan]`", parse_mode="Markdown")
            return
        msg = " ".join(ctx.args[1:])
        await update.message.reply_text(
            f"📢 *PENGUMUMAN KERAJAAN*\n\n{msg}\n\n— Admin {user.first_name}",
            parse_mode="Markdown"
        )

    elif cmd == "promote":
        if len(ctx.args) < 2:
            await update.message.reply_text("❌ Format: `/kadmin promote @username`", parse_mode="Markdown")
            return
        target_uname = ctx.args[1].lstrip("@")
        import aiosqlite, os
        DB_PATH = os.environ.get("DB_PATH", "./game.db")
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM players WHERE username=?", (target_uname,)) as cur:
                target = await cur.fetchone()
        if not target:
            await update.message.reply_text(f"❌ Pemain *{target_uname}* tidak ditemukan.", parse_mode="Markdown")
            return
        await update_player(target["user_id"], role="officer")
        await update.message.reply_text(f"✅ *{target_uname}* dipromosikan menjadi Officer!", parse_mode="Markdown")

    elif cmd == "kick":
        if len(ctx.args) < 2:
            await update.message.reply_text("❌ Format: `/kadmin kick @username`", parse_mode="Markdown")
            return
        target_uname = ctx.args[1].lstrip("@")
        import aiosqlite, os
        DB_PATH = os.environ.get("DB_PATH", "./game.db")
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM players WHERE username=?", (target_uname,)) as cur:
                target = await cur.fetchone()
        if not target:
            await update.message.reply_text(f"❌ Pemain *{target_uname}* tidak ditemukan.", parse_mode="Markdown")
            return
        await update_player(target["user_id"], kingdom_id=0, role="member")
        await update.message.reply_text(f"✅ *{target_uname}* dikeluarkan dari kerajaan.", parse_mode="Markdown")

    else:
        await update.message.reply_text("❌ Command tidak dikenal. Ketik `/kadmin` untuk bantuan.", parse_mode="Markdown")


# ──────────────────────────────────────────────
async def kingdom_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "kingdom_members":
        chat = update.effective_chat
        if not chat or chat.type not in ("group", "supergroup"):
            await query.edit_message_text("❌ Hanya tersedia di group.")
            return
        kd = await get_kingdom(chat.id)
        if not kd:
            await query.edit_message_text("❌ Kingdom tidak ditemukan.")
            return
        members = await get_kingdom_members(kd["id"])
        if not members:
            await query.edit_message_text("👥 Belum ada member terdaftar di kerajaan ini.")
            return
        lines = [f"👥 *MEMBER {kd['name']}*\n"]
        for m in members[:20]:
            role_icon = "👑" if m["role"] == "kadmin" else ("⭐" if m["role"] == "officer" else "👤")
            lines.append(f"{role_icon} {m['username']} — Lv.{m['level']}")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")

    elif data == "kingdom_stats":
        await query.edit_message_text(
            "📊 Fitur statistik kerajaan akan segera hadir!",
            parse_mode="Markdown"
        )
