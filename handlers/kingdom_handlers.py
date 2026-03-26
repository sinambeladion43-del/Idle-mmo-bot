import time
import aiosqlite
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_player, create_player, update_player,
    get_kingdom, create_kingdom, update_kingdom,
    get_kingdom_members
)
from game_data import RESOURCES, RESOURCE_EMOJI, KINGDOM_CONTRIBUTE_MIN

DB_PATH = os.environ.get("DB_PATH", "./game.db")


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
        await create_kingdom(chat.id, name, admin_id)
        kingdom = await get_kingdom(chat.id)
    return kingdom


# ──────────────────────────────────────────────
async def kingdom(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    chat = update.effective_chat

    # ── Di DM: tampilkan info kerajaan player + tombol join ──
    if chat.type == "private":
        if player["kingdom_id"] == 0:
            await update.message.reply_text(
                "🏰 *Kingdom*\n\n"
                "Kamu belum bergabung ke kerajaan manapun.\n\n"
                "📌 *Cara Join Kingdom:*\n"
                "1. Masuk ke Group Telegram yang punya bot ini\n"
                "2. Ketik `/join` di group tersebut\n\n"
                "📌 *Cara Buat Kingdom Baru:*\n"
                "1. Tambahkan bot ke Group kamu\n"
                "2. Ketik `/kingdom` di group tersebut",
                parse_mode="Markdown"
            )
        else:
            from database import get_kingdom_by_id
            kd = await get_kingdom_by_id(player["kingdom_id"])
            if not kd:
                await update_player(player["user_id"], kingdom_id=0)
                await update.message.reply_text("❌ Kingdom kamu sudah tidak ada. Kamu telah dikeluarkan.")
                return
            members = await get_kingdom_members(kd["id"])
            role_icon = "👑" if player["role"] == "kadmin" else ("⭐" if player["role"] == "officer" else "👤")
            await update.message.reply_text(
                f"🏰 *Kerajaanmu: {kd['name']}*\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"⭐ Level   : {kd['level']}\n"
                f"👥 Member  : {len(members)}\n"
                f"💸 Pajak   : {kd['tax_rate']}%\n"
                f"🎖️ Posisimu: {role_icon} {player['role'].title()}\n"
                f"━━━━━━━━━━━━━━━━\n"
                f"*Kas Kerajaan:*\n"
                f"🪙 Gold  : {kd['gold']:,}\n"
                f"🪵 Wood  : {kd['wood']:,}\n"
                f"🪨 Stone : {kd['stone']:,}\n"
                f"🌾 Food  : {kd['food']:,}\n"
                f"⚔️ Iron  : {kd['iron']:,}\n\n"
                f"💡 Sumbang resource: `/contribute gold 500`\n"
                f"💡 Keluar kerajaan: `/leave`",
                parse_mode="Markdown"
            )
        return

    # ── Di Group ──────────────────────────────────────────────
    kd = await _get_or_create_kingdom(update)
    if not kd:
        await update.message.reply_text("❌ Gagal memuat kingdom.")
        return

    # Auto-assign player ke kingdom ini kalau belum join manapun
    if player["kingdom_id"] == 0:
        await update_player(player["user_id"], kingdom_id=kd["id"], role="member")
        player = await get_player(player["user_id"])

    members = await get_kingdom_members(kd["id"])

    text = (
        f"🏰 *{kd['name']}*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"⭐ Level   : {kd['level']}\n"
        f"👥 Member  : {len(members)}\n"
        f"💸 Pajak   : {kd['tax_rate']}%\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"*Kas Kerajaan:*\n"
        f"🪙 Gold  : {kd['gold']:,}\n"
        f"🪵 Wood  : {kd['wood']:,}\n"
        f"🪨 Stone : {kd['stone']:,}\n"
        f"🌾 Food  : {kd['food']:,}\n"
        f"⚔️ Iron  : {kd['iron']:,}\n\n"
        f"💡 Ketik `/join` untuk bergabung ke kerajaan ini!\n"
        f"💡 Sumbang: `/contribute gold 500`"
    )

    kb = [[
        InlineKeyboardButton("👥 Member",    callback_data="kingdom_members"),
        InlineKeyboardButton("🏆 Top Kingdom", callback_data="kingdom_top"),
    ]]
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ──────────────────────────────────────────────
async def join(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Ketik /join di group untuk bergabung ke kerajaan group tersebut."""
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text(
            "❌ `/join` hanya bisa digunakan di dalam Group Telegram!\n\n"
            "Masuk ke group yang ingin kamu ikuti, lalu ketik `/join` di sana.",
            parse_mode="Markdown"
        )
        return

    kd = await _get_or_create_kingdom(update)
    if not kd:
        await update.message.reply_text("❌ Gagal memuat kingdom.")
        return

    # Sudah di kingdom ini
    if player["kingdom_id"] == kd["id"]:
        await update.message.reply_text(
            f"✅ Kamu sudah menjadi member *{kd['name']}*!",
            parse_mode="Markdown"
        )
        return

    # Sudah di kingdom lain
    if player["kingdom_id"] != 0:
        from database import get_kingdom_by_id
        old_kd = await get_kingdom_by_id(player["kingdom_id"])
        old_name = old_kd["name"] if old_kd else "kerajaan lama"
        kb = [[
            InlineKeyboardButton("✅ Ya, pindah!", callback_data=f"kingdom_switch_{kd['id']}_{chat.id}"),
            InlineKeyboardButton("❌ Batal",       callback_data="kingdom_cancel"),
        ]]
        await update.message.reply_text(
            f"⚠️ *Kamu sudah di kerajaan lain!*\n\n"
            f"Kerajaan sekarang: *{old_name}*\n"
            f"Kerajaan baru: *{kd['name']}*\n\n"
            f"Yakin ingin pindah kerajaan? Semua kontribusi lama tidak bisa dikembalikan.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    # Belum punya kingdom — langsung join
    await update_player(player["user_id"], kingdom_id=kd["id"], role="member")
    members = await get_kingdom_members(kd["id"])

    await update.message.reply_text(
        f"🎉 *Selamat datang di {kd['name']}!*\n\n"
        f"👥 Total member sekarang: {len(members)}\n"
        f"💸 Pajak kerajaan: {kd['tax_rate']}%\n\n"
        f"💡 Mulai berkontribusi: `/contribute gold 100`\n"
        f"💡 Lihat info kerajaan: `/kingdom`",
        parse_mode="Markdown"
    )


# ──────────────────────────────────────────────
async def leave(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Keluar dari kerajaan."""
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    if player["kingdom_id"] == 0:
        await update.message.reply_text("❌ Kamu tidak sedang bergabung di kerajaan manapun.")
        return

    from database import get_kingdom_by_id
    kd = await get_kingdom_by_id(player["kingdom_id"])
    kd_name = kd["name"] if kd else "kerajaan"

    # Kalau dia admin kerajaan, tidak bisa keluar
    if kd and kd["admin_id"] == player["user_id"]:
        await update.message.reply_text(
            "⚠️ Kamu adalah *Admin Kerajaan*!\n"
            "Gunakan `/kadmin promote @user` untuk transfer kekuasaan dulu sebelum keluar.",
            parse_mode="Markdown"
        )
        return

    kb = [[
        InlineKeyboardButton("✅ Ya, keluar", callback_data="kingdom_leave_confirm"),
        InlineKeyboardButton("❌ Batal",      callback_data="kingdom_cancel"),
    ]]
    await update.message.reply_text(
        f"⚠️ Yakin ingin keluar dari *{kd_name}*?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ──────────────────────────────────────────────
async def contribute(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    chat = update.effective_chat

    # Tentukan kingdom_id dari context
    if chat.type in ("group", "supergroup"):
        kd = await _get_or_create_kingdom(update)
    else:
        if player["kingdom_id"] == 0:
            await update.message.reply_text(
                "❌ Kamu belum bergabung ke kerajaan manapun!\n"
                "Masuk ke group dan ketik `/join` dulu.",
                parse_mode="Markdown"
            )
            return
        from database import get_kingdom_by_id
        kd = await get_kingdom_by_id(player["kingdom_id"])

    if not kd:
        await update.message.reply_text("❌ Kingdom tidak ditemukan.")
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
        await update.message.reply_text(f"❌ Minimum kontribusi: {KINGDOM_CONTRIBUTE_MIN}")
        return

    if player[res] < amount:
        await update.message.reply_text(
            f"❌ {res.title()} kamu tidak cukup!\n"
            f"Kamu punya: {player[res]:,} | Dibutuhkan: {amount:,}"
        )
        return

    group_id = kd["group_id"]
    await update_player(player["user_id"], **{res: player[res] - amount})
    await update_kingdom(group_id, **{res: kd[res] + amount})

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
    user = update.effective_user

    if data == "kingdom_members":
        chat = update.effective_chat
        kd = None
        if chat and chat.type in ("group", "supergroup"):
            kd = await get_kingdom(chat.id)
        else:
            await create_player(user.id, user.username or user.first_name)
            p = await get_player(user.id)
            if p and p["kingdom_id"]:
                from database import get_kingdom_by_id
                kd = await get_kingdom_by_id(p["kingdom_id"])
        if not kd:
            await query.edit_message_text("❌ Kingdom tidak ditemukan.")
            return
        members = await get_kingdom_members(kd["id"])
        if not members:
            await query.edit_message_text("👥 Belum ada member terdaftar di kerajaan ini.")
            return
        lines = [f"👥 *MEMBER {kd['name']}* ({len(members)})\n"]
        for m in members[:20]:
            role_icon = "👑" if m["role"] == "kadmin" else ("⭐" if m["role"] == "officer" else "👤")
            lines.append(f"{role_icon} {m['username']} — Lv.{m['level']}")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")

    elif data == "kingdom_top":
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT *, (gold+wood+stone+food+iron) as total_res FROM kingdoms ORDER BY level DESC, total_res DESC LIMIT 10"
            ) as cur:
                kingdoms = await cur.fetchall()
        if not kingdoms:
            await query.edit_message_text("Belum ada kerajaan.")
            return
        medals = ["🥇", "🥈", "🥉"]
        lines = ["🏆 *TOP KINGDOM*\n"]
        for i, k in enumerate(kingdoms):
            medal = medals[i] if i < 3 else f"{i+1}."
            lines.append(f"{medal} *{k['name']}* — Lv.{k['level']}")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")

    elif data == "kingdom_leave_confirm":
        await create_player(user.id, user.username or user.first_name)
        player = await get_player(user.id)
        if player["kingdom_id"] == 0:
            await query.edit_message_text("❌ Kamu tidak sedang di kerajaan manapun.")
            return
        from database import get_kingdom_by_id
        kd = await get_kingdom_by_id(player["kingdom_id"])
        kd_name = kd["name"] if kd else "kerajaan"
        await update_player(player["user_id"], kingdom_id=0, role="member")
        await query.edit_message_text(
            f"✅ Kamu telah keluar dari *{kd_name}*.\n\n"
            f"Ketik `/join` di group manapun untuk bergabung lagi.",
            parse_mode="Markdown"
        )

    elif data.startswith("kingdom_switch_"):
        # format: kingdom_switch_{kingdom_id}_{group_id}
        parts = data.split("_")
        try:
            new_kingdom_id = int(parts[2])
            group_id = int(parts[3])
        except (IndexError, ValueError):
            await query.edit_message_text("❌ Data tidak valid.")
            return
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM kingdoms WHERE id=?", (new_kingdom_id,)) as cur:
                kd = await cur.fetchone()
        if not kd:
            await query.edit_message_text("❌ Kingdom tidak ditemukan.")
            return
        await create_player(user.id, user.username or user.first_name)
        await update_player(user.id, kingdom_id=new_kingdom_id, role="member")
        members = await get_kingdom_members(new_kingdom_id)
        await query.edit_message_text(
            f"🎉 *Berhasil pindah ke {kd['name']}!*\n\n"
            f"👥 Total member: {len(members)}\n"
            f"💡 Mulai berkontribusi: `/contribute gold 100`",
            parse_mode="Markdown"
        )

    elif data == "kingdom_cancel":
        await query.edit_message_text("❌ Dibatalkan.")
