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

        "⚔️ *Battle 1v1*\n"
        "`/attack` — Serang pemain (reply pesan lawan)\n"
        "`/defend` — Lihat kekuatan pertahanan kamu\n"
        "`/battlelog` — Riwayat pertempuran 1v1\n\n"

        "🏰 *Kingdom*\n"
        "`/kingdom` — Info kerajaan (group/DM)\n"
        "`/join` — Bergabung ke kerajaan group ini\n"
        "`/leave` — Keluar dari kerajaan\n"
        "`/contribute [res] [jml]` — Sumbang ke kas kerajaan\n"
        "`/kadmin` — Command admin kerajaan\n\n"

        "⚔️ *War System (2 Kerajaan)*\n"
        "`/war` — Info & panel perang kerajaan\n"
        "`/war declare` — Nyatakan perang ke musuh\n"
        "`/war status` — Status voting perang\n"
        "`/war history` — Riwayat perang kerajaan\n\n"

        "🤝 *Aliansi*\n"
        "`/alliance` — Info aliansi kerajaan kamu\n"
        "`/alliance create [nama]` — Buat aliansi baru\n"
        "`/alliance invite [nama kd]` — Undang kerajaan\n"
        "`/alliance accept/reject` — Terima/tolak undangan\n"
        "`/alliance leave` — Keluar dari aliansi\n"
        "`/alliance disband` — Bubarkan aliansi\n"
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
            InlineKeyboardButton("5️⃣ Market",          callback_data="help_tut_5"),
            InlineKeyboardButton("6️⃣ War System",      callback_data="help_tut_6"),
        ],
        [
            InlineKeyboardButton("7️⃣ Aliansi",         callback_data="help_tut_7"),
            InlineKeyboardButton("8️⃣ Tips & Tricks",   callback_data="help_tut_8"),
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
        "• `/build farm` untuk mulai produksi resource\n"
        "• Kembali nanti dan `/collect` resource yang terkumpul\n\n"
        "📊 *Stats Karakter:*\n"
        "• ❤️ HP — nyawa saat battle\n"
        "• ⚔️ Attack — kekuatan serangan\n"
        "• 🛡️ Defense — kekuatan pertahanan\n"
        "• ⭐ Level — naik dengan EXP dari battle & aktivitas\n\n"
        "💡 *Tips:* Klaim `/daily` setiap hari dan selalu `/collect` resource!\n\n"
        "📋 Lihat profil kamu dengan `/profile`"
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
        "1. Ketik `/build` → pilih dari tombol\n"
        "2. Cek progress: `/status`\n"
        "3. Ambil hasil: `/collect`\n\n"
        "⚠️ Resource terkumpul maksimal *12 jam* — sering-sering collect!"
    ),
    "help_tut_3": (
        "3️⃣ *BATTLE 1v1*\n\n"
        "⚔️ Serang pemain lain dan rampas Gold mereka!\n\n"
        "🎯 *Cara Menyerang:*\n"
        "• *Reply* pesan lawan lalu ketik `/attack`\n"
        "• Atau: `/attack [user_id]` jika tau ID pemain\n\n"
        "📊 *Perhitungan Battle:*\n"
        "• Attack vs Defense + random ±20%\n"
        "• Menang = dapat 10% Gold musuh + EXP\n"
        "• Kalah = HP berkurang + sedikit EXP\n\n"
        "🛡️ `/defend` — lihat kekuatan pertahananmu\n"
        "📜 `/battlelog` — riwayat battle 1v1\n\n"
        "⏰ *Cooldown:* 1 jam per target\n\n"
        "💡 Upgrade `barracks` → +Attack\n"
        "💡 Upgrade `wall` → +Defense\n\n"
        "🔔 Lawan otomatis dapat notifikasi saat diserang!"
    ),
    "help_tut_4": (
        "4️⃣ *KINGDOM SYSTEM*\n\n"
        "🏰 Satu Telegram Group = Satu Kingdom!\n\n"
        "📌 *Setup Kingdom:*\n"
        "1. Tambahkan bot ke Group Telegram\n"
        "2. Ketik `/kingdom` → kerajaan otomatis dibuat\n"
        "3. Ketik `/join` → langsung jadi member\n\n"
        "👥 *Kerja Sama:*\n"
        "`/contribute gold 500` — sumbang ke kas kerajaan\n"
        "`/kingdom` — lihat info & kas kerajaan\n"
        "`/leave` — keluar dari kerajaan\n\n"
        "⚙️ *Kingdom Admin (admin group):*\n"
        "`/kadmin setname [nama]` — ganti nama\n"
        "`/kadmin settax [0-20]` — set pajak\n"
        "`/kadmin promote @user` — jadikan officer\n"
        "`/kadmin kick @user` — keluarkan member\n"
        "`/kadmin announce [pesan]` — umumkan ke group"
    ),
    "help_tut_5": (
        "5️⃣ *MARKET & TRADING*\n\n"
        "💰 Jual beli resource dengan pemain lain!\n\n"
        "📊 *Market Global:*\n"
        "`/market` — lihat semua listing\n"
        "`/market sell wood 100 500` — jual 100 Wood harga 500 Gold\n"
        "`/market buy [ID]` — beli berdasarkan ID\n\n"
        "🔄 *Trade Langsung:*\n"
        "`/trade @user wood 100 gold 500`\n"
        "= Tawarkan 100 Wood, minta 500 Gold\n\n"
        "💡 *Info Penting:*\n"
        "• Fee *5%* untuk setiap penjualan di market\n"
        "• Trade langsung = tidak ada fee\n"
        "• Bangun `market` untuk bonus Gold pasif\n\n"
        "📈 *Resource yang bisa ditrade:*\n"
        "🪵 wood • 🪨 stone • 🌾 food • ⚔️ iron"
    ),
    "help_tut_6": (
        "6️⃣ *WAR SYSTEM — PERANG 2 KERAJAAN*\n\n"
        "🔥 Sistem perang khusus antara 2 kerajaan dengan voting member!\n\n"
        "📌 *Alur Perang:*\n"
        "1️⃣ Admin Group A ketik `/war declare`\n"
        "2️⃣ Notifikasi + tombol voting masuk ke Group B\n"
        "3️⃣ Member Group B vote *Setuju* atau *Tolak* (30 menit)\n"
        "4️⃣ Kalau >50% setuju → Perang dimulai!\n"
        "5️⃣ Hasil perang di-announce ke kedua group\n\n"
        "📊 *Sistem Perang:*\n"
        "• Kekuatan = total ATK+DEF+Level semua member\n"
        "• Random ±15% — yang lemah bisa menang!\n"
        "• Menang = rampas 15% resource kas lawan\n"
        "• Kalah = kehilangan 15% resource kas sendiri\n\n"
        "⏰ *Cooldown:* 24 jam antar perang\n\n"
        "📋 *Command:*\n"
        "`/war` — panel info perang\n"
        "`/war declare` — nyatakan perang *(admin only)*\n"
        "`/war status` — lihat progress voting\n"
        "`/war history` — riwayat perang kerajaan\n\n"
        "⚠️ Hanya *Admin Group* yang bisa declare war!"
    ),
    "help_tut_7": (
        "7️⃣ *SISTEM ALIANSI*\n\n"
        "🤝 Persekutuan antar kerajaan — sesama anggota *tidak bisa saling serang!*\n\n"
        "📌 *Cara Buat Aliansi:*\n"
        "1. Ketik di group kerajaanmu:\n"
        "   `/alliance create Nama Aliansi`\n"
        "2. Kerajaanmu jadi *Pendiri*\n"
        "3. Undang kerajaan lain bergabung\n\n"
        "📨 *Cara Mengundang:*\n"
        "`/alliance invite Nama Kerajaan`\n"
        "→ Target dapat notif otomatis di group mereka\n"
        "→ Terima: `/alliance accept`\n"
        "→ Tolak: `/alliance reject`\n\n"
        "📋 *Semua Command:*\n"
        "`/alliance` — info aliansi + cek undangan\n"
        "`/alliance create [nama]` — buat aliansi baru\n"
        "`/alliance invite [nama kd]` — undang kerajaan\n"
        "`/alliance accept` — terima undangan\n"
        "`/alliance reject` — tolak undangan\n"
        "`/alliance leave` — keluar dari aliansi\n"
        "`/alliance disband` — bubarkan aliansi\n"
        "`/alliance list` — lihat semua aliansi\n\n"
        "⚔️ Sesama anggota aliansi *tidak bisa saling serang* di War!\n"
        "💡 Satu kerajaan hanya bisa di *satu aliansi*"
    ),
    "help_tut_8": (
        "8️⃣ *TIPS & TRICKS*\n\n"
        "💡 *Untuk Pemula:*\n"
        "• Prioritas build: `farm` → `mine` → `lumbermill` dulu\n"
        "• Klaim `/daily` setiap hari tanpa gagal\n"
        "• `/collect` resource sebelum penuh (max 12 jam)\n"
        "• Gabung kingdom dan `/contribute` untuk bantu kerajaan\n\n"
        "⚔️ *Untuk Battle:*\n"
        "• Upgrade `barracks` untuk nambah Attack\n"
        "• Upgrade `wall` untuk nambah Defense\n"
        "• Serang lawan yang levelnya lebih rendah untuk EXP mudah\n"
        "• Reply pesan lawan → `/attack` untuk serang\n\n"
        "🏰 *Untuk Kingdom:*\n"
        "• Makin banyak member aktif = kerajaan makin kuat di war\n"
        "• Isi kas kerajaan dengan `/contribute` sebelum war\n"
        "• Admin harus aktif urus kerajaan\n\n"
        "💰 *Untuk Economy:*\n"
        "• Jual resource yang berlebih di `/market`\n"
        "• Beli resource yang kurang dari pemain lain\n"
        "• Trade langsung ke teman = tidak kena fee 5%\n\n"
        "🔔 *Notifikasi:*\n"
        "• Kamu dapat DM saat diserang\n"
        "• Group dapat notif saat ada deklarasi perang\n"
        "• Group dapat notif saat diundang aliansi"
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
                InlineKeyboardButton("1️⃣ Dasar Game",    callback_data="help_tut_1"),
                InlineKeyboardButton("2️⃣ Bangunan",      callback_data="help_tut_2"),
            ],
            [
                InlineKeyboardButton("3️⃣ Battle 1v1",    callback_data="help_tut_3"),
                InlineKeyboardButton("4️⃣ Kingdom",       callback_data="help_tut_4"),
            ],
            [
                InlineKeyboardButton("5️⃣ Market",        callback_data="help_tut_5"),
                InlineKeyboardButton("6️⃣ War System",    callback_data="help_tut_6"),
            ],
            [
                InlineKeyboardButton("7️⃣ Aliansi",       callback_data="help_tut_7"),
                InlineKeyboardButton("8️⃣ Tips & Tricks", callback_data="help_tut_8"),
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
