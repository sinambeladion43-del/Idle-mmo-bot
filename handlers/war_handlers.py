"""
Sistem Perang 2 Kerajaan dengan Voting

/war declare   — Admin/SuperAdmin nyatakan perang ke kerajaan musuh
/war status    — Lihat status perang & voting saat ini
/war history   — Riwayat perang kerajaan
vote_yes / vote_no — Tombol voting member
"""
import time
import asyncio
import aiosqlite
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_player, create_player, update_player,
    get_kingdom, get_kingdom_by_id, update_kingdom,
    get_kingdom_members, get_all_buildings,
    add_kingdom_war,
    create_war_declaration, get_active_declaration,
    update_declaration_status, add_vote, get_votes,
    get_declaration_by_id, get_last_war_cooldown
)
from game_data import BUILDINGS
from config import ADMIN_IDS

DB_PATH     = os.environ.get("DB_PATH", "./game.db")
WAR_COOLDOWN = 86400   # 24 jam
VOTE_DURATION = 1800   # 30 menit
VOTE_THRESHOLD = 0.5   # >50%
LOOT_PERCENT   = 0.15  # 15% kas dirampas


def _fmt_time(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s   = divmod(rem, 60)
    if h:   return f"{h}j {m}m"
    if m:   return f"{m}m {s}d"
    return f"{s}d"


async def _ensure_player(update: Update):
    user = update.effective_user
    await create_player(user.id, user.username or user.first_name)
    return await get_player(user.id)


async def _is_admin(ctx, chat_id: int, user_id: int, kingdom) -> bool:
    """Cek apakah user adalah admin group atau super admin."""
    if user_id in ADMIN_IDS:
        return True
    try:
        member = await ctx.bot.get_chat_member(chat_id, user_id)
        return member.status in ("administrator", "creator")
    except Exception:
        return kingdom["admin_id"] == user_id


async def _calc_kingdom_power(kingdom_id: int) -> int:
    members = await get_kingdom_members(kingdom_id)
    if not members:
        return 0
    total = 0
    now = int(time.time())
    for m in members:
        atk  = m["attack_pow"]
        def_ = m["defense_pow"]
        lvl  = m["level"]
        buildings = await get_all_buildings(m["user_id"])
        for b in buildings:
            if b["finish_time"] <= now and b["level"] > 0:
                bdata = BUILDINGS.get(b["name"], {})
                for stat, bonus in bdata.get("stat_bonus", {}).items():
                    if stat == "attack_pow":   atk  += bonus * b["level"]
                    elif stat == "defense_pow": def_ += bonus * b["level"]
        total += atk + def_ + lvl * 10
    return total


async def _get_enemy_kingdom(my_kingdom_id: int):
    """Cari kerajaan musuh (kerajaan lain yang ada di DB)."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM kingdoms WHERE id != ? LIMIT 1",
            (my_kingdom_id,)
        ) as cur:
            return await cur.fetchone()


# ──────────────────────────────────────────────
async def war(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    chat = update.effective_chat
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text(
            "⚔️ Command ini hanya bisa digunakan di Group Telegram!",
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
    sub  = args[0].lower() if args else ""

    # ── /war (tanpa argumen) ──────────────────
    if not sub:
        await _show_war_info(update, my_kd)
        return

    # ── /war status ───────────────────────────
    if sub == "status":
        await _show_war_status(update, my_kd)
        return

    # ── /war history ──────────────────────────
    if sub == "history":
        from database import get_kingdom_wars
        wars = await get_kingdom_wars(my_kd["id"], 10)
        if not wars:
            await update.message.reply_text(
                f"📜 *{my_kd['name']}* belum pernah berperang.",
                parse_mode="Markdown"
            )
            return
        import datetime
        lines = [f"📜 *RIWAYAT PERANG — {my_kd['name']}*\n"]
        for w in wars:
            dt  = datetime.datetime.fromtimestamp(w["timestamp"]).strftime("%d/%m %H:%M")
            is_atk = w["attacker_kingdom_id"] == my_kd["id"]
            won    = (is_atk and w["result"] == "attacker_win") or \
                     (not is_atk and w["result"] == "defender_win")
            icon   = "🏆" if won else "💀"
            role   = "⚔️ Serang" if is_atk else "🛡️ Diserang"
            enemy  = w["defender_name"] if is_atk else w["attacker_name"]
            lines.append(
                f"{icon} [{dt}] {role} *{enemy}*\n"
                f"   🪙{w['loot_gold']} 🪵{w['loot_wood']} 🪨{w['loot_stone']} 🌾{w['loot_food']} ⚔️{w['loot_iron']}"
            )
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    # ── /war declare ──────────────────────────
    if sub == "declare":
        # Cek permission — hanya admin group atau super admin
        if not await _is_admin(ctx, chat.id, player["user_id"], my_kd):
            await update.message.reply_text(
                "🚫 *Hanya Admin Group atau Super Admin* yang bisa menyatakan perang!",
                parse_mode="Markdown"
            )
            return

        # Cek apakah sudah ada deklarasi pending
        existing = await get_active_declaration(attacker_id=my_kd["id"])
        if existing:
            remaining = existing["expires_at"] - int(time.time())
            await update.message.reply_text(
                f"⚠️ Sudah ada deklarasi perang yang sedang berjalan!\n"
                f"Voting berakhir dalam: *{_fmt_time(remaining)}*\n\n"
                f"Ketik `/war status` untuk lihat info voting.",
                parse_mode="Markdown"
            )
            return

        # Cek cooldown 24 jam
        last = await get_last_war_cooldown(my_kd["id"])
        if last:
            elapsed = int(time.time()) - last["created_at"]
            if elapsed < WAR_COOLDOWN:
                remaining = WAR_COOLDOWN - elapsed
                await update.message.reply_text(
                    f"⏰ *Cooldown Perang!*\n\n"
                    f"Kerajaan kamu baru saja berperang.\n"
                    f"Bisa menyatakan perang lagi dalam: *{_fmt_time(remaining)}*",
                    parse_mode="Markdown"
                )
                return

        # Cari kerajaan musuh
        enemy_kd = await _get_enemy_kingdom(my_kd["id"])
        if not enemy_kd:
            await update.message.reply_text(
                "❌ Belum ada kerajaan lain yang terdaftar!\n"
                "Minta musuhmu untuk setup kerajaan di group mereka dulu.",
                parse_mode="Markdown"
            )
            return

        # Buat deklarasi perang
        decl_id = await create_war_declaration(
            my_kd["id"], enemy_kd["id"], player["user_id"]
        )

        my_power    = await _calc_kingdom_power(my_kd["id"])
        enemy_power = await _calc_kingdom_power(enemy_kd["id"])
        my_members  = await get_kingdom_members(my_kd["id"])
        en_members  = await get_kingdom_members(enemy_kd["id"])

        # Announce di group penyerang
        await update.message.reply_text(
            f"⚔️ *DEKLARASI PERANG!*\n\n"
            f"*{my_kd['name']}* telah menyatakan perang terhadap\n"
            f"*{enemy_kd['name']}*!\n\n"
            f"🏰 Kekuatan kita : {my_power:,}\n"
            f"👥 Member kita   : {len(my_members)}\n\n"
            f"⏰ Menunggu keputusan musuh...\n"
            f"Voting berlangsung *30 menit*.",
            parse_mode="Markdown"
        )

        # Kirim notifikasi + voting ke group musuh
        kb = [[
            InlineKeyboardButton("✅ SETUJU BERPERANG",  callback_data=f"war_vote_yes_{decl_id}"),
            InlineKeyboardButton("❌ TOLAK PERANG",      callback_data=f"war_vote_no_{decl_id}"),
        ]]
        try:
            await ctx.bot.send_message(
                enemy_kd["group_id"],
                f"🚨 *DEKLARASI PERANG MASUK!*\n\n"
                f"⚔️ *{my_kd['name']}* menyatakan perang terhadap *{enemy_kd['name']}*!\n\n"
                f"💪 Kekuatan musuh : {enemy_power:,}\n"
                f"👥 Member musuh   : {len(my_members)}\n\n"
                f"📊 *Kekuatan kalian : {my_power:,}*\n"
                f"👥 Member kalian  : {len(en_members)}\n\n"
                f"🗳️ *VOTING: Apakah kerajaan menyetujui perang ini?*\n"
                f"⏰ Waktu voting: *30 menit*\n"
                f"📌 Butuh lebih dari *50%* member setuju untuk perang dimulai!\n\n"
                f"Tekan tombol di bawah untuk vote!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(kb)
            )
        except Exception:
            await update.message.reply_text(
                "⚠️ Gagal kirim notifikasi ke group musuh.\n"
                "Pastikan bot sudah ada di group mereka!",
                parse_mode="Markdown"
            )

        return

    await update.message.reply_text(
        "❌ Sub-command tidak dikenal.\n\n"
        "Gunakan:\n"
        "`/war declare` — Nyatakan perang\n"
        "`/war status`  — Status voting\n"
        "`/war history` — Riwayat perang",
        parse_mode="Markdown"
    )


# ──────────────────────────────────────────────
async def _show_war_info(update, my_kd):
    from database import get_kingdom_wars
    wars  = await get_kingdom_wars(my_kd["id"], 5)
    power = await _calc_kingdom_power(my_kd["id"])
    mems  = await get_kingdom_members(my_kd["id"])
    wins  = sum(1 for w in wars if
                (w["attacker_kingdom_id"] == my_kd["id"] and w["result"] == "attacker_win") or
                (w["defender_kingdom_id"] == my_kd["id"] and w["result"] == "defender_win"))
    losses = len(wars) - wins

    enemy_kd = await _get_enemy_kingdom(my_kd["id"])
    enemy_info = f"🏴 Musuh: *{enemy_kd['name']}*" if enemy_kd else "🏴 Belum ada musuh terdaftar"

    kb = [[
        InlineKeyboardButton("⚔️ Nyatakan Perang", callback_data=f"war_declare_{my_kd['id']}"),
        InlineKeyboardButton("📜 Riwayat",          callback_data=f"war_hist_{my_kd['id']}"),
    ]]
    await update.message.reply_text(
        f"⚔️ *SISTEM PERANG — {my_kd['name']}*\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"💪 Kekuatan  : {power:,}\n"
        f"👥 Member    : {len(mems)}\n"
        f"🏆 Menang    : {wins}\n"
        f"💀 Kalah     : {losses}\n"
        f"━━━━━━━━━━━━━━━━\n"
        f"{enemy_info}\n\n"
        f"📌 *Cara Perang:*\n"
        f"Admin ketik `/war declare` untuk menyatakan perang\n"
        f"Member musuh akan melakukan voting 30 menit\n"
        f"Butuh >50% setuju untuk perang dimulai\n\n"
        f"⏰ Cooldown antar perang: 24 jam",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


async def _show_war_status(update, my_kd):
    # Cek sebagai attacker
    decl = await get_active_declaration(attacker_id=my_kd["id"])
    role = "attacker"
    if not decl:
        decl = await get_active_declaration(defender_id=my_kd["id"])
        role = "defender"

    if not decl:
        await update.message.reply_text(
            "📊 Tidak ada perang yang sedang berlangsung.\n"
            "Admin bisa ketik `/war declare` untuk menyatakan perang.",
            parse_mode="Markdown"
        )
        return

    now       = int(time.time())
    remaining = max(0, decl["expires_at"] - now)
    votes     = await get_votes(decl["id"], decl["defender_kingdom_id"])
    total_mems = await get_kingdom_members(decl["defender_kingdom_id"])
    yes_votes  = sum(1 for v in votes if v["vote"] == "yes")
    no_votes   = sum(1 for v in votes if v["vote"] == "no")
    total_votes = len(votes)
    total_mems_count = len(total_mems) or 1
    pct = int((yes_votes / total_mems_count) * 100)

    atk_kd = await get_kingdom_by_id(decl["attacker_kingdom_id"])
    def_kd = await get_kingdom_by_id(decl["defender_kingdom_id"])

    await update.message.reply_text(
        f"📊 *STATUS VOTING PERANG*\n\n"
        f"⚔️ {atk_kd['name']} vs 🛡️ {def_kd['name']}\n\n"
        f"✅ Setuju  : {yes_votes} vote\n"
        f"❌ Tolak   : {no_votes} vote\n"
        f"👥 Total member defender: {total_mems_count}\n"
        f"📊 Persentase setuju: {pct}%\n\n"
        f"⏰ Sisa waktu voting: *{_fmt_time(remaining)}*\n\n"
        f"📌 Butuh >50% untuk perang dimulai",
        parse_mode="Markdown"
    )


# ──────────────────────────────────────────────
async def war_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data
    user  = update.effective_user

    # ── Tombol declare dari info panel ────────
    if data.startswith("war_declare_"):
        kingdom_id = int(data.split("_")[2])
        chat = update.effective_chat
        my_kd = await get_kingdom(chat.id) if chat else None
        if not my_kd:
            await query.edit_message_text("❌ Kingdom tidak ditemukan.")
            return
        await create_player(user.id, user.username or user.first_name)
        player = await get_player(user.id)
        if not await _is_admin(ctx, chat.id, user.id, my_kd):
            await query.answer("🚫 Hanya Admin yang bisa menyatakan perang!", show_alert=True)
            return
        # Redirect ke /war declare logic
        ctx.args = ["declare"]
        await war(update, ctx)
        return

    # ── Riwayat dari panel ────────────────────
    if data.startswith("war_hist_"):
        kingdom_id = int(data.split("_")[2])
        from database import get_kingdom_wars
        kd   = await get_kingdom_by_id(kingdom_id)
        wars = await get_kingdom_wars(kingdom_id, 8)
        if not wars:
            await query.edit_message_text(f"📜 Belum ada riwayat perang.", parse_mode="Markdown")
            return
        import datetime
        lines = [f"📜 *RIWAYAT PERANG — {kd['name']}*\n"]
        for w in wars:
            dt     = datetime.datetime.fromtimestamp(w["timestamp"]).strftime("%d/%m %H:%M")
            is_atk = w["attacker_kingdom_id"] == kingdom_id
            won    = (is_atk and w["result"] == "attacker_win") or \
                     (not is_atk and w["result"] == "defender_win")
            icon   = "🏆" if won else "💀"
            enemy  = w["defender_name"] if is_atk else w["attacker_name"]
            lines.append(f"{icon} [{dt}] vs *{enemy}*")
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")
        return

    # ── VOTING ────────────────────────────────
    if data.startswith("war_vote_"):
        parts    = data.split("_")
        vote     = parts[2]          # "yes" atau "no"
        decl_id  = int(parts[3])

        decl = await get_declaration_by_id(decl_id)
        if not decl or decl["status"] != "pending":
            await query.answer("⚠️ Voting sudah berakhir!", show_alert=True)
            return

        now = int(time.time())
        if now > decl["expires_at"]:
            await query.answer("⚠️ Waktu voting sudah habis!", show_alert=True)
            return

        # Pastikan voter adalah member kerajaan defender
        await create_player(user.id, user.username or user.first_name)
        player = await get_player(user.id)

        if player["kingdom_id"] != decl["defender_kingdom_id"]:
            await query.answer("🚫 Hanya member kerajaan yang diserang yang bisa vote!", show_alert=True)
            return

        # Simpan vote
        await add_vote(decl_id, user.id, decl["defender_kingdom_id"], vote)

        # Hitung ulang vote
        votes      = await get_votes(decl_id, decl["defender_kingdom_id"])
        total_mems = await get_kingdom_members(decl["defender_kingdom_id"])
        yes_votes  = sum(1 for v in votes if v["vote"] == "yes")
        no_votes   = sum(1 for v in votes if v["vote"] == "no")
        total_count = len(total_mems) or 1
        yes_pct    = yes_votes / total_count

        vote_label = "✅ SETUJU" if vote == "yes" else "❌ TOLAK"
        await query.answer(f"{vote_label} berhasil dicatat!", show_alert=False)

        # Update pesan voting
        remaining = max(0, decl["expires_at"] - now)
        kb = [[
            InlineKeyboardButton(f"✅ Setuju ({yes_votes})",  callback_data=f"war_vote_yes_{decl_id}"),
            InlineKeyboardButton(f"❌ Tolak ({no_votes})",    callback_data=f"war_vote_no_{decl_id}"),
        ]]

        atk_kd = await get_kingdom_by_id(decl["attacker_kingdom_id"])
        def_kd = await get_kingdom_by_id(decl["defender_kingdom_id"])

        await query.edit_message_text(
            f"🚨 *DEKLARASI PERANG MASUK!*\n\n"
            f"⚔️ *{atk_kd['name']}* menyatakan perang terhadap *{def_kd['name']}*!\n\n"
            f"🗳️ *STATUS VOTING:*\n"
            f"✅ Setuju : {yes_votes} ({int(yes_pct*100)}%)\n"
            f"❌ Tolak  : {no_votes}\n"
            f"👥 Total member: {total_count}\n\n"
            f"⏰ Sisa waktu: *{_fmt_time(remaining)}*\n"
            f"📌 Butuh >50% setuju untuk perang dimulai!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )

        # Cek apakah semua member sudah vote atau mayoritas sudah tercapai
        all_voted    = len(votes) >= total_count
        majority_yes = yes_pct > VOTE_THRESHOLD
        majority_no  = no_votes / total_count > VOTE_THRESHOLD

        if all_voted or majority_yes or majority_no:
            await _resolve_war(ctx, decl, yes_votes, no_votes, total_count, atk_kd, def_kd, query.message)
        return


async def _resolve_war(ctx, decl, yes_votes, no_votes, total_count, atk_kd, def_kd, trigger_message=None):
    """Eksekusi hasil voting — mulai perang atau batalkan."""
    import random

    yes_pct = yes_votes / total_count if total_count > 0 else 0

    if yes_pct > VOTE_THRESHOLD:
        # ── PERANG DIMULAI ────────────────────
        await update_declaration_status(decl["id"], "war_started")

        # Hitung kekuatan
        import random as rnd
        atk_base  = await _calc_kingdom_power(atk_kd["id"])
        def_base  = await _calc_kingdom_power(def_kd["id"])
        atk_var   = int(atk_base * 0.15)
        def_var   = int(def_base * 0.15)
        atk_power = max(1, atk_base + rnd.randint(-atk_var, atk_var))
        def_power = max(1, def_base + rnd.randint(-def_var, def_var))

        attacker_wins = atk_power > def_power

        if attacker_wins:
            # Ambil fresh data
            from database import get_kingdom_by_id as gkbi
            fresh_atk = await gkbi(atk_kd["id"])
            fresh_def = await gkbi(def_kd["id"])
            loot_gold  = int(fresh_def["gold"]  * LOOT_PERCENT)
            loot_wood  = int(fresh_def["wood"]  * LOOT_PERCENT)
            loot_stone = int(fresh_def["stone"] * LOOT_PERCENT)
            loot_food  = int(fresh_def["food"]  * LOOT_PERCENT)
            loot_iron  = int(fresh_def["iron"]  * LOOT_PERCENT)
            result = "attacker_win"
            await update_kingdom(fresh_atk["group_id"],
                gold=fresh_atk["gold"]+loot_gold, wood=fresh_atk["wood"]+loot_wood,
                stone=fresh_atk["stone"]+loot_stone, food=fresh_atk["food"]+loot_food,
                iron=fresh_atk["iron"]+loot_iron)
            await update_kingdom(fresh_def["group_id"],
                gold=max(0,fresh_def["gold"]-loot_gold), wood=max(0,fresh_def["wood"]-loot_wood),
                stone=max(0,fresh_def["stone"]-loot_stone), food=max(0,fresh_def["food"]-loot_food),
                iron=max(0,fresh_def["iron"]-loot_iron))
        else:
            from database import get_kingdom_by_id as gkbi
            fresh_atk = await gkbi(atk_kd["id"])
            fresh_def = await gkbi(def_kd["id"])
            loot_gold  = int(fresh_atk["gold"]  * LOOT_PERCENT)
            loot_wood  = int(fresh_atk["wood"]  * LOOT_PERCENT)
            loot_stone = int(fresh_atk["stone"] * LOOT_PERCENT)
            loot_food  = int(fresh_atk["food"]  * LOOT_PERCENT)
            loot_iron  = int(fresh_atk["iron"]  * LOOT_PERCENT)
            result = "defender_win"
            await update_kingdom(fresh_def["group_id"],
                gold=fresh_def["gold"]+loot_gold, wood=fresh_def["wood"]+loot_wood,
                stone=fresh_def["stone"]+loot_stone, food=fresh_def["food"]+loot_food,
                iron=fresh_def["iron"]+loot_iron)
            await update_kingdom(fresh_atk["group_id"],
                gold=max(0,fresh_atk["gold"]-loot_gold), wood=max(0,fresh_atk["wood"]-loot_wood),
                stone=max(0,fresh_atk["stone"]-loot_stone), food=max(0,fresh_atk["food"]-loot_food),
                iron=max(0,fresh_atk["iron"]-loot_iron))

        await add_kingdom_war(
            atk_kd["id"], def_kd["id"],
            atk_kd["name"], def_kd["name"],
            result, atk_power, def_power,
            loot_gold, loot_wood, loot_stone, loot_food, loot_iron
        )
        await update_declaration_status(decl["id"], "war_done")

        if attacker_wins:
            atk_result = (
                f"🏆 *{atk_kd['name']} MENANG!*\n\n"
                f"⚔️ Kekuatan kita : {atk_power:,}\n"
                f"🛡️ Kekuatan musuh: {def_power:,}\n\n"
                f"💰 *Rampasan:*\n"
                f"🪙 +{loot_gold:,} Gold\n🪵 +{loot_wood:,} Wood\n"
                f"🪨 +{loot_stone:,} Stone\n🌾 +{loot_food:,} Food\n⚔️ +{loot_iron:,} Iron"
            )
            def_result = (
                f"💀 *{def_kd['name']} KALAH!*\n\n"
                f"⚔️ Kekuatan musuh: {atk_power:,}\n"
                f"🛡️ Kekuatan kita : {def_power:,}\n\n"
                f"💸 *Resource Hilang:*\n"
                f"🪙 -{loot_gold:,} Gold\n🪵 -{loot_wood:,} Wood\n"
                f"🪨 -{loot_stone:,} Stone\n🌾 -{loot_food:,} Food\n⚔️ -{loot_iron:,} Iron\n\n"
                f"💡 Perkuat kerajaan dan balas dendam!"
            )
        else:
            atk_result = (
                f"💀 *{atk_kd['name']} KALAH!*\n\n"
                f"⚔️ Kekuatan kita : {atk_power:,}\n"
                f"🛡️ Kekuatan musuh: {def_power:,}\n\n"
                f"💸 *Resource Hilang:*\n"
                f"🪙 -{loot_gold:,} Gold\n🪵 -{loot_wood:,} Wood\n"
                f"🪨 -{loot_stone:,} Stone\n🌾 -{loot_food:,} Food\n⚔️ -{loot_iron:,} Iron"
            )
            def_result = (
                f"🏆 *{def_kd['name']} MENANG!*\n\n"
                f"⚔️ Kekuatan musuh: {atk_power:,}\n"
                f"🛡️ Kekuatan kita : {def_power:,}\n\n"
                f"💰 *Rampasan dari penyerang:*\n"
                f"🪙 +{loot_gold:,} Gold\n🪵 +{loot_wood:,} Wood\n"
                f"🪨 +{loot_stone:,} Stone\n🌾 +{loot_food:,} Food\n⚔️ +{loot_iron:,} Iron"
            )

        # Kirim hasil ke kedua group
        try:
            await ctx.bot.send_message(atk_kd["group_id"], f"⚔️ *HASIL PERANG!*\n\n{atk_result}", parse_mode="Markdown")
        except Exception:
            pass
        try:
            await ctx.bot.send_message(def_kd["group_id"], f"⚔️ *HASIL PERANG!*\n\n{def_result}", parse_mode="Markdown")
        except Exception:
            pass

    else:
        # ── PERANG DIBATALKAN ─────────────────
        await update_declaration_status(decl["id"], "rejected")
        msg = (
            f"❌ *Perang Dibatalkan!*\n\n"
            f"Mayoritas member *{def_kd['name']}* menolak perang.\n"
            f"✅ Setuju: {yes_votes} | ❌ Tolak: {no_votes}\n\n"
            f"⏰ Cooldown 24 jam berlaku."
        )
        try:
            await ctx.bot.send_message(atk_kd["group_id"], msg, parse_mode="Markdown")
        except Exception:
            pass
        try:
            await ctx.bot.send_message(def_kd["group_id"], msg, parse_mode="Markdown")
        except Exception:
            pass
