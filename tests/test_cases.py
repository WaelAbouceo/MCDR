import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import create_access_token, hash_password
from src.models.user import Role, User


@pytest.fixture
async def agent_token(cx_db: AsyncSession) -> str:
    role = Role(name="agent", description="Agent role")
    cx_db.add(role)
    await cx_db.flush()

    user = User(
        username="caseagent",
        email="caseagent@test.com",
        hashed_password=hash_password("pass"),
        full_name="Case Agent",
        role_id=role.id,
    )
    cx_db.add(user)
    await cx_db.commit()
    return create_access_token({"sub": str(user.id), "role": "agent"})


@pytest.mark.asyncio
async def test_create_and_get_case(client: AsyncClient, agent_token: str):
    headers = {"Authorization": f"Bearer {agent_token}"}
    create_resp = await client.post(
        "/api/cases",
        json={"subject": "Test dispute", "priority": "high", "description": "Billing issue"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    case_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/cases/{case_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["subject"] == "Test dispute"


@pytest.mark.asyncio
async def test_add_note(client: AsyncClient, agent_token: str):
    headers = {"Authorization": f"Bearer {agent_token}"}
    case = await client.post(
        "/api/cases",
        json={"subject": "Note test", "priority": "medium"},
        headers=headers,
    )
    case_id = case.json()["id"]

    note_resp = await client.post(
        f"/api/cases/{case_id}/notes",
        json={"content": "Customer called back", "is_internal": True},
        headers=headers,
    )
    assert note_resp.status_code == 201
    assert note_resp.json()["is_internal"] is True


@pytest.mark.asyncio
async def test_unauthorized(client: AsyncClient):
    resp = await client.get("/api/cases")
    assert resp.status_code == 403
