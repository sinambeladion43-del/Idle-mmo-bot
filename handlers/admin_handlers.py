import time
import aiosqlite
import os
from telegram import Update
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
            "`/admin stats` — Statistik bot\n"
            "`/admin additem @user [res] [amt]` — Tambah resource\n"
            "`/admin removeitem @user [res] [amt]` — Hapus resource\n"
            "`/admin setgold @user [amt]` — Set gold\n"
            "`/admin ban @user` — Ban player\n"
            "`/admin unban @user` — Unban player\n"
            "`/admin broadcast [pesan]` — Broadcast ke semua\n"
            "`/admin resetwar` — Reset semua data war",
            parse_mode="Markdown"
        )
        return

    cmd = args[0].lower()

    # ── /admin stats ──────────────────────────
    if cmd == "stats":
        players = await get_all_players()
        total = len(players)
        banned = sum(1 for p in players if p["is_banned"])
        now = int(time.time())
        active_24h = sum(
            1 for p in players
            if (now - (p["last_daily"] or 0)) < 86400
        )
        wars = await get_all_wars(1000)
        await update.message.reply_text(
            f"📊 *STATISTIK BOT*\n\n"
            f"👥 Total Player : {total}\n"
            f"✅ Aktif (24h)  : {active_24h}\n"
            f"🚫 Di-ban       : {banned}\n"
            f"⚔️ Total War    : {len(wars)}",
            parse_mode="Markdown"
        )

    # ── /admin additem ────────────────────────
    elif cmd == "additem":
        if len(args) < 4:
            await update.message.reply_text(
                "❌ Format: `/admin additem @user [resource] [jumlah]`",
                parse_mode="Markdown"
            )
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
            await update.message.reply_text(f"❌ Pemain *{target_uname}* tidak ditemukan.", parse_mode="Markdown")
            return

        await update_player(target["user_id"], **{res: target[res] + amt})
        await update.message.reply_text(
            f"✅ +{amt:,} {res} diberikan ke *{target_uname}*", parse_mode="Markdown"
        )

    # ── /admin removeitem ─────────────────────
    elif cmd == "removeitem":
        if len(args) < 4:
            await update.message.reply_text(
                "❌ Format: `/admin removeitem @user [resource] [jumlah]`",
                parse_mode="Markdown"
            )
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
            await update.message.reply_text(f"❌ Pemain *{target_uname}* tidak ditemukan.", parse_mode="Markdown")
            return

        new_val = max(0, target[res] - amt)
        await update_player(target["user_id"], **{res: new_val})
        await update.message.reply_text(
            f"✅ -{amt:,} {res} dihapus dari *{target_uname}*", parse_mode="Markdown"
        )

    # ── /admin setgold ────────────────────────
    elif cmd == "setgold":
        if len(args) < 3:
            await update.message.reply_text(
                "❌ Format: `/admin setgold @user [jumlah]`", parse_mode="Markdown"
            )
            return
        target_uname = args[1].lstrip("@")
        try:
            amt = int(args[2])
        except ValueError:
            await update.message.reply_text("❌ Jumlah harus angka.")
            return

        target = await _find_player_by_username(target_uname)
        if not target:
            await update.message.reply_text(f"❌ Pemain *{target_uname}* tidak ditemukan.", parse_mode="Markdown")
            return

        await update_player(target["user_id"], gold=amt)
        await update.message.reply_text(
            f"✅ Gold *{target_uname}* diset ke {amt:,}", parse_mode="Markdown"
        )

    # ── /admin ban ────────────────────────────
    elif cmd == "ban":
        if len(args) < 2:
            await update.message.reply_text("❌ Format: `/admin ban @user`", parse_mode="Markdown")
            return
        target_uname = args[1].lstrip("@")
        target = await _find_player_by_username(target_uname)
        if not target:
            await update.message.reply_text(f"❌ Pemain *{target_uname}* tidak ditemukan.", parse_mode="Markdown")
            return
        await update_player(target["user_id"], is_banned=1)
        await update.message.reply_text(f"🚫 *{target_uname}* telah di-ban.", parse_mode="Markdown")

    # ── /admin unban ──────────────────────────
    elif cmd == "unban":
        if len(args) < 2:
            await update.message.reply_text("❌ Format: `/admin unban @user`", parse_mode="Markdown")
            return
        target_uname = args[1].lstrip("@")
        target = await _find_player_by_username(target_uname)
        if not target:
            await update.message.reply_text(f"❌ Pemain *{target_uname}* tidak ditemukan.", parse_mode="Markdown")
            return
        await update_player(target["user_id"], is_banned=0)
        await update.message.reply_text(f"✅ *{target_uname}* berhasil di-unban.", parse_mode="Markdown")

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
                await ctx.bot.send_message(
                    p["user_id"],
                    f"📢 *BROADCAST*\n\n{msg}",
                    parse_mode="Markdown"
                )
                sent += 1
            except Exception:
                failed += 1
        await update.message.reply_text(
            f"✅ Broadcast terkirim: {sent} berhasil, {failed} gagal"
        )

    # ── /admin resetwar ───────────────────────
    elif cmd == "resetwar":
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM wars")
            await db.commit()
        await update.message.reply_text("✅ Semua data war telah direset.")

    else:
        await update.message.reply_text(
            f"❌ Command tidak dikenal: `{cmd}`\nKetik `/admin` untuk bantuan.",
            parse_mode="Markdown"
        )


# ──────────────────────────────────────────────
async def _find_player_by_username(username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM players WHERE username=?", (username,)
        ) as cur:
            return await cur.fetchone()
