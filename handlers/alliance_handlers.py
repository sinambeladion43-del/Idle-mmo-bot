import time
import aiosqlite
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_player, create_player, update_player,
    get_kingdom, get_kingdom_by_id,
    get_alliance, get_alliance_by_id, get_alliance_members,
    create_alliance, add_alliance_member, remove_alliance_member,
    delete_alliance, get_alliance_invite, create_alliance_invite,
    update_alliance_invite, get_all_alliances
)

DB_PATH = os.environ.get("DB_PATH", "./game.db")


async def _ensure_player(update: Update):
    user = update.effective_user
    await create_player(user.id, user.username or user.first_name)
    return await get_player(user.id)


async def _get_kingdom_of_group(chat_id: int):
    return await get_kingdom(chat_id)


async def _is_kingdom_admin(ctx, chat_id: int, user_id: int, kingdom) -> bool:
    try:
        member = await ctx.bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator") or kingdom["admin_id"] == user_id
    except Exception:
        return kingdom["admin_id"] == user_id


# ──────────────────────────────────────────────
async def alliance(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /alliance                  — lihat info aliansi kerajaan ini
    /alliance create [nama]    — buat aliansi baru
    /alliance invite [nama kd] — undang kerajaan lain
    /alliance accept           — terima undangan
    /alliance reject           — tolak undangan
    /alliance leave            — keluar dari aliansi
    /alliance disband          — bubarkan aliansi (founder)
    /alliance list             — lihat semua aliansi
    """
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text(
            "🤝 *Command /alliance hanya bisa di Group Telegram!*",
            parse_mode="Markdown"
        )
        return

    my_kd = await get_kingdom(chat.id)
    if not my_kd:
        await update.message.reply_text(
            "❌ Group ini belum punya kerajaan.\nKetik `/kingdom` dulu.",
            parse_mode="Markdown"
        )
        return

    args = ctx.args or []

    # ── /alliance (tanpa argumen) ─────────────
    if not args:
        al = await get_alliance(my_kd["id"])
        if not al:
            # Cek apakah ada undangan pending
            invite = await get_alliance_invite(my_kd["id"])
            if invite:
                from_kd = await get_kingdom_by_id(invite["from_kingdom_id"])
                from_al = await get_alliance_by_id(invite["alliance_id"])
                kb = [[
                    InlineKeyboardButton("✅ Terima", callback_data=f"al_accept_{invite['id']}"),
                    InlineKeyboardButton("❌ Tolak",  callback_data=f"al_reject_{invite['id']}"),
                ]]
                await update.message.reply_text(
                    f"📨 *Ada Undangan Aliansi!*\n\n"
                    f"Kerajaan *{from_kd['name'] if from_kd else 'Unknown'}* "
                    f"mengundang kamu ke aliansi *{from_al['name'] if from_al else 'Unknown'}*!\n\n"
                    f"Ketik `/alliance accept` atau `/alliance reject`",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(kb)
                )
                return

            await update.message.reply_text(
                f"🤝 *ALIANSI — {my_kd['name']}*\n\n"
                f"Kerajaan kamu belum bergabung ke aliansi manapun.\n\n"
                f"📌 *Command Aliansi:*\n"
                f"`/alliance create [nama]` — Buat aliansi baru\n"
                f"`/alliance list` — Lihat semua aliansi\n"
                f"`/alliance invite [nama kerajaan]` — Undang kerajaan lain\n\n"
                f"💡 Aliansi tidak bisa saling serang di Kingdom War!",
                parse_mode="Markdown"
            )
            return

        # Sudah punya aliansi
        members = await get_alliance_members(al["id"])
        founder_kd = await get_kingdom_by_id(al["founder_kingdom_id"])
        is_founder = al["founder_kingdom_id"] == my_kd["id"]

        lines = [
            f"🤝 *ALIANSI: {al['name']}*\n",
            f"👑 Pendiri : {founder_kd['name'] if founder_kd else 'Unknown'}",
            f"🏰 Anggota : {len(members)} kerajaan\n",
            "*Daftar Kerajaan:*"
        ]
        for m in members:
            role_icon = "👑" if m["alliance_role"] == "founder" else "🏰"
            lines.append(f"  {role_icon} {m['name']}")

        lines.append(f"\n💡 `/alliance invite [nama kerajaan]` — undang kerajaan baru")
        if is_founder:
            lines.append(f"💡 `/alliance disband` — bubarkan aliansi")
        else:
            lines.append(f"💡 `/alliance leave` — keluar dari aliansi")

        kb = [[InlineKeyboardButton("🏆 Top Aliansi", callback_data="al_list")]]
        await update.message.reply_text(
            "\n".join(lines), parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    cmd = args[0].lower()

    # ── /alliance create [nama] ───────────────
    if cmd == "create":
        if not await _is_kingdom_admin(ctx, chat.id, player["user_id"], my_kd):
            await update.message.reply_text("🚫 Hanya Admin Kerajaan yang bisa membuat aliansi!")
            return

        existing = await get_alliance(my_kd["id"])
        if existing:
            await update.message.reply_text(
                f"❌ Kerajaan kamu sudah bergabung di aliansi *{existing['name']}*!\n"
                f"Keluar dulu dengan `/alliance leave`",
                parse_mode="Markdown"
            )
            return

        if len(args) < 2:
            await update.message.reply_text(
                "❌ Format: `/alliance create [nama aliansi]`\n"
                "Contoh: `/alliance create Pakta Nusantara`",
                parse_mode="Markdown"
            )
            return

        name = " ".join(args[1:])
        if len(name) > 50:
            await update.message.reply_text("❌ Nama aliansi maksimal 50 karakter.")
            return

        # Cek nama unik
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT id FROM alliances WHERE LOWER(name)=?", (name.lower(),)) as cur:
                existing_name = await cur.fetchone()
        if existing_name:
            await update.message.reply_text(f"❌ Nama aliansi *{name}* sudah dipakai!", parse_mode="Markdown")
            return

        al_id = await create_alliance(name, my_kd["id"])
        await add_alliance_member(al_id, my_kd["id"], "founder")

        await update.message.reply_text(
            f"🎉 *Aliansi '{name}' berhasil dibuat!*\n\n"
            f"🏰 Kerajaan *{my_kd['name']}* adalah pendiri.\n\n"
            f"📌 Undang kerajaan lain:\n"
            f"`/alliance invite [nama kerajaan]`\n\n"
            f"💡 Anggota aliansi tidak bisa saling serang!",
            parse_mode="Markdown"
        )

    # ── /alliance invite [nama kerajaan] ─────
    elif cmd == "invite":
        if not await _is_kingdom_admin(ctx, chat.id, player["user_id"], my_kd):
            await update.message.reply_text("🚫 Hanya Admin/Officer yang bisa mengundang!")
            return

        al = await get_alliance(my_kd["id"])
        if not al:
            await update.message.reply_text(
                "❌ Kerajaan kamu belum punya aliansi!\n"
                "Buat dulu dengan `/alliance create [nama]`",
                parse_mode="Markdown"
            )
            return

        if len(args) < 2:
            await update.message.reply_text(
                "❌ Format: `/alliance invite [nama kerajaan]`",
                parse_mode="Markdown"
            )
            return

        target_name = " ".join(args[1:])
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM kingdoms WHERE LOWER(name) LIKE ?",
                (f"%{target_name.lower()}%",)
            ) as cur:
                target_kd = await cur.fetchone()

        if not target_kd:
            await update.message.reply_text(
                f"❌ Kerajaan *{target_name}* tidak ditemukan!\n"
                f"Gunakan nama lengkap kerajaan.",
                parse_mode="Markdown"
            )
            return

        if target_kd["id"] == my_kd["id"]:
            await update.message.reply_text("❌ Tidak bisa mengundang kerajaan sendiri.")
            return

        # Cek apakah target sudah di aliansi
        target_al = await get_alliance(target_kd["id"])
        if target_al:
            await update.message.reply_text(
                f"❌ *{target_kd['name']}* sudah bergabung di aliansi lain!",
                parse_mode="Markdown"
            )
            return

        await create_alliance_invite(al["id"], my_kd["id"], target_kd["id"])

        # Kirim notif ke group target
        try:
            await ctx.bot.send_message(
                target_kd["group_id"],
                f"📨 *UNDANGAN ALIANSI!*\n\n"
                f"Kerajaan *{my_kd['name']}* mengundang kamu bergabung ke aliansi *{al['name']}*!\n\n"
                f"Ketik `/alliance accept` untuk menerima\n"
                f"Ketik `/alliance reject` untuk menolak",
                parse_mode="Markdown"
            )
        except Exception:
            pass

        await update.message.reply_text(
            f"✅ Undangan dikirim ke *{target_kd['name']}*!\n"
            f"Mereka akan dapat notifikasi di group mereka.",
            parse_mode="Markdown"
        )

    # ── /alliance accept ──────────────────────
    elif cmd == "accept":
        if not await _is_kingdom_admin(ctx, chat.id, player["user_id"], my_kd):
            await update.message.reply_text("🚫 Hanya Admin Kerajaan yang bisa menerima undangan!")
            return

        invite = await get_alliance_invite(my_kd["id"])
        if not invite:
            await update.message.reply_text("❌ Tidak ada undangan aliansi yang pending.")
            return

        al = await get_alliance_by_id(invite["alliance_id"])
        if not al:
            await update.message.reply_text("❌ Aliansi tidak ditemukan.")
            return

        await add_alliance_member(al["id"], my_kd["id"], "member")
        await update_alliance_invite(invite["id"], "accepted")

        members = await get_alliance_members(al["id"])

        # Notif ke semua group member aliansi
        for m in members:
            if m["id"] != my_kd["id"]:
                try:
                    await ctx.bot.send_message(
                        m["group_id"],
                        f"🎉 *{my_kd['name']}* telah bergabung ke aliansi *{al['name']}*!\n"
                        f"Total anggota: {len(members)} kerajaan",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

        await update.message.reply_text(
            f"✅ *Berhasil bergabung ke aliansi {al['name']}!*\n\n"
            f"🏰 Total anggota: {len(members)} kerajaan\n\n"
            f"💡 Sesama anggota aliansi tidak bisa saling serang!",
            parse_mode="Markdown"
        )

    # ── /alliance reject ──────────────────────
    elif cmd == "reject":
        invite = await get_alliance_invite(my_kd["id"])
        if not invite:
            await update.message.reply_text("❌ Tidak ada undangan yang perlu ditolak.")
            return

        al = await get_alliance_by_id(invite["alliance_id"])
        await update_alliance_invite(invite["id"], "rejected")

        await update.message.reply_text(
            f"✅ Undangan dari aliansi *{al['name'] if al else 'Unknown'}* ditolak.",
            parse_mode="Markdown"
        )

    # ── /alliance leave ───────────────────────
    elif cmd == "leave":
        if not await _is_kingdom_admin(ctx, chat.id, player["user_id"], my_kd):
            await update.message.reply_text("🚫 Hanya Admin Kerajaan yang bisa keluar dari aliansi!")
            return

        al = await get_alliance(my_kd["id"])
        if not al:
            await update.message.reply_text("❌ Kerajaan kamu tidak sedang di aliansi manapun.")
            return

        if al["founder_kingdom_id"] == my_kd["id"]:
            await update.message.reply_text(
                "⚠️ Kamu adalah *Pendiri Aliansi*!\n"
                "Gunakan `/alliance disband` untuk membubarkan aliansi,\n"
                "atau transfer kepemimpinan ke kerajaan lain dulu.",
                parse_mode="Markdown"
            )
            return

        await remove_alliance_member(al["id"], my_kd["id"])

        # Notif ke anggota lain
        members = await get_alliance_members(al["id"])
        for m in members:
            try:
                await ctx.bot.send_message(
                    m["group_id"],
                    f"📢 *{my_kd['name']}* telah keluar dari aliansi *{al['name']}*.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        await update.message.reply_text(
            f"✅ Kerajaan *{my_kd['name']}* telah keluar dari aliansi *{al['name']}*.",
            parse_mode="Markdown"
        )

    # ── /alliance disband ─────────────────────
    elif cmd == "disband":
        if not await _is_kingdom_admin(ctx, chat.id, player["user_id"], my_kd):
            await update.message.reply_text("🚫 Hanya Admin Kerajaan yang bisa membubarkan aliansi!")
            return

        al = await get_alliance(my_kd["id"])
        if not al:
            await update.message.reply_text("❌ Kerajaan kamu tidak sedang di aliansi manapun.")
            return

        if al["founder_kingdom_id"] != my_kd["id"]:
            await update.message.reply_text("🚫 Hanya *Pendiri Aliansi* yang bisa membubarkan!")
            return

        members = await get_alliance_members(al["id"])
        al_name = al["name"]
        await delete_alliance(al["id"])

        # Notif ke semua anggota
        for m in members:
            try:
                await ctx.bot.send_message(
                    m["group_id"],
                    f"💔 *Aliansi {al_name} telah dibubarkan* oleh pendirinya.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        await update.message.reply_text(
            f"✅ Aliansi *{al_name}* telah dibubarkan.",
            parse_mode="Markdown"
        )

    # ── /alliance list ────────────────────────
    elif cmd == "list":
        alliances = await get_all_alliances()
        if not alliances:
            await update.message.reply_text("🤝 Belum ada aliansi yang terbentuk.")
            return

        lines = ["🤝 *DAFTAR ALIANSI*\n"]
        for al in alliances[:15]:
            members = await get_alliance_members(al["id"])
            lines.append(f"⚜️ *{al['name']}* — {len(members)} kerajaan")

        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    else:
        await update.message.reply_text(
            "❌ Command tidak dikenal.\nKetik `/alliance` untuk bantuan.",
            parse_mode="Markdown"
        )


# ──────────────────────────────────────────────
async def alliance_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "al_list":
        alliances = await get_all_alliances()
        if not alliances:
            await query.edit_message_text("🤝 Belum ada aliansi.")
            return
        lines = ["🏆 *TOP ALIANSI*\n"]
        for al in alliances[:10]:
            members = await get_alliance_members(al["id"])
            lines.append(f"⚜️ *{al['name']}* — {len(members)} kerajaan")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")

    elif data.startswith("al_accept_"):
        invite_id = int(data.split("_")[2])
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM alliance_invites WHERE id=?", (invite_id,)) as cur:
                invite = await cur.fetchone()
        if not invite or invite["status"] != "pending":
            await query.edit_message_text("❌ Undangan sudah tidak valid.")
            return
        al = await get_alliance_by_id(invite["alliance_id"])
        target_kd = await get_kingdom_by_id(invite["target_kingdom_id"])
        if not al or not target_kd:
            await query.edit_message_text("❌ Data tidak valid.")
            return
        await add_alliance_member(al["id"], target_kd["id"], "member")
        await update_alliance_invite(invite_id, "accepted")
        await query.edit_message_text(
            f"✅ *Berhasil bergabung ke aliansi {al['name']}!*\n\n"
            f"💡 Sesama anggota tidak bisa saling serang!",
            parse_mode="Markdown"
        )

    elif data.startswith("al_reject_"):
        invite_id = int(data.split("_")[2])
        await update_alliance_invite(invite_id, "rejected")
        await query.edit_message_text("✅ Undangan ditolak.")
