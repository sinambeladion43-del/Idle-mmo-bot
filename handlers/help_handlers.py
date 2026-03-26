import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import get_player, create_player

# ─────────────────────────────────────────────
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await create_player(user.id, user.username or user.first_name)
    player = await get_player(user.id)

    text = (
        f"⚔️ *Selamat datang di IDLE MMO, {user.first_name}!*\n\n"
        "🏰 Kamu sudah terdaftar sebagai petualang!\n\n"
        "📜 *Langkah Pertama:*\n"
        "1️⃣ Bangun `/build farm` untuk mulai produksi Food\n"
        "2️⃣ Klaim reward harian dengan `/daily`\n"
        "3️⃣ Lihat profil kamu dengan `/profile`\n"
        "4️⃣ Cek semua bangunan dengan `/buildings`\n\n"
        "📖 Ketik /tutorial untuk panduan lengkap\n"
        "📋 Ketik /help untuk semua command\n\n"
        "🏰 *Ingin main bareng teman?*\n"
        "Tambahkan bot ke Group Telegram kamu — satu group = satu Kingdom!"
    )
    kb = [
        [
            InlineKeyboardButton("📖 Tutorial", callback_data="help_tutorial"),
            InlineKeyboardButton("📋 Commands", callback_data="help_commands"),
        ],
        [InlineKeyboardButton("👤 Lihat Profil", callback_data="help_profile")],
    ]
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ─────────────────────────────────────────────
async def help_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "📋 *DAFTAR COMMAND*\n\n"
        "👤 *Player*\n"
        "`/start` — Daftar / mulai game\n"
        "`/profile` — Lihat stats & level kamu\n"
        "`/inventory` — Lihat resource yang kamu punya\n"
        "`/daily` — Klaim reward harian (reset 24 jam)\n"
        "`/leaderboard` — Ranking pemain terkuat\n\n"
        "🏘️ *Bangunan*\n"
        "`/buildings` — Lihat semua bangunan & levelnya\n"
        "`/build [nama]` — Bangun atau upgrade bangunan\n"
        "`/status` — Cek bangunan yang sedang dibangun\n"
        "`/collect` — Ambil resource produksi offline\n\n"
        "⚔️ *Battle*\n"
        "`/attack @username` — Serang pemain lain\n"
        "`/defend` — Lihat kekuatan pertahanan kamu\n"
        "`/war` — Riwayat pertempuran\n\n"
        "🏰 *Kingdom (di Group)*\n"
        "`/kingdom` — Info kerajaan group ini\n"
        "`/contribute [resource] [jumlah]` — Sumbang ke kerajaan\n\n"
        "💰 *Market*\n"
        "`/market` — Lihat listing pasar\n"
        "`/market sell [resource] [jumlah] [harga]` — Jual resource\n"
        "`/market buy [id]` — Beli listing di pasar\n"
        "`/resources` — Lihat resource kamu\n\n"
        "📖 Ketik /tutorial untuk panduan cara main\n"
        "⚙️ Ketik /commands untuk command admin"
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
            InlineKeyboardButton("3️⃣ Battle",          callback_data="help_tut_3"),
            InlineKeyboardButton("4️⃣ Kingdom",         callback_data="help_tut_4"),
        ],
        [InlineKeyboardButton("5️⃣ Market & Trading",   callback_data="help_tut_5")],
    ]
    text = (
        "📖 *TUTORIAL IDLE MMO*\n\n"
        "Pilih topik yang ingin kamu pelajari:"
    )
    await update.message.reply_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ─────────────────────────────────────────────
async def commands_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "⚙️ *COMMAND ADMIN*\n\n"
        "👑 *Super Admin* (hanya owner bot)\n"
        "`/admin additem @user [resource] [jumlah]`\n"
        "`/admin removeitem @user [resource] [jumlah]`\n"
        "`/admin setgold @user [jumlah]`\n"
        "`/admin ban @user`\n"
        "`/admin unban @user`\n"
        "`/admin broadcast [pesan]`\n"
        "`/admin resetwar`\n"
        "`/admin stats`\n\n"
        "🏰 *Kingdom Admin* (admin per Group)\n"
        "`/kadmin promote @user`\n"
        "`/kadmin kick @user`\n"
        "`/kadmin settax [%]`\n"
        "`/kadmin setname [nama]`\n"
        "`/kadmin announce [pesan]`\n\n"
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
        "• Gunakan `/start` untuk daftar\n"
        "• Klaim `/daily` setiap hari untuk Gold + Resource gratis\n"
        "• Bangun bangunan dengan `/build [nama]`\n"
        "• Kembali nanti dan `/collect` resource yang sudah terkumpul\n\n"
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
        "• 🌾 `farm` — Produksi Food\n"
        "• ⛏️ `mine` — Produksi Stone & Iron\n"
        "• 🪵 `lumbermill` — Produksi Wood\n"
        "• ⚔️ `barracks` — +Attack Power\n"
        "• 🛡️ `wall` — +Defense Power\n"
        "• 🏪 `market` — +Gold & akses trading\n"
        "• 🏰 `castle` — +HP & semua stats\n\n"
        "⚙️ *Cara Build:*\n"
        "Ketik `/build farm` → pilih dari tombol\n"
        "Setiap bangunan punya *waktu konstruksi*\n"
        "Cek progress dengan `/status`\n\n"
        "📈 Setiap bangunan bisa di-*upgrade* sampai level 10!\n"
        "Makin tinggi level = makin banyak produksi"
    ),
    "help_tut_3": (
        "3️⃣ *BATTLE SYSTEM*\n\n"
        "⚔️ Serang pemain lain dan rampas Gold mereka!\n\n"
        "🎯 *Cara Serang:*\n"
        "`/attack @username` — ketik username lawan\n\n"
        "📊 *Perhitungan Battle:*\n"
        "• Kemenangan ditentukan oleh Attack vs Defense\n"
        "• Ada faktor random ±20% untuk kejutan\n"
        "• Menang = dapatkan 10% Gold musuh\n"
        "• Kalah = kehilangan sedikit HP\n\n"
        "🛡️ *Defense:*\n"
        "`/defend` — lihat kekuatan pertahananmu\n"
        "Naikkan level `wall` dan `barracks` untuk jadi lebih kuat!\n\n"
        "📜 *Riwayat:*\n"
        "`/war` — lihat semua pertempuranmu\n\n"
        "⏰ Cooldown: 1 jam antar serangan ke target yang sama"
    ),
    "help_tut_4": (
        "4️⃣ *KINGDOM SYSTEM*\n\n"
        "🏰 Satu Telegram Group = Satu Kingdom!\n\n"
        "📌 *Cara Setup Kingdom:*\n"
        "1. Tambahkan bot ke Group Telegram\n"
        "2. Ketik `/kingdom` — bot auto-buat kerajaan\n"
        "3. Admin group jadi Kingdom Admin\n\n"
        "👥 *Kerja Sama:*\n"
        "`/contribute gold 500` — sumbang Gold ke kas kerajaan\n"
        "`/contribute wood 200` — sumbang Wood\n"
        "Semua member bisa sumbang resource!\n\n"
        "⚙️ *Kingdom Admin bisa:*\n"
        "`/kadmin setname [nama]` — ganti nama kerajaan\n"
        "`/kadmin settax [%]` — set pajak (0-20%)\n"
        "`/kadmin promote @user` — jadikan officer\n"
        "`/kadmin kick @user` — keluarkan member\n"
        "`/kadmin announce [pesan]` — umumkan ke member\n\n"
        "💡 Kingdom yang kuat = member yang aktif sumbang resource!"
    ),
    "help_tut_5": (
        "5️⃣ *MARKET & TRADING*\n\n"
        "💰 Jual beli resource dengan pemain lain!\n\n"
        "📊 *Market Global:*\n"
        "`/market` — lihat semua listing\n"
        "`/market sell gold 100 500` — jual 100 Gold seharga 500 (koin)\n"
        "`/market buy [ID]` — beli listing berdasarkan ID\n\n"
        "🔄 *Trade Langsung:*\n"
        "`/trade @username wood 50 gold 100`\n"
        "= Tawarkan 50 Wood, minta 100 Gold\n\n"
        "💡 *Tips Market:*\n"
        "• Ada fee 5% untuk setiap penjualan\n"
        "• Bangun `market` untuk bonus Gold\n"
        "• Cek `/resources` untuk lihat stok kamu\n\n"
        "📈 *Resource yang bisa ditrade:*\n"
        "🪙 gold • 🪵 wood • 🪨 stone • 🌾 food • ⚔️ iron"
    ),
}

_BACK_KB = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Kembali ke Tutorial", callback_data="help_tutorial")]])

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
                InlineKeyboardButton("3️⃣ Battle",        callback_data="help_tut_3"),
                InlineKeyboardButton("4️⃣ Kingdom",       callback_data="help_tut_4"),
            ],
            [InlineKeyboardButton("5️⃣ Market & Trading", callback_data="help_tut_5")],
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
