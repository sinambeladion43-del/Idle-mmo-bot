# 🏰 Idle MMO Bot — Telegram

Game idle berbasis Telegram. Bangun kota, serang musuh, dan kelola kerajaan bersama teman!

---

## 🚀 Deploy ke Railway (3 Langkah)

### 1. Upload ke GitHub
- Buat repo baru di GitHub (misal: `idle-mmo-bot`)
- Upload semua file ini ke repo tersebut

### 2. Hubungkan ke Railway
- Buka [railway.app](https://railway.app) → New Project → Deploy from GitHub repo
- Pilih repo `idle-mmo-bot` kamu

### 3. Set Environment Variables
Di Railway dashboard → Variables, tambahkan:

| Variable | Nilai | Keterangan |
|----------|-------|------------|
| `BOT_TOKEN` | `123456:ABC...` | Token dari @BotFather |
| `ADMIN_IDS` | `123456789` | Telegram User ID kamu (bisa cek via @userinfobot) |
| `DB_PATH` | `/app/game.db` | Path database (opsional, default: `./game.db`) |

> 💡 Untuk multiple admin: `ADMIN_IDS=123456789,987654321`

### ✅ Selesai! Bot langsung jalan.

---

## 🎮 Cara Main

### Mulai
1. Chat bot langsung → `/start` untuk daftar
2. Klaim `/daily` setiap hari
3. Bangun `/build farm` untuk mulai produksi
4. `/collect` untuk ambil resource offline

### Bangunan
| Bangunan | Produksi | Max Level |
|----------|----------|-----------|
| 🌾 farm | Food | 10 |
| ⛏️ mine | Stone + Iron | 10 |
| 🪵 lumbermill | Wood | 10 |
| ⚔️ barracks | +Attack | 10 |
| 🛡️ wall | +Defense | 10 |
| 🏪 market | +Gold | 5 |
| 🏰 castle | +HP & Stats | 5 |

### Kingdom (Group)
- Tambahkan bot ke Group Telegram
- Ketik `/kingdom` → kerajaan otomatis terbuat
- Member bisa `/contribute gold 500` untuk sumbang

---

## 📋 Semua Command

| Command | Keterangan |
|---------|-----------|
| `/start` | Daftar & mulai main |
| `/profile` | Lihat stats karakter |
| `/inventory` | Lihat resource |
| `/daily` | Klaim reward harian |
| `/leaderboard` | Ranking pemain |
| `/buildings` | Lihat semua bangunan |
| `/build [nama]` | Bangun/upgrade bangunan |
| `/status` | Cek konstruksi |
| `/collect` | Ambil resource offline |
| `/attack @user` | Serang pemain lain |
| `/defend` | Lihat kekuatan pertahanan |
| `/war` | Riwayat pertempuran |
| `/kingdom` | Info kerajaan (di group) |
| `/contribute [res] [amt]` | Sumbang ke kerajaan |
| `/kadmin [cmd]` | Admin kerajaan |
| `/market` | Lihat market |
| `/market sell [res] [amt] [harga]` | Jual resource |
| `/market buy [ID]` | Beli listing |
| `/trade @user [res] [amt] [res] [amt]` | Trade langsung |
| `/resources` | Lihat resource kamu |
| `/tutorial` | Panduan main |
| `/help` | Semua command |

---

## ⚙️ Admin Commands

### Super Admin (ADMIN_IDS)
```
/admin stats
/admin additem @user gold 1000
/admin removeitem @user wood 500
/admin setgold @user 5000
/admin ban @user
/admin unban @user
/admin broadcast [pesan]
/admin resetwar
```

### Kingdom Admin (admin group)
```
/kadmin setname [nama kerajaan]
/kadmin settax [0-20]
/kadmin promote @user
/kadmin kick @user
/kadmin announce [pesan]
```

---

## 🗂️ Struktur File

```
idle-mmo-bot/
├── bot.py              ← Main entry point
├── config.py           ← Konfigurasi & env vars
├── database.py         ← Database & queries
├── game_data.py        ← Balance game (edit untuk rebalance)
├── requirements.txt    ← Dependencies
├── Procfile            ← Railway startup
├── runtime.txt         ← Python version
└── handlers/
    ├── __init__.py
    ├── help_handlers.py
    ├── player_handlers.py
    ├── building_handlers.py
    ├── battle_handlers.py
    ├── kingdom_handlers.py
    ├── economy_handlers.py
    └── admin_handlers.py
```

---

## 🔧 Rebalance Game

Edit `game_data.py` untuk ubah:
- `DAILY_REWARD` — reward harian
- `BUILDINGS[...]["cost"]` — biaya bangun
- `BUILDINGS[...]["produces"]` — produksi per jam
- `LOOT_PERCENT` — % gold yang dicuri saat menang
- `ATTACK_COOLDOWN` — cooldown antar serangan
