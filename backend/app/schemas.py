"""Pydantic request and response models.

Shared file. W1-6 writes the contract for every remaining endpoint in CLAUDE.md
Section 6 - please ADD to this file rather than recreating it. The models below
already back POST /api/auth/login and GET /api/auth/me.
"""

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    """The current user with their agency resolved, as GET /auth/me returns it."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    agency_id: int
    agency_code: str
    agency_name: str


class LoginRequest(BaseModel):
    """Documented for completeness only.

    The login route takes an OAuth2 form body, not JSON, because CLAUDE.md
    Section 6 specifies a form body. This model exists so the contract is
    written down in one place.
    """

    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
