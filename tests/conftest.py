import asyncio
import os
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database import Base, CustomerBase, get_customer_db, get_cx_db
from src.main import app

TEST_CX_DB = os.environ.get(
    "TEST_DATABASE_URL",
    "mysql+aiomysql://mcdr:mcdr_pass@localhost:3306/test_mcdr_cx",
)
TEST_CUSTOMER_DB = os.environ.get(
    "TEST_CUSTOMER_DB_URL",
    "mysql+aiomysql://mcdr:mcdr_pass@localhost:3306/test_mcdr_customer",
)

cx_engine = create_async_engine(TEST_CX_DB, echo=False)
customer_engine = create_async_engine(TEST_CUSTOMER_DB, echo=False)

CxTestSession = async_sessionmaker(cx_engine, class_=AsyncSession, expire_on_commit=False)
CustomerTestSession = async_sessionmaker(customer_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with cx_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with customer_engine.begin() as conn:
        await conn.run_sync(CustomerBase.metadata.create_all)
    yield
    async with cx_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    async with customer_engine.begin() as conn:
        await conn.run_sync(CustomerBase.metadata.drop_all)


async def override_cx_db() -> AsyncGenerator[AsyncSession, None]:
    async with CxTestSession() as session:
        yield session


async def override_customer_db() -> AsyncGenerator[AsyncSession, None]:
    async with CustomerTestSession() as session:
        yield session


app.dependency_overrides[get_cx_db] = override_cx_db
app.dependency_overrides[get_customer_db] = override_customer_db


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def cx_db() -> AsyncGenerator[AsyncSession, None]:
    async with CxTestSession() as session:
        yield session
