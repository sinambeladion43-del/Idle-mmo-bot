import logging
import asyncio
from telegram.error import Conflict
from telegram.ext import (
    Application, CommandHandler,
    filters, CallbackQueryHandler
)
from config import BOT_TOKEN
from database import init_db
from handlers import (
    kwar_handlers,
    player_handlers,
    building_handlers,
    battle_handlers,
    kingdom_handlers,
    economy_handlers,
    admin_handlers,
    help_handlers,
)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application):
    await init_db()
    logger.info("Database initialized successfully")


def build_app() -> Application:
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start",       help_handlers.start))
    app.add_handler(CommandHandler("help",        help_handlers.help_command))
    app.add_handler(CommandHandler("tutorial",    help_handlers.tutorial))
    app.add_handler(CommandHandler("commands",    help_handlers.commands_list))

    app.add_handler(CommandHandler("profile",     player_handlers.profile))
    app.add_handler(CommandHandler("daily",       player_handlers.daily))
    app.add_handler(CommandHandler("leaderboard", player_handlers.leaderboard))
    app.add_handler(CommandHandler("inventory",   player_handlers.inventory))

    app.add_handler(CommandHandler("build",       building_handlers.build))
    app.add_handler(CommandHandler("status",      building_handlers.status))
    app.add_handler(CommandHandler("collect",     building_handlers.collect))
    app.add_handler(CommandHandler("buildings",   building_handlers.list_buildings))

    app.add_handler(CommandHandler("attack",      battle_handlers.attack))
    app.add_handler(CommandHandler("defend",      battle_handlers.defend))
    app.add_handler(CommandHandler("war",         battle_handlers.war_history))

    app.add_handler(CommandHandler("kingdom",     kingdom_handlers.kingdom))
    app.add_handler(CommandHandler("join",        kingdom_handlers.join))
    app.add_handler(CommandHandler("leave",       kingdom_handlers.leave))
    app.add_handler(CommandHandler("contribute",  kingdom_handlers.contribute))
    app.add_handler(CommandHandler("kadmin",      kingdom_handlers.kadmin))

    app.add_handler(CommandHandler("market",      economy_handlers.market))
    app.add_handler(CommandHandler("trade",       economy_handlers.trade))
    app.add_handler(CommandHandler("resources",   economy_handlers.resources))

    app.add_handler(CommandHandler("admin",       admin_handlers.admin))

    # ── Kingdom War ──────────────────────────────────────────────
    app.add_handler(CommandHandler("kwar",        kwar_handlers.kwar))

    app.add_handler(CallbackQueryHandler(building_handlers.build_callback,  pattern="^build_"))
    app.add_handler(CallbackQueryHandler(economy_handlers.market_callback,  pattern="^market_"))
    app.add_handler(CallbackQueryHandler(kingdom_handlers.kingdom_callback, pattern="^kingdom_"))
    app.add_handler(CallbackQueryHandler(help_handlers.help_callback,       pattern="^help_"))
    app.add_handler(CallbackQueryHandler(battle_handlers.battle_callback,   pattern="^battle_"))
    app.add_handler(CallbackQueryHandler(kwar_handlers.kwar_callback,        pattern="^kwar_"))

    return app


def main():
    max_retries = 5
    retry_delay = 10  # seconds

    for attempt in range(1, max_retries + 1):
        try:
            logger.info(f"🏰 Idle MMO Bot starting… (attempt {attempt}/{max_retries})")
            app = build_app()
            app.run_polling(
                drop_pending_updates=True,
                allowed_updates=["message", "callback_query"],
            )
            break

        except Conflict:
            if attempt < max_retries:
                logger.warning(
                    f"⚠️  Conflict: another bot instance detected. "
                    f"Retrying in {retry_delay}s… ({attempt}/{max_retries})"
                )
                asyncio.run(asyncio.sleep(retry_delay))
            else:
                logger.error("❌ Max retries reached. Exiting.")
                raise

        except Exception as e:
            logger.error(f"❌ Unexpected error: {e}")
            raise


if __name__ == "__main__":
    main()
