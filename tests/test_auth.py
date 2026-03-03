import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.models.user import Role, User


@pytest.fixture
async def seeded_user(cx_db: AsyncSession):
    role = Role(name="agent", description="Test agent")
    cx_db.add(role)
    await cx_db.flush()

    user = User(
        username="testagent",
        email="agent@test.com",
        hashed_password=hash_password("pass123"),
        full_name="Test Agent",
        role_id=role.id,
    )
    cx_db.add(user)
    await cx_db.commit()
    return user


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, seeded_user):
    resp = await client.post("/api/auth/login", json={"username": "testagent", "password": "pass123"})
    assert resp.status_code == 200
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_bad_password(client: AsyncClient, seeded_user):
    resp = await client.post("/api/auth/login", json={"username": "testagent", "password": "wrong"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
