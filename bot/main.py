"""Entry point — STAR VPN Telegram bot + Mini App API."""

import asyncio
import logging

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage

from bot.api import app as fastapi_app
from bot.config import settings
from bot.utils.database import init_db, AsyncSessionLocal
from bot.utils import admin_auth
from bot.middlewares.db import DbSessionMiddleware
from bot.middlewares.ban import BanMiddleware
from bot.handlers import admin, start, payment, profile, referral, instructions, gift, devices, crypto_payment, card_payment, support
from bot.tasks.scheduler import scheduler_loop

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    await init_db()
    logger.info("Database initialized.")

    async with AsyncSessionLocal() as session:
        await admin_auth.load_sessions_cache(session)
    logger.info("Admin sessions cache warmed.")

    bot = Bot(
        token=settings.telegram_api_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Middlewares
    dp.message.middleware(DbSessionMiddleware())
    dp.callback_query.middleware(DbSessionMiddleware())
    dp.pre_checkout_query.middleware(DbSessionMiddleware())
    dp.message.middleware(BanMiddleware())
    dp.callback_query.middleware(BanMiddleware())

    # Routers
    dp.include_router(admin.router)
    dp.include_router(devices.router)
    dp.include_router(gift.router)
    dp.include_router(start.router)
    dp.include_router(support.router)
    dp.include_router(payment.router)
    dp.include_router(profile.router)
    dp.include_router(referral.router)
    dp.include_router(instructions.router)
    dp.include_router(crypto_payment.router)
    dp.include_router(card_payment.router)

    # FastAPI (Mini App API) — порт 8080
    api_config = uvicorn.Config(
        fastapi_app,
        host="0.0.0.0",
        port=8080,
        log_level="warning",
        access_log=False,
    )
    api_server = uvicorn.Server(api_config)

    logger.info("STAR VPN bot + API + Scheduler starting (API on :8080)...")
    await asyncio.gather(
        dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types()),
        api_server.serve(),
        scheduler_loop(bot),
    )


if __name__ == "__main__":
    asyncio.run(main())
