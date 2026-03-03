import ssl

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.config import get_settings

settings = get_settings()

POC_MODE = settings.database_url.startswith("sqlite")

if POC_MODE:
    _sqlite_args = {"check_same_thread": False, "timeout": 30}
    cx_engine = create_async_engine(
        settings.database_url, echo=False, connect_args=_sqlite_args,
    )
    customer_engine = create_async_engine(
        settings.customer_db_url, echo=False, connect_args=_sqlite_args,
    )
else:
    _pg_connect_args: dict = {}
    if settings.database_ssl:
        _ssl_ctx = ssl.create_default_context()
        if settings.database_ssl == "require":
            _ssl_ctx.check_hostname = False
            _ssl_ctx.verify_mode = ssl.CERT_NONE
        _pg_connect_args["ssl"] = _ssl_ctx

    cx_engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_pre_ping=True,
        connect_args=_pg_connect_args,
    )
    customer_engine = create_async_engine(
        settings.customer_db_url,
        echo=False,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_pre_ping=True,
        connect_args=_pg_connect_args,
    )

CxSessionLocal = async_sessionmaker(cx_engine, class_=AsyncSession, expire_on_commit=False)
CustomerSessionLocal = async_sessionmaker(customer_engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class CustomerBase(DeclarativeBase):
    pass


async def get_cx_db() -> AsyncSession:
    async with CxSessionLocal() as session:
        yield session


async def get_customer_db() -> AsyncSession:
    async with CustomerSessionLocal() as session:
        yield session


async def init_db():
    """Create all tables (used in POC/SQLite mode)."""
    async with cx_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with customer_engine.begin() as conn:
        await conn.run_sync(CustomerBase.metadata.create_all)
