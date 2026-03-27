import time
import aiosqlite
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_player, create_player, update_player,
    get_all_players, get_all_wars
)
from config import ADMIN_IDS
from game_data import RESOURCES

DB_PATH = os.environ.get("DB_PATH", "./game.db")


async def _ensure_player(update: Update):
    user = update.effective_user
    await create_player(user.id, user.username or user.first_name)
    return await get_player(user.id)


def _is_super_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def _escape(text: str) -> str:
    for ch in ["_", "*", "[", "]", "`"]:
        text = text.replace(ch, f"\\{ch}")
    return text


# ──────────────────────────────────────────────
async def admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not _is_super_admin(user.id):
        await update.message.reply_text("🚫 Kamu bukan Super Admin!")
        return

    args = ctx.args or []
    if not args:
        await update.message.reply_text(
            "👑 *SUPER ADMIN PANEL*\n\n"
            "👤 *Player*\n"
            "`/admin stats` — Statistik bot\n"
            "`/admin playerinfo @user` — Info detail pemain\n"
            "`/admin additem @user [res] [amt]` — Tambah resource\n"
            "`/admin removeitem @user [res] [amt]` — Hapus resource\n"
            "`/admin setgold @user [amt]` — Set gold\n"
            "`/admin resetplayer @user` — Reset data pemain\n"
            "`/admin ban @user` — Ban player\n"
            "`/admin unban @user` — Unban player\n"
            "`/admin broadcast [pesan]` — Broadcast ke semua\n\n"
            "🏰 *Kingdom*\n"
            "`/admin kingdoms` — Lihat semua kerajaan\n"
            "`/admin kingdominfo [nama/id]` — Info detail kerajaan\n"
            "`/admin resetkingdom [nama/id]` — Reset 1 kerajaan\n"
            "`/admin resetallkingdoms` — Reset SEMUA kerajaan\n\n"
            "⚔️ *War*\n"
            "`/admin resetwar` — Reset data war 1v1\n"
            "`/admin resetkwar` — Reset data kingdom war",
            parse_mode="Markdown"
        )
        return

    cmd = args[0].lower()

    # ── /admin stats ──────────────────────────
    if cmd == "stats":
        players = await get_all_players()
        total   = len(players)
        banned  = sum(1 for p in players if p["is_banned"])
        now     = int(time.time())
        active_24h = sum(1 for p in players if (now - (p["last_daily"] or 0)) < 86400)
        wars    = await get_all_wars(1000)

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT COUNT(*) as c FROM kingdoms") as cur:
                kd_count = (await cur.fetchone())["c"]
            async with db.execute("SELECT COUNT(*) as c FROM alliances") as cur:
                al_count = (await cur.fetchone())["c"]

        await update.message.reply_text(
            f"📊 *STATISTIK BOT*\n\n"
            f"👥 Total Player    : {total}\n"
            f"✅ Aktif (24h)     : {active_24h}\n"
            f"🚫 Di-ban          : {banned}\n"
            f"🏰 Total Kingdom   : {kd_count}\n"
            f"🤝 Total Aliansi   : {al_count}\n"
            f"⚔️ Total War 1v1   : {len(wars)}",
            parse_mode="Markdown"
        )

    # ── /admin playerinfo @user ───────────────
    elif cmd == "playerinfo":
        if len(args) < 2:
            await update.message.reply_text("❌ Format: `/admin playerinfo @username`", parse_mode="Markdown")
            return
        target_uname = args[1].lstrip("@")
        target = await _find_player_by_username(target_uname)
        if not target:
            await update.message.reply_text(f"❌ Pemain *{_escape(target_uname)}* tidak ditemukan.", parse_mode="Markdown")
            return

        import datetime
        joined = datetime.datetime.fromtimestamp(target["created_at"]).strftime("%d/%m/%Y") if target["created_at"] else "?"
        last_daily = datetime.datetime.fromtimestamp(target["last_daily"]).strftime("%d/%m %H:%M") if target["last_daily"] else "Belum"

        # Cari kerajaan
        kd_name = "Tidak ada"
        if target["kingdom_id"]:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT name FROM kingdoms WHERE id=?", (target["kingdom_id"],)) as cur:
                    kd_row = await cur.fetchone()
                    if kd_row:
                        kd_name = kd_row["name"]

        name = _escape(target["username"])
        await update.message.reply_text(
            f"👤 *INFO PEMAIN: {name}*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🆔 User ID     : `{target['user_id']}`\n"
            f"⭐ Level       : {target['level']}\n"
            f"📊 EXP         : {target['exp']:,}\n"
            f"❤️ HP           : {target['hp']}/{target['max_hp']}\n"
            f"⚔️ Attack       : {target['attack_pow']}\n"
            f"🛡️ Defense      : {target['defense_pow']}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🪙 Gold         : {target['gold']:,}\n"
            f"🪵 Wood         : {target['wood']:,}\n"
            f"🪨 Stone        : {target['stone']:,}\n"
            f"🌾 Food         : {target['food']:,}\n"
            f"⚔️ Iron         : {target['iron']:,}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"🏰 Kingdom     : {_escape(kd_name)}\n"
            f"🎖️ Role        : {target['role']}\n"
            f"🚫 Banned      : {'Ya' if target['is_banned'] else 'Tidak'}\n"
            f"📅 Bergabung   : {joined}\n"
            f"🎁 Daily terakhir: {last_daily}",
            parse_mode="Markdown"
        )

    # ── /admin kingdoms ───────────────────────
    elif cmd == "kingdoms":
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM kingdoms ORDER BY id") as cur:
                kingdoms = await cur.fetchall()

        if not kingdoms:
            await update.message.reply_text("🏰 Belum ada kerajaan terdaftar.")
            return

        lines = [f"🏰 *DAFTAR KERAJAAN ({len(kingdoms)})*\n"]
        for kd in kingdoms:
            async with aiosqlite.connect(DB_PATH) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute("SELECT COUNT(*) as c FROM players WHERE kingdom_id=?", (kd["id"],)) as cur:
                    member_count = (await cur.fetchone())["c"]
            lines.append(
                f"[{kd['id']}] *{_escape(kd['name'])}*\n"
                f"   👥 {member_count} member | Lv.{kd['level']} | "
                f"🪙{kd['gold']:,} 🪵{kd['wood']:,} 🪨{kd['stone']:,}"
            )
        lines.append("\n💡 Detail: `/admin kingdominfo [id]`")
        lines.append("💡 Hapus: `/admin resetkingdom [id]`")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    # ── /admin kingdominfo [id/nama] ──────────
    elif cmd == "kingdominfo":
        if len(args) < 2:
            await update.message.reply_text("❌ Format: `/admin kingdominfo [id atau nama]`", parse_mode="Markdown")
            return

        kd = await _find_kingdom(args[1])
        if not kd:
            await update.message.reply_text(f"❌ Kerajaan tidak ditemukan.", parse_mode="Markdown")
            return

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM players WHERE kingdom_id=?", (kd["id"],)) as cur:
                members = await cur.fetchall()
            async with db.execute("SELECT username FROM players WHERE user_id=?", (kd["admin_id"],)) as cur:
                admin_row = await cur.fetchone()

        import datetime
        created = datetime.datetime.fromtimestamp(kd["created_at"]).strftime("%d/%m/%Y") if kd["created_at"] else "?"
        admin_name = admin_row["username"] if admin_row else "?"

        member_lines = []
        for m in members[:10]:
            role_icon = "👑" if m["role"] == "kadmin" else "⭐" if m["role"] == "officer" else "👤"
            member_lines.append(f"  {role_icon} {_escape(m['username'])} Lv.{m['level']}")

        await update.message.reply_text(
            f"🏰 *INFO KERAJAAN*\n\n"
            f"🆔 ID        : `{kd['id']}`\n"
            f"📛 Nama      : *{_escape(kd['name'])}*\n"
            f"⭐ Level     : {kd['level']}\n"
            f"👑 Admin     : {_escape(admin_name)}\n"
            f"👥 Member    : {len(members)}\n"
            f"💸 Pajak     : {kd['tax_rate']}%\n"
            f"📅 Dibuat    : {created}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"*Kas Kerajaan:*\n"
            f"🪙 Gold  : {kd['gold']:,}\n"
            f"🪵 Wood  : {kd['wood']:,}\n"
            f"🪨 Stone : {kd['stone']:,}\n"
            f"🌾 Food  : {kd['food']:,}\n"
            f"⚔️ Iron  : {kd['iron']:,}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"*Member ({len(members)}):*\n" +
            ("\n".join(member_lines) if member_lines else "  Tidak ada member") +
            (f"\n  ... dan {len(members)-10} lainnya" if len(members) > 10 else "") +
            f"\n\n💡 Hapus: `/admin resetkingdom {kd['id']}`",
            parse_mode="Markdown"
        )

    # ── /admin resetkingdom [id/nama] ─────────
    elif cmd == "resetkingdom":
        if len(args) < 2:
            await update.message.reply_text(
                "❌ Format: `/admin resetkingdom [id atau nama kerajaan]`\n\n"
                "Lihat ID kerajaan dengan `/admin kingdoms`",
                parse_mode="Markdown"
            )
            return

        kd = await _find_kingdom(args[1])
        if not kd:
            await update.message.reply_text("❌ Kerajaan tidak ditemukan.", parse_mode="Markdown")
            return

        kd_name = kd["name"]
        kd_id   = kd["id"]

        async with aiosqlite.connect(DB_PATH) as db:
            # Reset kingdom_id semua member ke 0
            await db.execute(
                "UPDATE players SET kingdom_id=0, role='member' WHERE kingdom_id=?",
                (kd_id,)
            )
            # Hapus kerajaan
            await db.execute("DELETE FROM kingdoms WHERE id=?", (kd_id,))
            # Hapus war history kerajaan ini
            await db.execute(
                "DELETE FROM kingdom_wars WHERE attacker_kingdom_id=? OR defender_kingdom_id=?",
                (kd_id, kd_id)
            )
            # Hapus dari aliansi
            await db.execute("DELETE FROM alliance_members WHERE kingdom_id=?", (kd_id,))
            await db.commit()

        await update.message.reply_text(
            f"✅ *Kerajaan '{_escape(kd_name)}' berhasil dihapus!*\n\n"
            f"• Semua member dikeluarkan dari kerajaan\n"
            f"• Data war kerajaan dihapus\n"
            f"• Data pemain tetap aman ✅\n\n"
            f"Member bisa join kerajaan baru dengan `/join` di group.",
            parse_mode="Markdown"
        )

    # ── /admin resetallkingdoms ───────────────
    elif cmd == "resetallkingdoms":
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT COUNT(*) as c FROM kingdoms") as cur:
                count = (await cur.fetchone())["c"]

        if count == 0:
            await update.message.reply_text("❌ Tidak ada kerajaan yang perlu direset.")
            return

        # Konfirmasi dulu
        kb = [[
            InlineKeyboardButton(f"✅ Ya, hapus semua {count} kerajaan", callback_data="admin_resetallkd_confirm"),
            InlineKeyboardButton("❌ Batal", callback_data="admin_cancel"),
        ]]
        await update.message.reply_text(
            f"⚠️ *KONFIRMASI HAPUS SEMUA KERAJAAN*\n\n"
            f"Ini akan menghapus *{count} kerajaan* beserta:\n"
            f"• Semua data kas kerajaan\n"
            f"• Semua war history kerajaan\n"
            f"• Semua data aliansi\n\n"
            f"✅ Data pemain (level, resource, dll) *TIDAK* dihapus.\n\n"
            f"Yakin?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # ── /admin resetplayer @user ──────────────
    elif cmd == "resetplayer":
        if len(args) < 2:
            await update.message.reply_text("❌ Format: `/admin resetplayer @username`", parse_mode="Markdown")
            return
        target_uname = args[1].lstrip("@")
        target = await _find_player_by_username(target_uname)
        if not target:
            await update.message.reply_text(f"❌ Pemain *{_escape(target_uname)}* tidak ditemukan.", parse_mode="Markdown")
            return

        kb = [[
            InlineKeyboardButton(f"✅ Ya, reset {target_uname}", callback_data=f"admin_resetplayer_{target['user_id']}"),
            InlineKeyboardButton("❌ Batal", callback_data="admin_cancel"),
        ]]
        await update.message.reply_text(
            f"⚠️ *KONFIRMASI RESET PEMAIN*\n\n"
            f"Ini akan reset *{_escape(target_uname)}* ke kondisi awal:\n"
            f"• Level → 1, EXP → 0\n"
            f"• HP → 100, ATK → 10, DEF → 10\n"
            f"• Gold → 100, semua resource → 0\n"
            f"• Keluar dari kerajaan\n"
            f"• Semua bangunan dihapus\n\n"
            f"Yakin?",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # ── /admin additem ────────────────────────
    elif cmd == "additem":
        if len(args) < 4:
            await update.message.reply_text("❌ Format: `/admin additem @user [resource] [jumlah]`", parse_mode="Markdown")
            return
        target_uname = args[1].lstrip("@")
        res = args[2].lower()
        if res not in RESOURCES:
            await update.message.reply_text(f"❌ Resource tidak valid: {res}")
            return
        try:
            amt = int(args[3])
        except ValueError:
            await update.message.reply_text("❌ Jumlah harus angka.")
            return
        target = await _find_player_by_username(target_uname)
        if not target:
            await update.message.reply_text(f"❌ Pemain *{_escape(target_uname)}* tidak ditemukan.", parse_mode="Markdown")
            return
        await update_player(target["user_id"], **{res: target[res] + amt})
        await update.message.reply_text(f"✅ +{amt:,} {res} diberikan ke *{_escape(target_uname)}*", parse_mode="Markdown")

    # ── /admin removeitem ─────────────────────
    elif cmd == "removeitem":
        if len(args) < 4:
            await update.message.reply_text("❌ Format: `/admin removeitem @user [resource] [jumlah]`", parse_mode="Markdown")
            return
        target_uname = args[1].lstrip("@")
        res = args[2].lower()
        if res not in RESOURCES:
            await update.message.reply_text(f"❌ Resource tidak valid: {res}")
            return
        try:
            amt = int(args[3])
        except ValueError:
            await update.message.reply_text("❌ Jumlah harus angka.")
            return
        target = await _find_player_by_username(target_uname)
        if not target:
            await update.message.reply_text(f"❌ Pemain *{_escape(target_uname)}* tidak ditemukan.", parse_mode="Markdown")
            return
        new_val = max(0, target[res] - amt)
        await update_player(target["user_id"], **{res: new_val})
        await update.message.reply_text(f"✅ -{amt:,} {res} dihapus dari *{_escape(target_uname)}*", parse_mode="Markdown")

    # ── /admin setgold ────────────────────────
    elif cmd == "setgold":
        if len(args) < 3:
            await update.message.reply_text("❌ Format: `/admin setgold @user [jumlah]`", parse_mode="Markdown")
            return
        target_uname = args[1].lstrip("@")
        try:
            amt = int(args[2])
        except ValueError:
            await update.message.reply_text("❌ Jumlah harus angka.")
            return
        target = await _find_player_by_username(target_uname)
        if not target:
            await update.message.reply_text(f"❌ Pemain *{_escape(target_uname)}* tidak ditemukan.", parse_mode="Markdown")
            return
        await update_player(target["user_id"], gold=amt)
        await update.message.reply_text(f"✅ Gold *{_escape(target_uname)}* diset ke {amt:,}", parse_mode="Markdown")

    # ── /admin ban ────────────────────────────
    elif cmd == "ban":
        if len(args) < 2:
            await update.message.reply_text("❌ Format: `/admin ban @user`", parse_mode="Markdown")
            return
        target_uname = args[1].lstrip("@")
        target = await _find_player_by_username(target_uname)
        if not target:
            await update.message.reply_text(f"❌ Pemain *{_escape(target_uname)}* tidak ditemukan.", parse_mode="Markdown")
            return
        await update_player(target["user_id"], is_banned=1)
        await update.message.reply_text(f"🚫 *{_escape(target_uname)}* telah di-ban.", parse_mode="Markdown")

    # ── /admin unban ──────────────────────────
    elif cmd == "unban":
        if len(args) < 2:
            await update.message.reply_text("❌ Format: `/admin unban @user`", parse_mode="Markdown")
            return
        target_uname = args[1].lstrip("@")
        target = await _find_player_by_username(target_uname)
        if not target:
            await update.message.reply_text(f"❌ Pemain *{_escape(target_uname)}* tidak ditemukan.", parse_mode="Markdown")
            return
        await update_player(target["user_id"], is_banned=0)
        await update.message.reply_text(f"✅ *{_escape(target_uname)}* berhasil di-unban.", parse_mode="Markdown")

    # ── /admin broadcast ──────────────────────
    elif cmd == "broadcast":
        if len(args) < 2:
            await update.message.reply_text("❌ Format: `/admin broadcast [pesan]`", parse_mode="Markdown")
            return
        msg = " ".join(args[1:])
        players = await get_all_players()
        sent = 0
        failed = 0
        for p in players:
            if p["is_banned"]:
                continue
            try:
                await ctx.bot.send_message(p["user_id"], f"📢 *BROADCAST*\n\n{msg}", parse_mode="Markdown")
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(f"✅ Broadcast: {sent} berhasil, {failed} gagal")

    # ── /admin resetwar ───────────────────────
    elif cmd == "resetwar":
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM wars")
            await db.commit()
        await update.message.reply_text("✅ Semua data war 1v1 telah direset.")

    # ── /admin resetkwar ──────────────────────
    elif cmd == "resetkwar":
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM kingdom_wars")
            await db.execute("DELETE FROM war_declarations")
            await db.execute("DELETE FROM war_votes")
            await db.commit()
        await update.message.reply_text("✅ Semua data kingdom war telah direset.")

    else:
        await update.message.reply_text(
            f"❌ Command tidak dikenal: `{cmd}`\nKetik `/admin` untuk bantuan.",
            parse_mode="Markdown"
        )


# ──────────────────────────────────────────────
async def admin_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user  = update.effective_user

    if not _is_super_admin(user.id):
        await query.answer("🚫 Bukan Super Admin!", show_alert=True)
        return

    await query.answer()
    data = query.data

    if data == "admin_cancel":
        await query.edit_message_text("❌ Dibatalkan.")
        return

    # ── Konfirmasi reset semua kerajaan ───────
    if data == "admin_resetallkd_confirm":
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("UPDATE players SET kingdom_id=0, role='member'")
            await db.execute("DELETE FROM kingdoms")
            await db.execute("DELETE FROM kingdom_wars")
            await db.execute("DELETE FROM war_declarations")
            await db.execute("DELETE FROM war_votes")
            await db.execute("DELETE FROM alliance_members")
            await db.execute("DELETE FROM alliances")
            await db.commit()
        await query.edit_message_text(
            "✅ *Semua kerajaan berhasil direset!*\n\n"
            "• Semua kerajaan dihapus\n"
            "• Semua aliansi dihapus\n"
            "• Semua war history dihapus\n"
            "• Data pemain tetap aman ✅\n\n"
            "Member bisa buat kerajaan baru dengan `/kingdom` di group.",
            parse_mode="Markdown"
        )

    # ── Konfirmasi reset 1 pemain ─────────────
    elif data.startswith("admin_resetplayer_"):
        target_id = int(data.split("_")[2])
        async with aiosqlite.connect(DB_PATH) as db:
            # Reset stats pemain
            await db.execute(
                """UPDATE players SET
                   level=1, exp=0, gold=100, wood=0, stone=0, food=0, iron=0,
                   attack_pow=10, defense_pow=10, hp=100, max_hp=100,
                   kingdom_id=0, role='member', last_daily=0, last_collect=0
                   WHERE user_id=?""",
                (target_id,)
            )
            # Hapus semua bangunan
            await db.execute("DELETE FROM buildings WHERE user_id=?", (target_id,))
            # Hapus market listing
            await db.execute("DELETE FROM market_listings WHERE seller_id=?", (target_id,))
            await db.commit()

        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT username FROM players WHERE user_id=?", (target_id,)) as cur:
                row = await cur.fetchone()

        name = _escape(row["username"]) if row else str(target_id)
        await query.edit_message_text(
            f"✅ *Pemain {name} berhasil direset!*\n\n"
            f"• Level → 1, EXP → 0\n"
            f"• Gold → 100, resource → 0\n"
            f"• Semua bangunan dihapus\n"
            f"• Keluar dari kerajaan",
            parse_mode="Markdown"
        )


# ──────────────────────────────────────────────
async def _find_player_by_username(username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM players WHERE username=?", (username,)) as cur:
            return await cur.fetchone()


async def _find_kingdom(identifier: str):
    """Cari kingdom by ID (angka) atau nama."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if identifier.isdigit():
            async with db.execute("SELECT * FROM kingdoms WHERE id=?", (int(identifier),)) as cur:
                return await cur.fetchone()
        else:
            async with db.execute(
                "SELECT * FROM kingdoms WHERE LOWER(name) LIKE ?",
                (f"%{identifier.lower()}%",)
            ) as cur:
                return await cur.fetchone()
