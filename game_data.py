"""
Central place for all game balance numbers.
Change values here to rebalance the whole game.
"""

# ── Resources ────────────────────────────────
RESOURCES = ["gold", "wood", "stone", "food", "iron"]
RESOURCE_EMOJI = {
    "gold":  "🪙",
    "wood":  "🪵",
    "stone": "🪨",
    "food":  "🌾",
    "iron":  "⚔️",
}

# ── Buildings ────────────────────────────────
# Each building: cost per level, production per hour per level, build time (sec)
BUILDINGS = {
    "farm": {
        "emoji": "🌾",
        "description": "Menghasilkan Food setiap jam",
        "max_level": 10,
        "cost": lambda lvl: {"gold": 50 * lvl, "wood": 30 * lvl},
        "produces": {"food": 5},          # × level per hour
        "build_time": lambda lvl: 60 * lvl,   # seconds
        "stat_bonus": {},
    },
    "mine": {
        "emoji": "⛏️",
        "description": "Menghasilkan Stone & Iron",
        "max_level": 10,
        "cost": lambda lvl: {"gold": 60 * lvl, "wood": 20 * lvl, "stone": 10 * lvl},
        "produces": {"stone": 4, "iron": 2},
        "build_time": lambda lvl: 90 * lvl,
        "stat_bonus": {},
    },
    "lumbermill": {
        "emoji": "🪵",
        "description": "Menghasilkan Wood",
        "max_level": 10,
        "cost": lambda lvl: {"gold": 40 * lvl, "stone": 20 * lvl},
        "produces": {"wood": 6},
        "build_time": lambda lvl: 60 * lvl,
        "stat_bonus": {},
    },
    "barracks": {
        "emoji": "⚔️",
        "description": "Meningkatkan Attack Power",
        "max_level": 10,
        "cost": lambda lvl: {"gold": 80 * lvl, "wood": 40 * lvl, "stone": 40 * lvl},
        "produces": {},
        "build_time": lambda lvl: 120 * lvl,
        "stat_bonus": {"attack_pow": 5},  # × level
    },
    "wall": {
        "emoji": "🛡️",
        "description": "Meningkatkan Defense Power",
        "max_level": 10,
        "cost": lambda lvl: {"gold": 70 * lvl, "stone": 60 * lvl},
        "produces": {},
        "build_time": lambda lvl: 120 * lvl,
        "stat_bonus": {"defense_pow": 5},
    },
    "market": {
        "emoji": "🏪",
        "description": "Buka akses Market & kurangi biaya trading",
        "max_level": 5,
        "cost": lambda lvl: {"gold": 100 * lvl, "wood": 50 * lvl, "stone": 50 * lvl},
        "produces": {"gold": 3},
        "build_time": lambda lvl: 180 * lvl,
        "stat_bonus": {},
    },
    "castle": {
        "emoji": "🏰",
        "description": "Meningkatkan level max & HP",
        "max_level": 5,
        "cost": lambda lvl: {"gold": 200 * lvl, "wood": 100 * lvl, "stone": 100 * lvl, "iron": 50 * lvl},
        "produces": {},
        "build_time": lambda lvl: 300 * lvl,
        "stat_bonus": {"max_hp": 50, "attack_pow": 2, "defense_pow": 2},
    },
}

# ── EXP & Leveling ───────────────────────────
def exp_needed(level: int) -> int:
    return 100 * level * level

# ── Daily Reward ─────────────────────────────
DAILY_REWARD = {"gold": 100, "wood": 30, "stone": 30, "food": 50}
DAILY_COOLDOWN = 86400   # 24 h in seconds

# ── Battle ───────────────────────────────────
ATTACK_COOLDOWN = 3600   # 1 hour between attacks on same target
LOOT_PERCENT    = 0.10   # 10 % of defender gold looted on win

# ── Collection ───────────────────────────────
MAX_COLLECT_HOURS = 12   # Resources cap at 12 h of production

# ── Market ───────────────────────────────────
MARKET_FEE = 0.05        # 5 % fee on sales

# ── Kingdom ──────────────────────────────────
KINGDOM_CONTRIBUTE_MIN = 10   # Minimum resource per contribution
