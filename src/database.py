import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import get_settings

logger = logging.getLogger("mcdr.database")
settings = get_settings()

_engine_kwargs = {
    "echo": False,
    "pool_size": 20,
    "max_overflow": 10,
    "pool_timeout": 30,
    "pool_recycle": 3600,
    "pool_pre_ping": True,
}

cx_engine = create_async_engine(settings.database_url, **_engine_kwargs)
customer_engine = create_async_engine(
    settings.customer_db_url,
    echo=False,
    pool_size=5,
    max_overflow=2,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
)

CxSessionLocal = async_sessionmaker(cx_engine, class_=AsyncSession, expire_on_commit=False)
CustomerSessionLocal = async_sessionmaker(customer_engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class CustomerBase(DeclarativeBase):
    pass


async def get_cx_db() -> AsyncSession:
    async with CxSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def get_customer_db() -> AsyncSession:
    async with CustomerSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables from ORM metadata."""
    try:
        async with cx_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with customer_engine.begin() as conn:
            await conn.run_sync(CustomerBase.metadata.create_all)
    except Exception as e:
        logger.error("Database initialization failed: %s", e, exc_info=True)
        raise
