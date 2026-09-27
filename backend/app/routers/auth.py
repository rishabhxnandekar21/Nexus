"""Login and current-user routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_current_user, verify_password
from app.database import get_db
from app.models import Agency, User
from app.schemas import TokenResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(db: Session, user: User) -> UserOut:
    """Attach the agency's code and name, which the nav bar displays."""
    agency = db.get(Agency, user.agency_id)
    if agency is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"user {user.id} references agency {user.agency_id}, which does not exist",
        )
    return UserOut(
        id=user.id,
        username=user.username,
        role=user.role,
        agency_id=user.agency_id,
        agency_code=agency.code,
        agency_name=agency.name,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Form body, per CLAUDE.md Section 6. Returns the token and the user."""
    user = db.scalar(select(User).where(User.username == form.username))
    if user is None or not verify_password(form.password, user.password_hash):
        # Deliberately the same message either way, so the response does not
        # reveal which usernames exist.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(access_token=create_access_token(user), user=_user_out(db, user))


@router.get("/me", response_model=UserOut)
def me(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserOut:
    """The caller's own record, with role and agency."""
    return _user_out(db, user)
