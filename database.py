import time
import json
import aiosqlite
import os

DB_PATH = os.environ.get("DB_PATH", "./game.db")

# ──────────────────────────────────────────────
# Init
# ──────────────────────────────────────────────
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS players (
            user_id     INTEGER PRIMARY KEY,
            username    TEXT DEFAULT 'Unknown',
            level       INTEGER DEFAULT 1,
            exp         INTEGER DEFAULT 0,
            gold        INTEGER DEFAULT 100,
            wood        INTEGER DEFAULT 50,
            stone       INTEGER DEFAULT 50,
            food        INTEGER DEFAULT 50,
            iron        INTEGER DEFAULT 0,
            attack_pow  INTEGER DEFAULT 10,
            defense_pow INTEGER DEFAULT 10,
            hp          INTEGER DEFAULT 100,
            max_hp      INTEGER DEFAULT 100,
            last_daily  INTEGER DEFAULT 0,
            last_collect INTEGER DEFAULT 0,
            is_banned   INTEGER DEFAULT 0,
            kingdom_id  INTEGER DEFAULT 0,
            role        TEXT DEFAULT 'member',
            created_at  INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS buildings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER,
            name        TEXT,
            level       INTEGER DEFAULT 0,
            finish_time INTEGER DEFAULT 0,
            UNIQUE(user_id, name)
        );

        CREATE TABLE IF NOT EXISTS kingdoms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            group_id    INTEGER UNIQUE,
            name        TEXT DEFAULT 'Unnamed Kingdom',
            level       INTEGER DEFAULT 1,
            gold        INTEGER DEFAULT 0,
            wood        INTEGER DEFAULT 0,
            stone       INTEGER DEFAULT 0,
            food        INTEGER DEFAULT 0,
            iron        INTEGER DEFAULT 0,
            tax_rate    INTEGER DEFAULT 5,
            admin_id    INTEGER DEFAULT 0,
            created_at  INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS wars (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_id     INTEGER,
            defender_id     INTEGER,
            attacker_name   TEXT,
            defender_name   TEXT,
            result          TEXT,
            damage_dealt    INTEGER DEFAULT 0,
            damage_taken    INTEGER DEFAULT 0,
            loot_gold       INTEGER DEFAULT 0,
            timestamp       INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS market_listings (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            seller_id   INTEGER,
            seller_name TEXT,
            resource    TEXT,
            amount      INTEGER,
            price       INTEGER,
            created_at  INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS kingdom_wars (
            id                    INTEGER PRIMARY KEY AUTOINCREMENT,
            attacker_kingdom_id   INTEGER,
            defender_kingdom_id   INTEGER,
            attacker_name         TEXT,
            defender_name         TEXT,
            result                TEXT,
            attacker_power        INTEGER DEFAULT 0,
            defender_power        INTEGER DEFAULT 0,
            loot_gold             INTEGER DEFAULT 0,
            loot_wood             INTEGER DEFAULT 0,
            loot_stone            INTEGER DEFAULT 0,
            loot_food             INTEGER DEFAULT 0,
            loot_iron             INTEGER DEFAULT 0,
            timestamp             INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS kingdom_war_cooldowns (
            attacker_id  INTEGER,
            defender_id  INTEGER,
            last_war     INTEGER DEFAULT 0,
            PRIMARY KEY (attacker_id, defender_id)
        );

        CREATE TABLE IF NOT EXISTS trade_offers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            from_id         INTEGER,
            to_id           INTEGER,
            offer_resource  TEXT,
            offer_amount    INTEGER,
            want_resource   TEXT,
            want_amount     INTEGER,
            status          TEXT DEFAULT 'pending',
            created_at      INTEGER DEFAULT 0
        );
        """)
        await db.commit()

# ──────────────────────────────────────────────
# Player helpers
# ──────────────────────────────────────────────
async def get_player(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM players WHERE user_id=?", (user_id,)) as cur:
            return await cur.fetchone()

async def create_player(user_id: int, username: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO players
               (user_id, username, created_at)
               VALUES (?,?,?)""",
            (user_id, username, int(time.time()))
        )
        await db.commit()

async def update_player(user_id: int, **kwargs):
    if not kwargs:
        return
    cols = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [user_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE players SET {cols} WHERE user_id=?", vals)
        await db.commit()

async def get_top_players(limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM players WHERE is_banned=0 ORDER BY level DESC, exp DESC LIMIT ?",
            (limit,)
        ) as cur:
            return await cur.fetchall()

async def get_all_players():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM players") as cur:
            return await cur.fetchall()

# ──────────────────────────────────────────────
# Building helpers
# ──────────────────────────────────────────────
async def get_building(user_id: int, name: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM buildings WHERE user_id=? AND name=?", (user_id, name)
        ) as cur:
            return await cur.fetchone()

async def get_all_buildings(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM buildings WHERE user_id=?", (user_id,)
        ) as cur:
            return await cur.fetchall()

async def upsert_building(user_id: int, name: str, level: int, finish_time: int = 0):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO buildings (user_id, name, level, finish_time)
               VALUES (?,?,?,?)
               ON CONFLICT(user_id, name) DO UPDATE SET level=?, finish_time=?""",
            (user_id, name, level, finish_time, level, finish_time)
        )
        await db.commit()

# ──────────────────────────────────────────────
# Kingdom helpers
# ──────────────────────────────────────────────
async def get_kingdom(group_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM kingdoms WHERE group_id=?", (group_id,)) as cur:
            return await cur.fetchone()

async def get_kingdom_by_id(kingdom_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM kingdoms WHERE id=?", (kingdom_id,)) as cur:
            return await cur.fetchone()

async def create_kingdom(group_id: int, name: str, admin_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT OR IGNORE INTO kingdoms (group_id, name, admin_id, created_at)
               VALUES (?,?,?,?)""",
            (group_id, name, admin_id, int(time.time()))
        )
        await db.commit()
        async with db.execute("SELECT id FROM kingdoms WHERE group_id=?", (group_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def update_kingdom(group_id: int, **kwargs):
    if not kwargs:
        return
    cols = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [group_id]
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(f"UPDATE kingdoms SET {cols} WHERE group_id=?", vals)
        await db.commit()

async def get_kingdom_members(kingdom_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM players WHERE kingdom_id=?", (kingdom_id,)
        ) as cur:
            return await cur.fetchall()

# ──────────────────────────────────────────────
# War helpers
# ──────────────────────────────────────────────
async def add_war(attacker_id, defender_id, attacker_name, defender_name,
                  result, dmg_dealt, dmg_taken, loot_gold):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO wars
               (attacker_id, defender_id, attacker_name, defender_name,
                result, damage_dealt, damage_taken, loot_gold, timestamp)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (attacker_id, defender_id, attacker_name, defender_name,
             result, dmg_dealt, dmg_taken, loot_gold, int(time.time()))
        )
        await db.commit()

async def get_war_history(user_id: int, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM wars
               WHERE attacker_id=? OR defender_id=?
               ORDER BY timestamp DESC LIMIT ?""",
            (user_id, user_id, limit)
        ) as cur:
            return await cur.fetchall()

async def get_all_wars(limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM wars ORDER BY timestamp DESC LIMIT ?", (limit,)
        ) as cur:
            return await cur.fetchall()

# ──────────────────────────────────────────────
# Market helpers
# ──────────────────────────────────────────────
async def add_listing(seller_id, seller_name, resource, amount, price):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO market_listings
               (seller_id, seller_name, resource, amount, price, created_at)
               VALUES (?,?,?,?,?,?)""",
            (seller_id, seller_name, resource, amount, price, int(time.time()))
        )
        await db.commit()

async def get_listings(resource: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if resource:
            async with db.execute(
                "SELECT * FROM market_listings WHERE resource=? ORDER BY price ASC LIMIT 20",
                (resource,)
            ) as cur:
                return await cur.fetchall()
        async with db.execute(
            "SELECT * FROM market_listings ORDER BY created_at DESC LIMIT 20"
        ) as cur:
            return await cur.fetchall()

async def delete_listing(listing_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM market_listings WHERE id=?", (listing_id,))
        await db.commit()

async def get_listing_by_id(listing_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM market_listings WHERE id=?", (listing_id,)
        ) as cur:
            return await cur.fetchone()

# ──────────────────────────────────────────────
# Kingdom War helpers
# ──────────────────────────────────────────────
async def add_kingdom_war(
    attacker_kingdom_id, defender_kingdom_id,
    attacker_name, defender_name,
    result, attacker_power, defender_power,
    loot_gold, loot_wood, loot_stone, loot_food, loot_iron
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """INSERT INTO kingdom_wars
               (attacker_kingdom_id, defender_kingdom_id,
                attacker_name, defender_name, result,
                attacker_power, defender_power,
                loot_gold, loot_wood, loot_stone, loot_food, loot_iron,
                timestamp)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (attacker_kingdom_id, defender_kingdom_id,
             attacker_name, defender_name, result,
             attacker_power, defender_power,
             loot_gold, loot_wood, loot_stone, loot_food, loot_iron,
             int(time.time()))
        )
        await db.commit()

async def get_kingdom_wars(kingdom_id: int, limit=10):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM kingdom_wars
               WHERE attacker_kingdom_id=? OR defender_kingdom_id=?
               ORDER BY timestamp DESC LIMIT ?""",
            (kingdom_id, kingdom_id, limit)
        ) as cur:
            return await cur.fetchall()

async def get_last_war_between(attacker_id: int, defender_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT * FROM kingdom_wars
               WHERE attacker_kingdom_id=? AND defender_kingdom_id=?
               ORDER BY timestamp DESC LIMIT 1""",
            (attacker_id, defender_id)
        ) as cur:
            return await cur.fetchone()

async def get_all_kingdom_wars(limit=20):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM kingdom_wars ORDER BY timestamp DESC LIMIT ?", (limit,)
        ) as cur:
            return await cur.fetchall()
