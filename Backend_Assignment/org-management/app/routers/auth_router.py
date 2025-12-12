from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from ..db import db
from ..schemas import AdminLoginRequest, TokenResponse
from ..services.auth_service import AuthService

router = APIRouter(prefix="/admin", tags=["auth"])


async def get_auth_service() -> AuthService:
    master_db = db.get_master_db()
    return AuthService(master_db["organizations"])


@router.post("/login", response_model=TokenResponse)
async def login(payload: AdminLoginRequest):
    service = await get_auth_service()
    try:
        org = await service.authenticate_admin(payload.email, payload.password)
    except PermissionError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    token = await service.issue_token(payload.email, org["organization_name"])
    return TokenResponse(access_token=token)


