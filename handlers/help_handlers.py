import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_player, create_player

# ─────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await create_player(user.id, user.username or user.first_name)

    text = (
        f"⚔️ *Selamat datang di IDLE MMO, {user.first_name}!*\n\n"
        "🏰 Kamu sudah terdaftar sebagai petualang!\n\n"
        "📜 *Langkah Pertama:*\n"
        "1️⃣ Klaim `/daily` untuk reward gratis\n"
        "2️⃣ Bangun `/build farm` untuk produksi Food\n"
        "3️⃣ Lihat profil kamu dengan `/profile`\n"
        "4️⃣ Cek semua bangunan dengan `/buildings`\n\n"
        "🏰 *Ingin main bareng teman?*\n"
        "Tambahkan bot ke Group Telegram — satu group = satu Kingdom!\n"
        "Lalu ketik `/join` di group untuk bergabung.\n\n"
        "📖 /tutorial — panduan lengkap cara main\n"
        "📋 /help — semua command"
    )
    kb = [
        [
            InlineKeyboardButton("📖 Tutorial",    callback_data="help_tutorial"),
            InlineKeyboardButton("📋 Commands",    callback_data="help_commands"),
        ],
        [InlineKeyboardButton("👤 Lihat Profil",   callback_data="help_profile")],
    ]
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ─────────────────────────────────────────────
async def help_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "📋 *SEMUA COMMAND*\n\n"

        "👤 *Player*\n"
        "`/start` — Daftar & mulai game\n"
        "`/profile` — Lihat stats & level kamu\n"
        "`/inventory` — Lihat resource kamu\n"
        "`/resources` — Lihat resource + tips jual\n"
        "`/daily` — Klaim reward harian (reset 24 jam)\n"
        "`/leaderboard` — Ranking 10 pemain terkuat\n\n"

        "🏘️ *Bangunan*\n"
        "`/buildings` — Lihat semua bangunan & levelnya\n"
        "`/build [nama]` — Bangun atau upgrade bangunan\n"
        "`/status` — Cek bangunan yang sedang dibangun\n"
        "`/collect` — Ambil resource produksi offline\n\n"

        "⚔️ *Battle (1v1)*\n"
        "`/attack @username` — Serang pemain lain\n"
        "`/defend` — Lihat kekuatan pertahanan kamu\n"
        "`/war` — Riwayat pertempuran 1v1\n\n"

        "🏰 *Kingdom*\n"
        "`/kingdom` — Info kerajaan (group/DM)\n"
        "`/join` — Bergabung ke kerajaan group ini\n"
        "`/leave` — Keluar dari kerajaan\n"
        "`/contribute [res] [jml]` — Sumbang ke kas kerajaan\n"
        "`/kadmin` — Command admin kerajaan\n\n"

        "🔥 *Kingdom War*\n"
        "`/kwar` — Info & stats kingdom war\n"
        "`/kwar [nama kerajaan]` — Tantang kerajaan lain\n"
        "`/kwar history` — Riwayat perang kerajaan\n\n"

        "🤝 *Aliansi*\n"
        "`/alliance` — Info aliansi kerajaan kamu\n"
        "`/alliance create [nama]` — Buat aliansi baru\n"
        "`/alliance invite [nama kd]` — Undang kerajaan lain\n"
        "`/alliance accept` — Terima undangan aliansi\n"
        "`/alliance reject` — Tolak undangan aliansi\n"
        "`/alliance leave` — Keluar dari aliansi\n"
        "`/alliance disband` — Bubarkan aliansi (founder)\n"
        "`/alliance list` — Lihat semua aliansi\n\n"

        "💰 *Market & Trading*\n"
        "`/market` — Lihat semua listing pasar\n"
        "`/market sell [res] [jml] [harga]` — Jual resource\n"
        "`/market buy [ID]` — Beli listing di pasar\n"
        "`/trade @user [res] [jml] [res] [jml]` — Trade langsung\n\n"

        "📖 *Bantuan*\n"
        "`/tutorial` — Panduan lengkap cara main\n"
        "`/help` — Tampilkan pesan ini\n"
        "`/commands` — Command khusus admin"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ─────────────────────────────────────────────
async def tutorial(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [
            InlineKeyboardButton("1️⃣ Dasar Game",      callback_data="help_tut_1"),
            InlineKeyboardButton("2️⃣ Bangunan",        callback_data="help_tut_2"),
        ],
        [
            InlineKeyboardButton("3️⃣ Battle 1v1",      callback_data="help_tut_3"),
            InlineKeyboardButton("4️⃣ Kingdom",         callback_data="help_tut_4"),
        ],
        [
            InlineKeyboardButton("5️⃣ Market & Trade",  callback_data="help_tut_5"),
            InlineKeyboardButton("6️⃣ Kingdom War",     callback_data="help_tut_6"),
        ],
        [
            InlineKeyboardButton("🤝 Aliansi",          callback_data="help_tut_7"),
        ],
    ]
    await update.message.reply_text(
        "📖 *TUTORIAL IDLE MMO*\n\nPilih topik yang ingin kamu pelajari:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ─────────────────────────────────────────────
async def commands_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚙️ *COMMAND ADMIN*\n\n"
        "👑 *Super Admin* (hanya owner bot)\n"
        "`/admin stats` — Statistik bot\n"
        "`/admin additem @user [res] [jml]` — Tambah resource\n"
        "`/admin removeitem @user [res] [jml]` — Hapus resource\n"
        "`/admin setgold @user [jml]` — Set gold pemain\n"
        "`/admin ban @user` — Ban pemain\n"
        "`/admin unban @user` — Unban pemain\n"
        "`/admin broadcast [pesan]` — Broadcast ke semua\n"
        "`/admin resetwar` — Reset data war 1v1\n\n"
        "🏰 *Kingdom Admin* (admin per Group)\n"
        "`/kadmin setname [nama]` — Ganti nama kerajaan\n"
        "`/kadmin settax [%]` — Set pajak kerajaan\n"
        "`/kadmin promote @user` — Jadikan Officer\n"
        "`/kadmin kick @user` — Keluarkan dari kerajaan\n"
        "`/kadmin announce [pesan]` — Umumkan ke group\n\n"
        "🔒 *Permission Level:*\n"
        "SuperAdmin > KingdomAdmin > Officer > Member"
    )
    await update.message.reply_text(text, parse_mode="Markdown")

# ─────────────────────────────────────────────
TUTORIAL_PAGES = {
    "help_tut_1": (
        "1️⃣ *DASAR GAME*\n\n"
        "🎮 Ini adalah *Idle MMO* — game yang jalan terus meski kamu offline!\n\n"
        "📌 *Cara Main:*\n"
        "• `/start` untuk daftar\n"
        "• `/daily` setiap hari untuk Gold + Resource gratis\n"
        "• `/build farm` untuk mulai produksi\n"
        "• Kembali nanti dan `/collect` resource yang terkumpul\n\n"
        "📊 *Stats Karakter:*\n"
        "• ❤️ HP — nyawa saat battle\n"
        "• ⚔️ Attack — kekuatan serangan\n"
        "• 🛡️ Defense — kekuatan pertahanan\n"
        "• ⭐ Level — naik dengan EXP dari battle & aktivitas\n\n"
        "💡 *Tips:* Klaim `/daily` setiap hari dan selalu `/collect` resource!"
    ),
    "help_tut_2": (
        "2️⃣ *BANGUNAN*\n\n"
        "🏗️ Bangunan menghasilkan resource otomatis selama kamu offline!\n\n"
        "🏘️ *Daftar Bangunan:*\n"
        "• 🌾 `farm` — Produksi Food (max lv.10)\n"
        "• ⛏️ `mine` — Produksi Stone & Iron (max lv.10)\n"
        "• 🪵 `lumbermill` — Produksi Wood (max lv.10)\n"
        "• ⚔️ `barracks` — +Attack Power (max lv.10)\n"
        "• 🛡️ `wall` — +Defense Power (max lv.10)\n"
        "• 🏪 `market` — +Gold & akses trading (max lv.5)\n"
        "• 🏰 `castle` — +HP & semua stats (max lv.5)\n\n"
        "⚙️ *Cara Build:*\n"
        "Ketik `/build` → pilih dari tombol\n"
        "Cek progress dengan `/status`\n"
        "Ambil hasil produksi dengan `/collect`\n\n"
        "⚠️ Resource produksi maksimal terkumpul *12 jam*!"
    ),
    "help_tut_3": (
        "3️⃣ *BATTLE 1v1*\n\n"
        "⚔️ Serang pemain lain dan rampas Gold mereka!\n\n"
        "🎯 *Cara Serang:*\n"
        "`/attack @username`\n\n"
        "📊 *Perhitungan Battle:*\n"
        "• Kemenangan ditentukan oleh Attack vs Defense\n"
        "• Ada faktor random ±20%\n"
        "• Menang = dapat 10% Gold musuh + EXP\n"
        "• Kalah = kehilangan sedikit HP + sedikit EXP\n\n"
        "🛡️ *Cek Pertahanan:*\n"
        "`/defend` — lihat kekuatan pertahananmu\n\n"
        "📜 *Riwayat:*\n"
        "`/war` — lihat semua pertempuranmu\n\n"
        "⏰ *Cooldown:* 1 jam antar serangan ke target sama\n\n"
        "💡 Upgrade `barracks` untuk +Attack\n"
        "💡 Upgrade `wall` untuk +Defense"
    ),
    "help_tut_4": (
        "4️⃣ *KINGDOM SYSTEM*\n\n"
        "🏰 Satu Telegram Group = Satu Kingdom!\n\n"
        "📌 *Cara Setup & Join Kingdom:*\n"
        "1. Tambahkan bot ke Group Telegram\n"
        "2. Ketik `/kingdom` di group → kerajaan otomatis dibuat\n"
        "3. Ketik `/join` di group → langsung jadi member\n"
        "4. Kalau sudah di kerajaan lain → muncul konfirmasi pindah\n\n"
        "👥 *Kerja Sama:*\n"
        "`/contribute gold 500` — sumbang Gold ke kas\n"
        "`/contribute wood 200` — sumbang Wood ke kas\n"
        "`/kingdom` — lihat info & kas kerajaan\n"
        "`/leave` — keluar dari kerajaan\n\n"
        "⚙️ *Kingdom Admin:*\n"
        "`/kadmin setname` — ganti nama kerajaan\n"
        "`/kadmin settax` — set pajak 0-20%\n"
        "`/kadmin promote @user` — jadikan officer\n"
        "`/kadmin kick @user` — keluarkan member\n"
        "`/kadmin announce` — umumkan ke group"
    ),
    "help_tut_5": (
        "5️⃣ *MARKET & TRADING*\n\n"
        "💰 Jual beli resource dengan pemain lain!\n\n"
        "📊 *Market Global:*\n"
        "`/market` — lihat semua listing\n"
        "`/market sell wood 100 500` — jual 100 Wood seharga 500 Gold\n"
        "`/market buy [ID]` — beli listing berdasarkan ID\n\n"
        "🔄 *Trade Langsung:*\n"
        "`/trade @username wood 50 gold 100`\n"
        "= Tawarkan 50 Wood, minta 100 Gold\n\n"
        "💡 *Info Penting:*\n"
        "• Ada fee *5%* untuk setiap penjualan di market\n"
        "• Trade langsung tidak kena fee\n"
        "• Bangun `market` untuk bonus Gold pasif\n\n"
        "📈 *Resource yang bisa ditrade:*\n"
        "🪙 gold • 🪵 wood • 🪨 stone • 🌾 food • ⚔️ iron"
    ),
    "help_tut_6": (
        "6️⃣ *KINGDOM WAR*\n\n"
        "🔥 Perang antar kerajaan untuk merampas resource kas lawan!\n\n"
        "📌 *Cara Berperang:*\n"
        "1. Ketik `/kwar` di group untuk lihat info\n"
        "2. Ketik `/kwar [nama kerajaan lawan]`\n"
        "3. Preview kekuatan & potensi rampasan muncul\n"
        "4. Konfirmasi → perang dimulai!\n\n"
        "📊 *Sistem Perang:*\n"
        "• Kekuatan = total ATK + DEF + Level semua member\n"
        "• Ada random ±15% — bisa saja yang lemah menang!\n"
        "• Menang = rampas *15% semua resource* kas lawan\n"
        "• Kalah = kehilangan *15% resource* kas sendiri\n\n"
        "⏰ *Cooldown:* 6 jam per target kerajaan\n\n"
        "🔔 Group lawan otomatis dapat notifikasi hasil perang\n\n"
        "📜 `/kwar history` — lihat riwayat perang kerajaan\n\n"
        "⚠️ *Hanya Admin/Officer* yang bisa nyatakan perang!\n"
        "💡 Makin banyak member aktif = kerajaan makin kuat!"
    ),
    "help_tut_7": (
        "🤝 *SISTEM ALIANSI*\n\n"
        "Aliansi adalah persekutuan antar kerajaan — anggota aliansi *tidak bisa saling serang!*\n\n"
        "📌 *Cara Buat Aliansi:*\n"
        "1. Ketik di group kerajaan kamu:\n"
        "   `/alliance create Nama Aliansi`\n"
        "2. Kerajaanmu otomatis jadi *Pendiri*\n"
        "3. Undang kerajaan lain untuk bergabung\n\n"
        "📨 *Cara Mengundang Kerajaan Lain:*\n"
        "`/alliance invite Nama Kerajaan`\n"
        "• Kerajaan target dapat notifikasi otomatis di group mereka\n"
        "• Mereka bisa terima dengan `/alliance accept`\n"
        "• Atau tolak dengan `/alliance reject`\n\n"
        "📋 *Semua Command Aliansi:*\n"
        "`/alliance` — lihat info aliansi & undangan pending\n"
        "`/alliance create [nama]` — buat aliansi baru\n"
        "`/alliance invite [nama kd]` — undang kerajaan\n"
        "`/alliance accept` — terima undangan\n"
        "`/alliance reject` — tolak undangan\n"
        "`/alliance leave` — keluar dari aliansi\n"
        "`/alliance disband` — bubarkan aliansi (pendiri)\n"
        "`/alliance list` — lihat semua aliansi yang ada\n\n"
        "🔒 *Permission:*\n"
        "• Hanya *Admin Kerajaan* yang bisa buat, undang, terima, keluar, atau bubarkan aliansi\n\n"
        "⚔️ *Efek di Kingdom War:*\n"
        "• Kerajaan yang bersekutu *tidak bisa saling serang*\n"
        "• Gunakan aliansi untuk perlindungan dari serangan!\n\n"
        "💡 *Tips:*\n"
        "• Satu kerajaan hanya bisa di *satu aliansi*\n"
        "• Pendiri tidak bisa keluar biasa — harus disband dulu\n"
        "• Ketik `/alliance` tanpa argumen untuk cek status & undangan"
    ),
}

_BACK_KB = InlineKeyboardMarkup([[
    InlineKeyboardButton("⬅️ Kembali ke Tutorial", callback_data="help_tutorial")
]])

# ─────────────────────────────────────────────
async def help_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "help_tutorial":
        kb = [
            [
                InlineKeyboardButton("1️⃣ Dasar Game",     callback_data="help_tut_1"),
                InlineKeyboardButton("2️⃣ Bangunan",       callback_data="help_tut_2"),
            ],
            [
                InlineKeyboardButton("3️⃣ Battle 1v1",     callback_data="help_tut_3"),
                InlineKeyboardButton("4️⃣ Kingdom",        callback_data="help_tut_4"),
            ],
            [
                InlineKeyboardButton("5️⃣ Market & Trade", callback_data="help_tut_5"),
                InlineKeyboardButton("6️⃣ Kingdom War",    callback_data="help_tut_6"),
            ],
            [
                InlineKeyboardButton("🤝 Aliansi",         callback_data="help_tut_7"),
            ],
        ]
        await query.edit_message_text(
            "📖 *TUTORIAL IDLE MMO*\n\nPilih topik:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    elif data == "help_commands":
        await query.edit_message_text(
            "📋 Ketik /help untuk melihat semua command.",
            parse_mode="Markdown"
        )

    elif data == "help_profile":
        await query.edit_message_text(
            "👤 Ketik /profile untuk melihat karakter kamu!",
            parse_mode="Markdown"
        )

    elif data in TUTORIAL_PAGES:
        await query.edit_message_text(
            TUTORIAL_PAGES[data],
            parse_mode="Markdown",
            reply_markup=_BACK_KB
        )
