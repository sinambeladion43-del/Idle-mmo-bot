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
            gold        INTEGER DEFAULT 200,
            wood        INTEGER DEFAULT 200,
            stone       INTEGER DEFAULT 200,
            food        INTEGER DEFAULT 200,
            iron        INTEGER DEFAULT 200,
            attack_pow  INTEGER DEFAULT 10,
            defense_pow INTEGER DEFAULT 10,
            hp          INTEGER DEFAULT 100,
            max_hp      INTEGER DEFAULT 100,
            last_daily  INTEGER DEFAULT 0,
            last_collect INTEGER DEFAULT 0,
            last_setname INTEGER DEFAULT 0,
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
            iron        INTEGER DEFAULT 200,
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

        CREATE TABLE IF NOT EXISTS alliances (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            name                TEXT UNIQUE,
            founder_kingdom_id  INTEGER,
            created_at          INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS alliance_members (
            alliance_id  INTEGER,
            kingdom_id   INTEGER,
            role         TEXT DEFAULT 'member',
            joined_at    INTEGER DEFAULT 0,
            PRIMARY KEY (alliance_id, kingdom_id)
        );

        CREATE TABLE IF NOT EXISTS alliance_invites (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            alliance_id         INTEGER,
            from_kingdom_id     INTEGER,
            target_kingdom_id   INTEGER,
            status              TEXT DEFAULT 'pending',
            created_at          INTEGER DEFAULT 0
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

        # Migration: tambah kolom last_setname jika belum ada (untuk DB lama)
        try:
            await db.execute("ALTER TABLE players ADD COLUMN last_setname INTEGER DEFAULT 0")
            await db.commit()
        except Exception:
            pass  # Kolom sudah ada, skip

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

# ──────────────────────────────────────────────
# Alliance helpers
# ──────────────────────────────────────────────
async def get_alliance(kingdom_id: int):
    """Get alliance that this kingdom belongs to."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT a.* FROM alliances a
               JOIN alliance_members am ON a.id = am.alliance_id
               WHERE am.kingdom_id=?""",
            (kingdom_id,)
        ) as cur:
            return await cur.fetchone()

async def get_alliance_by_id(alliance_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM alliances WHERE id=?", (alliance_id,)) as cur:
            return await cur.fetchone()

async def get_alliance_members(alliance_id: int):
    """Get all kingdoms in an alliance."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT k.*, am.role as alliance_role
               FROM kingdoms k
               JOIN alliance_members am ON k.id = am.kingdom_id
               WHERE am.alliance_id=?""",
            (alliance_id,)
        ) as cur:
            return await cur.fetchall()

async def create_alliance(name: str, founder_kingdom_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO alliances (name, founder_kingdom_id, created_at) VALUES (?,?,?)",
            (name, founder_kingdom_id, int(time.time()))
        )
        await db.commit()
        async with db.execute("SELECT id FROM alliances WHERE founder_kingdom_id=? ORDER BY id DESC LIMIT 1",
                              (founder_kingdom_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def add_alliance_member(alliance_id: int, kingdom_id: int, role: str = "member"):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR REPLACE INTO alliance_members (alliance_id, kingdom_id, role, joined_at) VALUES (?,?,?,?)",
            (alliance_id, kingdom_id, role, int(time.time()))
        )
        await db.commit()

async def remove_alliance_member(alliance_id: int, kingdom_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM alliance_members WHERE alliance_id=? AND kingdom_id=?",
            (alliance_id, kingdom_id)
        )
        await db.commit()

async def delete_alliance(alliance_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM alliance_members WHERE alliance_id=?", (alliance_id,))
        await db.execute("DELETE FROM alliances WHERE id=?", (alliance_id,))
        await db.commit()

async def get_alliance_invite(kingdom_id: int):
    """Get pending invite for a kingdom."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM alliance_invites WHERE target_kingdom_id=? AND status='pending'",
            (kingdom_id,)
        ) as cur:
            return await cur.fetchone()

async def create_alliance_invite(alliance_id: int, from_kingdom_id: int, target_kingdom_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        # Remove old invite first
        await db.execute(
            "DELETE FROM alliance_invites WHERE target_kingdom_id=? AND alliance_id=?",
            (target_kingdom_id, alliance_id)
        )
        await db.execute(
            "INSERT INTO alliance_invites (alliance_id, from_kingdom_id, target_kingdom_id, status, created_at) VALUES (?,?,?,?,?)",
            (alliance_id, from_kingdom_id, target_kingdom_id, "pending", int(time.time()))
        )
        await db.commit()

async def update_alliance_invite(invite_id: int, status: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE alliance_invites SET status=? WHERE id=?", (status, invite_id))
        await db.commit()

async def get_all_alliances():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM alliances ORDER BY id DESC") as cur:
            return await cur.fetchall()
