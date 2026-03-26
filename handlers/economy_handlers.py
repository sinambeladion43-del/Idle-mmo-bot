import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_player, create_player, update_player,
    add_listing, get_listings, delete_listing, get_listing_by_id
)
from game_data import RESOURCES, RESOURCE_EMOJI, MARKET_FEE


async def _ensure_player(update: Update):
    user = update.effective_user
    await create_player(user.id, user.username or user.first_name)
    return await get_player(user.id)


# ──────────────────────────────────────────────
async def resources(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    text = (
        f"💰 *Resource: {player['username']}*\n\n"
        f"🪙 Gold  : {player['gold']:,}\n"
        f"🪵 Wood  : {player['wood']:,}\n"
        f"🪨 Stone : {player['stone']:,}\n"
        f"🌾 Food  : {player['food']:,}\n"
        f"⚔️ Iron  : {player['iron']:,}\n\n"
        f"💡 Jual resource: `/market sell [resource] [jumlah] [harga]`"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


# ──────────────────────────────────────────────
async def market(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    args = ctx.args or []

    # /market sell [resource] [amount] [price]
    if args and args[0].lower() == "sell":
        if len(args) < 4:
            await update.message.reply_text(
                "❌ Format: `/market sell [resource] [jumlah] [harga]`\n"
                "Contoh: `/market sell wood 100 500`",
                parse_mode="Markdown"
            )
            return

        res = args[1].lower()
        if res not in RESOURCES or res == "gold":
            await update.message.reply_text(
                f"❌ Resource tidak valid.\nBisa jual: wood, stone, food, iron"
            )
            return

        try:
            amount = int(args[2])
            price = int(args[3])
        except ValueError:
            await update.message.reply_text("❌ Jumlah dan harga harus angka.")
            return

        if amount <= 0 or price <= 0:
            await update.message.reply_text("❌ Jumlah dan harga harus lebih dari 0.")
            return

        if player[res] < amount:
            await update.message.reply_text(
                f"❌ {res.title()} tidak cukup!\nKamu punya: {player[res]:,}"
            )
            return

        # Deduct resource & create listing
        await update_player(player["user_id"], **{res: player[res] - amount})
        await add_listing(player["user_id"], player["username"], res, amount, price)

        emoji = RESOURCE_EMOJI.get(res, "•")
        await update.message.reply_text(
            f"✅ *Listing Ditambahkan!*\n\n"
            f"{emoji} {amount:,} {res.title()} — 🪙 {price:,} Gold\n\n"
            f"Orang lain bisa beli dengan `/market buy [ID]`",
            parse_mode="Markdown"
        )
        return

    # /market buy [id]
    if args and args[0].lower() == "buy":
        if len(args) < 2:
            await update.message.reply_text(
                "❌ Format: `/market buy [ID]`\n"
                "Lihat ID listing dengan `/market`",
                parse_mode="Markdown"
            )
            return

        try:
            listing_id = int(args[1])
        except ValueError:
            await update.message.reply_text("❌ ID harus berupa angka.")
            return

        listing = await get_listing_by_id(listing_id)
        if not listing:
            await update.message.reply_text("❌ Listing tidak ditemukan atau sudah terjual.")
            return

        if listing["seller_id"] == player["user_id"]:
            await update.message.reply_text("❌ Kamu tidak bisa membeli listingmu sendiri.")
            return

        if player["gold"] < listing["price"]:
            await update.message.reply_text(
                f"❌ Gold tidak cukup!\n"
                f"Harga: {listing['price']:,} | Kamu punya: {player['gold']:,}"
            )
            return

        # Execute purchase
        res = listing["resource"]
        fee = int(listing["price"] * MARKET_FEE)
        seller_receive = listing["price"] - fee

        # Update buyer
        await update_player(
            player["user_id"],
            gold=player["gold"] - listing["price"],
            **{res: player[res] + listing["amount"]}
        )

        # Update seller
        import aiosqlite, os
        DB_PATH = os.environ.get("DB_PATH", "./game.db")
        async with aiosqlite.connect(DB_PATH) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM players WHERE user_id=?", (listing["seller_id"],)) as cur:
                seller = await cur.fetchone()
        if seller:
            await update_player(seller["user_id"], gold=seller["gold"] + seller_receive)

        await delete_listing(listing_id)

        emoji = RESOURCE_EMOJI.get(res, "•")
        await update.message.reply_text(
            f"✅ *Pembelian Berhasil!*\n\n"
            f"{emoji} +{listing['amount']:,} {res.title()}\n"
            f"🪙 -{listing['price']:,} Gold (fee: {fee:,})\n\n"
            f"Dibeli dari: {listing['seller_name']}",
            parse_mode="Markdown"
        )
        return

    # /market — show listings
    listings = await get_listings()
    if not listings:
        await update.message.reply_text(
            "🏪 *MARKET*\n\nBelum ada listing.\n"
            "Jual resource kamu: `/market sell wood 100 500`",
            parse_mode="Markdown"
        )
        return

    lines = ["🏪 *MARKET GLOBAL*\n"]
    for l in listings[:15]:
        emoji = RESOURCE_EMOJI.get(l["resource"], "•")
        lines.append(
            f"[#{l['id']}] {emoji} {l['amount']:,} {l['resource'].title()} "
            f"— 🪙 {l['price']:,} Gold\n"
            f"   Penjual: {l['seller_name']}"
        )

    lines.append(
        "\n📌 Beli: `/market buy [ID]`\n"
        "📌 Jual: `/market sell [resource] [jumlah] [harga]`"
    )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ──────────────────────────────────────────────
async def trade(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    player = await _ensure_player(update)
    if player["is_banned"]:
        await update.message.reply_text("🚫 Akun kamu di-ban.")
        return

    if not ctx.args or len(ctx.args) < 4:
        await update.message.reply_text(
            "🔄 *Cara Trade Langsung:*\n"
            "`/trade @username [offer_resource] [offer_amt] [want_resource] [want_amt]`\n\n"
            "Contoh:\n`/trade @player wood 100 gold 500`\n"
            "= Tawarkan 100 Wood, minta 500 Gold",
            parse_mode="Markdown"
        )
        return

    target_uname = ctx.args[0].lstrip("@")
    if len(ctx.args) < 5:
        await update.message.reply_text(
            "❌ Format: `/trade @username [offer_res] [offer_amt] [want_res] [want_amt]`",
            parse_mode="Markdown"
        )
        return

    offer_res = ctx.args[1].lower()
    want_res  = ctx.args[3].lower()

    if offer_res not in RESOURCES or want_res not in RESOURCES:
        await update.message.reply_text(
            f"❌ Resource tidak valid.\nPilih dari: {', '.join(RESOURCES)}"
        )
        return

    try:
        offer_amt = int(ctx.args[2])
        want_amt  = int(ctx.args[4])
    except ValueError:
        await update.message.reply_text("❌ Jumlah harus berupa angka.")
        return

    if offer_amt <= 0 or want_amt <= 0:
        await update.message.reply_text("❌ Jumlah harus lebih dari 0.")
        return

    if player[offer_res] < offer_amt:
        await update.message.reply_text(
            f"❌ {offer_res.title()} tidak cukup!\nKamu punya: {player[offer_res]:,}"
        )
        return

    # Find target
    import aiosqlite, os
    DB_PATH = os.environ.get("DB_PATH", "./game.db")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM players WHERE username=? AND is_banned=0", (target_uname,)
        ) as cur:
            target = await cur.fetchone()

    if not target:
        await update.message.reply_text(f"❌ Pemain *{target_uname}* tidak ditemukan.", parse_mode="Markdown")
        return

    if target["user_id"] == player["user_id"]:
        await update.message.reply_text("❌ Kamu tidak bisa trade dengan diri sendiri.")
        return

    if target[want_res] < want_amt:
        await update.message.reply_text(
            f"❌ {target_uname} tidak punya cukup {want_res}!\n"
            f"Mereka punya: {target[want_res]:,}"
        )
        return

    # Execute direct trade
    await update_player(
        player["user_id"],
        **{
            offer_res: player[offer_res] - offer_amt,
            want_res:  player[want_res]  + want_amt,
        }
    )
    await update_player(
        target["user_id"],
        **{
            want_res:  target[want_res]  - want_amt,
            offer_res: target[offer_res] + offer_amt,
        }
    )

    offer_emoji = RESOURCE_EMOJI.get(offer_res, "•")
    want_emoji  = RESOURCE_EMOJI.get(want_res,  "•")
    await update.message.reply_text(
        f"✅ *Trade Berhasil!*\n\n"
        f"Kamu → {target_uname}: {offer_emoji} {offer_amt:,} {offer_res.title()}\n"
        f"{target_uname} → Kamu: {want_emoji} {want_amt:,} {want_res.title()}",
        parse_mode="Markdown"
    )


# ──────────────────────────────────────────────
async def market_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🏪 Gunakan `/market` untuk melihat semua listing.",
        parse_mode="Markdown"
    )
