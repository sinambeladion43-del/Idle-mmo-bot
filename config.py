import os

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
ADMIN_IDS_RAW = os.environ.get("ADMIN_IDS", "")

# Support comma-separated admin IDs, e.g. "123456789,987654321"
ADMIN_IDS: list[int] = []
for raw in ADMIN_IDS_RAW.split(","):
    raw = raw.strip()
    if raw.isdigit():
        ADMIN_IDS.append(int(raw))

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///./game.db")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is not set!")
