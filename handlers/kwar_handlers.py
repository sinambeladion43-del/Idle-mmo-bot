import time
import random
import aiosqlite
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_player, create_player, update_player,
    get_kingdom, get_kingdom_by_id, update_kingdom,
    get_kingdom_members, get_all_buildings,
    add_kingdom_war, get_kingdom_wars, get_last_war_between
)
from game_data import BUILDINGS, RESOURCE_EMOJI

DB_PATH = os.environ.get("DB_PATH", "./game.db")

# Cooldown 6 jam antar war kerajaan yang sama
KWAR_COOLDOWN = 21600
# Persentase resource kas yang dirampas saat menang
LOOT_PERCENT  = 0.15


def _fmt_time(seconds: int) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s   = divmod(rem, 60)
    if h:
        return f"{h}j {m}m"
    return f"{m}m {s}d"


async def _ensure_player(update: Update):
    user = update.effective_user
    await create_player(user.id, user.username or user.first_name)
    return await get_player(user.id)


async def _calc_kingdom_power(kingdom_id: int) -> int:
    """
    Kekuatan kerajaan = jumlah total (attack + defense + level*10)
    semua member aktif + bonus dari bangunan masing-masing member.
    """
    members = await get_kingdom_members(kingdom_id)
    if not members:
        return 0

    total = 0
    now   = int(time.time())

    for m in members:
        atk  = m["attack_pow"]
        def_ = m["defense_pow"]
        lvl  = m["level"]

        # Tambah bonus bangunan tiap member
        buildings = await get_all_buildings(m["user_id"])
        for b in buildings:
            if b["finish_time"] <= now and b["level"] > 0:
                bdata = BUILDINGS.get(b["name"], {})
                for stat, bonus in bdata.get("stat_bonus", {}).items():
                    if stat == "attack_pow":
                        atk  += bonus * b["level"]
                    elif stat == "defense_pow":
                        def_ += bonus * b["level"]

        total += atk + def_ + lvl * 10

    return total


# ──────────────────────────────────────────────
async def kwar(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /kwar          — lihat info + riwayat war kerajaan ini
    /kwar @group   — tantang kerajaan lain (pakai username group)
    /kwar history  — riwayat lengkap war kerajaan ini
    """
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    chat = update.effective_chat

    # ── Harus di group ────────────────────────
    if chat.type not in ("group", "supergroup"):
        await update.message.reply_text(
            "⚔️ *Kingdom War hanya bisa dilakukan di Group Telegram!*\n\n"
            "Masuk ke group kerajaanmu dan ketik `/kwar` di sana.",
            parse_mode="Markdown"
        )
        return

    my_kd = await get_kingdom(chat.id)
    if not my_kd:
        await update.message.reply_text(
            "❌ Group ini belum punya kerajaan.\nKetik `/kingdom` untuk membuat kerajaan dulu.",
            parse_mode="Markdown"
        )
        return

    args = ctx.args or []

    # ── /kwar history ─────────────────────────
    if args and args[0].lower() == "history":
        await _show_war_history(update, my_kd)
        return

    # ── /kwar (tanpa argumen) — info ──────────
    if not args:
        power    = await _calc_kingdom_power(my_kd["id"])
        members  = await get_kingdom_members(my_kd["id"])
        wars     = await get_kingdom_wars(my_kd["id"], 5)
        wins     = sum(1 for w in wars if
                       (w["attacker_kingdom_id"] == my_kd["id"] and w["result"] == "attacker_win") or
                       (w["defender_kingdom_id"] == my_kd["id"] and w["result"] == "defender_win"))
        losses   = len(wars) - wins

        text = (
            f"⚔️ *KINGDOM WAR — {my_kd['name']}*\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💪 Kekuatan    : {power:,}\n"
            f"👥 Member      : {len(members)}\n"
            f"🏆 Menang      : {wins}\n"
            f"💀 Kalah       : {losses}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"*Cara Berperang:*\n"
            f"1. Cari username group lawan\n"
            f"2. Ketik `/kwar @username_group`\n"
            f"3. Konfirmasi serangan\n\n"
            f"⏰ Cooldown antar war ke target sama: 6 jam\n"
            f"💰 Menang = rampas 15% resource kas lawan\n\n"
            f"📜 Ketik `/kwar history` untuk riwayat war"
        )
        kb = [[
            InlineKeyboardButton("📜 Riwayat War",    callback_data=f"kwar_history_{my_kd['id']}"),
            InlineKeyboardButton("💪 Kekuatan Kita",  callback_data=f"kwar_power_{my_kd['id']}"),
        ]]
        await update.message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )
        return

    # ── /kwar @target_group ───────────────────
    target_group_username = args[0].lstrip("@")

    # Cari kerajaan target berdasarkan username group
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        # Cari by group username (stored as group_id, we need to search by name as fallback)
        async with db.execute(
            "SELECT * FROM kingdoms WHERE LOWER(name) LIKE ?",
            (f"%{target_group_username.lower()}%",)
        ) as cur:
            enemy_kd = await cur.fetchone()

    if not enemy_kd:
        await update.message.reply_text(
            f"❌ Kerajaan *{target_group_username}* tidak ditemukan!\n\n"
            f"💡 *Tips:* Gunakan nama kerajaan, bukan username group.\n"
            f"Contoh: `/kwar Kingdom of Friends`\n\n"
            f"Atau minta admin kerajaan lawan untuk share nama kerajaannya.",
            parse_mode="Markdown"
        )
        return

    if enemy_kd["id"] == my_kd["id"]:
        await update.message.reply_text("😅 Kamu tidak bisa menyerang kerajaanmu sendiri!")
        return

    # Cek apakah sesama aliansi
    from database import get_alliance
    my_al    = await get_alliance(my_kd["id"])
    enemy_al = await get_alliance(enemy_kd["id"])
    if my_al and enemy_al and my_al["id"] == enemy_al["id"]:
        await update.message.reply_text(
            f"🤝 *Tidak bisa menyerang sesama aliansi!*\n\n"
            f"*{enemy_kd['name']}* adalah anggota aliansi *{my_al['name']}*.",
            parse_mode="Markdown"
        )
        return

    # Cek cooldown
    now      = int(time.time())
    last_war = await get_last_war_between(my_kd["id"], enemy_kd["id"])
    if last_war and (now - last_war["timestamp"]) < KWAR_COOLDOWN:
        remaining = KWAR_COOLDOWN - (now - last_war["timestamp"])
        await update.message.reply_text(
            f"⏰ *Cooldown War!*\n\n"
            f"Kamu baru saja menyerang *{enemy_kd['name']}*.\n"
            f"Tunggu *{_fmt_time(remaining)}* lagi.",
            parse_mode="Markdown"
        )
        return

    # Cek apakah user adalah admin/officer kerajaan
    chat_member = await ctx.bot.get_chat_member(chat.id, player["user_id"])
    is_officer  = (
        chat_member.status in ("administrator", "creator") or
        my_kd["admin_id"] == player["user_id"] or
        player.get("role") in ("officer", "kadmin")
    )
    if not is_officer:
        await update.message.reply_text(
            "🚫 Hanya *Admin* atau *Officer* kerajaan yang bisa menyatakan perang!",
            parse_mode="Markdown"
        )
        return

    # Preview sebelum konfirmasi
    my_power    = await _calc_kingdom_power(my_kd["id"])
    enemy_power = await _calc_kingdom_power(enemy_kd["id"])
    my_members  = await get_kingdom_members(my_kd["id"])
    en_members  = await get_kingdom_members(enemy_kd["id"])

    # Hitung potensi loot
    pot_gold  = int(enemy_kd["gold"]  * LOOT_PERCENT)
    pot_wood  = int(enemy_kd["wood"]  * LOOT_PERCENT)
    pot_stone = int(enemy_kd["stone"] * LOOT_PERCENT)
    pot_food  = int(enemy_kd["food"]  * LOOT_PERCENT)
    pot_iron  = int(enemy_kd["iron"]  * LOOT_PERCENT)

    text = (
        f"⚔️ *DEKLARASI PERANG!*\n\n"
        f"🏰 *{my_kd['name']}*\n"
        f"   💪 Kekuatan : {my_power:,}\n"
        f"   👥 Member   : {len(my_members)}\n\n"
        f"   VS\n\n"
        f"🏴 *{enemy_kd['name']}*\n"
        f"   💪 Kekuatan : {enemy_power:,}\n"
        f"   👥 Member   : {len(en_members)}\n\n"
        f"💰 *Potensi Rampasan (jika menang):*\n"
        f"🪙 Gold  : {pot_gold:,}\n"
        f"🪵 Wood  : {pot_wood:,}\n"
        f"🪨 Stone : {pot_stone:,}\n"
        f"🌾 Food  : {pot_food:,}\n"
        f"⚔️ Iron  : {pot_iron:,}\n\n"
        f"⚠️ Yakin ingin memulai perang?"
    )
    kb = [[
        InlineKeyboardButton(
            "⚔️ SERANG SEKARANG!",
            callback_data=f"kwar_confirm_{my_kd['id']}_{enemy_kd['id']}"
        ),
        InlineKeyboardButton("❌ Batal", callback_data="kwar_cancel"),
    ]]
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )


# ──────────────────────────────────────────────
async def _show_war_history(update, kd):
    wars = await get_kingdom_wars(kd["id"], 15)
    if not wars:
        await update.message.reply_text(
            f"📜 *{kd['name']}* belum pernah berperang.\n"
            f"Ketik `/kwar [nama kerajaan]` untuk mulai!",
            parse_mode="Markdown"
        )
        return

    import datetime
    lines = [f"📜 *RIWAYAT WAR — {kd['name']}*\n"]
    for w in wars:
        dt = datetime.datetime.fromtimestamp(w["timestamp"]).strftime("%d/%m %H:%M")
        is_attacker = w["attacker_kingdom_id"] == kd["id"]
        won = (is_attacker and w["result"] == "attacker_win") or \
              (not is_attacker and w["result"] == "defender_win")

        icon    = "🏆" if won else "💀"
        role    = "Serang" if is_attacker else "Diserang"
        enemy   = w["defender_name"] if is_attacker else w["attacker_name"]
        outcome = "MENANG" if won else "KALAH"

        loot_total = w["loot_gold"] + w["loot_wood"] + w["loot_stone"] + w["loot_food"] + w["loot_iron"]
        lines.append(
            f"{icon} [{dt}] {role} *{enemy}* — {outcome}\n"
            f"   Rampasan: 🪙{w['loot_gold']} 🪵{w['loot_wood']} 🪨{w['loot_stone']} 🌾{w['loot_food']} ⚔️{w['loot_iron']}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ──────────────────────────────────────────────
async def kwar_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data
    user  = update.effective_user

    if data == "kwar_cancel":
        await query.edit_message_text("❌ Perang dibatalkan.")
        return

    # ── Lihat kekuatan kerajaan ───────────────
    if data.startswith("kwar_power_"):
        kingdom_id = int(data.split("_")[2])
        kd         = await get_kingdom_by_id(kingdom_id)
        if not kd:
            await query.edit_message_text("❌ Kingdom tidak ditemukan.")
            return
        members = await get_kingdom_members(kingdom_id)
        power   = await _calc_kingdom_power(kingdom_id)

        lines = [f"💪 *KEKUATAN {kd['name']}*\n", f"Total Power: {power:,}\n"]
        for m in members[:15]:
            lines.append(f"👤 {m['username']} — Lv.{m['level']} | ATK:{m['attack_pow']} DEF:{m['defense_pow']}")

        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")
        return

    # ── Riwayat war ───────────────────────────
    if data.startswith("kwar_history_"):
        kingdom_id = int(data.split("_")[2])
        kd         = await get_kingdom_by_id(kingdom_id)
        if not kd:
            await query.edit_message_text("❌ Kingdom tidak ditemukan.")
            return
        wars = await get_kingdom_wars(kingdom_id, 10)
        if not wars:
            await query.edit_message_text(
                f"📜 *{kd['name']}* belum pernah berperang.",
                parse_mode="Markdown"
            )
            return

        import datetime
        lines = [f"📜 *RIWAYAT WAR — {kd['name']}*\n"]
        for w in wars:
            dt          = datetime.datetime.fromtimestamp(w["timestamp"]).strftime("%d/%m %H:%M")
            is_attacker = w["attacker_kingdom_id"] == kingdom_id
            won         = (is_attacker and w["result"] == "attacker_win") or \
                          (not is_attacker and w["result"] == "defender_win")
            icon    = "🏆" if won else "💀"
            role    = "⚔️ Serang" if is_attacker else "🛡️ Diserang"
            enemy   = w["defender_name"] if is_attacker else w["attacker_name"]
            outcome = "MENANG" if won else "KALAH"
            lines.append(
                f"{icon} [{dt}] {role} *{enemy}* — {outcome}\n"
                f"   🪙{w['loot_gold']} 🪵{w['loot_wood']} 🪨{w['loot_stone']} 🌾{w['loot_food']} ⚔️{w['loot_iron']}"
            )
        await query.edit_message_text("\n".join(lines), parse_mode="Markdown")
        return

    # ── Konfirmasi & eksekusi war ─────────────
    if data.startswith("kwar_confirm_"):
        parts = data.split("_")
        try:
            my_kd_id    = int(parts[2])
            enemy_kd_id = int(parts[3])
        except (IndexError, ValueError):
            await query.edit_message_text("❌ Data tidak valid.")
            return

        my_kd    = await get_kingdom_by_id(my_kd_id)
        enemy_kd = await get_kingdom_by_id(enemy_kd_id)

        if not my_kd or not enemy_kd:
            await query.edit_message_text("❌ Kingdom tidak ditemukan.")
            return

        # Cek cooldown sekali lagi (jaga-jaga double click)
        now      = int(time.time())
        last_war = await get_last_war_between(my_kd_id, enemy_kd_id)
        if last_war and (now - last_war["timestamp"]) < KWAR_COOLDOWN:
            remaining = KWAR_COOLDOWN - (now - last_war["timestamp"])
            await query.edit_message_text(
                f"⏰ Masih cooldown! Tunggu *{_fmt_time(remaining)}* lagi.",
                parse_mode="Markdown"
            )
            return

        # Hitung kekuatan dengan variance random ±15%
        my_base    = await _calc_kingdom_power(my_kd_id)
        enemy_base = await _calc_kingdom_power(enemy_kd_id)

        my_var    = int(my_base    * 0.15)
        enemy_var = int(enemy_base * 0.15)
        my_power    = my_base    + random.randint(-my_var,    my_var)
        enemy_power = enemy_base + random.randint(-enemy_var, enemy_var)

        # Pastikan minimal 1
        my_power    = max(1, my_power)
        enemy_power = max(1, enemy_power)

        attacker_wins = my_power > enemy_power

        # Hitung loot
        if attacker_wins:
            loot_gold  = int(enemy_kd["gold"]  * LOOT_PERCENT)
            loot_wood  = int(enemy_kd["wood"]  * LOOT_PERCENT)
            loot_stone = int(enemy_kd["stone"] * LOOT_PERCENT)
            loot_food  = int(enemy_kd["food"]  * LOOT_PERCENT)
            loot_iron  = int(enemy_kd["iron"]  * LOOT_PERCENT)
            result     = "attacker_win"

            # Transfer resource
            await update_kingdom(my_kd["group_id"],
                gold  = my_kd["gold"]  + loot_gold,
                wood  = my_kd["wood"]  + loot_wood,
                stone = my_kd["stone"] + loot_stone,
                food  = my_kd["food"]  + loot_food,
                iron  = my_kd["iron"]  + loot_iron,
            )
            await update_kingdom(enemy_kd["group_id"],
                gold  = max(0, enemy_kd["gold"]  - loot_gold),
                wood  = max(0, enemy_kd["wood"]  - loot_wood),
                stone = max(0, enemy_kd["stone"] - loot_stone),
                food  = max(0, enemy_kd["food"]  - loot_food),
                iron  = max(0, enemy_kd["iron"]  - loot_iron),
            )
        else:
            # Kalah — lawan yang rampas dari kita
            loot_gold  = int(my_kd["gold"]  * LOOT_PERCENT)
            loot_wood  = int(my_kd["wood"]  * LOOT_PERCENT)
            loot_stone = int(my_kd["stone"] * LOOT_PERCENT)
            loot_food  = int(my_kd["food"]  * LOOT_PERCENT)
            loot_iron  = int(my_kd["iron"]  * LOOT_PERCENT)
            result     = "defender_win"

            await update_kingdom(enemy_kd["group_id"],
                gold  = enemy_kd["gold"]  + loot_gold,
                wood  = enemy_kd["wood"]  + loot_wood,
                stone = enemy_kd["stone"] + loot_stone,
                food  = enemy_kd["food"]  + loot_food,
                iron  = enemy_kd["iron"]  + loot_iron,
            )
            await update_kingdom(my_kd["group_id"],
                gold  = max(0, my_kd["gold"]  - loot_gold),
                wood  = max(0, my_kd["wood"]  - loot_wood),
                stone = max(0, my_kd["stone"] - loot_stone),
                food  = max(0, my_kd["food"]  - loot_food),
                iron  = max(0, my_kd["iron"]  - loot_iron),
            )

        # Simpan ke DB
        await add_kingdom_war(
            my_kd_id, enemy_kd_id,
            my_kd["name"], enemy_kd["name"],
            result, my_power, enemy_power,
            loot_gold, loot_wood, loot_stone, loot_food, loot_iron
        )

        # ── Hasil war ─────────────────────────
        if attacker_wins:
            result_text = (
                f"🏆 *{my_kd['name']} MENANG!*\n\n"
                f"⚔️ Kekuatan {my_kd['name']}  : {my_power:,}\n"
                f"🛡️ Kekuatan {enemy_kd['name']}: {enemy_power:,}\n\n"
                f"💰 *Resource Dirampas dari {enemy_kd['name']}:*\n"
                f"🪙 Gold  : +{loot_gold:,}\n"
                f"🪵 Wood  : +{loot_wood:,}\n"
                f"🪨 Stone : +{loot_stone:,}\n"
                f"🌾 Food  : +{loot_food:,}\n"
                f"⚔️ Iron  : +{loot_iron:,}\n\n"
                f"🎉 Selamat! Kas kerajaan bertambah!"
            )
        else:
            result_text = (
                f"💀 *{my_kd['name']} KALAH!*\n\n"
                f"⚔️ Kekuatan {my_kd['name']}  : {my_power:,}\n"
                f"🛡️ Kekuatan {enemy_kd['name']}: {enemy_power:,}\n\n"
                f"💸 *Resource Dirampas oleh {enemy_kd['name']}:*\n"
                f"🪙 Gold  : -{loot_gold:,}\n"
                f"🪵 Wood  : -{loot_wood:,}\n"
                f"🪨 Stone : -{loot_stone:,}\n"
                f"🌾 Food  : -{loot_food:,}\n"
                f"⚔️ Iron  : -{loot_iron:,}\n\n"
                f"💡 Perkuat kerajaan dengan upgrade bangunan member!\n"
                f"⏰ Bisa war lagi dalam 6 jam."
            )

        await query.edit_message_text(result_text, parse_mode="Markdown")

        # Notif ke group lawan juga
        try:
            if attacker_wins:
                notif = (
                    f"🚨 *KERAJAAN KAMU DISERANG!*\n\n"
                    f"⚔️ *{my_kd['name']}* menyerang *{enemy_kd['name']}*\n\n"
                    f"💀 Kerajaan kamu *KALAH*!\n\n"
                    f"💸 *Resource yang dirampas:*\n"
                    f"🪙 -{loot_gold:,} Gold\n"
                    f"🪵 -{loot_wood:,} Wood\n"
                    f"🪨 -{loot_stone:,} Stone\n"
                    f"🌾 -{loot_food:,} Food\n"
                    f"⚔️ -{loot_iron:,} Iron\n\n"
                    f"💡 Balas dendam! Ketik `/kwar {my_kd['name']}`"
                )
            else:
                notif = (
                    f"🛡️ *SERANGAN BERHASIL DIHADANG!*\n\n"
                    f"⚔️ *{my_kd['name']}* mencoba menyerang *{enemy_kd['name']}*\n\n"
                    f"🏆 Kerajaan kamu *MENANG* mempertahankan diri!\n\n"
                    f"💰 *Resource dirampas dari penyerang:*\n"
                    f"🪙 +{loot_gold:,} Gold\n"
                    f"🪵 +{loot_wood:,} Wood\n"
                    f"🪨 +{loot_stone:,} Stone\n"
                    f"🌾 +{loot_food:,} Food\n"
                    f"⚔️ +{loot_iron:,} Iron"
                )
            await ctx.bot.send_message(
                enemy_kd["group_id"], notif, parse_mode="Markdown"
            )
        except Exception:
            pass  # Kalau bot tidak di group lawan, skip saja
