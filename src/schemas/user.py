from pydantic import BaseModel, Field


class RoleOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=2, max_length=100)
    tier: str = "tier1"
    role_id: int = Field(ge=1)


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    tier: str | None = None
    role_id: int | None = Field(default=None, ge=1)
    is_active: bool | None = None


class UserOut(BaseModel):
    id: int
    username: str
    email: str | None = None
    full_name: str
    tier: str | None = None
    is_active: int | bool = True
    role: RoleOut
    created_at: str | None = None
    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int | None = None


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)
