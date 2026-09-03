"""
Async SQLAlchemy engine and session factory.
All DB operations must use AsyncSession.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from bot.config import settings
from bot.models.user import Base

# Import all models so their tables are registered with Base.metadata
import bot.models.payment       # noqa: F401
import bot.models.device               # noqa: F401
import bot.models.gift_notification    # noqa: F401
import bot.models.guest_order   # noqa: F401
import bot.models.email_code    # noqa: F401
import bot.models.web_session   # noqa: F401
import bot.models.support_ticket       # noqa: F401
import bot.models.support_ticket_message  # noqa: F401
import bot.models.wiki_article  # noqa: F401
import bot.models.app_setting   # noqa: F401
import bot.models.admin_account # noqa: F401
import bot.models.admin_session # noqa: F401
import bot.models.ad_banner     # noqa: F401
import bot.models.referral_credit  # noqa: F401

engine = create_async_engine(
    settings.sqlalchemy_database_url,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create all tables on startup (idempotent)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
